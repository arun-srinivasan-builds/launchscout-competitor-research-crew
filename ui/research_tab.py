"""Research Workspace tab: input panel, live agent workflow, cockpit results.

Flow: input -> Run Research -> live workflow (updates from real run events while the crew
executes in the background) -> Research Intelligence Cockpit (`ui/cockpit.py`) for any finished
run, live or reopened from disk. The run is owned by the process-wide `RunManager`, so reruns
and widget edits never interrupt it.
"""

from __future__ import annotations

import streamlit as st

from launchscout.inputs import InputValidationError, validate_input
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
    section("Live Agent Workflow", _workflow_caption(snap))
    st.markdown(
        render_workflow_html(mode, states, _workflow_status_text(snap)),
        unsafe_allow_html=True,
    )


def _live_workflow(run_id: str | None, selected_mode: ResearchMode) -> None:
    manager = get_manager()
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
            "agent that delegates; its execution arrives in a later milestone (M5).",
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
    if mode is ResearchMode.HIERARCHICAL:
        notices.append(
            (
                "info",
                "Hierarchical execution is not available yet (milestone M5). Input validated; "
                "no research was run. Choose Sequential to run the four-agent crew.",
            )
        )
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
