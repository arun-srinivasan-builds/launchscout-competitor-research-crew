"""Deterministic sequential vs hierarchical comparison from recorded run data only.

Nothing is estimated or projected. A run that does not exist, or a number that was not
recorded, is shown as "Not yet measured" / "Unavailable". Task completion (did the agents
finish) is kept apart from research quality (what evidence was obtained and validated).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from launchscout.progress import MANAGER_ROLE
from launchscout.runner import RunSnapshot, input_key
from launchscout.saved_runs import list_saved_runs, load_saved_snapshot
from launchscout.schemas import ResearchMode

NOT_MEASURED = "Not yet measured"
UNAVAILABLE = "Unavailable"


class ComparisonRow(BaseModel):
    group: str
    metric: str
    sequential: str
    hierarchical: str


def _num(value: float | int | None) -> str:
    return UNAVAILABLE if value is None else f"{int(value):,}"


def _duration(snap: RunSnapshot) -> str:
    if snap.finished_at is None:
        return UNAVAILABLE
    seconds = int(snap.elapsed_seconds())
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def summarize(snap: RunSnapshot | None) -> dict[str, tuple[str, str]]:
    """{metric key: (group, display value)} for one run, or {} when there is no run."""
    if snap is None:
        return {}
    metrics = snap.agent_metrics()
    manager = metrics.get(MANAGER_ROLE, {})
    specialists = [v for k, v in metrics.items() if k not in (MANAGER_ROLE, "(run)")]

    def total(key: str, rows: list[dict[str, int | float]]) -> int:
        return int(sum(r.get(key, 0) for r in rows))

    all_rows = [v for k, v in metrics.items() if k != "(run)"]
    hier = snap.mode is ResearchMode.HIERARCHICAL
    usage = snap.usage
    v = snap.validation
    rules = v.rules if v else []
    sourced = sum(1 for f in snap.reviews.findings if f.source_url) if snap.reviews else None
    out: dict[str, tuple[str, str]] = {
        "mode": ("Execution", snap.mode.value),
        "run": ("Execution", snap.run_id),
        "status": ("Task completion", snap.status),
        "agents": ("Task completion", f"{len(snap.completed_tasks)}/4 tasks completed"),
        "duration": ("Execution", _duration(snap)),
        "manager_calls": (
            "Model usage",
            _num(manager.get("llm_calls")) if hier else "n/a (no Manager)",
        ),
        "specialist_calls": ("Model usage", _num(total("llm_calls", specialists))),
        "total_calls": ("Model usage", _num(usage.llm_calls)),
        "prompt_tokens": ("Model usage", _num(usage.prompt_tokens)),
        "completion_tokens": ("Model usage", _num(usage.completion_tokens)),
        "total_tokens": ("Model usage", _num(usage.total_tokens)),
        "manager_tokens": (
            "Model usage",
            _num(manager.get("total_tokens")) if hier else "n/a (no Manager)",
        ),
        "delegations": (
            "Tools",
            _num(manager.get("delegations")) if hier else "n/a (no Manager)",
        ),
        "searches": ("Tools", _num(usage.serper_calls)),
        "page_reads": ("Tools", _num(usage.scrape_calls)),
        "cache_hits": ("Tools", _num(usage.cache_hits)),
        "refusals": ("Tools", _num(total("refused_budget", all_rows))),
        "errors": ("Tools", _num(total("tool_errors", all_rows))),
        "competitors_evidence": (
            "Research quality",
            _num(v.eligible_competitors) if v else UNAVAILABLE,
        ),
        "verified_prices": ("Research quality", _num(v.verified_prices) if v else UNAVAILABLE),
        "sourced_findings": ("Research quality", _num(sourced)),
        "rules": (
            "Research quality",
            f"{sum(1 for r in rules if r.status == 'pass')}/{len(rules)} passed"
            if rules
            else UNAVAILABLE,
        ),
        "failed_rules": (
            "Research quality",
            ", ".join(r.id for r in rules if r.status == "fail")
            or ("none" if rules else UNAVAILABLE),
        ),
        "acceptance": (
            "Research quality",
            snap.report_state or "not evaluated",
        ),
    }
    return out


_LABELS: tuple[tuple[str, str], ...] = (
    ("mode", "Execution mode"),
    ("run", "Run"),
    ("status", "Crew status"),
    ("agents", "Specialist tasks"),
    ("duration", "Duration"),
    ("manager_calls", "Manager model calls"),
    ("specialist_calls", "Specialist model calls"),
    ("total_calls", "Total model calls"),
    ("prompt_tokens", "Prompt tokens"),
    ("completion_tokens", "Completion tokens"),
    ("total_tokens", "Total tokens"),
    ("manager_tokens", "Manager tokens"),
    ("delegations", "Delegations"),
    ("searches", "Searches executed"),
    ("page_reads", "Page reads executed"),
    ("cache_hits", "Cache hits"),
    ("refusals", "Budget refusals"),
    ("errors", "Tool errors"),
    ("competitors_evidence", "Competitors with evidence (3 required)"),
    ("verified_prices", "Verified competitor prices (3 required)"),
    ("sourced_findings", "Customer findings with a source"),
    ("rules", "R1-R8 checks"),
    ("failed_rules", "Failed rules"),
    ("acceptance", "Final acceptance state"),
)


def build_comparison(
    sequential: RunSnapshot | None, hierarchical: RunSnapshot | None
) -> list[ComparisonRow]:
    """One row per metric; absent runs show "Not yet measured" instead of any number."""
    seq, hier = summarize(sequential), summarize(hierarchical)
    rows: list[ComparisonRow] = []
    for key, label in _LABELS:
        group = (seq.get(key) or hier.get(key) or ("Execution", ""))[0]
        rows.append(
            ComparisonRow(
                group=group,
                metric=label,
                sequential=seq[key][1] if key in seq else NOT_MEASURED,
                hierarchical=hier[key][1] if key in hier else NOT_MEASURED,
            )
        )
    return rows


def pick_pair(
    runs_dir: Path, current: RunSnapshot
) -> tuple[RunSnapshot | None, RunSnapshot | None]:
    """(sequential, hierarchical) runs with the same input as `current`, newest finished first.

    The current run supplies its own side; the other side is the newest saved run with an
    identical input and the other mode, if one exists.
    """
    wanted = input_key(current.input.model_copy(update={"mode": ResearchMode.SEQUENTIAL}))
    other_mode = (
        ResearchMode.HIERARCHICAL
        if current.mode is ResearchMode.SEQUENTIAL
        else ResearchMode.SEQUENTIAL
    )
    other: RunSnapshot | None = None
    for summary in list_saved_runs(runs_dir):
        if summary.mode != other_mode.value or summary.run_id == current.run_id:
            continue
        if summary.status in ("created", "running"):
            continue
        candidate = load_saved_snapshot(runs_dir, summary.run_id)
        if candidate is None:
            continue
        key = input_key(candidate.input.model_copy(update={"mode": ResearchMode.SEQUENTIAL}))
        if key == wanted:
            other = candidate
            break
    if current.mode is ResearchMode.SEQUENTIAL:
        return current, other
    return other, current
