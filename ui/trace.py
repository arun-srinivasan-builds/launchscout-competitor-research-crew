"""Engineering trace content shared by the idle/running view and the cockpit.

Everything here is read from run events, the evidence ledger and measured usage.
It never calls a model or a search tool.
"""

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

from launchscout.config import load_settings
from launchscout.runner import RunSnapshot
from ui.theme import pill

MAX_TABLE_ROWS = 200


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def fmt_time(value: datetime | None) -> str:
    return value.astimezone().strftime("%H:%M:%S") if value else "-"


def fmt_elapsed(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def render_environment() -> None:
    """Which required variables are set, by name only."""
    st.markdown('<div class="ls-section">Environment</div>', unsafe_allow_html=True)
    settings = load_settings()
    pills = "".join(
        pill(f"{name}: {'set' if ok else 'missing'}", "ok" if ok else "warn")
        for name, ok in settings.key_presence().items()
    )
    st.markdown(pills, unsafe_allow_html=True)
    st.caption(
        "Variable names only; values are never shown. Model availability is checked by "
        "`python -m launchscout.model_check`."
    )


def render_trace_idle() -> None:
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
            f'<div class="ls-row"><b>{esc(label)}:</b> {esc(value)}</div>' for label, value in rows
        ),
        unsafe_allow_html=True,
    )


def render_trace_run(snap: RunSnapshot) -> None:
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
        ("Started", fmt_time(snap.started_at)),
        ("Elapsed", fmt_elapsed(snap.elapsed_seconds())),
        ("Events", str(len(snap.events))),
        (
            "Search calls / page reads / cache hits",
            f"{usage.serper_calls} / {usage.scrape_calls} / {usage.cache_hits}",
        ),
        ("Model calls", str(usage.llm_calls if usage.llm_calls is not None else "unavailable")),
        ("Tool calls recorded", str(len(tool_events))),
        ("Errors", str(len(errors))),
        ("Usage", usage_text),
        ("Acceptance", f"{snap.acceptance.result} ({snap.report_state or 'no report'})"),
    )
    st.markdown(
        "".join(f'<div class="ls-row"><b>{esc(k)}:</b> {esc(v)}</div>' for k, v in summary),
        unsafe_allow_html=True,
    )
    metrics = snap.agent_metrics()
    if any(m["llm_calls"] or m["tool_calls"] for m in metrics.values()):
        st.markdown("**Per-agent efficiency (measured from events)**")
        st.dataframe(
            [
                {
                    "Agent": agent,
                    "LLM calls": int(m["llm_calls"]),
                    "Tokens": str(int(m["total_tokens"])) if m["total_tokens"] else "unavailable",
                    "Tool calls": int(m["tool_calls"]),
                    "Executed": int(m["executed"]),
                    "Cache hits": int(m["cache_hits"]),
                    "Refused (budget)": int(m["refused_budget"]),
                    "Errors": int(m["tool_errors"]),
                    "Task seconds": m["seconds"],
                }
                for agent, m in metrics.items()
            ],
            hide_index=True,
            width="stretch",
        )
    if tool_events:
        st.markdown("**Tool calls**")
        st.dataframe(
            [
                {
                    "Time": fmt_time(e.ts),
                    "Agent": e.agent or "",
                    "Tool": str(e.data.get("tool", "")),
                    "Input": str(e.data.get("arg", "")),
                }
                for e in tool_events[-MAX_TABLE_ROWS:]
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
                for e in snap.evidence[-MAX_TABLE_ROWS:]
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
            st.markdown(f"- {fmt_time(event.ts)} {event.agent or 'run'}: {event.summary}")
    if snap.events:
        st.markdown("**Event log**")
        st.dataframe(
            [
                {
                    "Time": fmt_time(e.ts),
                    "Agent": e.agent or "",
                    "Event": e.kind,
                    "Detail": e.summary,
                }
                for e in snap.events[-MAX_TABLE_ROWS:]
            ],
            hide_index=True,
            width="stretch",
        )
