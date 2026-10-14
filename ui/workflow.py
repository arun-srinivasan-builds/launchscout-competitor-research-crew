"""Live Agent Workflow: markup for the four connected agent nodes (CSS lives in ui/theme.py).

Each node renders an `AgentState` derived from recorded run events (see
`launchscout/progress.py`). With no run, every node is Idle with no events; nothing here
simulates execution.
"""

from __future__ import annotations

import html
from collections.abc import Mapping
from dataclasses import dataclass

from launchscout.progress import AgentState, AgentStatus
from launchscout.schemas import ResearchMode

__all__ = ["AGENTS", "AgentState", "AgentStatus", "render_workflow_html"]


@dataclass(frozen=True)
class AgentNode:
    key: str
    name: str
    role: str
    tools: tuple[str, ...]
    handoff: str
    glyph: str


AGENTS: tuple[AgentNode, ...] = (
    AgentNode(
        "market_researcher", "Market Researcher",
        "Finds 3-5 real competitors, offers, prices and sales channels.",
        ("Web search", "Website scraper"), "Competitor profiles", "&#8981;",
    ),
    AgentNode(
        "review_analyst", "Review Analyst",
        "Collects attributable customer praise and complaints.",
        ("Web search", "Website scraper"), "Review evidence", "&#9776;",
    ),
    AgentNode(
        "strategy_analyst", "Strategy Analyst",
        "Compares competitors; recommends gap, price and positioning.",
        ("No tools: reasons over research",), "Gap and positioning", "&#9672;",
    ),
    AgentNode(
        "report_writer", "Report Writer",
        "Writes the six-section sourced report to file.",
        ("File writer",), "Sourced report", "&#9998;",
    ),
)

_STATUS_CLASS = {
    AgentStatus.IDLE: "ls-st-idle",
    AgentStatus.ACTIVE: "ls-st-active",
    AgentStatus.COMPLETE: "ls-st-complete",
    AgentStatus.FAILED: "ls-st-failed",
    AgentStatus.CANCELLED: "ls-st-cancelled",
}


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _progress_class(percent: int | None) -> str:
    if percent is None:
        return "ls-p-none"
    return f"ls-p-{min(100, max(0, round(percent / 10) * 10))}"


def _card(index: int, node: AgentNode, state: AgentState) -> str:
    chips = "".join(f'<span class="ls-chip">{_esc(tool)}</span>' for tool in node.tools)
    events = (
        "".join(f"<li>{_esc(e)}</li>" for e in state.events)
        or '<li class="ls-none">No events received</li>'
    )
    calls = (
        "".join(f"<li>{_esc(c)}</li>" for c in state.tool_calls)
        or '<li class="ls-none">No tool calls</li>'
    )
    progress = "&mdash;" if state.progress_percent is None else f"{state.progress_percent}%"
    return (
        f'<div class="ls-node ls-a{index} {_STATUS_CLASS[state.status]}" '
        f'id="ls-agent-{node.key}" data-agent="{node.key}">'
        '<div class="ls-node-head">'
        f'<span class="ls-glyph">{node.glyph}<span class="ls-node-num">{index}</span></span>'
        '<span class="ls-node-id">'
        f'<span class="ls-node-name">{_esc(node.name)}</span>'
        f'<span class="ls-node-status">{_esc(state.status.value)}</span></span></div>'
        '<div class="ls-task">'
        '<div class="ls-task-row">'
        f'<span>{_esc(state.task_label)}</span><span>{progress}</span></div>'
        f'<div class="ls-track"><div class="ls-fill {_progress_class(state.progress_percent)}">'
        "</div></div></div>"
        '<div class="ls-panel"><div class="ls-panel-title">Planned tools</div>'
        f'<div class="ls-chips">{chips}</div>'
        f'<div class="ls-panel-text">{_esc(node.role)}</div></div>'
        '<div class="ls-panel"><div class="ls-panel-title">Live events</div>'
        f'<ul class="ls-events">{events}</ul>'
        '<div class="ls-panel-title ls-gap">Tool calls</div>'
        f'<ul class="ls-events">{calls}</ul></div>'
        '<div class="ls-handoff"><span class="ls-doc"></span>'
        f'<span class="ls-handoff-text">Output: {_esc(node.handoff)}</span></div>'
        "</div>"
    )


def render_workflow_html(
    mode: ResearchMode,
    states: Mapping[str, AgentState] | None = None,
    status_text: str = "All agents idle. No run has been executed.",
) -> str:
    """Return the connected-node canvas as one HTML string (no blank lines, no indentation)."""
    states = states or {}
    parts = ['<div class="ls-canvas" role="group" aria-label="Live Agent Workflow">']
    parts.append('<div class="ls-flow">')
    if mode is ResearchMode.HIERARCHICAL:
        parts.append(
            '<div class="ls-manager-node" id="ls-agent-manager" data-agent="manager">'
            '<div class="ls-node-head"><span class="ls-glyph">&#9733;</span>'
            '<span class="ls-node-id"><span class="ls-node-name">Manager agent</span>'
            '<span class="ls-node-status">Idle</span></span></div>'
            '<div class="ls-panel-text">Coordinates and delegates to the four specialists. '
            "Hierarchical execution is not yet available (M5).</div>"
            '<span class="ls-chip ls-chip-warn">Not yet implemented</span></div>'
        )
    parts.append('<div class="ls-arc ls-arc-top ls-arc-12"></div>')
    parts.append('<div class="ls-arc ls-arc-bottom ls-arc-23"></div>')
    parts.append('<div class="ls-arc ls-arc-top ls-arc-34"></div>')
    for index, node in enumerate(AGENTS, start=1):
        parts.append(_card(index, node, states.get(node.key, AgentState())))
        if index < len(AGENTS):
            parts.append('<div class="ls-vlink"></div>')
    parts.append("</div>")
    mode_label = "Hierarchical" if mode is ResearchMode.HIERARCHICAL else "Sequential"
    parts.append(
        '<div class="ls-statusbar"><span><span class="ls-dot"></span>'
        f"{_esc(status_text)}</span>"
        f"<span>Mode: {mode_label}</span></div></div>"
    )
    return "".join(parts)
