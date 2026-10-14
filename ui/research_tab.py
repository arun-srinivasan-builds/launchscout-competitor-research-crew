"""Research Workspace tab: mode selector, input form, agent workflow, Behind the Scenes."""

from __future__ import annotations

import html

import streamlit as st

from launchscout.config import load_settings
from launchscout.inputs import InputValidationError, validate_input
from launchscout.schemas import ResearchInput, ResearchMode
from ui.theme import pill, section
from ui.workflow import render_workflow_html

MODE_LABELS = {
    ResearchMode.SEQUENTIAL: "Sequential",
    ResearchMode.HIERARCHICAL: "Hierarchical",
}

def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _render_workflow(mode: ResearchMode) -> None:
    section(
        "Live Agent Workflow",
        "All agents are idle: no research has run. Live status will come from real CrewAI "
        "events in M3; nothing here is simulated.",
    )
    st.markdown(render_workflow_html(mode), unsafe_allow_html=True)


def _render_behind_the_scenes() -> None:
    settings = load_settings()
    with st.expander("Behind the Scenes", expanded=False):
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
        st.markdown('<div class="ls-section">Environment</div>', unsafe_allow_html=True)
        pills = "".join(
            pill(f"{name}: {'set' if ok else 'missing'}", "ok" if ok else "warn")
            for name, ok in settings.key_presence().items()
        )
        st.markdown(pills, unsafe_allow_html=True)
        st.caption(
            "Variable names only; values are never shown. Model availability has not been "
            "verified from this page: run `python -m launchscout.model_check`."
        )


def _render_validated(research_input: ResearchInput) -> None:
    st.success("Input validated.")
    competitors = ", ".join(research_input.known_competitors) or "none"
    st.markdown(
        '<div class="ls-card"><h4>Research request</h4>'
        f'<div class="ls-row"><b>Idea:</b> {_esc(research_input.idea)}</div>'
        f'<div class="ls-row"><b>City / market:</b> {_esc(research_input.city)}</div>'
        f'<div class="ls-row"><b>Target customer:</b> {_esc(research_input.target_customer)}</div>'
        f'<div class="ls-row"><b>Known competitors:</b> {_esc(competitors)}</div>'
        f'<div class="ls-row"><b>Mode:</b> {MODE_LABELS[research_input.mode]}</div></div>',
        unsafe_allow_html=True,
    )
    st.info(
        "Research execution is not part of this build (milestone M2 provides the form and "
        "validation only). No research was run, no files were created and nothing was saved."
    )


def _render_input_panel() -> tuple[ResearchMode, bool, tuple[str, str, str, str]]:
    """Left control panel: heading, then one card with the fields, mode selector and button."""
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
            "agent that delegates; its execution arrives in a later milestone.",
        )
        submitted = st.button("Run Research", type="primary", key="run_research")
    return mode, submitted, (idea, city, customer, known)


def render() -> None:
    left, center = st.columns([3, 8], gap="large")
    with left, st.container(key="ls_left_panel"):
        mode, submitted, (idea, city, customer, known) = _render_input_panel()
    with center:
        _render_workflow(mode)
        if submitted:
            try:
                research_input = validate_input(idea, city, customer, known, mode)
            except InputValidationError as exc:
                for message in exc.errors.values():
                    st.error(message)
            else:
                _render_validated(research_input)
        _render_behind_the_scenes()
