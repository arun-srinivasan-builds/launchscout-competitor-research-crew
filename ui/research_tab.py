"""Research Workspace tab: input panel, live agent workflow, results, Behind the Scenes.

Flow: input -> Run Research -> live workflow (updates from real run events while the crew
executes in the background) -> results -> Behind the Scenes. The run is owned by the
process-wide `RunManager`, so reruns and widget edits never interrupt it.
"""

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

from launchscout.config import load_settings
from launchscout.inputs import InputValidationError, validate_input
from launchscout.runner import RunSnapshot, get_manager
from launchscout.schemas import ResearchMode
from ui.theme import pill, section
from ui.workflow import render_workflow_html

MODE_LABELS = {
    ResearchMode.SEQUENTIAL: "Sequential",
    ResearchMode.HIERARCHICAL: "Hierarchical",
}
POLL_SECONDS = 1.5
SESSION_RUN_KEY = "active_run_id"
_MAX_TABLE_ROWS = 200


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _fmt_time(value: datetime | None) -> str:
    return value.astimezone().strftime("%H:%M:%S") if value else "-"


def _fmt_elapsed(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


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
    if snap.active:
        return f"Running: {done}/4 tasks complete, {_fmt_elapsed(snap.elapsed_seconds())} elapsed."
    return f"Run {snap.status}: {done}/4 tasks completed in {_fmt_elapsed(snap.elapsed_seconds())}."


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
        snap = manager.snapshot(run_id) if run_id else None
        _render_canvas(snap, selected_mode)
        if was_active and snap is not None and not snap.active:
            st.rerun()  # full rerun: show results and re-enable the form

    _panel()


# ---- results ------------------------------------------------------------------------------


def _render_banner(snap: RunSnapshot) -> None:
    if snap.status == "complete":
        st.success(
            "All four agents finished. This is an unvalidated draft: acceptance validation, "
            "PDF and Markdown exports arrive in M4."
        )
    elif snap.status == "partial":
        st.warning(
            "Partial run: some tasks did not complete or their output could not be parsed. "
            "Only what was actually produced is shown below."
        )
    elif snap.status == "cancelled":
        st.warning("Run cancelled. Outputs from tasks completed before cancellation are shown.")
    elif snap.status == "timeout":
        st.error("Run timed out and was stopped. Outputs from completed tasks are shown.")
    else:
        st.error(f"Run failed: {snap.error or 'no usable output was produced'}.")


def _render_results(snap: RunSnapshot) -> None:
    section("Results", f"Run {snap.run_id}. Content comes only from tool-retrieved evidence.")
    _render_banner(snap)
    if snap.competitors and snap.competitors.competitors:
        rows = [
            {
                "Competitor": c.name,
                "Site": c.url,
                "Offer": c.offer or "unknown",
                "Price": (
                    f"{c.price.amount} {c.price.currency} / {c.price.unit}"
                    if c.price.status == "verified"
                    else "unknown"
                ),
                "Evidence URLs": ", ".join(c.evidence_urls) or "none found",
                "Flags": "; ".join(c.unknowns),
            }
            for c in snap.competitors.competitors
        ]
        st.markdown("**Competitors**")
        st.dataframe(rows, hide_index=True, width="stretch")
        if snap.competitors.shortfall_reason:
            st.caption(f"Shortfall: {snap.competitors.shortfall_reason}")
    elif "Competitor research" in snap.completed_tasks:
        st.caption("Competitor output could not be parsed into a validated set.")
    if snap.reviews and snap.reviews.findings:
        st.markdown("**Customer feedback**")
        st.dataframe(
            [
                {
                    "Competitor": f.competitor,
                    "Type": f.kind,
                    "Basis": f.basis,
                    "Text": f.text,
                    "Source": f.source_url or "none",
                }
                for f in snap.reviews.findings
            ],
            hide_index=True,
            width="stretch",
        )
    if snap.strategy and (snap.strategy.market_gap or snap.strategy.recommended_offer):
        st.markdown("**Strategy (recommendation, not verified fact)**")
        st.markdown(
            f"- **Market gap:** {snap.strategy.market_gap or 'unknown'}\n"
            f"- **Offer:** {snap.strategy.recommended_offer or 'unknown'}\n"
            f"- **Positioning:** {snap.strategy.positioning_line or 'unknown'}\n"
            f"- **Recommended price:** {snap.strategy.recommended_price or 'unknown'} "
            "(Recommendation)"
        )
    if snap.report_markdown:
        with st.expander("Draft report (unvalidated)", expanded=False):
            if snap.unsupported_report_urls:
                st.warning(
                    f"{len(snap.unsupported_report_urls)} URL(s) in this draft were not returned "
                    "by any tool and must be treated as unverified."
                )
            st.markdown(snap.report_markdown)


# ---- Behind the Scenes --------------------------------------------------------------------


def _render_bts_idle() -> None:
    st.markdown(
        '<div class="ls-caption">Execution details appear here for each run: active agent, '
        "task status, tool calls, source retrieval, validation results, errors and retries, "
        "measured usage and timestamps. No run has been executed, so there are no events "
        "to show.</div>",
        unsafe_allow_html=True,
    )
    rows = (
        ("Run events", "None"),
        ("Tool calls", "None"),
        ("Validation and guardrail results", "Not evaluated"),
        ("API usage", "Unavailable (nothing measured)"),
    )
    st.markdown(
        "".join(
            f'<div class="ls-row"><b>{_esc(label)}:</b> {_esc(value)}</div>'
            for label, value in rows
        ),
        unsafe_allow_html=True,
    )


def _render_bts_run(snap: RunSnapshot) -> None:
    usage = snap.usage
    tool_events = [e for e in snap.events if e.kind == "tool_started"]
    errors = [e for e in snap.events if e.status == "error"]
    if usage.basis == "measured" and usage.total_tokens:
        usage_text = (
            f"{usage.total_tokens} tokens measured "
            f"({usage.prompt_tokens} prompt + {usage.completion_tokens} completion)"
        )
    else:
        usage_text = "Token usage unavailable (the provider reported none)"
    summary = (
        ("Run", snap.run_id),
        ("Status", f"{snap.status} ({snap.phase})"),
        ("Model", snap.model_name or "not set"),
        ("Started", _fmt_time(snap.started_at)),
        ("Elapsed", _fmt_elapsed(snap.elapsed_seconds())),
        ("Events", str(len(snap.events))),
        (
            "Search calls / page reads / cache hits",
            f"{usage.serper_calls} / {usage.scrape_calls} / {usage.cache_hits}",
        ),
        ("Tool calls recorded", str(len(tool_events))),
        ("Errors", str(len(errors))),
        ("Usage", usage_text),
        ("Acceptance", "Not evaluated (validation arrives in M4)"),
    )
    st.markdown(
        "".join(
            f'<div class="ls-row"><b>{_esc(k)}:</b> {_esc(v)}</div>' for k, v in summary
        ),
        unsafe_allow_html=True,
    )
    if tool_events:
        st.markdown("**Tool calls**")
        st.dataframe(
            [
                {
                    "Time": _fmt_time(e.ts),
                    "Agent": e.agent or "",
                    "Tool": str(e.data.get("tool", "")),
                    "Input": str(e.data.get("arg", "")),
                }
                for e in tool_events[-_MAX_TABLE_ROWS:]
            ],
            hide_index=True,
            width="stretch",
        )
    if snap.evidence:
        st.markdown("**Evidence ledger (URLs returned by tools)**")
        st.dataframe(
            [
                {
                    "URL": e.url,
                    "Kind": e.kind,
                    "Status": e.status,
                    "Accessed": e.accessed_on.isoformat(),
                    "Found via": e.via,
                }
                for e in snap.evidence[-_MAX_TABLE_ROWS:]
            ],
            hide_index=True,
            width="stretch",
        )
    if snap.grounding_issues or snap.unsupported_report_urls:
        st.markdown("**Guardrail findings**")
        for issue in snap.grounding_issues:
            st.markdown(f"- {issue}")
        for url in snap.unsupported_report_urls:
            st.markdown(f"- Report URL not returned by any tool: `{url}`")
    if errors:
        st.markdown("**Errors**")
        for event in errors[-20:]:
            st.markdown(f"- {_fmt_time(event.ts)} {event.agent or 'run'}: {event.summary}")
    if snap.events:
        st.markdown("**Event log**")
        st.dataframe(
            [
                {
                    "Time": _fmt_time(e.ts),
                    "Agent": e.agent or "",
                    "Event": e.kind,
                    "Detail": e.summary,
                }
                for e in snap.events[-_MAX_TABLE_ROWS:]
            ],
            hide_index=True,
            width="stretch",
        )


def _render_bts(snap: RunSnapshot | None) -> None:
    settings = load_settings()
    with st.expander("Behind the Scenes", expanded=False):
        if snap is None:
            _render_bts_idle()
        else:
            _render_bts_run(snap)
        st.markdown('<div class="ls-section">Environment</div>', unsafe_allow_html=True)
        pills = "".join(
            pill(f"{name}: {'set' if ok else 'missing'}", "ok" if ok else "warn")
            for name, ok in settings.key_presence().items()
        )
        st.markdown(pills, unsafe_allow_html=True)
        st.caption(
            "Variable names only; values are never shown. Model availability is checked by "
            "`python -m launchscout.model_check`."
        )


def _live_bts(run_id: str | None) -> None:
    manager = get_manager()
    initial = manager.snapshot(run_id) if run_id else None
    was_active = initial is not None and initial.active

    @st.fragment(run_every=POLL_SECONDS if was_active else None)
    def _panel() -> None:
        _render_bts(manager.snapshot(run_id) if run_id else None)

    _panel()


# ---- input panel and orchestration --------------------------------------------------------


Fields = tuple[str, str, str, str]


def _render_input_panel(active: bool) -> tuple[ResearchMode, bool, bool, Fields]:
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
    missing = manager.settings().missing()
    if missing:
        notices.append(("error", "Missing configuration: " + ", ".join(missing)))
        return
    run = manager.start(research_input)
    if run is None:
        notices.append(("warning", "A research run is already in progress; wait for it to end."))
        return
    st.session_state[SESSION_RUN_KEY] = run.paths.run_id
    st.rerun()  # re-render the input panel in its running state (Run disabled, Cancel shown)


def render() -> None:
    manager = get_manager()
    run_id: str | None = st.session_state.get(SESSION_RUN_KEY) or manager.latest_run_id()
    active_run = manager.active_run()
    left, center = st.columns([3, 8], gap="large")
    notices: list[tuple[str, str]] = []
    with left, st.container(key="ls_left_panel"):
        mode, submitted, cancelled, fields = _render_input_panel(active_run is not None)
    if cancelled and active_run is not None:
        manager.cancel(active_run.paths.run_id)
    if submitted:
        _handle_submit(mode, fields, notices)
        run_id = st.session_state.get(SESSION_RUN_KEY) or run_id
    with center:
        for level, message in notices:
            getattr(st, level)(message)
        _live_workflow(run_id, mode)
        snap = manager.snapshot(run_id) if run_id else None
        if snap is not None and not snap.active:
            _render_results(snap)
        _live_bts(run_id)
