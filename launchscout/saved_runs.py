"""Browse and replay saved runs from `runs/<run_id>/`. Read-only and deterministic.

Nothing here calls a model, a search API or the research crew, and nothing writes to a run
directory: historical results are shown exactly as persisted (no regeneration, no repair).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from launchscout.runner import RunSnapshot, input_key, snapshot_from_disk
from launchscout.runs import RunPaths
from launchscout.schemas import ResearchInput, RunMetadata
from launchscout.validation import ValidationReport

RunLabel = Literal[
    "validated", "partial", "failed", "cancelled", "timed_out", "interrupted", "legacy", "running"
]
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")

LABEL_TEXT: dict[str, str] = {
    "validated": "VALIDATED",
    "partial": "PARTIAL (failed acceptance)",
    "failed": "FAILED",
    "cancelled": "CANCELLED",
    "timed_out": "TIMED OUT",
    "interrupted": "INTERRUPTED",
    "running": "RUNNING NOW",
    "legacy": "LEGACY (not validated)",
}


class SavedRunSummary(BaseModel):
    run_id: str
    label: RunLabel
    status: str
    report_state: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    idea: str = ""
    city: str = ""
    mode: str = "sequential"
    total_tokens: int | None = None

    @property
    def title(self) -> str:
        when = self.started_at.astimezone().strftime("%d %b %H:%M")
        idea = self.idea if len(self.idea) <= 42 else self.idea[:41] + "…"
        return f"[{LABEL_TEXT[self.label]}] {when} · {idea} · {self.city}"


def classify(status: str, validation_state: str | None, has_report: bool, finished: bool
             ) -> RunLabel:
    """Distinguish validated / partial / failed / cancelled (plus timeout, interrupted, legacy)."""
    if not finished:
        return "interrupted"
    if status == "cancelled":
        return "cancelled"
    if status == "timeout":
        return "timed_out"
    if status == "failed":
        return "failed"
    if validation_state == "validated_pass":
        return "validated"
    if validation_state == "partial_failed_acceptance":
        return "partial"
    if validation_state == "failed_no_report":
        return "failed"
    if has_report:
        return "legacy"  # produced before report validation existed
    return "failed" if status != "complete" else "legacy"


def is_safe_run_id(run_id: str | None) -> bool:
    return bool(run_id) and bool(_RUN_ID_RE.match(run_id or "")) and ".." not in (run_id or "")


def _summary(root: Path) -> SavedRunSummary | None:
    try:
        meta = RunMetadata.model_validate_json((root / "metadata.json").read_text("utf-8"))
        run_input = ResearchInput.model_validate_json((root / "input.json").read_text("utf-8"))
    except (OSError, ValueError):
        return None
    validation_state: str | None = None
    vpath = root / "validation.json"
    if vpath.is_file():
        try:
            validation_state = ValidationReport.model_validate_json(vpath.read_text("utf-8")).state
        except ValueError:
            validation_state = None
    has_report = any(
        (root / n).is_file() for n in ("report.md", "report-PARTIAL.md", "report.writer.md")
    )
    finished = meta.status not in ("created", "running")
    return SavedRunSummary(
        run_id=meta.run_id,
        label=classify(meta.status, validation_state, has_report, finished),
        status=meta.status,
        report_state=validation_state,
        started_at=meta.started_at,
        finished_at=meta.finished_at,
        idea=run_input.idea,
        city=run_input.city,
        mode=run_input.mode.value,
        total_tokens=meta.usage.total_tokens,
    )


def list_saved_runs(
    runs_dir: Path, active_ids: frozenset[str] | set[str] = frozenset()
) -> list[SavedRunSummary]:
    """All readable saved runs, newest first. Unreadable directories are skipped.

    `active_ids` are runs this process is executing right now (shown as RUNNING NOW, not
    interrupted).
    """
    if not runs_dir.is_dir():
        return []
    found: list[SavedRunSummary] = []
    for child in runs_dir.iterdir():
        if child.is_dir() and is_safe_run_id(child.name):
            summary = _summary(child)
            if summary is not None:
                if summary.run_id in active_ids:
                    summary = summary.model_copy(update={"label": "running"})
                found.append(summary)
    return sorted(found, key=lambda s: s.started_at, reverse=True)


def find_matching_saved_run(runs_dir: Path, research_input: ResearchInput) -> str | None:
    """Newest saved run with identical input whose crew finished (`complete`), else None."""
    wanted = input_key(research_input)
    for summary in list_saved_runs(runs_dir):
        if summary.status != "complete":
            continue
        try:
            saved = ResearchInput.model_validate_json(
                (runs_dir / summary.run_id / "input.json").read_text("utf-8")
            )
        except (OSError, ValueError):
            continue
        if input_key(saved) == wanted:
            return summary.run_id
    return None


def load_saved_snapshot(runs_dir: Path, run_id: str) -> RunSnapshot | None:
    """Rebuild the UI snapshot of a saved run from its files (read-only)."""
    if not is_safe_run_id(run_id):
        return None
    root = runs_dir / run_id
    if not root.is_dir():
        return None
    snap = snapshot_from_disk(RunPaths(run_id=run_id, root=root))
    return snap
