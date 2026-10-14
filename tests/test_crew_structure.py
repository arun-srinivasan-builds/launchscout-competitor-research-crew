from datetime import date

import pytest
from crewai import LLM, Process

from launchscout.agents import ROLE_MARKET, ROLE_REVIEWS, ROLE_STRATEGY, ROLE_WRITER
from launchscout.config import RunLimits
from launchscout.crew import RunCancelled, build_crew
from launchscout.events import EventCollector
from launchscout.evidence import EvidenceLedger
from launchscout.schemas import ResearchInput, ResearchMode
from launchscout.tasks import TASK_ORDER
from launchscout.tools import ToolContext


@pytest.fixture
def ctx_and_crew(tmp_path):
    ctx = ToolContext(
        ledger=EvidenceLedger(),
        collector=EventCollector(),
        limits=RunLimits(),
        run_dir=tmp_path,
        today=date(2026, 10, 14),
    )
    research_input = ResearchInput(
        idea="Healthy {millet} meal boxes", city="Coimbatore", target_customer="office workers"
    )
    llm = LLM(model="openai/gpt-4o-mini", api_key="test-key-not-real")
    return ctx, build_crew(research_input, llm, ctx, RunLimits(), date(2026, 10, 14))


@pytest.fixture
def crew(ctx_and_crew):
    return ctx_and_crew[1]


def test_cancel_request_stops_crew_via_callbacks(ctx_and_crew):
    ctx, crew = ctx_and_crew
    crew.step_callback(object())  # not cancelled: no error
    ctx.cancel_event.set()
    with pytest.raises(RunCancelled):
        crew.step_callback(object())
    with pytest.raises(RunCancelled):
        crew.tasks[0].callback(type("Out", (), {"raw": "{}"})())


def test_four_distinct_agents(crew):
    roles = [a.role for a in crew.agents]
    assert roles == [ROLE_MARKET, ROLE_REVIEWS, ROLE_STRATEGY, ROLE_WRITER]
    assert len({a.goal for a in crew.agents}) == 4
    assert len({a.backstory for a in crew.agents}) == 4
    assert all(a.allow_delegation is False for a in crew.agents)


def test_tool_assignment_and_boundaries(crew):
    by_role = {a.role: [t.name for t in a.tools] for a in crew.agents}
    assert by_role[ROLE_MARKET] == ["Search the web", "Read web page"]
    assert by_role[ROLE_REVIEWS] == ["Search the web", "Read web page"]
    assert by_role[ROLE_STRATEGY] == []
    assert by_role[ROLE_WRITER] == ["Write report file"]


def test_task_fields_and_context_chain(crew):
    names = [t.name for t in crew.tasks]
    assert names == list(TASK_ORDER)
    for task in crew.tasks:
        assert task.description and task.expected_output and task.agent is not None
    research, reviews, strategy, report = crew.tasks
    assert not isinstance(research.context, list) or not research.context
    assert [t.name for t in reviews.context] == [research.name]
    assert [t.name for t in strategy.context] == [research.name, reviews.name]
    assert [t.name for t in report.context] == [research.name, reviews.name, strategy.name]


def test_sequential_process_and_bounded_agents(crew):
    assert crew.process == Process.sequential
    assert all(a.max_iter == RunLimits().agent_max_iter for a in crew.agents)
    assert all(a.max_execution_time == RunLimits().agent_timeout_s for a in crew.agents)


def test_user_braces_neutralised_in_descriptions(crew):
    assert "{" not in crew.tasks[0].description


def test_hierarchical_not_available_in_m3(tmp_path):
    ctx = ToolContext(
        ledger=EvidenceLedger(),
        collector=EventCollector(),
        limits=RunLimits(),
        run_dir=tmp_path,
        today=date(2026, 10, 14),
    )
    research_input = ResearchInput(
        idea="x y", city="c", target_customer="t", mode=ResearchMode.HIERARCHICAL
    )
    llm = LLM(model="openai/gpt-4o-mini", api_key="test-key-not-real")
    with pytest.raises(NotImplementedError):
        build_crew(research_input, llm, ctx, RunLimits(), date(2026, 10, 14))
