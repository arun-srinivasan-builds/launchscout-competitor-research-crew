"""Turn a finished run's artifacts into the validated (or partial) report and its exports.

Deterministic end to end: reads stored outputs and the evidence ledger, validates, assembles,
writes Markdown and PDF. It never calls a model and never searches (efficiency standard E-03).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from launchscout.evidence import EvidenceEntry, EvidenceLedger
from launchscout.exports.markdown import write_report_files
from launchscout.links import Fetcher, LinkStatus, check_links
from launchscout.logging_utils import get_logger
from launchscout.report import build_final_report
from launchscout.runs import RunPaths
from launchscout.schemas import CompetitorSet, ReviewSet, StrategyOutput
from launchscout.validation import ValidationReport, validate_report

log = get_logger(__name__)
_URL_RE = re.compile(r"https?://[^\s)>\]\"'`]+")


class ReportOutcome(BaseModel):
    validation: ValidationReport
    final_markdown: str | None = None
    files: dict[str, str] = {}


def load_ledger(path: Path) -> EvidenceLedger:
    ledger = EvidenceLedger()
    if path.is_file():
        try:
            for row in json.loads(path.read_text(encoding="utf-8")):
                ledger.add(EvidenceEntry.model_validate(row))
        except ValueError:
            log.warning("evidence ledger unreadable")
    return ledger


def report_urls(markdown: str) -> list[str]:
    seen: list[str] = []
    for match in _URL_RE.findall(markdown):
        url = match.rstrip(".,;:!?")
        if url not in seen:
            seen.append(url)
    return seen


def produce_report(
    paths: RunPaths,
    competitors: CompetitorSet | None,
    reviews: ReviewSet | None,
    strategy: StrategyOutput | None,
    ledger: EvidenceLedger,
    fetcher: Fetcher | None = None,
    stored_links: list[LinkStatus] | None = None,
) -> ReportOutcome:
    """Validate the Report Writer's output and write the final report files.

    `stored_links` lets a re-validation reuse earlier link results instead of the network.
    """
    writer = paths.report_writer_md
    if paths.report_md.is_file() and not writer.is_file():
        paths.report_md.replace(writer)  # keep the agent's original text untouched
    writer_text = writer.read_text(encoding="utf-8", errors="replace") if writer.is_file() else None

    if not writer_text or not writer_text.strip():
        validation = validate_report(None, competitors, ledger)
        paths.validation_json.write_text(validation.model_dump_json(indent=2), encoding="utf-8")
        return ReportOutcome(validation=validation)

    urls = report_urls(writer_text)
    links = stored_links if stored_links is not None else check_links(urls, ledger, fetcher)
    counts = dict(Counter(f.basis for f in reviews.findings)) if reviews else {}
    validation = validate_report(writer_text, competitors, ledger, links, counts)
    final = build_final_report(
        writer_text, validation, competitors, reviews, strategy, ledger, paths.run_id
    )
    files = write_report_files(paths.root, final, validation.state, f"Run {paths.run_id}")
    paths.validation_json.write_text(validation.model_dump_json(indent=2), encoding="utf-8")
    return ReportOutcome(validation=validation, final_markdown=final, files=files)


def revalidate_run(paths: RunPaths) -> ReportOutcome:
    """Re-run the validators on a run's stored artifacts (no model, no network).

    Can only change the outcome if the artifacts or the rules changed; there is no override.
    """

    def load(name: str, model: type[BaseModel]):
        path = paths.root / name
        return model.model_validate_json(path.read_text("utf-8")) if path.is_file() else None

    previous = load("validation.json", ValidationReport)
    stored = previous.links if previous else []
    return produce_report(
        paths,
        load("competitors.json", CompetitorSet),
        load("reviews.json", ReviewSet),
        load("strategy.json", StrategyOutput),
        load_ledger(paths.root / "evidence.json"),
        stored_links=stored,
    )
