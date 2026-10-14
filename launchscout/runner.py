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
from launchscout.crew import run_crew
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
)
from launchscout.links import Fetcher
from launchscout.logging_utils import get_logger, redact
from launchscout.progress import (
    AGENT_KEYS,
    AGENT_ORDER,
    MANAGER_ROLE,
    AgentState,
    RunEvent,
    agent_metrics,
    reduce_events,
)
from launchscout.reporting import produce_report
from launchscout.runs import DEFAULT_RUNS_DIR, RunPaths, create_run_dir
from launchscout.schemas import (
    Acceptance,
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
from launchscout.validation import ValidationReport

log = get_logger(__name__)

Phase = Literal["running", "stopping", "finished"]
Executor = Callable[["ResearchRun"], None]


class RunSnapshot(BaseModel):
    """Everything the UI needs, as plain data (safe to hold across reruns)."""

    run_id: str
    mode: ResearchMode
    status: Literal["created", "running", "complete", "partial", "failed", "cancelled", "timeout"]
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
    validation: ValidationReport | None = None
    report_files: dict[str, str] = Field(default_factory=dict)
    run_dir: str | None = None

    @property
    def acceptance(self) -> Acceptance:
        """Single source of truth for the acceptance result (never recomputed by the UI)."""
        return self.validation.acceptance if self.validation else Acceptance()

    @property
    def report_state(self) -> str | None:
        return self.validation.state if self.validation else None

    def agent_metrics(self) -> dict[str, dict[str, int | float]]:
        """Per-agent efficiency numbers derived only from recorded events."""
        return agent_metrics(self.events)

    @property
    def active(self) -> bool:
        return self.phase != "finished"

    def agent_states(self) -> dict[str, AgentState]:
        return reduce_events(
            self.events,
            run_active=self.active,
            with_manager=self.mode is ResearchMode.HIERARCHICAL,
        )

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
        link_fetcher: Fetcher | None = None,
    ) -> None:
        self.paths = paths
        self.link_fetcher = link_fetcher
        self.validation: ValidationReport | None = None
        self.report_files: dict[str, str] = {}
        self.input = research_input
        self.settings = settings
        self.limits = limits
        self.started_at = started_at
        self.finished_at: datetime | None = None
        self.today: date = started_at.astimezone().date()
        self.llm_limit_hit = False
        self.limit_reason: str | None = None
        self.guard_issues: list[str] = []
        hierarchical = research_input.mode is ResearchMode.HIERARCHICAL
        self.llm_cap = limits.max_llm_calls_hierarchical if hierarchical else limits.max_llm_calls
        self.collector = EventCollector(
            paths.events_jsonl,
            llm_limit=self.llm_cap,
            on_llm_limit=self._on_llm_limit,
            agent_llm_limits={MANAGER_ROLE: limits.max_manager_llm_calls} if hierarchical else None,
            delegation_limit=limits.max_delegations if hierarchical else None,
            on_limit=self._on_limit,
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

    def _stop_for_budget(self, reason: str, summary: str) -> None:
        self.llm_limit_hit = True
        self.limit_reason = reason
        self.phase = "stopping"
        self.ctx.cancel_event.set()
        self.collector.emit("run_budget_stop", summary, status="error")

    def _on_llm_limit(self, count: int) -> None:
        """Hard stop: the run made more model calls than the configured limit."""
        self._stop_for_budget(
            f"LLM call limit ({self.llm_cap}) reached",
            f"LLM call limit ({self.llm_cap}) exceeded after {count} calls; stopping",
        )

    def _on_limit(self, kind: str, count: int, limit: int) -> None:
        """Hard stop for Manager-specific or delegation budgets (hierarchical mode)."""
        if kind == "delegations":
            reason = f"Delegation limit ({limit}) reached"
        else:
            who = kind.split(":", 1)[-1] or "agent"
            reason = f"{who} LLM call limit ({limit}) reached"
        self._stop_for_budget(reason, f"{reason} after {count}; stopping")

    # -- called from the worker/executor --------------------------------------------------
    def record_output(self, task_name: str, raw: str) -> None:
        with self._lock:
            self.raw_outputs[task_name] = raw

    # -- snapshot --------------------------------------------------------------------------
    def snapshot(self) -> RunSnapshot:
        with self._lock:
            outputs = dict(self.raw_outputs)
            comp, rev, strat = self.competitors, self.reviews, self.strategy
            issues: list[str] = list(self.guard_issues)
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
                validation=self.validation,
                report_files=dict(self.report_files),
                run_dir=str(self.paths.root),
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
            cache_hits=counters["cache_hits"] + max(0, c.tool_started - self.ctx.invocations),
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
    out = run_crew(run.input, run.settings, run.ctx, run.limits, run.today, run.record_output)
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
        link_fetcher: Fetcher | None = None,
    ) -> None:
        self._link_fetcher = link_fetcher
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
    def runs_dir(self) -> Path:
        """Directory holding saved runs for this manager."""
        return self._runs_dir if self._runs_dir is not None else DEFAULT_RUNS_DIR

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
                self._link_fetcher,
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
        run.collector.emit(
            "run_started", f"Run {run.paths.run_id} started ({run.input.mode.value})"
        )
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
            try:
                self._finalize(run, error)
            except Exception as exc:  # noqa: BLE001 - a failed finalization must not strand the run
                self._finalize_failed(run, exc)
            finally:
                set_active_collector(None)

    def _finalize_failed(self, run: ResearchRun, exc: Exception) -> None:
        """Finalization itself raised (disk, PDF, validation): end the run as failed, visibly.

        Without this the worker thread dies while the run still reports "running", so the UI
        would poll an unfinishable run forever and nothing would explain why.
        """
        reason = f"Finalization failed: {type(exc).__name__}: {redact(str(exc))}"[:400]
        log.warning("run finalization failed: %s", type(exc).__name__)
        with run._lock:
            has_outputs = bool(run.raw_outputs)
            run.status = "partial" if has_outputs else "failed"
            run.error = reason if not run.error else f"{run.error}; {reason}"
            run.finished_at = datetime.now(UTC)
        run.collector.emit("run_finished", f"Run ended: {reason}", status="error")
        try:
            self._persist(run)
        except Exception:  # noqa: BLE001 - disk may be the very problem; the state still flips
            log.warning("could not persist a failed finalization")
        with run._lock:
            run.phase = "finished"

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
        comp = (
            ground_competitors(parse_competitors(outputs[TASK_RESEARCH]), ledger)
            if (TASK_RESEARCH in outputs)
            else None
        )
        rev = parse_reviews(outputs[TASK_REVIEWS], ledger) if TASK_REVIEWS in outputs else None
        strat = parse_strategy(outputs[TASK_STRATEGY], ledger) if TASK_STRATEGY in outputs else None
        # Deterministic validation + export from stored outputs (no model, no new searches).
        outcome = produce_report(
            run.paths,
            comp.value if comp else None,
            rev.value if rev else None,
            strat.value if strat else None,
            ledger,
            run.link_fetcher,
        )
        report_text = outcome.final_markdown
        unsupported = next((r.items for r in outcome.validation.rules if r.id == "R3"), [])
        with run._lock:
            run.validation = outcome.validation
            run.report_files = outcome.files

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
                f"{len(unsupported)} URL(s) in the report were not returned by any tool",
            )
        run.collector.emit(
            "grounding",
            f"Report validation: {outcome.validation.state}"
            + (
                ""
                if outcome.validation.acceptance.result == "pass"
                else f" ({len(outcome.validation.acceptance.reasons)} reason(s))"
            ),
            status="ok" if outcome.validation.acceptance.result == "pass" else "error",
        )

        parsed_ok = all(
            g is not None and g.value is not None
            for g in (comp, rev, strat)  # type: ignore[union-attr]
        )
        have_report = report_text is not None
        if run.llm_limit_hit and not error:
            error = run.limit_reason or f"LLM call limit ({run.llm_cap}) reached"
        undelegated = self._undelegated(run, outputs)
        if undelegated:
            with run._lock:
                run.guard_issues.extend(undelegated)
            for issue in undelegated:
                run.collector.emit("grounding", issue, status="error")
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
        elif undelegated:
            status = "partial"  # Manager did the work itself: not specialist evidence
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

    @staticmethod
    def _undelegated(run: ResearchRun, outputs: dict[str, str]) -> list[str]:
        """Hierarchical guard: every completed task must show its specialist at work."""
        if run.input.mode is not ResearchMode.HIERARCHICAL:
            return []
        seen = {
            e.agent
            for e in run.collector.events()
            if e.kind == "agent_started" and e.agent in AGENT_KEYS
        }
        task_roles = {
            "Competitor research": "Market Researcher",
            "Customer review analysis": "Review Analyst",
            "Strategy and positioning": "Strategy Analyst",
            "Report writing": "Report Writer",
        }
        return [
            f"Manager reported '{task}' complete without delegating to the {role}; "
            "the output is not specialist work and is not evidence"
            for task, role in task_roles.items()
            if task in outputs and role not in seen
        ]

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
            acceptance=snap.acceptance,
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
    validation = load("validation.json", ValidationReport)
    report = None
    report_files: dict[str, str] = {}
    names = (("report.md", "report.pdf"), ("report-PARTIAL.md", "report-PARTIAL.pdf"))
    for md_name, pdf_name in names:
        candidate = paths.root / md_name
        if candidate.is_file():
            report = candidate.read_text("utf-8", errors="replace")
            report_files = {"md": md_name}
            if (paths.root / pdf_name).is_file():
                report_files["pdf"] = pdf_name
            break
    finished = meta.status not in ("created", "running")
    events = load_events(paths.events_jsonl)
    done: set[str] = set()
    for event in events:
        if event.kind == "task_completed":
            name = event.task or event.summary.removeprefix("Task complete: ")
            done.add(name)
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
        events=events,
        competitors=load("competitors.json", CompetitorSet),
        reviews=load("reviews.json", ReviewSet),
        strategy=load("strategy.json", StrategyOutput),
        report_markdown=report,
        grounding_issues=list(grounding.get("issues", [])),
        unsupported_report_urls=list(grounding.get("unsupported_report_urls", [])),
        evidence=evidence,
        usage=meta.usage,
        completed_tasks=[t for t in TASK_ORDER if t in done],
        model_name=meta.model_name,
        validation=validation,
        report_files=report_files,
        run_dir=str(paths.root),
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
