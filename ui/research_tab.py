"""Research Workspace tab: mode selector, input form, agent workflow, Behind the Scenes."""

from __future__ import annotations

import html

import streamlit as st

from launchscout.config import load_settings
from launchscout.inputs import InputValidationError, validate_input
from launchscout.schemas import ResearchInput, ResearchMode
from ui.theme import pill, section

MODE_LABELS = {
    ResearchMode.SEQUENTIAL: "Sequential",
    ResearchMode.HIERARCHICAL: "Hierarchical",
}

# Static roster from the PRP. Statuses are idle until M3 wires real CrewAI events.
AGENT_ROSTER: tuple[tuple[str, str, str], ...] = (
    ("Market Researcher", "Finds 3-5 real competitors, offers, prices and sales channels.",
     "Planned tools: web search, website scraper"),
    ("Review Analyst", "Collects attributable customer praise and complaints.",
     "Planned tools: web search, website scraper"),
    ("Strategy Analyst", "Compares competitors; recommends gap, price and positioning.",
     "No tools: reasons over the research outputs"),
    ("Report Writer", "Writes the six-section sourced report to file.",
     "Planned tool: file writer"),
)


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _render_workflow(mode: ResearchMode) -> None:
    section(
        "Agent workflow",
        "No research has been run. Every agent is idle. Live status from real CrewAI events "
        "will appear here once execution is added (M3); nothing below is simulated progress.",
    )
    if mode is ResearchMode.HIERARCHICAL:
        st.markdown(
            '<div class="ls-step ls-manager"><div class="ls-step-title">Manager agent</div>'
            '<div class="ls-step-desc">Coordinates and delegates to the four specialists. '
            "Hierarchical execution is not yet available (M5).</div>"
            f"{pill('Idle', 'idle')}{pill('Not yet implemented', 'warn')}</div>",
            unsafe_allow_html=True,
        )
    columns = st.columns(len(AGENT_ROSTER))
    for index, (column, (name, description, tools)) in enumerate(
        zip(columns, AGENT_ROSTER, strict=True), start=1
    ):
        column.markdown(
            f'<div class="ls-step"><div class="ls-step-num">{index}</div>'
            f'<div class="ls-step-title">{_esc(name)}</div>'
            f'<div class="ls-step-desc">{_esc(description)}<br>{_esc(tools)}</div>'
            f"{pill('Idle', 'idle')}</div>",
            unsafe_allow_html=True,
        )


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


def render() -> None:
    section("Describe the business idea", "Fields marked * are required.")
    mode = st.radio(
        "Research mode",
        options=list(MODE_LABELS.keys()),
        format_func=lambda m: MODE_LABELS[m],
        horizontal=True,
        key="research_mode",
        help="Sequential runs the four specialists in order. Hierarchical adds a Manager "
        "agent that delegates; its execution arrives in a later milestone.",
    )
    with st.form("research_form", border=False):
        idea = st.text_input(
            "Business idea *",
            placeholder="e.g. Healthy millet meal boxes delivered for lunch",
            max_chars=300,
        )
        col_city, col_customer = st.columns(2)
        city = col_city.text_input("City / target market *", placeholder="e.g. Coimbatore")
        customer = col_customer.text_input(
            "Target customer *", placeholder="e.g. office workers aged 25-40"
        )
        known = st.text_area(
            "Known competitors (optional)",
            placeholder="Comma or line separated. These are starting points, not verified facts.",
            height=90,
        )
        submitted = st.form_submit_button("Run Research", type="primary")

    if submitted:
        try:
            research_input = validate_input(idea, city, customer, known, mode)
        except InputValidationError as exc:
            for message in exc.errors.values():
                st.error(message)
        else:
            _render_validated(research_input)

    _render_workflow(mode)
    _render_behind_the_scenes()
