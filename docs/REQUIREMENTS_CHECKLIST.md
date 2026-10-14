# REQUIREMENTS CHECKLIST — LaunchScout

> Source of truth: `PRPs/launchscout-prp.md` section 10. Status values: `Not started`, `Partial`, `Done`, `Blocked`.
> Rows sourced from `INITIAL.md` carry the caveat **unverified vs original assignment text** (TD-3).

## Status after M3 (14 Oct 2026, awaiting acceptance review)

| Req | Requirement | Implementation | Test evidence | Status |
|---|---|---|---|---|
| F-01 | Input fields + validation | `launchscout/inputs.py`, `ui/research_tab.py` | `tests/test_inputs.py` (7), `tests/test_ui_structure.py::test_validation_errors_displayed` | **Done** |
| F-02 | Sample + alternate input, no code change | same | `test_inputs.py::test_sample_and_alt_inputs` (validation only); live runs not executed | Partial (live runs M3/M8) |
| F-03 | Env/keys by name only | `launchscout/config.py` | `tests/test_config.py` (6) | **Done** |
| A-01..A-04 | Agents, tasks, sequential process | `launchscout/agents.py`, `tasks.py`, `crew.py` | `tests/test_crew_structure.py`; live runs L1-L4 | **Done (M3)** |
| P-01, P-02 | Progress, Behind the Scenes | `launchscout/events.py`, `progress.py`, `runner.py`, `ui/research_tab.py` | `test_events.py`, `test_runner.py`, `test_ui_run.py`; live runs | **Done (M3)**; validation results arrive in M4 |
| R-01..R-06 | Report, exports, downloads | — | — | Not started (M4) |
| R-07 | Run-specific directories | `launchscout/runs.py` | `tests/test_runs.py` (4) | Partial (report/export use in M4) |
| G-01..G-04, G-06 | Acceptance gate, evidence validation, tools | `tools.py`, `evidence.py`, `grounding.py` | `test_tools.py`, `test_grounding.py` | Partial: caps, cache, injection envelope and ledger grounding done (M3); acceptance gate and report validators M4 |
| G-05 | Secrets excluded | `.gitignore`, `.env.example`, `launchscout/logging_utils.py` | `tests/test_secrets.py` (5), `tests/test_config.py` | **Done** |
| E-01 | No model call from UI reruns, polling, tabs, downloads | `ui/research_tab.py`, `launchscout/runner.py` | `test_efficiency.py` (3 tests) | **Done (M3 scope)**; downloads/exports verified when added (M4) |
| E-02 | One active run; explicit reuse of completed results | `runner.py`, `ui/research_tab.py` | `test_runner.py::test_duplicate_run_prevented_while_active`, `test_efficiency.py` (3 tests) | **Done (M3)** |
| E-03 | Deterministic modules import no LLM code | `grounding`, `evidence`, `progress`, `runs`, `inputs`, `schemas`, `config`, `logging_utils` | `test_efficiency.py::test_deterministic_modules_import_no_llm_code` | Partial: extend to `validation`, `report`, `exports/*`, `deck` claim checks, `weekly/diff` (M4, M6, M7) |
| E-04 | Bounded budgets, retries, timeouts, LLM-call cap | `config.RunLimits`, `tools.py`, `runner.py` | `test_tools.py`, `test_runner.py`, `test_efficiency.py::test_llm_call_limit_stops_the_run` | **Done (M3)** |
| E-05 | Reuse evidence and structured outputs | `evidence.py`, run artifacts | `test_runner.py` (persistence) | Partial: structured hand-off between tasks and cross-run evidence cache (M4/M5, M7) |
| E-06 | Deck never repeats research | — | — | Not started (M6) |
| E-07 | Weekly rerun deterministic-first | — | — | Not started (M7) |
| E-08 | Per-agent calls, tokens, outcomes, latency measured | `events.py`, `progress.agent_metrics`, `tools.py` | `test_efficiency.py::test_tool_outcomes_and_per_agent_metrics_are_measured` | **Done (M3)**; first live run with per-agent tokens still to be recorded |
| E-09 | Quality preserved when optimizing | `docs/LLM_EFFICIENCY_AUDIT.md` baseline | — | Process rule; applied from M4 |
| E-10 | Each standard has an automated test | `tests/test_efficiency.py` | 17 tests | Partial (E-06, E-07 pending their milestones) |
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
Not marked complete. Live runs L1-L4 (see `BUILD_LOG.md`) exercised the sequential crew; acceptance validation and exports are M4.
