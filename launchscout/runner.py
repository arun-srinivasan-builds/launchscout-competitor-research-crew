"""Background research runs: one active run at a time, observable from Streamlit reruns.

The crew executes in a daemon worker thread. The UI never blocks on it: it asks the manager
for an immutable `RunSnapshot` (events, per-agent state, outputs, usage). Run state is also
mirrored to the run directory so a restarted server can still show a finished run.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from launchscout.config import RunLimits, Settings, load_settings
from launchscout.crew import run_sequential
from launchscout.events import EventCollector, load_events, set_active_collector
from launchscout.evidence import EvidenceEntry, EvidenceLedger
from launchscout.grounding import (
    GroundedCompetitors,
    GroundedReviews,
    GroundedStrategy,
    ground_competitors,
    parse_competitors,
    parse_reviews,
    parse_strategy,
    report_unsupported_urls,
)
from launchscout.logging_utils import get_logger, redact
from launchscout.progress import AGENT_ORDER, AgentState, RunEvent, agent_metrics, reduce_events
from launchscout.runs import RunPaths, create_run_dir
from launchscout.schemas import (
    CompetitorSet,
    ResearchInput,
    ResearchMode,
    ReviewSet,
    RunMetadata,
    StrategyOutput,
    Usage,
)
from launchscout.tasks import TASK_ORDER, TASK_RESEARCH, TASK_REVIEWS, TASK_STRATEGY
from launchscout.tools import ToolContext

log = get_logger(__name__)

Phase = Literal["running", "stopping", "finished"]
Executor = Callable[["ResearchRun"], None]


class RunSnapshot(BaseModel):
    """Everything the UI needs, as plain data (safe to hold across reruns)."""

    run_id: str
    mode: ResearchMode
    status: Literal[
        "created", "running", "complete", "partial", "failed", "cancelled", "timeout"
    ]
    phase: Phase
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    input: ResearchInput
    events: list[RunEvent] = Field(default_factory=list)
    competitors: CompetitorSet | None = None
    reviews: ReviewSet | None = None
    strategy: StrategyOutput | None = None
    report_markdown: str | None = None
    grounding_issues: list[str] = Field(default_factory=list)
    unsupported_report_urls: list[str] = Field(default_factory=list)
    evidence: list[EvidenceEntry] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    completed_tasks: list[str] = Field(default_factory=list)
    model_name: str | None = None

    def agent_metrics(self) -> dict[str, dict[str, int | float]]:
        """Per-agent efficiency numbers derived only from recorded events."""
        return agent_metrics(self.events)

    @property
    def active(self) -> bool:
        return self.phase != "finished"

    def agent_states(self) -> dict[str, AgentState]:
        return reduce_events(self.events, run_active=self.active)

    def elapsed_seconds(self, now: datetime | None = None) -> float:
        end = self.finished_at or now or datetime.now(UTC)
        return max(0.0, (end - self.started_at).total_seconds())


class ResearchRun:
    """One run: worker thread, collector, tool context and the outputs gathered so far."""

    def __init__(
        self,
        paths: RunPaths,
        research_input: ResearchInput,
        settings: Settings,
        limits: RunLimits,
        started_at: datetime,
        search_impl: Any = None,
        scrape_impl: Any = None,
    ) -> None:
        self.paths = paths
        self.input = research_input
        self.settings = settings
        self.limits = limits
        self.started_at = started_at
        self.finished_at: datetime | None = None
        self.today: date = started_at.astimezone().date()
        self.llm_limit_hit = False
        self.collector = EventCollector(
            paths.events_jsonl,
            llm_limit=limits.max_llm_calls,
            on_llm_limit=self._on_llm_limit,
        )
        self.ledger = EvidenceLedger()
        self.ctx = ToolContext(
            ledger=self.ledger,
            collector=self.collector,
            limits=limits,
            run_dir=paths.root,
            today=self.today,
            search_impl=search_impl,
            scrape_impl=scrape_impl,
        )
        self.status: str = "running"
        self.phase: Phase = "running"
        self.error: str | None = None
        self.raw_outputs: dict[str, str] = {}
        self.competitors: GroundedCompetitors | None = None
        self.reviews: GroundedReviews | None = None
        self.strategy: GroundedStrategy | None = None
        self.report_markdown: str | None = None
        self.unsupported_urls: list[str] = []
        self.crew_usage: Any = None
        self.timed_out = False
        self.cancel_requested = False
        self.thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _on_llm_limit(self, count: int) -> None:
        """Hard stop: the run made more model calls than the configured limit."""
        self.llm_limit_hit = True
        self.phase = "stopping"
        self.ctx.cancel_event.set()
        self.collector.emit(
            "run_budget_stop",
            f"LLM call limit ({self.limits.max_llm_calls}) exceeded after {count} calls; stopping",
            status="error",
        )

    # -- called from the worker/executor --------------------------------------------------
    def record_output(self, task_name: str, raw: str) -> None:
        with self._lock:
            self.raw_outputs[task_name] = raw

    # -- snapshot --------------------------------------------------------------------------
    def snapshot(self) -> RunSnapshot:
        with self._lock:
            outputs = dict(self.raw_outputs)
            comp, rev, strat = self.competitors, self.reviews, self.strategy
            issues: list[str] = []
            for grounded in (comp, rev, strat):
                if grounded is not None:
                    issues.extend(grounded.issues)
            return RunSnapshot(
                run_id=self.paths.run_id,
                mode=self.input.mode,
                status=self.status,  # type: ignore[arg-type]
                phase=self.phase,
                error=self.error,
                started_at=self.started_at,
                finished_at=self.finished_at,
                input=self.input,
                events=self.collector.events(),
                competitors=comp.value if comp else None,
                reviews=rev.value if rev else None,
                strategy=strat.value if strat else None,
                report_markdown=self.report_markdown,
                grounding_issues=issues,
                unsupported_report_urls=list(self.unsupported_urls),
                evidence=self.ledger.entries(),
                usage=self._usage(),
                completed_tasks=[t for t in TASK_ORDER if t in outputs],
                model_name=self.settings.model_name,
            )

    def _usage(self) -> Usage:
        counters = self.ctx.counters()
        c = self.collector
        total = c.total_tokens
        prompt, completion = c.prompt_tokens, c.completion_tokens
        if not total and self.crew_usage is not None:
            total = int(getattr(self.crew_usage, "total_tokens", 0) or 0)
            prompt = int(getattr(self.crew_usage, "prompt_tokens", 0) or 0)
            completion = int(getattr(self.crew_usage, "completion_tokens", 0) or 0)
        measured = bool(total)
        return Usage(
            basis="measured" if measured or counters["serper_calls"] else "unavailable",
            total_tokens=total if measured else None,
            prompt_tokens=prompt if measured else None,
            completion_tokens=completion if measured else None,
            serper_calls=counters["serper_calls"],
            scrape_calls=counters["scrape_calls"],
            # wrapper cache hits plus calls CrewAI's own cache answered before our tool ran
            cache_hits=counters["cache_hits"]
            + max(0, c.tool_started - self.ctx.invocations),
            llm_calls=c.llm_events or None,
        )


def input_key(research_input: ResearchInput) -> tuple[str, ...]:
    """Normalised identity of a research request (case, spacing and list order ignored)."""

    def norm(text: str) -> str:
        return " ".join(text.casefold().split())

    return (
        norm(research_input.idea),
        norm(research_input.city),
        norm(research_input.target_customer),
        "|".join(sorted(norm(c) for c in research_input.known_competitors)),
        research_input.mode.value,
    )


def _default_executor(run: ResearchRun) -> None:
    if os.environ.get("LAUNCHSCOUT_NO_LIVE"):
        raise RuntimeError("live runs are disabled in this process (LAUNCHSCOUT_NO_LIVE)")
    out = run_sequential(
        run.input, run.settings, run.ctx, run.limits, run.today, run.record_output
    )
    run.crew_usage = getattr(out, "token_usage", None)
    for task_output in getattr(out, "tasks_output", None) or []:
        name = getattr(task_output, "name", None)
        if name and name not in run.raw_outputs:
            run.record_output(name, str(getattr(task_output, "raw", "") or ""))


class RunManager:
    """Owns at most one active run (duplicate prevention) and remembers finished ones."""

    def __init__(
        self,
        runs_dir: Path | None = None,
        executor: Executor | None = None,
        limits: RunLimits | None = None,
        settings_loader: Callable[[], Settings] | None = None,
        search_impl: Any = None,
        scrape_impl: Any = None,
    ) -> None:
        self._runs_dir = runs_dir
        self._executor = executor or _default_executor
        self._limits = limits or RunLimits()
        self._settings_loader = settings_loader or load_settings
        self._search_impl = search_impl
        self._scrape_impl = scrape_impl
        self._runs: dict[str, ResearchRun] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    # -- queries ---------------------------------------------------------------------------
    def settings(self) -> Settings:
        """Current settings (same loader the runs use)."""
        return self._settings_loader()

    def active_run(self) -> ResearchRun | None:
        with self._lock:
            for run_id in reversed(self._order):
                run = self._runs[run_id]
                if run.thread is not None and run.thread.is_alive():
                    return run
        return None

    def latest_run_id(self) -> str | None:
        with self._lock:
            return self._order[-1] if self._order else None

    def snapshot(self, run_id: str) -> RunSnapshot | None:
        with self._lock:
            run = self._runs.get(run_id)
        if run is not None:
            return run.snapshot()
        return None

    def find_reusable(self, research_input: ResearchInput) -> str | None:
        """Run id of the newest completed run with identical input, else None (no API use)."""
        wanted = input_key(research_input)
        with self._lock:
            for run_id in reversed(self._order):
                run = self._runs[run_id]
                if run.status == "complete" and input_key(run.input) == wanted:
                    return run_id
        return None

    # -- commands --------------------------------------------------------------------------
    def start(self, research_input: ResearchInput) -> ResearchRun | None:
        """Start a run, or return None if one is already active (duplicate prevention)."""
        if research_input.mode is not ResearchMode.SEQUENTIAL:
            raise NotImplementedError("hierarchical execution is not available until M5")
        with self._lock:
            for run_id in self._order:
                existing = self._runs[run_id]
                if existing.thread is not None and existing.thread.is_alive():
                    return None
            settings = self._settings_loader()
            paths = create_run_dir(research_input, base_dir=self._runs_dir)
            run = ResearchRun(
                paths,
                research_input,
                settings,
                self._limits,
                datetime.now(UTC),
                self._search_impl,
                self._scrape_impl,
            )
            run.thread = threading.Thread(
                target=self._work, args=(run,), name=f"run-{paths.run_id}", daemon=True
            )
            self._runs[paths.run_id] = run
            self._order.append(paths.run_id)
        run.thread.start()
        return run

    def cancel(self, run_id: str) -> bool:
        with self._lock:
            run = self._runs.get(run_id)
        if run is None or run.phase == "finished" or run.cancel_requested:
            return False
        run.cancel_requested = True
        run.phase = "stopping"
        run.ctx.cancel_event.set()
        run.collector.emit(
            "run_cancel_requested",
            "Cancellation requested; waiting for the current step to return",
        )
        return True

    # -- worker ----------------------------------------------------------------------------
    def _work(self, run: ResearchRun) -> None:
        set_active_collector(run.collector)
        run.collector.emit("run_started", f"Run {run.paths.run_id} started (sequential)")
        watchdog = threading.Timer(run.limits.run_timeout_s, self._on_timeout, args=(run,))
        watchdog.daemon = True
        watchdog.start()
        error: str | None = None
        try:
            self._executor(run)
        except Exception as exc:  # noqa: BLE001 - recorded in the run, never lost
            error = f"{type(exc).__name__}: {redact(str(exc))}"[:400]
            run.collector.emit("crew_failed", f"Run error: {error}", status="error")
        finally:
            watchdog.cancel()
            self._flush_bus()
            self._finalize(run, error)
            set_active_collector(None)

    @staticmethod
    def _flush_bus() -> None:
        try:
            from crewai.events import crewai_event_bus

            crewai_event_bus.flush()
        except Exception:  # noqa: BLE001
            time.sleep(0.2)

    def _on_timeout(self, run: ResearchRun) -> None:
        if run.phase == "finished":
            return
        run.timed_out = True
        run.phase = "stopping"
        run.ctx.cancel_event.set()
        run.collector.emit(
            "run_timeout",
            f"Run exceeded the {run.limits.run_timeout_s}s limit; stopping",
            status="error",
        )

    def _finalize(self, run: ResearchRun, error: str | None) -> None:
        ledger, outputs = run.ledger, dict(run.raw_outputs)
        comp = ground_competitors(parse_competitors(outputs[TASK_RESEARCH]), ledger) if (
            TASK_RESEARCH in outputs
        ) else None
        rev = parse_reviews(outputs[TASK_REVIEWS], ledger) if TASK_REVIEWS in outputs else None
        strat = (
            parse_strategy(outputs[TASK_STRATEGY], ledger) if TASK_STRATEGY in outputs else None
        )
        report_text: str | None = None
        if run.paths.report_md.is_file():
            report_text = run.paths.report_md.read_text(encoding="utf-8", errors="replace")
        unsupported = report_unsupported_urls(report_text, ledger) if report_text else []

        with run._lock:
            run.competitors, run.reviews, run.strategy = comp, rev, strat
            run.report_markdown, run.unsupported_urls = report_text, unsupported

        for grounded in (comp, rev, strat):
            if grounded is None:
                continue
            for issue in grounded.issues:
                run.collector.emit("grounding", issue, status="info")
        if unsupported:
            run.collector.emit(
                "grounding",
                f"{len(unsupported)} URL(s) in the draft report were not returned by any tool",
            )

        parsed_ok = all(
            g is not None and g.value is not None for g in (comp, rev, strat)  # type: ignore[union-attr]
        )
        have_report = report_text is not None
        if run.llm_limit_hit and not error:
            error = f"LLM call limit ({run.limits.max_llm_calls}) reached"
        if run.timed_out:
            status = "timeout"
        elif run.cancel_requested:
            status = "cancelled"
        elif run.llm_limit_hit:
            status = "partial" if (outputs or have_report) else "failed"
        elif error and not outputs:
            status = "failed"
        elif error or not (parsed_ok and have_report and len(outputs) == len(TASK_ORDER)):
            status = "partial" if outputs or have_report else "failed"
        else:
            status = "complete"
        if status == "cancelled":
            run.collector.emit("run_cancelled", "Run cancelled by user", status="error")
        run.collector.emit("run_finished", f"Run finished with status: {status}")

        with run._lock:
            run.status = status
            run.error = error
            run.finished_at = datetime.now(UTC)
        self._persist(run)  # artifacts are on disk before the run is reported finished
        with run._lock:
            run.phase = "finished"

    def _persist(self, run: ResearchRun) -> None:
        snap = run.snapshot()
        root = run.paths.root

        def dump(name: str, model: BaseModel | None) -> None:
            if model is not None:
                (root / name).write_text(model.model_dump_json(indent=2), encoding="utf-8")

        dump("competitors.json", snap.competitors)
        dump("reviews.json", snap.reviews)
        dump("strategy.json", snap.strategy)
        run.ledger.save(root / "evidence.json")
        (root / "grounding.json").write_text(
            json.dumps(
                {
                    "issues": snap.grounding_issues,
                    "unsupported_report_urls": snap.unsupported_report_urls,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        metadata = RunMetadata(
            run_id=snap.run_id,
            mode=snap.mode,
            model_name=snap.model_name,
            started_at=snap.started_at,
            finished_at=snap.finished_at,
            status=snap.status,
            usage=snap.usage,
            error=snap.error,
        )
        (root / "metadata.json").write_text(metadata.model_dump_json(indent=2), encoding="utf-8")


def snapshot_from_disk(paths: RunPaths) -> RunSnapshot | None:
    """Rebuild a finished run's view from its run directory (after a server restart)."""
    try:
        meta = RunMetadata.model_validate_json(paths.metadata_json.read_text("utf-8"))
        research_input = ResearchInput.model_validate_json(paths.input_json.read_text("utf-8"))
    except (OSError, ValueError):
        return None

    def load(name: str, model: type[BaseModel]) -> Any:
        path = paths.root / name
        try:
            return model.model_validate_json(path.read_text("utf-8")) if path.is_file() else None
        except ValueError:
            return None

    grounding: dict[str, Any] = {}
    gpath = paths.root / "grounding.json"
    if gpath.is_file():
        try:
            grounding = json.loads(gpath.read_text("utf-8"))
        except ValueError:
            grounding = {}
    evidence: list[EvidenceEntry] = []
    epath = paths.root / "evidence.json"
    if epath.is_file():
        try:
            rows = json.loads(epath.read_text("utf-8"))
            evidence = [EvidenceEntry.model_validate(row) for row in rows]
        except ValueError:
            evidence = []
    report = (
        paths.report_md.read_text("utf-8", errors="replace") if paths.report_md.is_file() else None
    )
    finished = meta.status not in ("created", "running")
    return RunSnapshot(
        run_id=meta.run_id,
        mode=meta.mode,
        status=meta.status,
        # An unfinished run on disk belongs to a process that no longer exists.
        phase="finished",
        error=meta.error if finished else "Run was interrupted (server restarted).",
        started_at=meta.started_at,
        finished_at=meta.finished_at,
        input=research_input,
        events=load_events(paths.events_jsonl),
        competitors=load("competitors.json", CompetitorSet),
        reviews=load("reviews.json", ReviewSet),
        strategy=load("strategy.json", StrategyOutput),
        report_markdown=report,
        grounding_issues=list(grounding.get("issues", [])),
        unsupported_report_urls=list(grounding.get("unsupported_report_urls", [])),
        evidence=evidence,
        usage=meta.usage,
        completed_tasks=[],
        model_name=meta.model_name,
    )


_MANAGER: RunManager | None = None
_MANAGER_LOCK = threading.Lock()


def get_manager() -> RunManager:
    """Process-wide manager (shared by every Streamlit session and rerun)."""
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            _MANAGER = RunManager()
        return _MANAGER


def set_manager(manager: RunManager | None) -> None:
    """Replace the process-wide manager (tests)."""
    global _MANAGER
    with _MANAGER_LOCK:
        _MANAGER = manager


__all__ = [
    "AGENT_ORDER",
    "ResearchRun",
    "RunManager",
    "RunSnapshot",
    "get_manager",
    "set_manager",
    "snapshot_from_disk",
]
