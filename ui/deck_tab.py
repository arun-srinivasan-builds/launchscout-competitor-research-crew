"""Pitch Deck tab: six editable slides built from a saved research run.

Choosing a run, viewing a stored deck and downloading it make no model call. Only the explicit
"Generate pitch deck" click runs the Pitch Deck agent (one call, no tools, no research).
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from launchscout import deck as deck_mod
from launchscout.demo import DemoModeError, is_demo
from launchscout.runner import RunManager, get_manager
from launchscout.saved_runs import LABEL_TEXT, SavedRunSummary, list_saved_runs
from ui.theme import pill, section

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _eligible(manager: RunManager) -> list[SavedRunSummary]:
    runs = list_saved_runs(manager.runs_dir())
    return [r for r in runs if r.report_state in deck_mod.ELIGIBLE_STATES]


def _empty_state() -> None:
    st.markdown(
        '<div class="ls-card"><h4>Status</h4>'
        f"{pill('No saved report', 'warn')}"
        '<div class="ls-row ls-muted">Run research first. A deck is built only from a saved '
        "run's report and structured findings (validated, or partial and clearly labelled). "
        "Slides: Idea &amp; Market, Competitor Landscape, Customer Pain Points, Market Gap, "
        "Positioning &amp; Price, 30-Day Launch Plan.</div></div>",
        unsafe_allow_html=True,
    )
    st.button("Generate pitch deck", disabled=True, key="deck_generate")


def _render_preview(spec: deck_mod.DeckSpec) -> None:
    for number, slide in enumerate(spec.slides, 1):
        labels = "".join(pill(escape(label), "warn") for label in slide.labels)
        bullets = "".join(f"<li>{escape(b)}</li>" for b in slide.bullets) or "<li>None</li>"
        st.markdown(
            f'<div class="ls-card"><h4>{number}. {escape(slide.title)}</h4>{labels}'
            f"<ul>{bullets}</ul></div>",
            unsafe_allow_html=True,
        )


def _render_stored(manager: RunManager, run_id: str) -> None:
    stored = deck_mod.load_saved_deck(manager.runs_dir(), run_id)
    if stored is None:
        st.markdown(
            '<div class="ls-card ls-muted">No deck has been generated for this run yet. '
            "Generating makes one model call and no searches.</div>",
            unsafe_allow_html=True,
        )
        return
    spec, meta, pptx = stored
    violations = meta.get("violations") or []
    usage = meta.get("usage") or {}
    chips = [pill("Editable PPTX ready" if pptx else "Export blocked", "ok" if pptx else "warn")]
    if meta.get("partial"):
        chips.append(pill("Partial evidence deck", "warn"))
    tokens = usage.get("total_tokens")
    chips.append(
        pill(f"{tokens:,} tokens" if isinstance(tokens, int) else "Tokens not measured", "idle")
    )
    st.markdown(
        '<div class="ls-card"><h4>Generated deck</h4>' + "".join(chips) + "</div>",
        unsafe_allow_html=True,
    )
    if violations:
        items = "".join(
            f"<li>Slide {v['slide']} · {escape(v['rule'])}: {escape(v['detail'])} "
            f"({escape(v['text'])})</li>"
            for v in violations
        )
        st.markdown(
            f'<div class="ls-card"><h4>Claim check blocked the export</h4><ul>{items}</ul></div>',
            unsafe_allow_html=True,
        )
    if pptx is not None and Path(pptx).is_file():
        st.download_button(
            "Download PPTX",
            data=Path(pptx).read_bytes(),
            file_name=Path(pptx).name,
            mime=PPTX_MIME,
            key="deck_download",
        )
    _render_preview(spec)


def _generate(manager: RunManager, run_id: str) -> None:
    try:
        source = deck_mod.load_deck_source(manager.runs_dir(), run_id)
        settings = manager.settings()
        with st.spinner("Pitch Deck agent is writing six slides…"):
            result = deck_mod.generate_deck(source, settings)
            deck_mod.save_deck(manager.runs_dir(), source, result, settings.model_name)
    except DemoModeError as exc:
        st.warning(str(exc))
    except deck_mod.DeckRefused as exc:
        st.error(str(exc))
    except ValueError as exc:
        st.error(f"The agent did not return a usable deck: {exc}")
    except Exception as exc:  # noqa: BLE001 - shown by type name only, never with secrets
        st.error(f"Deck generation failed: {type(exc).__name__}")


def render() -> None:
    section(
        "Six-slide pitch deck",
        "An editable PowerPoint built from a saved research run; research is never rerun.",
    )
    manager = get_manager()
    runs = _eligible(manager)
    if not runs:
        _empty_state()
        return
    by_id = {r.run_id: r for r in runs}
    run_id = st.selectbox(
        "Source research run",
        options=list(by_id),
        format_func=lambda rid: by_id[rid].title,
        key="deck_source_run",
    )
    summary = by_id[run_id]
    partial = summary.label != "validated"
    chips = [pill(LABEL_TEXT[summary.label], "warn" if partial else "ok")]
    st.markdown(
        '<div class="ls-card"><h4>Source</h4>'
        + "".join(chips)
        + '<div class="ls-row ls-muted">'
        + (
            "This report failed acceptance. The deck is built from it anyway and every slide "
            "is labelled as partial evidence; unknown prices stay unknown."
            if partial
            else "Validated report: all acceptance checks passed."
        )
        + " Generating makes one model call (no searches, no page reads).</div></div>",
        unsafe_allow_html=True,
    )
    demo = is_demo()
    if demo:
        st.caption("Public demo: deck generation is disabled. Download the existing deck below.")
    if st.button("Generate pitch deck", key="deck_generate", disabled=demo):
        _generate(manager, run_id)
    _render_stored(manager, run_id)
