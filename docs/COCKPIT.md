# Research Intelligence Cockpit (production results view)

Status: **integrated** into the Research Workspace (`app.py` -> `ui/research_tab.render`). It
replaces the earlier Results page and Behind the Scenes expander. The left setup panel, the Saved
research runs selector and the four-agent Live Agent Workflow are unchanged. Every finished run,
live or reopened from disk, renders through `ui/cockpit.py`.

## Where things are

| Piece | File |
|---|---|
| Cockpit view (summary, six areas, downloads, full report) | `ui/cockpit.py` |
| Trace content shared with the idle/running view | `ui/trace.py` |
| Orchestration (notices, panels, workflow, cockpit or live trace) | `ui/research_tab.py` |
| Cockpit styles (loaded only when the cockpit renders) | `COCKPIT_CSS` in `ui/theme.py` |

## States

| State | What the user sees |
|---|---|
| No run yet | Workflow idle; collapsed **Engineering Trace** with the idle text and environment names |
| Running / stopping | Live workflow from real events; collapsed Engineering Trace updating; Run disabled, Cancel shown |
| Completed, validated | Cockpit: crew chip, "Report validated" chip, takeaway, KPI tiles, downloads, six areas |
| Completed, partial | Same, with "Report failed acceptance" and one "Why acceptance did not pass" block; downloads labelled (PARTIAL) |
| Failed / cancelled / timed out / no report | Cockpit header with the stated reason and error; areas show what exists (for example partial competitor output) |
| Legacy (saved before validation) | "Acceptance not evaluated", saved draft in the collapsed report, Markdown labelled (UNVALIDATED), nothing regenerated |

## Layout and interactions

```
Notices (full width, above both columns)
Left panel (unchanged)        | Live Agent Workflow (unchanged)
Research setup                | Executive summary: chips, takeaway, KPI tiles, one blocker block
Saved research runs           | Report downloads (one row, equal buttons)
                              | Six pills: Business intelligence (4) | Trust & engineering (2)
                              |   selected area
                              | Full original six-section report (collapsed)
```

| Control | Behaviour |
|---|---|
| Chips | Crew completion and report acceptance are two separate facts |
| KPI tiles | Competitors with evidence, with a verified price, quality checks passed, agents completed, **URLs discovered**, **Pages read** (URLs discovered are not verified; only pages read were fetched) |
| Downloads | Stored Markdown and PDF; `(PARTIAL)` / `(UNVALIDATED)` suffix; side by side down to 521 px |
| Pills | Six areas; selection persists; wraps (two rows at 1280 px is accepted by design) |
| Competitor Landscape | Profile cards, price badge, offer, strength, gap, channels, evidence links with provenance |
| Customer Voice | Findings by competitor with basis and source link |
| Market Opportunity | Gap (interpretation) and proposed offer (Recommendation, not a fact) |
| 30-Day Launch Roadmap | Four week cards parsed from the report; labelled proposals |
| Evidence & Quality | R1-R8, gate counts, unsupported items, link reachability (HTTP only), ledger summary |
| Engineering Trace | Measured tiles and a collapsed expander with events, tool calls, evidence ledger, per-agent usage and environment names |
| Full report | Collapsed; URLs and table cells wrap; no page-level horizontal scroll |

## Guarantees

- Rendering is deterministic from stored data; model-written text is labelled.
- No model, search or research call from viewing, navigating, switching saved runs or downloading
  (tests trap `build_llm`, `LLM.call`, Serper, page read and crew execution; file hashes of saved
  runs are compared before and after).
- Historical artifacts are never modified.

## Responsive verification (100 percent zoom, headless Edge, real saved runs)

Widths 1440, 1280, 1024, 768, 390 for the partial (L5), legacy and cancelled runs: no page-level
horizontal scroll; headings in both columns share one top at 1440 and 1280 (panels stack at 1200
px and below); four agent cards in one row down to 1024 px (single column below 820 px);
download buttons equal size; opened report without overflow or clipped text.
