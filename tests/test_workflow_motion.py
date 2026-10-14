"""Post-M6 workflow visualization: event-driven connector motion, full delegation list and
offline replay. Everything here is derived from recorded events; no model, search or crew runs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from launchscout.progress import (
    MANAGER_KEY,
    AgentStatus,
    active_links,
    reduce_events,
    replay_states,
)
from launchscout.runner import set_manager
from launchscout.saved_runs import load_saved_snapshot
from launchscout.schemas import ResearchMode
from tests.conftest import make_manager
from tests.test_hierarchical import HIER, SEQ, _app, ev, finish, hier_manager
from ui.theme import _CSS
from ui.workflow import render_workflow_html

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"

MR, RA, SA, RW, MGR = (
    "Market Researcher",
    "Review Analyst",
    "Strategy Analyst",
    "Report Writer",
    "Research Manager",
)


def _seq_events():
    return [
        ev("task_started", MR, "Task started"),
        ev("agent_started", MR, "started"),
        ev("tool_started", MR, "search_the_web: q", tool="search_the_web"),
        ev("agent_completed", MR, "answer", "ok"),
        ev("task_completed", MR, "Task complete", "ok"),
        ev("task_started", RA, "Task started"),
        ev("agent_started", RA, "started"),
        ev("agent_completed", RA, "answer", "ok"),
        ev("task_completed", RA, "Task complete", "ok"),
        ev("task_started", SA, "Task started"),
        ev("agent_started", SA, "started"),
        ev("agent_completed", SA, "answer", "ok"),
        ev("task_completed", SA, "Task complete", "ok"),
        ev("task_started", RW, "Task started"),
        ev("agent_started", RW, "started"),
        ev("agent_completed", RW, "answer", "ok"),
        ev("task_completed", RW, "Task complete", "ok"),
        ev("crew_completed", None, "done", "ok"),
    ]


def _delegate(role, task="do the work"):
    return ev(
        "tool_started",
        MGR,
        f"delegate_work_to_coworker: {role}: {task}",
        tool="delegate_work_to_coworker",
    )


def _hier_events():
    out = [ev("agent_started", MGR, "Manager started")]
    for role in (MR, RA, SA, RW):
        out += [
            ev("task_started", role, "Task started"),
            _delegate(role, f"task for {role}"),
            ev("agent_started", role, "started"),
            ev("agent_completed", role, "answer", "ok"),
            ev("task_completed", role, "Task complete", "ok"),
        ]
    out.append(ev("tool_started", MGR, "write_report_file", tool="write_report_file"))
    out.append(ev("crew_completed", None, "done", "ok"))
    return out


# ------------------------------------------------------------------ connector motion
def test_sequential_connector_follows_recorded_task_transitions():
    events = _seq_events()
    seen = []
    for pos in range(len(events) + 1):
        states = replay_states(events, pos)
        seen.append(active_links(states))
    # nothing moves before the first handoff and the links light up in recorded order
    assert seen[0] == frozenset() and seen[3] == frozenset()
    order = [next(iter(s)) for s in seen if s]
    assert order[0] == "flow-1-2" and order[-1] == "flow-3-4"
    firsts = []
    for link in order:
        if link not in firsts:
            firsts.append(link)
    assert firsts == ["flow-1-2", "flow-2-3", "flow-3-4"]
    # a link is active only while its source is complete and its target is active
    states = replay_states(events, 7)  # review analyst started, market researcher complete
    assert active_links(states) == frozenset({"flow-1-2"})
    assert states["market_researcher"].status is AgentStatus.COMPLETE
    assert states["review_analyst"].status is AgentStatus.ACTIVE


def test_manager_links_are_driven_only_by_recorded_delegations():
    # Manager active, specialist active, but no delegation recorded: no manager motion
    no_delegation = [
        ev("agent_started", MGR, "Manager started"),
        ev("task_started", MR, "Task started"),
        ev("agent_started", MR, "started"),
    ]
    states = reduce_events(no_delegation, run_active=True, with_manager=True)
    assert not any(link.startswith("delegate-") for link in active_links(states, True))
    # a non-delegation Manager tool call is not a delegation either
    other = [*no_delegation, ev("tool_started", MGR, "write_report_file", tool="write_report_file")]
    states = reduce_events(other, run_active=True, with_manager=True)
    assert not any(link.startswith("delegate-") for link in active_links(states, True))
    # a recorded delegation to the Review Analyst lights only delegate-2, and only while active
    events = [
        ev("agent_started", MGR, "Manager started"),
        ev("task_started", RA, "Task started"),
        _delegate(RA),
        ev("agent_started", RA, "started"),
    ]
    states = reduce_events(events, run_active=True, with_manager=True)
    assert active_links(states, True) == frozenset({"delegate-2"})
    done = [
        *events,
        ev("agent_completed", RA, "answer", "ok"),
        ev("task_completed", RA, "ok", "ok"),
    ]
    states = reduce_events(done, run_active=True, with_manager=True)
    assert "delegate-2" not in active_links(states, True)
    # sequential runs never produce manager links
    assert not any(
        link.startswith("delegate-") for link in active_links(replay_states(_hier_events(), 9))
    )


def test_idle_and_finished_workflows_have_no_moving_connector():
    assert active_links(None) == frozenset()
    assert active_links(reduce_events([], run_active=False)) == frozenset()
    for events, hier in ((_seq_events(), False), (_hier_events(), True)):
        final = replay_states(events, len(events), hier)
        assert active_links(final, hier) == frozenset()
        html = render_workflow_html(
            ResearchMode.HIERARCHICAL if hier else ResearchMode.SEQUENTIAL,
            final,
            "done",
            active_links(final, hier),
        )
        assert "ls-live" not in html
    idle = render_workflow_html(ResearchMode.SEQUENTIAL, None, "idle", frozenset())
    assert "ls-live" not in idle


def test_live_class_is_rendered_only_on_active_connectors():
    events = _seq_events()
    states = replay_states(events, 7)
    html = render_workflow_html(ResearchMode.SEQUENTIAL, states, "x", active_links(states))
    live = re.findall(r'data-link="([^"]+)"', html)
    assert "flow-1-2" in live
    marked = re.findall(r'class="[^"]*ls-live[^"]*" data-link="([^"]+)"', html)
    assert set(marked) == {"flow-1-2"}
    hier = replay_states(_hier_events(), 4, True)  # inside the first delegation
    html = render_workflow_html(ResearchMode.HIERARCHICAL, hier, "x", active_links(hier, True))
    marked = re.findall(r'ls-drop ls-live" data-link="([^"]+)"', html)
    assert marked == ["delegate-1"]


# ------------------------------------------------------------------ delegation list
def test_all_delegations_are_listed_in_recorded_order_and_kept_apart():
    states = replay_states(_hier_events(), len(_hier_events()), True)
    manager = states[MANAGER_KEY]
    assert len(manager.delegations) == 4
    roles = [re.search(r"Delegated to ([A-Za-z ]+)", d).group(1) for d in manager.delegations]
    assert roles == [MR, RA, SA, RW]
    assert not any("delegate" in c.lower() for c in manager.tool_calls)
    assert any("write_report_file" in c for c in manager.tool_calls)
    html = render_workflow_html(ResearchMode.HIERARCHICAL, states, "x")
    items = re.findall(r"<li>([^<]*Delegated to[^<]*)</li>", html)
    assert len(items) == 4
    assert [i.split("Delegated to ")[1].split(":")[0] for i in items] == roles


@pytest.mark.skipif(
    not any(RUNS.glob("*c0fe")), reason="saved L6 run is not present on this machine"
)
def test_saved_l6_shows_all_four_recorded_delegations():
    run_id = next(RUNS.glob("*c0fe")).name
    snap = load_saved_snapshot(RUNS, run_id)
    manager = snap.agent_states()[MANAGER_KEY]
    assert len(manager.delegations) == 4
    recorded = [e for e in snap.events if e.kind == "tool_started" and "coworker" in e.summary]
    assert len(recorded) == 4
    assert [d.split(" Delegated to ")[1].split(":")[0] for d in manager.delegations] == [
        e.summary.split(": ")[1] for e in recorded
    ]


# ------------------------------------------------------------------ replay
def test_replay_preserves_event_order_and_is_monotonic():
    events = _hier_events()
    previous = -1
    for pos in range(len(events) + 1):
        states = replay_states(events, pos, True)
        applied = sum(len(s.delegations) for s in states.values())
        assert applied >= previous  # delegations only ever accumulate, in order
        previous = applied
        # the state at a position equals reducing exactly that prefix
        expected = reduce_events(events[:pos], run_active=pos < len(events), with_manager=True)
        assert states == expected
    assert replay_states(events, -5, True) == replay_states(events, 0, True)
    assert replay_states(events, 999, True) == replay_states(events, len(events), True)


def test_replay_final_state_equals_saved_run_view(tmp_path):
    for research_input, build in ((SEQ, make_manager), (HIER, hier_manager)):
        manager = build(tmp_path / research_input.mode.value)
        run = manager.start(research_input)
        snap = finish(manager, run)
        saved = load_saved_snapshot(manager.runs_dir(), run.paths.run_id)
        hier = saved.mode is ResearchMode.HIERARCHICAL
        assert replay_states(saved.events, len(saved.events), hier) == saved.agent_states()
        assert snap.events and saved.events


@pytest.mark.skipif(not any(RUNS.glob("*")), reason="no saved runs on this machine")
def test_real_saved_runs_replay_to_their_saved_state():
    checked = 0
    for root in RUNS.iterdir():
        snap = load_saved_snapshot(RUNS, root.name)
        if snap is None or not snap.events:
            continue
        hier = snap.mode is ResearchMode.HIERARCHICAL
        assert replay_states(snap.events, len(snap.events), hier) == snap.agent_states()
        checked += 1
    assert checked >= 1


def _trap(monkeypatch):
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
    return hits


def test_replay_controls_step_play_restart_with_zero_calls(tmp_path, monkeypatch):
    manager = hier_manager(tmp_path)
    run = manager.start(HIER)
    finish(manager, run)
    hits = _trap(monkeypatch)
    set_manager(hier_manager(tmp_path))
    at = _app()
    at.selectbox(key="saved_run_select").set_value(run.paths.run_id).run()
    total = len(load_saved_snapshot(manager.runs_dir(), run.paths.run_id).events)
    assert at.session_state["replay_pos"] == total  # opens on the final saved state
    for key in ("replay_restart", "replay_back", "replay_play", "replay_forward"):
        assert at.button(key=key)
    at.button(key="replay_restart").click().run()
    assert at.session_state["replay_pos"] == 0 and not at.session_state["replay_playing"]
    for expected in (1, 2, 3):
        at.button(key="replay_forward").click().run()
        assert at.session_state["replay_pos"] == expected
    at.button(key="replay_back").click().run()
    assert at.session_state["replay_pos"] == 2
    md = " ".join(m.value for m in at.markdown)
    assert "Replay of the recorded execution" in md and "Event 2 /" in md
    assert "Agent status and delegations come from recorded CrewAI events" in md
    at.button(key="replay_play").click().run()
    assert at.session_state["replay_playing"] is True
    at.button(key="replay_play").click().run()  # pause
    assert at.session_state["replay_playing"] is False
    assert not at.exception
    assert hits == []  # replay never reached an LLM, search, scrape or the crew


def test_replay_controls_are_offline_by_construction():
    source = (ROOT / "ui" / "research_tab.py").read_text(encoding="utf-8")
    replay = source[
        source.index("# ---- recorded-event replay") : source.index("def _live_workflow")
    ]
    for forbidden in ("get_manager().start", "manager.start", "run_crew", "build_llm", "crewai"):
        assert forbidden not in replay


# ------------------------------------------------------------------ labels and accessibility
def test_view_note_is_present_and_no_progress_percentages():
    html = render_workflow_html(ResearchMode.SEQUENTIAL, None, "idle")
    assert "<details" in html and "About this view" in html
    assert "does not represent direct agent messages unless such messages were recorded" in html
    assert "%" not in re.sub(r"<[^>]+>", "", html)  # no artificial progress figures


def test_reduced_motion_disables_every_animation():
    block = _CSS[_CSS.index("@media (prefers-reduced-motion: reduce) {\n  .ls-arc.ls-live") :]
    block = block[: block.index("}\n") + 1]
    for selector in (".ls-arc.ls-live::before", ".ls-drop.ls-live i", ".ls-vlink.ls-live"):
        assert selector in block
    assert "animation: none" in block
    # animation is only ever attached to a live connector
    for match in re.finditer(r"([^{}]+)\{[^}]*animation:\s*ls-", _CSS):
        assert "ls-live" in match.group(1), match.group(1)
