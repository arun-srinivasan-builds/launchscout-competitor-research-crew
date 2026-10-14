"""Run event capture: CrewAI event bus -> typed `RunEvent`s -> thread-safe log + JSONL file.

Only real events are recorded. Summaries are short and redacted; raw model reasoning and
prompt/response bodies are never stored (PRP G9).
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from launchscout.logging_utils import get_logger, redact
from launchscout.progress import EventKind, RunEvent

log = get_logger(__name__)

_MAX_SUMMARY = 180


def _clip(text: str, limit: int = _MAX_SUMMARY) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _tool_argument(tool_args: Any) -> str:
    """Best short argument (query / URL / filename) from CrewAI's `tool_args`."""
    data = tool_args
    if isinstance(tool_args, str):
        try:
            data = json.loads(tool_args)
        except ValueError:
            return _clip(tool_args, 120)
    if isinstance(data, dict):
        for key in ("search_query", "query", "website_url", "url", "filename"):
            if data.get(key):
                return _clip(str(data[key]), 120)
    return ""


class EventCollector:
    """Per-run event log. Thread-safe; mirrors every event to `events.jsonl` when given."""

    def __init__(self, jsonl_path: Path | None = None, clock: Callable[[], datetime] | None = None):
        self._lock = threading.Lock()
        self._events: list[RunEvent] = []
        self._path = jsonl_path
        self._clock = clock or (lambda: datetime.now(UTC))
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.llm_calls = 0
        self.usage_reported = False

    def emit(
        self,
        kind: EventKind,
        summary: str = "",
        agent: str | None = None,
        task: str | None = None,
        status: str = "info",
        ts: datetime | None = None,
        **data: str | int | float | bool | None,
    ) -> RunEvent:
        event = RunEvent(
            ts=ts or self._clock(),
            kind=kind,
            agent=agent,
            task=task,
            status=status,  # type: ignore[arg-type]
            summary=redact(_clip(summary)),
            data={k: (redact(v) if isinstance(v, str) else v) for k, v in data.items()},
        )
        with self._lock:
            self._events.append(event)
            if self._path is not None:
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(event.model_dump_json() + "\n")
        return event

    def add_usage(self, usage: Any) -> None:
        """Accumulate provider-reported token usage (measured only)."""

        def pick(name: str) -> int:
            value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
            return int(value) if isinstance(value, int | float) else 0

        prompt, completion, total = (
            pick("prompt_tokens"),
            pick("completion_tokens"),
            pick("total_tokens"),
        )
        if not (prompt or completion or total):
            return
        with self._lock:
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.total_tokens += total or (prompt + completion)
            self.llm_calls += 1
            self.usage_reported = True

    def events(self) -> list[RunEvent]:
        with self._lock:
            return list(self._events)


def load_events(path: Path) -> list[RunEvent]:
    """Read a run's `events.jsonl` (used to restore state after a restart)."""
    if not path.is_file():
        return []
    out: list[RunEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(RunEvent.model_validate_json(line))
            except ValueError:
                log.warning("skipping unreadable event line")
    return out


# ---- CrewAI event-bus bridge -------------------------------------------------------------

_active: EventCollector | None = None
_active_lock = threading.Lock()
_installed = False


def set_active_collector(collector: EventCollector | None) -> None:
    global _active
    with _active_lock:
        _active = collector


def _current() -> EventCollector | None:
    with _active_lock:
        return _active


_TASK_ROLES = {
    "Competitor research": "Market Researcher",
    "Customer review analysis": "Review Analyst",
    "Strategy and positioning": "Strategy Analyst",
    "Report writing": "Report Writer",
}


def _role(event: Any) -> str | None:
    """Agent role from the event, falling back to the agent object or the task name."""
    role = getattr(event, "agent_role", None)
    if not role:
        role = getattr(getattr(event, "agent", None), "role", None)
    if not role:
        role = _TASK_ROLES.get(str(getattr(event, "task_name", "") or ""))
    return str(role) if role else None


def install_listeners() -> None:
    """Register CrewAI event handlers once per process; they feed the active collector."""
    global _installed
    if _installed:
        return
    from crewai.events import crewai_event_bus as bus
    from crewai.events.types.agent_events import (
        AgentExecutionCompletedEvent,
        AgentExecutionErrorEvent,
        AgentExecutionStartedEvent,
    )
    from crewai.events.types.crew_events import (
        CrewKickoffCompletedEvent,
        CrewKickoffFailedEvent,
        CrewKickoffStartedEvent,
    )
    from crewai.events.types.llm_events import LLMCallCompletedEvent
    from crewai.events.types.task_events import (
        TaskCompletedEvent,
        TaskFailedEvent,
        TaskStartedEvent,
    )
    from crewai.events.types.tool_usage_events import (
        ToolUsageErrorEvent,
        ToolUsageFinishedEvent,
        ToolUsageStartedEvent,
    )

    def on(event_type: type) -> Callable[[Callable[[Any, Any], None]], Any]:
        def register(fn: Callable[[Any, Any], None]) -> Any:
            def guarded(source: Any, event: Any) -> None:
                collector = _current()
                if collector is None:
                    return
                try:
                    fn(collector, event)
                except Exception:  # noqa: BLE001 - a listener must never break the crew
                    log.warning("event listener error for %s", event_type.__name__)

            bus.on(event_type)(guarded)
            return fn

        return register

    @on(CrewKickoffStartedEvent)
    def _crew_started(c: EventCollector, e: Any) -> None:
        c.emit("crew_started", "Crew started (sequential)")

    @on(CrewKickoffCompletedEvent)
    def _crew_done(c: EventCollector, e: Any) -> None:
        c.emit("crew_completed", "Crew finished all tasks", status="ok")

    @on(CrewKickoffFailedEvent)
    def _crew_failed(c: EventCollector, e: Any) -> None:
        c.emit("crew_failed", f"Crew failed: {getattr(e, 'error', '')}", status="error")

    @on(TaskStartedEvent)
    def _task_started(c: EventCollector, e: Any) -> None:
        name = getattr(e, "task_name", None) or "task"
        c.emit("task_started", f"Task started: {name}", _role(e), name)

    @on(TaskCompletedEvent)
    def _task_done(c: EventCollector, e: Any) -> None:
        name = getattr(e, "task_name", None) or "task"
        c.emit("task_completed", f"Task complete: {name}", _role(e), name, status="ok")

    @on(TaskFailedEvent)
    def _task_failed(c: EventCollector, e: Any) -> None:
        name = getattr(e, "task_name", None) or "task"
        c.emit(
            "task_failed",
            f"Task failed: {name}: {getattr(e, 'error', '')}",
            _role(e),
            name,
            status="error",
        )

    @on(AgentExecutionStartedEvent)
    def _agent_started(c: EventCollector, e: Any) -> None:
        c.emit("agent_started", f"{_role(e) or 'Agent'} started", _role(e))

    @on(AgentExecutionCompletedEvent)
    def _agent_done(c: EventCollector, e: Any) -> None:
        c.emit("tool_note", f"{_role(e) or 'Agent'} produced its answer", _role(e), status="ok")

    @on(AgentExecutionErrorEvent)
    def _agent_err(c: EventCollector, e: Any) -> None:
        c.emit(
            "agent_failed",
            f"{_role(e) or 'Agent'} error: {getattr(e, 'error', '')}",
            _role(e),
            status="error",
        )

    @on(ToolUsageStartedEvent)
    def _tool_started(c: EventCollector, e: Any) -> None:
        tool = str(getattr(e, "tool_name", "tool"))
        arg = _tool_argument(getattr(e, "tool_args", None))
        c.emit("tool_started", f"{tool}: {arg}" if arg else tool, _role(e), tool=tool, arg=arg)

    @on(ToolUsageFinishedEvent)
    def _tool_finished(c: EventCollector, e: Any) -> None:
        tool = str(getattr(e, "tool_name", "tool"))
        cached = bool(getattr(e, "from_cache", False))
        c.emit(
            "tool_finished",
            f"{tool} finished" + (" (cache)" if cached else ""),
            _role(e),
            status="ok",
            tool=tool,
            from_cache=cached,
        )

    @on(ToolUsageErrorEvent)
    def _tool_error(c: EventCollector, e: Any) -> None:
        tool = str(getattr(e, "tool_name", "tool"))
        c.emit(
            "tool_error",
            f"{tool} error: {getattr(e, 'error', '')}",
            _role(e),
            status="error",
            tool=tool,
        )

    @on(LLMCallCompletedEvent)
    def _llm_done(c: EventCollector, e: Any) -> None:
        c.add_usage(getattr(e, "usage", None))
        c.emit("llm_completed", "Model call completed", _role(e), status="ok")

    _installed = True
