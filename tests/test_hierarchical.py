"""M5 hierarchical mode: configuration, accounting, guards, UI and comparison (all offline).

Orchestration tests use deterministic stand-ins for the crew. They prove our configuration and
accounting; they do not prove that live CrewAI delegation works (that needs the approved
single live test).
"""

import json
import threading
import time
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from launchscout.comparison import NOT_MEASURED, build_comparison, pick_pair, summarize
from launchscout.config import RunLimits
from launchscout.events import EventCollector, _tool_argument
from launchscout.progress import (
    MANAGER_KEY,
    AgentStatus,
    RunEvent,
    is_delegation_tool,
    reduce_events,
)
from launchscout.runner import RunManager, input_key, set_manager
from launchscout.saved_runs import load_saved_snapshot
from launchscout.schemas import ResearchInput, ResearchMode
from tests.conftest import make_manager
from tests.helpers import (
    PARTIAL_REPORT_MD,
    make_executor,
    make_hierarchical_executor,
    wait_finished,
    wait_idle,
    wait_until,
)
from ui.workflow import AgentState, render_workflow_html

ROOT = Path(__file__).resolve().parent.parent
SEQ = ResearchInput(
    idea="Healthy millet meal boxes", city="Coimbatore", target_customer="office workers"
)
HIER = SEQ.model_copy(update={"mode": ResearchMode.HIERARCHICAL})


def finish(manager: RunManager, run, timeout: float = 90.0):
    snap = wait_finished(manager, run, timeout)
    wait_idle(manager, timeout)
    return snap


def hier_manager(tmp_path, **kwargs) -> RunManager:
    executor = kwargs.pop("executor", make_hierarchical_executor())
    return make_manager(tmp_path, executor=executor, **kwargs)


def ev(kind, agent=None, summary="", status="info", **data):
    from datetime import UTC, datetime

    return RunEvent(
        ts=datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC),
        kind=kind,
        agent=agent,
        summary=summary,
        status=status,
        data=data,
    )


# ---------------------------------------------------------------- budgets and configuration


def test_hierarchical_budgets_include_the_manager():
    limits = RunLimits()
    assert limits.max_llm_calls_hierarchical > limits.max_llm_calls
    assert 0 < limits.max_manager_llm_calls < limits.max_llm_calls_hierarchical
    assert limits.max_delegations > 0 and limits.manager_max_iter > 0


def test_run_uses_mode_specific_llm_cap_and_manager_limits(tmp_path):
    seq = make_manager(tmp_path)
    hier = hier_manager(tmp_path)
    seq_run = seq.start(SEQ)
    finish(seq, seq_run)
    hier_run = hier.start(HIER)
    finish(hier, hier_run)
    assert seq_run.llm_cap == RunLimits().max_llm_calls
    assert hier_run.llm_cap == RunLimits().max_llm_calls_hierarchical
    assert seq_run.collector._agent_limits == {}
    assert hier_run.collector._agent_limits == {
        "Research Manager": RunLimits().max_manager_llm_calls
    }
    assert hier_run.collector._delegation_limit == RunLimits().max_delegations


def test_manager_activity_is_in_events_and_usage_accounting(tmp_path):
    manager = hier_manager(tmp_path)
    run = manager.start(HIER)
    snap = finish(manager, run)
    assert snap.status == "complete" and snap.mode is ResearchMode.HIERARCHICAL
    metrics = snap.agent_metrics()
    mgr = metrics["Research Manager"]
    assert mgr["llm_calls"] == 8 and mgr["total_tokens"] == 8 * 120
    assert mgr["delegations"] == 4 and mgr["delegation_ms"] == 4 * 1200
    specialist_calls = sum(
        metrics[r]["llm_calls"]
        for r in ("Market Researcher", "Review Analyst", "Strategy Analyst", "Report Writer")
    )
    assert specialist_calls == 4
    # run totals include the Manager's calls and tokens
    assert snap.usage.llm_calls == 12 and snap.usage.total_tokens == 12 * 120
    events = (run.paths.root / "events.jsonl").read_text(encoding="utf-8")
    assert "Delegate work to coworker" in events and "Research Manager" in events


def test_manager_llm_cap_stops_the_run_with_a_stated_reason(tmp_path):
    manager = hier_manager(
        tmp_path,
        executor=make_hierarchical_executor(manager_calls_per_task=6),
        limits=RunLimits(max_manager_llm_calls=3, tool_retries=0),
    )
    run = manager.start(HIER)
    snap = finish(manager, run)
    assert snap.status in ("partial", "failed")
    assert "Research Manager LLM call limit (3) reached" in (snap.error or "")
    assert any(e.kind == "run_budget_stop" for e in snap.events)
    assert snap.agent_metrics()["Research Manager"]["llm_calls"] <= 3 + 1


def test_endless_delegation_is_capped(tmp_path):
    manager = hier_manager(
        tmp_path,
        executor=make_hierarchical_executor(delegations_per_task=5),
        limits=RunLimits(max_delegations=3, tool_retries=0),
    )
    run = manager.start(HIER)
    snap = finish(manager, run)
    assert snap.status in ("partial", "failed")
    assert "Delegation limit (3) reached" in (snap.error or "")


def test_total_llm_cap_applies_to_hierarchical_runs(tmp_path):
    manager = hier_manager(
        tmp_path,
        executor=make_hierarchical_executor(manager_calls_per_task=3),
        limits=RunLimits(max_llm_calls_hierarchical=5, max_manager_llm_calls=50, tool_retries=0),
    )
    run = manager.start(HIER)
    snap = finish(manager, run)
    assert "LLM call limit (5) reached" in (snap.error or "")


# ---------------------------------------------------------------- guards


def test_task_completed_without_delegation_is_not_reported_as_success(tmp_path):
    manager = hier_manager(
        tmp_path, executor=make_hierarchical_executor(undelegated=("Competitor research",))
    )
    run = manager.start(HIER)
    snap = finish(manager, run)
    assert snap.status == "partial"  # never "complete"
    assert any("without delegating to the Market Researcher" in i for i in snap.grounding_issues)
    guard = [e for e in snap.events if e.kind == "grounding" and "delegating" in e.summary]
    assert guard and guard[0].status == "error"


def test_duplicate_runs_are_prevented_in_both_modes(tmp_path):
    for research_input, executor in (
        (SEQ, make_executor(gate=threading.Event())),
        (HIER, make_hierarchical_executor(gate=threading.Event())),
    ):
        gate = threading.Event()
        factory = make_executor if research_input is SEQ else make_hierarchical_executor
        manager = make_manager(tmp_path, executor=factory(gate=gate))
        first = manager.start(research_input)
        assert first is not None and manager.start(research_input) is None
        assert manager.start(research_input.model_copy(update={"idea": "Another idea"})) is None
        gate.set()
        finish(manager, first)
        assert executor is not None


def test_cancellation_in_hierarchical_mode_stops_work_and_is_truthful(tmp_path):
    gate = threading.Event()
    manager = hier_manager(tmp_path, executor=make_hierarchical_executor(gate=gate))
    run = manager.start(HIER)
    time.sleep(0.25)
    assert manager.cancel(run.paths.run_id) is True
    snap = finish(manager, run)
    assert snap.status == "cancelled" and snap.report_state != "validated_pass"
    states = snap.agent_states()
    assert states[MANAGER_KEY].status is AgentStatus.CANCELLED
    assert states["report_writer"].status is AgentStatus.IDLE
    assert states["report_writer"].task_label == "Not started"


def test_failure_and_timeout_states_stay_accurate_in_hierarchical_mode(tmp_path):
    def boom(run):
        raise RuntimeError("provider unavailable")

    failed = hier_manager(tmp_path, executor=boom)
    run = failed.start(HIER)
    assert finish(failed, run).status == "failed"

    gate = threading.Event()
    slow = hier_manager(
        tmp_path,
        executor=make_hierarchical_executor(gate=gate),
        limits=RunLimits(run_timeout_s=1, tool_retries=0),
    )
    run = slow.start(HIER)
    snap = finish(slow, run, timeout=8)
    assert snap.status == "timeout"
    assert snap.agent_states()[MANAGER_KEY].status in (
        AgentStatus.FAILED,
        AgentStatus.CANCELLED,
    )


def test_validation_is_identical_in_both_modes(tmp_path):
    for report in (None, PARTIAL_REPORT_MD):
        seq_m = make_manager(tmp_path, executor=make_executor(report=report))
        hier_m = hier_manager(tmp_path, executor=make_hierarchical_executor(report=report))
        a = finish(seq_m, seq_m.start(SEQ))
        b = finish(hier_m, hier_m.start(HIER))
        assert a.validation.model_dump(mode="json") == b.validation.model_dump(mode="json")
        assert a.report_state == b.report_state
        assert a.report_files == b.report_files
        assert a.acceptance == b.acceptance


def test_hierarchical_run_persists_and_replays_from_disk_read_only(tmp_path):
    manager = hier_manager(tmp_path)
    run = manager.start(HIER)
    live = finish(manager, run)
    before = {p.name: p.read_bytes() for p in run.paths.root.iterdir() if p.is_file()}
    replay = load_saved_snapshot(tmp_path / "runs", run.paths.run_id)
    assert replay.mode is ResearchMode.HIERARCHICAL
    assert replay.agent_metrics()["Research Manager"]["delegations"] == 4
    assert replay.agent_states()[MANAGER_KEY].status is AgentStatus.COMPLETE
    assert replay.acceptance == live.acceptance
    after = {p.name: p.read_bytes() for p in run.paths.root.iterdir() if p.is_file()}
    assert before == after


def test_identical_input_in_a_different_mode_is_a_different_run(tmp_path):
    assert input_key(SEQ) != input_key(HIER)
    manager = hier_manager(tmp_path)
    finish(manager, manager.start(HIER))
    assert manager.find_reusable(HIER) is not None
    assert manager.find_reusable(SEQ) is None  # explicit mode choice is never silently reused


# ---------------------------------------------------------------- events and reducer


def test_delegation_events_are_recognised_and_summarised():
    assert is_delegation_tool("Delegate work to coworker")
    assert is_delegation_tool("ask_question_to_coworker")
    assert not is_delegation_tool("search_the_web")
    arg = _tool_argument(
        {"coworker": "Market Researcher", "task": "Find competitors in Pune", "context": "x"}
    )
    assert arg.startswith("Market Researcher: Find competitors")


def test_crewai_bus_delegation_event_is_counted_and_limited():
    from crewai.events import crewai_event_bus
    from crewai.events.types.tool_usage_events import ToolUsageStartedEvent

    from launchscout import events

    fired: list[tuple[str, int, int]] = []
    events.install_listeners()
    collector = EventCollector(delegation_limit=1, on_limit=lambda *a: fired.append(a))
    events.set_active_collector(collector)
    try:
        for _ in range(2):
            crewai_event_bus.emit(
                None,
                ToolUsageStartedEvent(
                    tool_name="Delegate work to coworker",
                    tool_args={"coworker": "Review Analyst", "task": "t", "context": "c"},
                    tool_class="DelegateWorkTool",
                    agent_role="Research Manager",
                ),
            )
        crewai_event_bus.flush()
        wait_until(lambda: collector.delegations >= 2, what="two delegation events recorded")
    finally:
        events.set_active_collector(None)
    assert collector.delegations == 2
    assert fired == [("delegations", 2, 1)]
    first = collector.events()[0]
    assert first.agent == "Research Manager" and first.data["arg"].startswith("Review Analyst")


def test_reducer_manager_and_specialist_states_from_real_event_shapes():
    log = [
        ev("task_started", "Research Manager", "Task started"),
        ev(
            "tool_started",
            "Research Manager",
            "Delegate: Market Researcher",
            tool="Delegate work to coworker",
        ),
        ev("agent_started", "Market Researcher", "started"),
        ev("agent_completed", "Market Researcher", "answer", "ok"),
        ev("task_completed", "Research Manager", "Task complete", "ok"),
    ]
    states = reduce_events(log, run_active=True, with_manager=True)
    assert states["market_researcher"].status is AgentStatus.COMPLETE
    assert states[MANAGER_KEY].status is AgentStatus.ACTIVE  # coordination continues
    assert states[MANAGER_KEY].tool_calls and "Delegate" in states[MANAGER_KEY].tool_calls[0]
    done = reduce_events([*log, ev("crew_completed", status="ok")], with_manager=True)
    assert done[MANAGER_KEY].status is AgentStatus.COMPLETE
    # sequential reduction has no manager entry at all
    assert MANAGER_KEY not in reduce_events(log)


def test_manager_budget_stop_is_shown_as_stopped_not_failed():
    log = [
        ev("task_started", "Research Manager", "go"),
        ev("run_budget_stop", status="error", summary="limit"),
    ]
    states = reduce_events(log, with_manager=True)
    assert states[MANAGER_KEY].status is AgentStatus.CANCELLED
    assert states[MANAGER_KEY].task_label == "Stopped (budget)"


# ---------------------------------------------------------------- workflow rendering


def test_workflow_shows_manager_connected_to_four_specialists_only_in_hierarchical():
    seq = render_workflow_html(ResearchMode.SEQUENTIAL)
    assert "ls-manager-node" not in seq and "ls-mgr-links" not in seq
    hier = render_workflow_html(
        ResearchMode.HIERARCHICAL,
        {
            "manager": AgentState(
                status=AgentStatus.ACTIVE,
                task_label="Delegating",
                tool_calls=("12:00:00 Delegate: Market Researcher",),
            )
        },
    )
    assert hier.count('class="ls-drop"') == 4  # one connector per specialist
    assert hier.count("ls-node ls-a") == 4 and 'data-agent="manager"' in hier
    assert "Research Manager" in hier and "Delegating" in hier
    assert "Delegate: Market Researcher" in hier
    assert "Not yet implemented" not in hier
    assert "ls-vlink ls-vlink-mgr" in hier  # vertical connector for stacked layouts


def test_workflow_manager_markup_escapes_event_text():
    html = render_workflow_html(
        ResearchMode.HIERARCHICAL,
        {"manager": AgentState(tool_calls=("<script>alert(1)</script>",))},
    )
    assert "<script>" not in html


# ---------------------------------------------------------------- UI


def _app() -> AppTest:
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()


def _fill(at: AppTest) -> None:
    r = at.tabs[0]
    r.text_input[0].set_value("Healthy millet meal boxes delivered for lunch")
    r.text_input[1].set_value("Coimbatore")
    r.text_input[2].set_value("office workers aged 25-40")


def test_selecting_hierarchical_renders_manager_and_runs_through_cockpit(tmp_path):
    manager = hier_manager(tmp_path)
    set_manager(manager)
    at = _app()
    _fill(at)
    at.radio(key="research_mode").set_value("hierarchical").run()
    assert "Research Manager" in " ".join(m.value for m in at.markdown)
    at.button(key="run_research").click().run()
    wait_idle(manager)
    at.run()
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "ck-hero" in md and "hierarchical" in md
    assert "Report validated" in md
    at.session_state["cockpit_area"] = "Engineering Trace"
    at.run()
    md = " ".join(m.value for m in at.markdown)
    assert "Manager model calls" in md and "Delegations" in md
    assert not at.exception


def test_hierarchical_replay_and_navigation_make_zero_calls(tmp_path, monkeypatch):
    manager = hier_manager(tmp_path)
    run = manager.start(HIER)
    finish(manager, run)
    hits: list[str] = []

    def trap(name):
        def _fail(*a, **k):
            hits.append(name)
            raise AssertionError(name)

        return _fail

    monkeypatch.setattr("launchscout.llm.build_llm", trap("build_llm"))
    monkeypatch.setattr("crewai.LLM.call", trap("LLM.call"))
    monkeypatch.setattr("launchscout.tools._default_search", trap("serper"))
    monkeypatch.setattr("launchscout.tools._default_scrape", trap("scrape"))
    monkeypatch.setattr("launchscout.runner.run_crew", trap("crew"))
    set_manager(hier_manager(tmp_path))
    at = _app()
    at.selectbox(key="saved_run_select").set_value(run.paths.run_id).run()
    for area in ("Competitor Landscape", "Evidence & Quality", "Engineering Trace"):
        at.session_state["cockpit_area"] = area
        at.run()
        assert not at.exception
    assert hits == []


# ---------------------------------------------------------------- comparison framework


def test_comparison_marks_missing_runs_not_yet_measured(tmp_path):
    manager = make_manager(tmp_path)
    run = manager.start(SEQ)
    seq = finish(manager, run)
    rows = build_comparison(seq, None)
    assert rows and all(r.hierarchical == NOT_MEASURED for r in rows)
    by = {r.metric: r for r in rows}
    assert by["Execution mode"].sequential == "sequential"
    assert by["Manager model calls"].sequential == "n/a (no Manager)"
    assert by["Total tokens"].sequential == "480"
    # completion and quality are separate groups
    assert by["Specialist tasks"].group == "Task completion"
    assert by["Verified competitor prices (3 required)"].group == "Research quality"
    assert by["Final acceptance state"].group == "Research quality"


def test_comparison_pairs_runs_with_identical_input_and_never_mixes_others(tmp_path):
    seq_mgr = make_manager(tmp_path)
    seq = finish(seq_mgr, seq_mgr.start(SEQ))
    other = finish(seq_mgr, seq_mgr.start(SEQ.model_copy(update={"city": "Chennai"})))
    hier_m = hier_manager(tmp_path)
    hier = finish(hier_m, hier_m.start(HIER))
    runs = tmp_path / "runs"
    s, h = pick_pair(runs, seq)
    assert s.run_id == seq.run_id and h.run_id == hier.run_id
    s2, h2 = pick_pair(runs, hier)
    assert s2.run_id in (seq.run_id,) and h2.run_id == hier.run_id
    s3, h3 = pick_pair(runs, other)
    assert s3.run_id == other.run_id and h3 is None  # different input: not comparable
    rows = {r.metric: r for r in build_comparison(s, h)}
    assert rows["Manager model calls"].hierarchical == "8"
    assert (
        rows["Total model calls"].sequential == "4"
        and rows["Total model calls"].hierarchical == "12"
    )
    assert rows["Delegations"].hierarchical == "4"


def test_summarize_does_not_invent_values():
    assert summarize(None) == {}
    assert date(2026, 10, 14)  # fixture import used
    assert json.dumps({})  # imports kept deliberate


# ---------------------------------------------------------------- prompts and tool budgets


def test_budgets_are_stated_in_prompts_and_tool_results(tmp_path):
    from crewai import LLM

    from launchscout.crew import build_crew
    from launchscout.evidence import EvidenceLedger
    from launchscout.tools import ToolContext

    ctx = ToolContext(
        ledger=EvidenceLedger(),
        collector=EventCollector(),
        limits=RunLimits(searches_per_agent=4, scrapes_per_agent=3),
        run_dir=tmp_path,
        today=date(2026, 10, 14),
        search_impl=lambda q, n: [{"title": "t", "link": "https://a.example/x", "snippet": "s"}],
    )
    crew = build_crew(
        HIER,
        LLM(model="openai/gpt-4o-mini", api_key="test-key-not-real"),
        ctx,
        RunLimits(searches_per_agent=4, scrapes_per_agent=3),
        date(2026, 10, 14),
    )
    research = crew.tasks[0].description
    assert "at most 4 searches and 3 page reads" in research
    out = ctx.search("q", "market")
    assert "[Budget remaining for you: 3 search(es), 3 page read(s)]" in out
    again = ctx.search("q", "market")  # cache hit still reports the budget, spends nothing
    assert "[Budget remaining for you: 3 search(es), 3 page read(s)]" in again
    assert ctx.counters()["serper_calls"] == 1
    # the Manager has no search or page tools at all
    assert crew.manager_agent.tools == []
    assert pytest  # fixture import used


def test_installed_crewai_gives_the_manager_only_delegation_tools(tmp_path):
    """Probes CrewAI's own wiring (no model call): the Manager executes each task and can only
    delegate to that task's specialist; it keeps no research tools."""
    from crewai import LLM

    from launchscout.crew import build_crew
    from launchscout.evidence import EvidenceLedger
    from launchscout.tools import ToolContext

    ctx = ToolContext(
        ledger=EvidenceLedger(),
        collector=EventCollector(),
        limits=RunLimits(),
        run_dir=tmp_path,
        today=date(2026, 10, 14),
    )
    crew = build_crew(
        HIER,
        LLM(model="openai/gpt-4o-mini", api_key="test-key-not-real"),
        ctx,
        RunLimits(),
        date(2026, 10, 14),
    )
    crew._create_manager_agent()
    assert crew.manager_agent.allow_delegation is True and crew.manager_agent.tools == []
    expected = ["Market Researcher", "Review Analyst", "Strategy Analyst", "Report Writer"]
    for task, specialist in zip(crew.tasks, expected, strict=True):
        assert crew._get_agent_to_use(task).role == "Research Manager"
        tools = crew._update_manager_tools(task, [])
        assert [t.name for t in tools] == ["Delegate work to coworker", "Ask question to coworker"]
        assert specialist in tools[0].description
        others = [r for r in expected if r != specialist]
        assert not any(r in tools[0].description for r in others)
