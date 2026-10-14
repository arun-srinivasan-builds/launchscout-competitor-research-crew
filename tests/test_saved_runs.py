"""Saved runs: persistence, restart recovery, labels and zero-call replay."""

import hashlib
import json
import shutil
import threading
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from launchscout.runner import RunManager, set_manager, snapshot_from_disk
from launchscout.runs import RunPaths
from launchscout.saved_runs import (
    LABEL_TEXT,
    classify,
    find_matching_saved_run,
    is_safe_run_id,
    list_saved_runs,
    load_saved_snapshot,
)
from launchscout.schemas import ResearchInput
from tests.conftest import make_manager
from tests.helpers import PARTIAL_REPORT_MD, make_executor, wait_finished, wait_idle

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
INPUT = ResearchInput(
    idea="Healthy millet meal boxes", city="Coimbatore", target_customer="office workers"
)
OTHER = ResearchInput(idea="Cold pressed juice", city="Pune", target_customer="gym-goers")


def _finish(manager: RunManager, run):
    return wait_finished(manager, run)


def _run(manager: RunManager, research_input: ResearchInput = INPUT):
    run = manager.start(research_input)
    wait_finished(manager, run)
    wait_idle(manager)
    return run


def _digest(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# ------------------------------------------------------------------ persistence


def test_run_persists_all_required_artifacts(tmp_path):
    manager = make_manager(tmp_path)
    run = _run(manager)
    names = {p.name for p in run.paths.root.iterdir()}
    for required in (
        "input.json",
        "metadata.json",
        "events.jsonl",
        "evidence.json",
        "validation.json",
        "report.md",
        "report.pdf",
        "report.writer.md",
        "competitors.json",
        "reviews.json",
        "strategy.json",
        "grounding.json",
    ):
        assert required in names, required
    meta = json.loads((run.paths.root / "metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "complete" and meta["model_name"]
    assert meta["usage"]["basis"] == "measured" and meta["usage"]["total_tokens"]
    assert meta["acceptance"]["result"] == "pass"


def test_labels_distinguish_validated_partial_failed_and_cancelled(tmp_path):
    runs_dir = tmp_path / "runs"
    validated = _run(make_manager(tmp_path))
    partial = _run(make_manager(tmp_path, executor=make_executor(report=PARTIAL_REPORT_MD)), OTHER)

    def boom(run):
        raise RuntimeError("provider unavailable")

    failed = _run(
        make_manager(tmp_path, executor=boom),
        INPUT.model_copy(update={"idea": "Failing idea here"}),
    )
    gate = threading.Event()
    cancel_mgr = make_manager(tmp_path, executor=make_executor(gate=gate))
    cancelled_run = cancel_mgr.start(INPUT.model_copy(update={"idea": "Cancelled idea here"}))
    time.sleep(0.15)
    cancel_mgr.cancel(cancelled_run.paths.run_id)
    _finish(cancel_mgr, cancelled_run)

    labels = {s.run_id: s.label for s in list_saved_runs(runs_dir)}
    assert labels[validated.paths.run_id] == "validated"
    assert labels[partial.paths.run_id] == "partial"
    assert labels[failed.paths.run_id] == "failed"
    assert labels[cancelled_run.paths.run_id] == "cancelled"
    assert len(set(labels.values())) == 4
    assert all(LABEL_TEXT[v] for v in labels.values())


def test_classify_covers_timeout_interrupted_and_legacy():
    assert classify("timeout", None, False, True) == "timed_out"
    assert classify("running", None, False, False) == "interrupted"
    assert classify("complete", None, True, True) == "legacy"
    assert classify("complete", "validated_pass", True, True) == "validated"
    assert classify("cancelled", "failed_no_report", False, True) == "cancelled"


def test_listing_is_newest_first_and_skips_unreadable_or_unsafe(tmp_path):
    manager = make_manager(tmp_path)
    first = _run(manager)
    second = _run(manager, OTHER)
    runs_dir = tmp_path / "runs"
    (runs_dir / "garbage").mkdir()
    (runs_dir / "garbage" / "metadata.json").write_text("{not json", encoding="utf-8")
    ids = [s.run_id for s in list_saved_runs(runs_dir)]
    assert ids == [second.paths.run_id, first.paths.run_id]
    assert not is_safe_run_id("../etc") and not is_safe_run_id("a/b") and not is_safe_run_id("")
    assert load_saved_snapshot(runs_dir, "../runs") is None
    assert load_saved_snapshot(runs_dir, "does-not-exist") is None


# ------------------------------------------------------------------ restart recovery


def test_restart_recovers_full_state_from_disk(tmp_path):
    live_mgr = make_manager(tmp_path, executor=make_executor(report=PARTIAL_REPORT_MD))
    run = _run(live_mgr)
    live = live_mgr.snapshot(run.paths.run_id)

    fresh = make_manager(tmp_path)  # a restarted server: empty memory, same runs directory
    assert fresh.latest_run_id() is None
    restored = load_saved_snapshot(fresh.runs_dir(), run.paths.run_id)
    assert restored.status == live.status == "complete"
    assert restored.report_state == live.report_state == "partial_failed_acceptance"
    assert restored.acceptance == live.acceptance
    assert restored.report_markdown == live.report_markdown
    assert restored.report_files == {"md": "report-PARTIAL.md", "pdf": "report-PARTIAL.pdf"}
    assert [e.kind for e in restored.events] == [e.kind for e in live.events]
    assert restored.usage.total_tokens == live.usage.total_tokens
    assert len(restored.evidence) == len(live.evidence)
    assert restored.completed_tasks == live.completed_tasks and len(restored.completed_tasks) == 4
    assert restored.agent_states().keys() == live.agent_states().keys()
    assert {k: v.status for k, v in restored.agent_states().items()} == {
        k: v.status for k, v in live.agent_states().items()
    }


def test_run_left_running_on_disk_is_shown_as_interrupted_not_running(tmp_path):
    from launchscout.runs import create_run_dir

    paths = create_run_dir(INPUT, base_dir=tmp_path / "runs")
    summary = next(s for s in list_saved_runs(tmp_path / "runs") if s.run_id == paths.run_id)
    assert summary.label == "interrupted"
    snap = snapshot_from_disk(paths)
    assert snap.phase == "finished" and "interrupted" in (snap.error or "")


def test_identical_input_is_reused_from_disk_after_restart(tmp_path):
    first = _run(make_manager(tmp_path))
    assert find_matching_saved_run(tmp_path / "runs", INPUT) == first.paths.run_id
    assert find_matching_saved_run(tmp_path / "runs", OTHER) is None


# ------------------------------------------------------------------ UI replay, zero calls


def _app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


@pytest.fixture
def no_calls(monkeypatch):
    """Any LLM, Serper, scrape or crew execution during replay fails the test."""
    hits: list[str] = []

    def trap(name):
        def _fail(*a, **k):
            hits.append(name)
            raise AssertionError(f"{name} called during saved-run replay")

        return _fail

    monkeypatch.setattr("launchscout.llm.build_llm", trap("build_llm"))
    monkeypatch.setattr("launchscout.crew.build_llm", trap("crew.build_llm"))
    monkeypatch.setattr("crewai.LLM.call", trap("LLM.call"))
    monkeypatch.setattr("launchscout.tools._default_search", trap("serper"))
    monkeypatch.setattr("launchscout.tools._default_scrape", trap("scrape"))
    monkeypatch.setattr("launchscout.runner.run_crew", trap("run_sequential"))
    return hits


def test_ui_restores_saved_run_after_restart_with_zero_calls(tmp_path, no_calls):
    # one run per label so switching exercises every state
    writer = make_manager(tmp_path)
    ok = _run(writer)
    partial = _run(make_manager(tmp_path, executor=make_executor(report=PARTIAL_REPORT_MD)), OTHER)
    before = {p.name: _digest(p) for p in (tmp_path / "runs").iterdir() if p.is_dir()}

    executions = {"n": 0}
    inner = make_executor()

    def counting(run):
        executions["n"] += 1
        inner(run)

    restarted = make_manager(tmp_path, executor=counting)
    set_manager(restarted)
    at = _app()
    assert not at.exception
    box = at.selectbox(key="saved_run_select")
    assert len(box.options) == 3  # "" + two saved runs
    assert not at.get("download_button")  # nothing selected yet: idle view

    box.set_value(ok.paths.run_id).run()
    assert not at.exception
    first = " ".join(m.value for m in at.markdown)
    assert "Report validated" in first and "ck-hero" in first
    assert any("Viewing saved run" in i.value for i in at.info)
    assert {d.proto.label for d in at.get("download_button")} == {
        "Download Markdown",
        "Download PDF",
    }
    md = " ".join(m.value for m in at.markdown)
    assert "Run complete: 4/4 tasks completed" in md and "ls-st-complete" in md

    at.selectbox(key="saved_run_select").set_value(partial.paths.run_id).run()
    assert "Report failed acceptance" in " ".join(m.value for m in at.markdown)
    assert {d.proto.label for d in at.get("download_button")} == {
        "Download Markdown (PARTIAL)",
        "Download PDF (PARTIAL)",
    }
    for _ in range(3):
        at.run()  # reruns while viewing

    at.selectbox(key="saved_run_select").set_value("").run()  # back to the live/idle view
    assert not at.get("download_button")

    assert executions["n"] == 0 and no_calls == []
    assert restarted.latest_run_id() is None  # nothing was started or adopted
    after = {p.name: _digest(p) for p in (tmp_path / "runs").iterdir() if p.is_dir()}
    assert before == after, "replay must not modify any saved run"


def test_legacy_pre_validation_run_is_shown_as_saved_never_regenerated(tmp_path, no_calls):
    run = _run(make_manager(tmp_path))
    root = run.paths.root
    for name in ("validation.json", "report.pdf", "report.writer.md"):
        (root / name).unlink()
    meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    meta["acceptance"] = {"result": "not_evaluated", "reasons": []}
    (root / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    before = _digest(root)

    set_manager(make_manager(tmp_path))
    at = _app()
    assert (
        next(s for s in list_saved_runs(tmp_path / "runs") if s.run_id == run.paths.run_id).label
        == "legacy"
    )
    at.selectbox(key="saved_run_select").set_value(run.paths.run_id).run()
    assert not at.exception
    legacy_md = " ".join(m.value for m in at.markdown)
    assert "saved before report validation existed" in legacy_md
    assert "Report validated" not in legacy_md
    assert {d.proto.label for d in at.get("download_button")} == {"Download Markdown (UNVALIDATED)"}
    assert any(e.label == "Full report as saved (never validated)" for e in at.expander)
    assert _digest(root) == before and not (root / "report.pdf").exists()
    assert no_calls == []


def test_saved_runs_not_selectable_while_a_run_is_active(tmp_path):
    saved = _run(make_manager(tmp_path))
    gate = threading.Event()
    manager = make_manager(tmp_path, executor=make_executor(gate=gate))
    set_manager(manager)
    at = _app()
    r = at.tabs[0]
    r.text_input[0].set_value("A different idea entirely")
    r.text_input[1].set_value("Chennai")
    r.text_input[2].set_value("students")
    at.button(key="run_research").click().run()
    assert at.selectbox(key="saved_run_select").disabled is True
    options = at.selectbox(key="saved_run_select").options
    assert any("[VALIDATED]" in o for o in options)
    assert any("[RUNNING NOW]" not in o and "INTERRUPTED" not in o for o in options)
    assert any("RUNNING NOW" in o for o in options)  # the live run is not "interrupted"
    assert saved.paths.run_id
    gate.set()
    wait_idle(manager)


def test_starting_a_new_run_returns_view_to_the_live_run(tmp_path):
    saved = _run(make_manager(tmp_path))
    manager = make_manager(tmp_path)
    set_manager(manager)
    at = _app()
    at.selectbox(key="saved_run_select").set_value(saved.paths.run_id).run()
    assert any("Viewing saved run" in i.value for i in at.info)
    r = at.tabs[0]
    r.text_input[0].set_value("A brand new idea for juice")
    r.text_input[1].set_value("Delhi")
    r.text_input[2].set_value("commuters")
    at.button(key="run_research").click().run()
    wait_idle(manager)
    at.run()
    assert at.selectbox(key="saved_run_select").value == ""
    assert not any("Viewing saved run" in i.value for i in at.info)
    assert manager.latest_run_id() != saved.paths.run_id


@pytest.mark.skipif(
    not (ROOT / "runs").is_dir() or not any((ROOT / "runs").iterdir()),
    reason="no local saved runs (runs/ is gitignored)",
)
def test_real_saved_runs_load_read_only_if_present(tmp_path):
    """Copies of the developer's actual runs (L1-L5 etc.) replay without changes."""
    real = ROOT / "runs"
    copy = tmp_path / "runs"
    shutil.copytree(real, copy)
    before = {p.name: _digest(p) for p in copy.iterdir() if p.is_dir()}
    summaries = list_saved_runs(copy)
    assert summaries, "expected readable saved runs"
    for summary in summaries:
        snap = load_saved_snapshot(copy, summary.run_id)
        assert snap is not None and snap.phase == "finished"
        assert snap.agent_states()  # reducer works on historical events
        if snap.report_markdown:
            assert snap.report_files
    assert {p.name: _digest(p) for p in copy.iterdir() if p.is_dir()} == before
    assert RunPaths  # imported for type clarity
