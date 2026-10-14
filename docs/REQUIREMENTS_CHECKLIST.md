# REQUIREMENTS CHECKLIST — LaunchScout

> Source of truth: `PRPs/launchscout-prp.md` section 10. Status values: `Not started`, `Partial`, `Done`, `Blocked`.
> Rows sourced from `INITIAL.md` carry the caveat **unverified vs original assignment text** (TD-3).

## Status after M2 (14 Oct 2026)

| Req | Requirement | Implementation | Test evidence | Status |
|---|---|---|---|---|
| F-01 | Input fields + validation | `launchscout/inputs.py`, `ui/research_tab.py` | `tests/test_inputs.py` (7), `tests/test_ui_structure.py::test_validation_errors_displayed` | **Done** |
| F-02 | Sample + alternate input, no code change | same | `test_inputs.py::test_sample_and_alt_inputs` (validation only); live runs not executed | Partial (live runs M3/M8) |
| F-03 | Env/keys by name only | `launchscout/config.py` | `tests/test_config.py` (6) | **Done** |
| A-01..A-04 | Agents, tasks, sequential process | — | — | Not started (M3) |
| P-01, P-02 | Progress, Behind the Scenes | — | — | Not started (M3) |
| R-01..R-06 | Report, exports, downloads | — | — | Not started (M4) |
| R-07 | Run-specific directories | `launchscout/runs.py` | `tests/test_runs.py` (4) | Partial (report/export use in M4) |
| G-01..G-04, G-06 | Acceptance gate, evidence validation, tools | — | — | Not started (M3/M4) |
| G-05 | Secrets excluded | `.gitignore`, `.env.example`, `launchscout/logging_utils.py` | `tests/test_secrets.py` (5), `tests/test_config.py` | **Done** |
| PR-01 | Partial-report behaviour | — | — | Not started (M4) |
| SA-01 | Hierarchical + Manager | — | — | Not started (M5) |
| SA-02 | Mode selector in Research Workspace | `ui/research_tab.py` | `test_ui_structure.py::test_selector_in_research_tab` | Partial (placement only; wired in M5) |
| SB-01..SB-03 | Deck agent, PPTX, claim validation | — | — | Not started (M6) |
| SB-04 | Deck tab disabled without report | `ui/deck_tab.py` | `test_ui_structure.py::test_deck_tab_disabled_without_report` | Partial (partial-report refusal in M6) |
| SC-01..SC-07 | Weekly tracking | `ui/weekly_tab.py` (placeholder) | — | Not started (M7) |
| UI-01 | Exactly three tabs | `app.py`, `ui/theme.py` | `test_ui_structure.py::test_three_tabs_only` | **Done** |
| D-01 | README setup | — | — | Not started (M8; replaces template README per D1) |
| D-02 | Docs | `docs/BUILD_LOG.md`, `QUALITY_REPORT.md`, this file | `docs/` present | Partial |
| D-03 | Live sample + alternate runs | — | — | Not started / blocked on TD-1, TD-2 |

Counts: Done 4 · Partial 6 · Not started remainder · Blocked: live gates (TD-1, TD-2).

## Acceptance criteria (INITIAL.md section 10)
None marked complete. No live verification has been performed.
