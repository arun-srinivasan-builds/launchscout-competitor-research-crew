"""Run progress model: typed run events and the reducer that turns them into per-agent state.

`AgentState` is the render contract consumed by `ui/workflow.py`. State is derived only from
recorded events; nothing here simulates progress.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

AGENT_KEYS: dict[str, str] = {
    "Market Researcher": "market_researcher",
    "Review Analyst": "review_analyst",
    "Strategy Analyst": "strategy_analyst",
    "Report Writer": "report_writer",
}
AGENT_ORDER: tuple[str, ...] = tuple(AGENT_KEYS.values())

EventKind = Literal[
    "run_started",
    "crew_started",
    "task_started",
    "agent_started",
    "tool_started",
    "tool_finished",
    "tool_error",
    "tool_note",
    "llm_completed",
    "task_completed",
    "task_failed",
    "agent_failed",
    "crew_completed",
    "crew_failed",
    "grounding",
    "run_cancel_requested",
    "run_cancelled",
    "run_timeout",
    "run_budget_stop",
    "run_finished",
]


class RunEvent(BaseModel):
    """One real event. `summary` is a short human-readable line; never model reasoning."""

    ts: datetime
    kind: EventKind
    agent: str | None = None
    task: str | None = None
    status: Literal["info", "ok", "error"] = "info"
    summary: str = ""
    data: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AgentStatus(StrEnum):
    IDLE = "Idle"
    ACTIVE = "Active"
    COMPLETE = "Complete"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass(frozen=True)
class AgentState:
    """Runtime state for one node. Defaults are the truthful pre-run state."""

    status: AgentStatus = AgentStatus.IDLE
    task_label: str = "Awaiting run"
    progress_percent: int | None = None  # None = no measured progress
    events: tuple[str, ...] = ()
    tool_calls: tuple[str, ...] = ()


# CrewAI reports tool names normalised to snake_case; accept either spelling.
_TOOL_LABELS = {
    "search_the_web": "Searching the web",
    "read_web_page": "Reading a web page",
    "write_report_file": "Writing report file",
}
_MAX_EVENT_LINES = 3
_MAX_TOOL_LINES = 3


def _clock(ts: datetime) -> str:
    return ts.astimezone().strftime("%H:%M:%S")


def reduce_events(
    events: Iterable[RunEvent],
    run_active: bool = False,
) -> dict[str, AgentState]:
    """Fold recorded events into one `AgentState` per agent key (deterministic, pure)."""
    status = {key: AgentStatus.IDLE for key in AGENT_ORDER}
    label = {key: ("Queued" if run_active else "Awaiting run") for key in AGENT_ORDER}
    lines: dict[str, list[str]] = {key: [] for key in AGENT_ORDER}
    calls: dict[str, list[str]] = {key: [] for key in AGENT_ORDER}
    run_state: str | None = None
    stopping = False  # cancel/timeout requested: later task/agent errors are the stop itself

    for event in events:
        if event.kind in ("run_cancel_requested", "run_timeout", "run_budget_stop"):
            stopping = True
        if event.kind in ("run_cancelled", "run_timeout", "crew_failed", "run_budget_stop"):
            run_state = event.kind
        key = AGENT_KEYS.get(event.agent or "")
        if key is None:
            continue
        stamp = _clock(event.ts)
        if event.kind in ("agent_started", "task_started"):
            status[key] = AgentStatus.ACTIVE
            label[key] = "Working"
            lines[key].append(f"{stamp} {event.summary}")
        elif event.kind == "tool_started":
            status[key] = AgentStatus.ACTIVE
            tool = str(event.data.get("tool", ""))
            label[key] = _TOOL_LABELS.get(tool.lower().replace(" ", "_"), "Using a tool")
            calls[key].append(f"{stamp} {event.summary}")
        elif event.kind == "tool_note" and event.data.get("outcome") in ("executed", "cache_hit"):
            pass  # measured per call (see metrics); not shown as a card line
        elif event.kind in ("tool_finished", "tool_error", "tool_note"):
            lines[key].append(f"{stamp} {event.summary}")
        elif event.kind == "llm_completed":
            pass
        elif event.kind == "task_completed":
            status[key] = AgentStatus.COMPLETE
            label[key] = "Task complete"
            lines[key].append(f"{stamp} {event.summary}")
        elif event.kind in ("task_failed", "agent_failed"):
            if stopping:
                status[key], label[key] = AgentStatus.CANCELLED, "Cancelled"
            else:
                status[key], label[key] = AgentStatus.FAILED, "Failed"
            lines[key].append(f"{stamp} {event.summary}")

    if run_state in ("run_cancelled", "run_timeout", "crew_failed", "run_budget_stop"):
        for key in AGENT_ORDER:
            if status[key] is AgentStatus.ACTIVE:
                if run_state == "run_budget_stop":
                    status[key], label[key] = AgentStatus.CANCELLED, "Stopped (LLM limit)"
                elif run_state == "run_cancelled":
                    status[key], label[key] = AgentStatus.CANCELLED, "Cancelled"
                elif run_state == "run_timeout":
                    status[key], label[key] = AgentStatus.FAILED, "Timed out"
                else:
                    status[key], label[key] = AgentStatus.FAILED, "Failed"
            elif status[key] is AgentStatus.IDLE:
                label[key] = "Not started"
    elif not run_active:
        for key in AGENT_ORDER:
            if status[key] is AgentStatus.IDLE and any(lines.values()):
                label[key] = "Not started"

    return {
        key: AgentState(
            status=status[key],
            task_label=label[key],
            events=tuple(lines[key][-_MAX_EVENT_LINES:]),
            tool_calls=tuple(calls[key][-_MAX_TOOL_LINES:]),
        )
        for key in AGENT_ORDER
    }


def agent_metrics(events: Iterable[RunEvent]) -> dict[str, dict[str, int | float]]:
    """Per-agent efficiency numbers (LLM calls, tokens, tool outcomes, seconds), from events."""
    out: dict[str, dict[str, int | float]] = {}
    started: dict[str, datetime] = {}

    def row(agent: str | None) -> dict[str, int | float]:
        return out.setdefault(
            agent or "(run)",
            {
                "llm_calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "tool_calls": 0,
                "executed": 0,
                "cache_hits": 0,
                "refused_budget": 0,
                "tool_errors": 0,
                "tool_ms": 0,
                "seconds": 0.0,
            },
        )

    for event in events:
        r = row(event.agent)
        if event.kind == "llm_completed":
            r["llm_calls"] += 1
            for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = event.data.get(name)
                if isinstance(value, int | float):
                    r[name] += int(value)
        elif event.kind == "tool_started":
            r["tool_calls"] += 1
        elif event.kind == "tool_note" and event.data.get("outcome"):
            outcome = str(event.data["outcome"])
            key = {"executed": "executed", "cache_hit": "cache_hits",
                   "refused_budget": "refused_budget", "error": "tool_errors"}.get(outcome)
            if key:
                r[key] += 1
            ms = event.data.get("ms")
            if isinstance(ms, int | float):
                r["tool_ms"] += int(ms)
        elif event.kind == "task_started" and event.agent:
            started[event.agent] = event.ts
        elif event.kind in ("task_completed", "task_failed") and event.agent in started:
            r["seconds"] += round((event.ts - started[event.agent]).total_seconds(), 1)
    return out
