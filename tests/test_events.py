import time
from datetime import UTC, datetime

from launchscout import events
from launchscout.events import EventCollector, load_events
from launchscout.progress import AGENT_ORDER, AgentStatus, RunEvent, reduce_events


def ev(kind, agent=None, summary="", status="info", **data):
    return RunEvent(
        ts=datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC),
        kind=kind,
        agent=agent,
        summary=summary,
        status=status,
        data=data,
    )


def test_no_events_means_all_idle_and_not_simulated():
    states = reduce_events([])
    assert set(states) == set(AGENT_ORDER)
    assert all(s.status is AgentStatus.IDLE for s in states.values())
    assert all(not s.events and not s.tool_calls for s in states.values())
    assert all(s.progress_percent is None for s in states.values())


def test_run_active_marks_agents_queued_not_active():
    states = reduce_events([ev("run_started")], run_active=True)
    assert all(s.status is AgentStatus.IDLE and s.task_label == "Queued" for s in states.values())


def test_event_mapping_active_tool_complete_failed():
    log = [
        ev("task_started", "Market Researcher", "Task started: Competitor research"),
        ev("tool_started", "Market Researcher", "search_the_web: q", tool="search_the_web"),
        ev("task_completed", "Market Researcher", "Task complete", "ok"),
        ev("task_started", "Review Analyst", "Task started"),
        ev("tool_started", "Review Analyst", "read_web_page: u", tool="read_web_page"),
        ev("task_failed", "Review Analyst", "Task failed", "error"),
        ev("task_started", "Strategy Analyst", "Task started"),
    ]
    states = reduce_events(log, run_active=True)
    assert states["market_researcher"].status is AgentStatus.COMPLETE
    assert states["market_researcher"].tool_calls and "search_the_web" in (
        states["market_researcher"].tool_calls[0]
    )
    assert states["review_analyst"].status is AgentStatus.FAILED
    assert states["strategy_analyst"].status is AgentStatus.ACTIVE
    assert states["report_writer"].status is AgentStatus.IDLE


def test_tool_label_uses_normalised_tool_names():
    log = [ev("tool_started", "Market Researcher", "x", tool="search_the_web")]
    assert reduce_events(log, True)["market_researcher"].task_label == "Searching the web"


def test_cancel_and_timeout_states():
    base = [ev("task_started", "Market Researcher", "go")]
    cancelled = reduce_events(base + [ev("run_cancelled")], run_active=False)
    assert cancelled["market_researcher"].status is AgentStatus.CANCELLED
    assert cancelled["report_writer"].task_label == "Not started"
    timed = reduce_events(base + [ev("run_timeout")], run_active=False)
    assert timed["market_researcher"].status is AgentStatus.FAILED
    assert timed["market_researcher"].task_label == "Timed out"


def test_collector_redacts_secrets_and_persists(tmp_path):
    path = tmp_path / "events.jsonl"
    collector = EventCollector(path)
    collector.emit("tool_note", "key sk-ABCDEFGH12345678 leaked", token="sk-ZZZZZZZZ99999999")
    stored = path.read_text(encoding="utf-8")
    assert "sk-ABCDEFGH" not in stored and "sk-ZZZZZZZZ" not in stored
    assert load_events(path)[0].kind == "tool_note"


def test_usage_is_measured_only_when_reported():
    collector = EventCollector()
    collector.add_usage(None)
    assert collector.usage_reported is False
    collector.add_usage({"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    assert collector.usage_reported and collector.total_tokens == 15


def test_crewai_bus_events_reach_active_collector():
    from crewai.events import crewai_event_bus
    from crewai.events.types.tool_usage_events import ToolUsageStartedEvent

    events.install_listeners()
    collector = EventCollector()
    events.set_active_collector(collector)
    try:
        event = ToolUsageStartedEvent(
            tool_name="search_the_web",
            tool_args={"search_query": "millet"},
            tool_class="GuardedSearchTool",
            agent_role="Market Researcher",
        )
        crewai_event_bus.emit(None, event)
        crewai_event_bus.flush()
        deadline = time.time() + 3
        while not collector.events() and time.time() < deadline:
            time.sleep(0.05)
    finally:
        events.set_active_collector(None)
    recorded = collector.events()
    assert recorded and recorded[0].kind == "tool_started"
    assert recorded[0].agent == "Market Researcher"
    assert recorded[0].data["arg"] == "millet"


def test_errors_after_cancel_request_show_cancelled_not_failed():
    log = [
        ev("task_started", "Market Researcher", "go"),
        ev("run_cancel_requested"),
        ev("task_failed", "Market Researcher", "stopped", "error"),
        ev("run_cancelled"),
    ]
    states = reduce_events(log, run_active=False)
    assert states["market_researcher"].status is AgentStatus.CANCELLED
