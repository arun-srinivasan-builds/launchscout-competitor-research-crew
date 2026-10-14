import json
import threading
import time

import pytest

from launchscout.config import RunLimits
from launchscout.progress import AgentStatus
from launchscout.runner import RunManager, snapshot_from_disk
from launchscout.schemas import ResearchInput, ResearchMode
from tests.conftest import make_manager
from tests.helpers import make_executor

INPUT = ResearchInput(
    idea="Healthy millet meal boxes", city="Coimbatore", target_customer="office workers"
)


def wait_finished(manager: RunManager, run_id: str, timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        snap = manager.snapshot(run_id)
        if snap is not None and not snap.active:
            return snap
        time.sleep(0.02)
    raise AssertionError("run did not finish")


def test_complete_run_collects_outputs_and_artifacts(tmp_path):
    manager = make_manager(tmp_path)
    run = manager.start(INPUT)
    snap = wait_finished(manager, run.paths.run_id)
    assert snap.status == "complete" and snap.phase == "finished"
    assert snap.completed_tasks == [
        "Competitor research",
        "Customer review analysis",
        "Strategy and positioning",
        "Report writing",
    ]
    assert snap.competitors.competitors[0].price.status == "verified"
    assert snap.report_markdown and not snap.unsupported_report_urls
    root = run.paths.root
    for name in (
        "events.jsonl",
        "metadata.json",
        "competitors.json",
        "evidence.json",
        "report.md",
        "report.pdf",
        "report.writer.md",
        "validation.json",
        "grounding.json",
    ):
        assert (root / name).is_file(), name
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "complete"
    assert metadata["acceptance"]["result"] == "pass"
    assert snap.report_state == "validated_pass"
    assert snap.usage.basis == "measured" and snap.usage.total_tokens == 480
    assert snap.usage.serper_calls == 1 and snap.usage.cache_hits == 2


def test_states_come_from_events(tmp_path):
    manager = make_manager(tmp_path)
    run = manager.start(INPUT)
    snap = wait_finished(manager, run.paths.run_id)
    states = snap.agent_states()
    assert all(s.status is AgentStatus.COMPLETE for s in states.values())
    assert states["market_researcher"].tool_calls


def test_duplicate_run_prevented_while_active(tmp_path):
    gate = threading.Event()
    manager = make_manager(tmp_path, executor=make_executor(gate=gate))
    first = manager.start(INPUT)
    assert first is not None
    assert manager.active_run() is first
    assert manager.start(INPUT) is None
    gate.set()
    wait_finished(manager, first.paths.run_id)
    deadline = time.time() + 5
    while manager.active_run() is not None and time.time() < deadline:
        time.sleep(0.02)
    assert manager.start(INPUT) is not None


def test_cancel_marks_cancelled_and_keeps_partial_outputs(tmp_path):
    gate = threading.Event()
    manager = make_manager(
        tmp_path,
        executor=make_executor(
            gate=gate, steps=("Competitor research", "Customer review analysis")
        ),
    )
    run = manager.start(INPUT)
    time.sleep(0.2)
    assert manager.cancel(run.paths.run_id) is True
    assert manager.snapshot(run.paths.run_id).phase in ("stopping", "finished")
    assert manager.cancel(run.paths.run_id) is False
    snap = wait_finished(manager, run.paths.run_id)
    assert snap.status == "cancelled"
    assert any(e.kind == "run_cancelled" for e in snap.events)
    assert snap.agent_states()["report_writer"].task_label == "Not started"
    assert not snap.report_markdown


def test_timeout_state(tmp_path):
    gate = threading.Event()
    manager = make_manager(
        tmp_path,
        executor=make_executor(gate=gate),
        limits=RunLimits(run_timeout_s=1, tool_retries=0),
    )
    run = manager.start(INPUT)
    snap = wait_finished(manager, run.paths.run_id, timeout=8)
    assert snap.status == "timeout"
    assert any(e.kind == "run_timeout" for e in snap.events)


def test_crew_error_before_any_output_is_failed(tmp_path):
    def boom(run):
        raise RuntimeError("provider unavailable")

    manager = make_manager(tmp_path, executor=boom)
    run = manager.start(INPUT)
    snap = wait_finished(manager, run.paths.run_id)
    assert snap.status == "failed"
    assert "provider unavailable" in (snap.error or "")


def test_failure_midway_is_partial_not_complete(tmp_path):
    manager = make_manager(tmp_path, executor=make_executor(fail_after="Customer review analysis"))
    run = manager.start(INPUT)
    snap = wait_finished(manager, run.paths.run_id)
    assert snap.status == "partial"
    assert snap.completed_tasks == ["Competitor research", "Customer review analysis"]
    assert snap.report_markdown is None
    assert snap.strategy is None


def test_ungrounded_report_url_flagged(tmp_path):
    from launchscout.tools import ToolContext

    def executor(run):
        make_executor()(run)
        run.paths.report_md.write_text("see https://fabricated.example/p", encoding="utf-8")

    manager = make_manager(tmp_path, executor=executor)
    run = manager.start(INPUT)
    snap = wait_finished(manager, run.paths.run_id)
    assert snap.unsupported_report_urls == ["https://fabricated.example/p"]
    assert ToolContext  # imported for clarity


def test_state_survives_new_manager_via_disk(tmp_path):
    manager = make_manager(tmp_path)
    run = manager.start(INPUT)
    live = wait_finished(manager, run.paths.run_id)
    restored = snapshot_from_disk(run.paths)
    assert restored.status == live.status == "complete"
    assert restored.competitors.competitors[0].name == "Millet Kitchen"
    assert len(restored.events) == len(live.events)
    assert restored.agent_states()["report_writer"].status is AgentStatus.COMPLETE


def test_unfinished_run_on_disk_is_not_shown_as_running(tmp_path):
    from launchscout.runs import create_run_dir

    paths = create_run_dir(INPUT, base_dir=tmp_path / "runs")
    snap = snapshot_from_disk(paths)
    assert snap.phase == "finished" and "interrupted" in (snap.error or "")


def test_hierarchical_start_refused(tmp_path):
    manager = make_manager(tmp_path)
    hier = INPUT.model_copy(update={"mode": ResearchMode.HIERARCHICAL})
    with pytest.raises(NotImplementedError):
        manager.start(hier)
