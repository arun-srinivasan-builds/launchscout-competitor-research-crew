"""M4 end to end (stub crew): report states, files, re-validation, UI and zero-LLM guarantees."""

import json
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from launchscout.reporting import revalidate_run
from launchscout.runner import set_manager, snapshot_from_disk
from launchscout.schemas import ResearchInput
from tests.conftest import make_manager
from tests.helpers import (
    COMPETITORS_JSON,
    PARTIAL_REPORT_MD,
    PASS_REPORT_MD,
    make_executor,
    wait_finished,
    wait_idle,
)

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
INPUT = ResearchInput(
    idea="Healthy millet meal boxes", city="Coimbatore", target_customer="office workers"
)


def _finish(manager, run):
    snap = wait_finished(manager, run)
    wait_idle(manager)
    return snap


def _run(tmp_path, **executor_kwargs):
    manager = make_manager(tmp_path, executor=make_executor(**executor_kwargs))
    run = manager.start(INPUT)
    return manager, run, _finish(manager, run)


def test_validated_run_writes_pass_files_and_single_source_acceptance(tmp_path):
    _, run, snap = _run(tmp_path)
    root = run.paths.root
    assert snap.report_state == "validated_pass" and snap.acceptance.result == "pass"
    assert (root / "report.md").is_file() and (root / "report.pdf").is_file()
    assert not (root / "report-PARTIAL.md").exists()
    assert (root / "report.writer.md").read_text(encoding="utf-8") == PASS_REPORT_MD.strip() or (
        (root / "report.writer.md").read_text(encoding="utf-8").strip() == PASS_REPORT_MD.strip()
    )
    meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert meta["acceptance"] == snap.acceptance.model_dump(mode="json")
    assert snap.report_markdown.startswith("> **Acceptance passed.**")


def test_partial_run_uses_partial_names_header_and_tags(tmp_path):
    _, run, snap = _run(tmp_path, report=PARTIAL_REPORT_MD)
    root = run.paths.root
    assert snap.report_state == "partial_failed_acceptance"
    assert snap.acceptance.result == "fail" and snap.acceptance.reasons
    assert (root / "report-PARTIAL.md").is_file() and (root / "report-PARTIAL.pdf").is_file()
    assert not (root / "report.md").exists() and not (root / "report.pdf").exists()
    text = (root / "report-PARTIAL.md").read_text(encoding="utf-8")
    assert "FAILED ACCEPTANCE - PARTIAL RESEARCH" in text.splitlines()[0]
    assert "[unverified link]" in text and "[unverified price]" in text
    assert "https://made-up.example/source" in text  # tagged, never silently dropped
    assert snap.unsupported_report_urls == ["https://made-up.example/source"]


def test_insufficient_verified_prices_fails_acceptance_even_with_good_report(tmp_path):
    one_verified = COMPETITORS_JSON.replace('"status": "verified"', '"status": "unknown"', 2)
    _, run, snap = _run(tmp_path, competitors_json=one_verified)
    assert snap.report_state == "partial_failed_acceptance"
    assert any("verified price" in r for r in snap.acceptance.reasons)
    assert (run.paths.root / "report-PARTIAL.md").is_file()


def test_missing_report_is_failed_no_report_without_files(tmp_path):
    _, run, snap = _run(tmp_path, skip_report=True)
    assert snap.report_state == "failed_no_report"
    assert snap.acceptance.result == "fail"
    assert snap.report_markdown is None and snap.report_files == {}
    root = run.paths.root
    assert not any(
        (root / n).exists()
        for n in ("report.md", "report.pdf", "report-PARTIAL.md", "report-PARTIAL.pdf")
    )
    assert snap.status != "complete"


def test_cancelled_run_has_no_validated_report(tmp_path):
    import threading

    gate = threading.Event()
    manager = make_manager(tmp_path, executor=make_executor(gate=gate))
    run = manager.start(INPUT)
    time.sleep(0.15)
    manager.cancel(run.paths.run_id)
    snap = _finish(manager, run)
    assert snap.status == "cancelled" and snap.report_state != "validated_pass"
    assert snap.acceptance.result != "pass"


def test_revalidation_is_deterministic_and_has_no_override(tmp_path):
    _, run, snap = _run(tmp_path, report=PARTIAL_REPORT_MD)
    before = snap.validation.model_dump(mode="json")
    again = revalidate_run(run.paths)
    assert again.validation.model_dump(mode="json") == before
    assert again.validation.state == "partial_failed_acceptance"
    assert (run.paths.root / "report-PARTIAL.md").is_file()
    assert not (run.paths.root / "report.md").exists()


def test_state_and_report_restore_from_disk(tmp_path):
    _, run, live = _run(tmp_path, report=PARTIAL_REPORT_MD)
    restored = snapshot_from_disk(run.paths)
    assert restored.report_state == live.report_state
    assert restored.acceptance == live.acceptance
    assert restored.report_files == {"md": "report-PARTIAL.md", "pdf": "report-PARTIAL.pdf"}
    assert "FAILED ACCEPTANCE" in restored.report_markdown


def test_verification_section_labels_recommendation_and_inferred(tmp_path):
    _, _, snap = _run(tmp_path)
    text = snap.report_markdown
    assert "### Verification status" in text
    assert "Recommendation (not a verified fact)" in text
    assert "Inferred, unsupported by a source: Green Tiffin" in text
    assert "1 reported" in text and "1 inferred" in text


# ---------------------------------------------------------------- UI and zero-LLM guarantees


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def _fill(at: AppTest) -> None:
    r = at.tabs[0]
    r.text_input[0].set_value("Healthy millet meal boxes delivered for lunch")
    r.text_input[1].set_value("Coimbatore")
    r.text_input[2].set_value("office workers aged 25-40")


def _wait(manager):
    wait_idle(manager)


@pytest.fixture
def no_llm(monkeypatch):
    built: list[int] = []

    def fail_build(settings):
        built.append(1)
        raise AssertionError("LLM built by a non-AI action")

    def fail_call(self, *a, **k):
        raise AssertionError("LLM called by a non-AI action")

    monkeypatch.setattr("launchscout.llm.build_llm", fail_build)
    monkeypatch.setattr("launchscout.crew.build_llm", fail_build)
    monkeypatch.setattr("crewai.LLM.call", fail_call)
    return built


def test_ui_shows_validated_report_downloads_and_quality_panel(tmp_path, no_llm):
    manager = make_manager(tmp_path)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    _wait(manager)
    at.run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Report validated" in text and "Validated." in text
    assert any(e.label == "Full original six-section report (validated)" for e in at.expander)
    assert "ck-hero" in text  # a live completed run renders through the cockpit
    downloads = at.get("download_button")
    assert len(downloads) == 2
    assert {d.proto.label for d in downloads} == {"Download Markdown", "Download PDF"}
    assert no_llm == []


def test_ui_partial_report_banner_lists_reasons_and_marks_downloads(tmp_path, no_llm):
    manager = make_manager(tmp_path, executor=make_executor(report=PARTIAL_REPORT_MD))
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    _wait(manager)
    at.run()
    text = " ".join(m.value for m in at.markdown)
    assert "Report failed acceptance" in text and "Why acceptance did not pass" in text
    assert any(
        e.label == "Full original six-section report (PARTIAL, not validated)" for e in at.expander
    )
    labels = {d.proto.label for d in at.get("download_button")}
    assert labels == {"Download Markdown (PARTIAL)", "Download PDF (PARTIAL)"}
    assert "Report validated" not in text


def test_viewing_downloading_and_reruns_make_zero_additional_llm_calls(tmp_path, no_llm):
    calls = {"n": 0}
    inner = make_executor()

    def counting(run):
        calls["n"] += 1
        inner(run)

    manager = make_manager(tmp_path, executor=counting)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.button(key="run_research").click().run()
    _wait(manager)
    for _ in range(4):  # report view, quality panel, download buttons, tabs re-rendered
        at.run()
    assert calls["n"] == 1
    assert no_llm == []
    run_id = manager.latest_run_id()
    before = (tmp_path / "runs" / run_id / "events.jsonl").read_text(encoding="utf-8")
    at.run()
    after = (tmp_path / "runs" / run_id / "events.jsonl").read_text(encoding="utf-8")
    assert before == after, "viewing a finished run must not append events or call anything"


def test_report_modules_are_deterministic_and_import_no_llm_code():
    import ast

    forbidden = (
        "crewai",
        "openai",
        "litellm",
        "launchscout.llm",
        "launchscout.crew",
        "launchscout.agents",
        "launchscout.tasks",
        "launchscout.tools",
    )
    files = [
        "validation.py",
        "report.py",
        "links.py",
        "reporting.py",
        "exports/pdf.py",
        "exports/markdown.py",
    ]
    for name in files:
        tree = ast.parse((ROOT / "launchscout" / name).read_text(encoding="utf-8"))
        mods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
        assert not [m for m in mods if m.startswith(forbidden)], name
