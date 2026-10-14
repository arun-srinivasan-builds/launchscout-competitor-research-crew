"""Research Workspace tab: input panel, live agent workflow, cockpit results.

Flow: input -> Run Research -> live workflow (updates from real run events while the crew
executes in the background) -> Research Intelligence Cockpit (`ui/cockpit.py`) for any finished
run, live or reopened from disk. The run is owned by the process-wide `RunManager`, so reruns
and widget edits never interrupt it.
"""

from __future__ import annotations

import html

import streamlit as st

from launchscout.inputs import InputValidationError, validate_input
from launchscout.progress import active_links, replay_states
from launchscout.runner import RunManager, RunSnapshot, get_manager
from launchscout.saved_runs import (
    LABEL_TEXT,
    SavedRunSummary,
    find_matching_saved_run,
    list_saved_runs,
    load_saved_snapshot,
)
from launchscout.schemas import ResearchInput, ResearchMode
from ui import cockpit, trace
from ui.theme import section
from ui.workflow import render_workflow_html

MODE_LABELS = {
    ResearchMode.SEQUENTIAL: "Sequential",
    ResearchMode.HIERARCHICAL: "Hierarchical",
}
POLL_SECONDS = 1.5
SESSION_RUN_KEY = "active_run_id"
SAVED_SELECT_KEY = "saved_run_select"
RESET_SAVED_KEY = "reset_saved_select"
REUSE_KEY = "reuse_input"
REPLAY_RUN_KEY = "replay_run"
REPLAY_POS_KEY = "replay_pos"
REPLAY_PLAYING_KEY = "replay_playing"
REPLAY_SECONDS = 0.6  # accelerated: one recorded event per tick


def _snapshot(manager: RunManager, run_id: str | None) -> RunSnapshot | None:
    """In-memory run if the process owns it, else the saved run from disk (read-only)."""
    if not run_id:
        return None
    return manager.snapshot(run_id) or load_saved_snapshot(manager.runs_dir(), run_id)


# ---- live workflow ------------------------------------------------------------------------


def _workflow_caption(snap: RunSnapshot | None) -> str:
    if snap is None:
        return (
            "All agents are idle: no research has run. Live status comes from real CrewAI "
            "events once a run starts; nothing here is simulated."
        )
    if snap.phase == "stopping":
        return "Stopping: waiting for the current agent step to return. Updates are live."
    if snap.active:
        return "Run in progress. This view updates from real CrewAI events as they happen."
    return f"Run {snap.run_id} ended with status: {snap.status}."


def _workflow_status_text(snap: RunSnapshot | None) -> str:
    if snap is None:
        return "All agents idle. No run has been executed."
    done = len(snap.completed_tasks)
    took = trace.fmt_elapsed(snap.elapsed_seconds())
    if snap.active:
        return f"Running: {done}/4 tasks complete, {took} elapsed."
    return f"Run {snap.status}: {done}/4 tasks completed in {took}."


def _render_canvas(snap: RunSnapshot | None, selected_mode: ResearchMode) -> None:
    mode = snap.mode if snap is not None else selected_mode
    states = snap.agent_states() if snap is not None else None
    hierarchical = mode is ResearchMode.HIERARCHICAL
    section("Live Agent Workflow", _workflow_caption(snap))
    st.markdown(
        render_workflow_html(
            mode, states, _workflow_status_text(snap), active_links(states, hierarchical)
        ),
        unsafe_allow_html=True,
    )


# ---- recorded-event replay (offline: reads saved events only, never runs anything) -------


def _replay_init(snap: RunSnapshot) -> None:
    if st.session_state.get(REPLAY_RUN_KEY) != snap.run_id:
        st.session_state[REPLAY_RUN_KEY] = snap.run_id
        st.session_state[REPLAY_POS_KEY] = len(snap.events)  # default: the final saved state
        st.session_state[REPLAY_PLAYING_KEY] = False


def _replay_restart() -> None:
    st.session_state[REPLAY_POS_KEY] = 0
    st.session_state[REPLAY_PLAYING_KEY] = False


def _replay_step(delta: int, total: int) -> None:
    pos = st.session_state.get(REPLAY_POS_KEY, total)
    st.session_state[REPLAY_POS_KEY] = max(0, min(total, pos + delta))
    st.session_state[REPLAY_PLAYING_KEY] = False


def _replay_toggle(total: int) -> None:
    if st.session_state.get(REPLAY_PLAYING_KEY):
        st.session_state[REPLAY_PLAYING_KEY] = False
        return
    if st.session_state.get(REPLAY_POS_KEY, total) >= total:
        st.session_state[REPLAY_POS_KEY] = 0  # play from the start after the end was reached
    st.session_state[REPLAY_PLAYING_KEY] = True


def _event_line(snap: RunSnapshot, pos: int) -> str:
    total = len(snap.events)
    if pos <= 0:
        return f"Event 0 / {total}: before the first recorded event."
    event = snap.events[pos - 1]
    stamp = event.ts.astimezone().strftime("%H:%M:%S")
    who = event.agent or "run"
    return f"Event {pos} / {total} · {stamp} · {event.kind} · {who}: {event.summary}"


def _replay_workflow(snap: RunSnapshot) -> None:
    total = len(snap.events)
    _replay_init(snap)
    playing = bool(st.session_state.get(REPLAY_PLAYING_KEY))
    hierarchical = snap.mode is ResearchMode.HIERARCHICAL

    @st.fragment(run_every=REPLAY_SECONDS if playing else None)
    def _panel() -> None:
        if bool(st.session_state.get(REPLAY_PLAYING_KEY)) != playing:
            st.rerun()  # play/pause toggled inside the fragment: re-arm its timer (full rerun)
        pos = int(st.session_state.get(REPLAY_POS_KEY, total))
        if st.session_state.get(REPLAY_PLAYING_KEY):
            pos = min(total, pos + 1)
            st.session_state[REPLAY_POS_KEY] = pos
            if pos >= total:
                st.session_state[REPLAY_PLAYING_KEY] = False
                st.rerun()  # leave play mode: the timer must stop and Play re-enables
        states = replay_states(snap.events, pos, hierarchical)
        links = active_links(states, hierarchical)
        section("Live Agent Workflow", _replay_caption(snap, pos))
        status = (
            _workflow_status_text(snap)
            if pos >= total
            else f"Replay: {pos} of {total} recorded events applied."
        )
        st.markdown(render_workflow_html(snap.mode, states, status, links), unsafe_allow_html=True)
        cols = st.columns(5)
        running = bool(st.session_state.get(REPLAY_PLAYING_KEY))
        cols[0].button(
            "Restart", key="replay_restart", on_click=_replay_restart, use_container_width=True
        )
        cols[1].button(
            "Step back",
            key="replay_back",
            on_click=_replay_step,
            args=(-1, total),
            disabled=running or pos <= 0,
            use_container_width=True,
        )
        cols[2].button(
            "Pause" if running else "Play",
            key="replay_play",
            on_click=_replay_toggle,
            args=(total,),
            type="primary",
            use_container_width=True,
        )
        cols[3].button(
            "Step forward",
            key="replay_forward",
            on_click=_replay_step,
            args=(1, total),
            disabled=running or pos >= total,
            use_container_width=True,
        )
        cols[4].caption(f"Position {pos} / {total}")
        st.markdown(
            f'<div class="ls-replay-caption">{html.escape(_event_line(snap, pos))}</div>',
            unsafe_allow_html=True,
        )

    _panel()


def _replay_caption(snap: RunSnapshot, pos: int) -> str:
    if pos >= len(snap.events):
        return _workflow_caption(snap)
    return (
        "Replay of the recorded execution, accelerated for demonstration. Nothing is "
        "running: no model, search or research call is made."
    )


def _live_workflow(run_id: str | None, selected_mode: ResearchMode) -> None:
    manager = get_manager()
    shown = _snapshot(manager, run_id)
    if shown is not None and not shown.active and shown.events:
        _replay_workflow(shown)  # finished or saved run: the workflow can be replayed offline
        return
    initial = manager.snapshot(run_id) if run_id else None
    was_active = initial is not None and initial.active

    @st.fragment(run_every=POLL_SECONDS if was_active else None)
    def _panel() -> None:
        snap = _snapshot(manager, run_id)
        _render_canvas(snap, selected_mode)
        if was_active and snap is not None and not snap.active:
            st.rerun()  # full rerun: show results and re-enable the form

    _panel()


# ---- engineering trace while idle or running ---------------------------------------------


def _render_trace_panel(snap: RunSnapshot | None) -> None:
    """Collapsed trace for the idle and running states (finished runs use the cockpit)."""
    with st.expander("Engineering Trace", expanded=False):
        if snap is None:
            trace.render_trace_idle()
        else:
            trace.render_trace_run(snap)
        trace.render_environment()


def _live_trace(run_id: str | None) -> None:
    manager = get_manager()
    initial = manager.snapshot(run_id) if run_id else None
    was_active = initial is not None and initial.active

    @st.fragment(run_every=POLL_SECONDS if was_active else None)
    def _panel() -> None:
        _render_trace_panel(_snapshot(manager, run_id))

    _panel()


# ---- input panel and orchestration --------------------------------------------------------


Fields = tuple[str, str, str, str]


def _render_input_panel(
    active: bool,
) -> tuple[ResearchMode, bool, bool, Fields]:
    """Left control panel: heading, then one card with fields, mode selector and buttons."""
    section("Describe the business idea", "Fields marked * are required.")
    with st.container(border=True, key="ls_left_card"):
        idea = st.text_input(
            "Business idea *",
            placeholder="e.g. Healthy millet meal boxes",
            max_chars=300,
        )
        city = st.text_input("City / target market *", placeholder="e.g. Coimbatore")
        customer = st.text_input("Target customer *", placeholder="e.g. office workers aged 25-40")
        known = st.text_area(
            "Known competitors (optional)",
            placeholder="Comma or line separated. These are starting points, not verified facts.",
            height=110,
        )
        mode = st.radio(
            "Research mode",
            options=list(MODE_LABELS.keys()),
            format_func=lambda m: MODE_LABELS[m],
            horizontal=True,
            key="research_mode",
            help="Sequential runs the four specialists in order. Hierarchical adds a Manager "
            "agent that delegates each task to the same four specialists (more model calls).",
        )
        submitted = st.button("Run Research", type="primary", key="run_research", disabled=active)
        cancelled = False
        if active:
            cancelled = st.button("Cancel run", key="cancel_run")
            st.caption("A run is in progress; a second run cannot start until it ends.")
    return mode, submitted, cancelled, (idea, city, customer, known)


def _render_saved_selector(manager: RunManager, active: bool) -> str | None:
    """Saved Research Runs: pick any run persisted under runs/. Read-only; no model, no search."""
    live = manager.active_run()
    runs = list_saved_runs(manager.runs_dir(), {live.paths.run_id} if live is not None else set())
    if not runs:
        st.caption("Saved research runs: none yet. Completed runs are kept under runs/.")
        return None
    by_id: dict[str, SavedRunSummary] = {r.run_id: r for r in runs}

    def title(run_id: str) -> str:
        return "Current session / latest run" if run_id == "" else by_id[run_id].title

    choice = st.selectbox(
        "Saved research runs",
        options=[""] + [r.run_id for r in runs],
        format_func=title,
        key=SAVED_SELECT_KEY,
        disabled=active,
        help="Reopen any earlier run from disk. Viewing, switching and downloading make no "
        "model calls, no searches and never start a research run.",
    )
    if active:
        st.caption("Saved runs are available again when the current run ends.")
    return choice or None


def _handle_submit(mode: ResearchMode, fields: Fields, notices: list[tuple[str, str]]) -> None:
    idea, city, customer, known = fields
    try:
        research_input = validate_input(idea, city, customer, known, mode)
    except InputValidationError as exc:
        notices.extend(("error", message) for message in exc.errors.values())
        return
    manager = get_manager()
    reusable = manager.find_reusable(research_input) or find_matching_saved_run(
        manager.runs_dir(), research_input
    )
    if reusable is not None:
        # explicit reuse: show the completed result; a new run needs a deliberate click
        st.session_state[SESSION_RUN_KEY] = reusable
        st.session_state[RESET_SAVED_KEY] = True
        st.session_state[REUSE_KEY] = research_input.model_dump(mode="json")
        return
    st.session_state.pop(REUSE_KEY, None)
    missing = manager.settings().missing()
    if missing:
        notices.append(("error", "Missing configuration: " + ", ".join(missing)))
        return
    run = manager.start(research_input)
    if run is None:
        notices.append(("warning", "A research run is already in progress; wait for it to end."))
        return
    st.session_state[SESSION_RUN_KEY] = run.paths.run_id
    st.session_state[RESET_SAVED_KEY] = True
    st.rerun()  # re-render the input panel in its running state (Run disabled, Cancel shown)


def _render_reuse_prompt(manager: RunManager, active: bool) -> None:
    """Shown while the last submit matched a completed run: no API calls were made."""
    pending = st.session_state.get(REUSE_KEY)
    if not pending or active:
        return
    st.info(
        "An identical research run has already completed, so its results are shown below "
        "and no new model or search calls were made."
    )
    if st.button("Run again (uses new API calls)", key="run_again"):
        st.session_state.pop(REUSE_KEY, None)
        run = manager.start(ResearchInput.model_validate(pending))
        if run is not None:
            st.session_state[SESSION_RUN_KEY] = run.paths.run_id
            st.session_state[RESET_SAVED_KEY] = True
        st.rerun()


def render() -> None:
    """Research Workspace: notices, two panels, workflow, then the cockpit or the live trace."""
    manager = get_manager()
    if st.session_state.pop(RESET_SAVED_KEY, False):
        st.session_state[SAVED_SELECT_KEY] = ""  # a new run or reuse returns to the live view
    run_id: str | None = st.session_state.get(SESSION_RUN_KEY) or manager.latest_run_id()
    active_run = manager.active_run()
    # Notices live above the two-column row, so headings in both columns always start together.
    notice_area = st.container(key="ls_notices")
    left, center = st.columns([3, 8], gap="large")
    notices: list[tuple[str, str]] = []
    with left, st.container(key="ls_left_panel"):
        mode, submitted, cancelled, fields = _render_input_panel(active_run is not None)
        saved_choice = _render_saved_selector(manager, active_run is not None)
    if cancelled and active_run is not None:
        manager.cancel(active_run.paths.run_id)
    if submitted:
        _handle_submit(mode, fields, notices)
        run_id = st.session_state.get(SESSION_RUN_KEY) or run_id
    viewing_saved = saved_choice is not None and active_run is None and not submitted
    if viewing_saved:
        run_id = saved_choice
    with notice_area:
        for level, message in notices:
            getattr(st, level)(message)
        if viewing_saved:
            _render_saved_notice(manager, saved_choice)
        else:
            _render_reuse_prompt(manager, active_run is not None)
    with center:
        _live_workflow(run_id, mode)
        snap = _snapshot(manager, run_id)
        if snap is not None and not snap.active:
            cockpit.render(snap)
        else:
            _live_trace(run_id)


def _render_saved_notice(manager: RunManager, run_id: str | None) -> None:
    snap = _snapshot(manager, run_id)
    if snap is None:
        st.error("This saved run could not be read from disk.")
        return
    summary = next((r for r in list_saved_runs(manager.runs_dir()) if r.run_id == run_id), None)
    label = LABEL_TEXT[summary.label] if summary else snap.status
    st.info(
        f"Viewing saved run {snap.run_id} - {label}. Loaded from disk exactly as saved: no "
        "model calls, no searches and no new research were made."
    )
