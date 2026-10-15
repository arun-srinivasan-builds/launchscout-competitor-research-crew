# REQUIREMENTS CHECKLIST — LaunchScout

> Source of truth: `PRPs/launchscout-prp.md` section 10. Status values: `Not started`, `Partial`, `Done`, `Blocked`.
> Rows sourced from `INITIAL.md` carry the caveat **unverified vs original assignment text** (TD-3).

## Status after M4 (14 Oct 2026, M4 gate)

| Req | Requirement | Implementation | Test evidence | Status |
|---|---|---|---|---|
| F-01 | Input fields + validation | `launchscout/inputs.py`, `ui/research_tab.py` | `tests/test_inputs.py` (7), `tests/test_ui_structure.py::test_validation_errors_displayed` | **Done** |
| F-02 | Sample + alternate input, no code change | same | `test_inputs.py::test_sample_and_alt_inputs` (validation only); live runs not executed | Partial (live runs M3/M8) |
| F-03 | Env/keys by name only | `launchscout/config.py` | `tests/test_config.py` (6) | **Done** |
| A-01..A-04 | Agents, tasks, sequential process | `launchscout/agents.py`, `tasks.py`, `crew.py` | `tests/test_crew_structure.py`; live runs L1-L4 | **Done (M3)** |
| P-01, P-02 | Progress, Behind the Scenes | `launchscout/events.py`, `progress.py`, `runner.py`, `ui/research_tab.py` | `test_events.py`, `test_runner.py`, `test_ui_run.py`; live runs | **Done (M3)**; validation results arrive in M4 |
| R-01..R-06 | Report, exports, downloads | `launchscout/validation.py`, `report.py`, `reporting.py`, `links.py`, `exports/{markdown,pdf}.py`, `ui/research_tab.py` | `test_validation.py` (19), `test_exports.py` (6), `test_m4_flow.py` (12) | **Done (M4)**; verified on stub crew, offline re-validation of two stored runs and one live run (L5: partial on actual evidence, links checked, PDF opened) |
| R-07 | Run-specific directories | `launchscout/runs.py` | `tests/test_runs.py` (4), `test_m4_flow.py` | **Done (M4)**: report, writer original, validation, PDF all under `runs/<id>/` |
| G-01..G-04, G-06 | Acceptance gate, evidence validation, tools | `tools.py`, `evidence.py`, `grounding.py`, `validation.py` | `test_tools.py`, `test_grounding.py`, `test_validation.py` | **Done (M3 + M4)**: caps, cache, injection envelope, ledger grounding, eight validators R1-R8 and the acceptance gate |
| G-05 | Secrets excluded | `.gitignore`, `.env.example`, `launchscout/logging_utils.py` | `tests/test_secrets.py` (5), `tests/test_config.py` | **Done** |
| E-01 | No model call from UI reruns, polling, tabs, downloads | `ui/research_tab.py`, `launchscout/runner.py` | `test_efficiency.py` (3), `test_m4_flow.py::test_viewing_downloading_and_reruns_make_zero_additional_llm_calls` | **Done through M4** (report view, quality panel, downloads, reruns) |
| E-02 | One active run; explicit reuse of completed results | `runner.py`, `saved_runs.py`, `ui/research_tab.py` | `test_runner.py::test_duplicate_run_prevented_while_active`, `test_efficiency.py` (3), `test_saved_runs.py::test_identical_input_is_reused_from_disk_after_restart` | **Done**; reuse also works across restarts |
| E-03 | Deterministic modules import no LLM code | M3 list plus `validation`, `report`, `links`, `reporting`, `exports/pdf`, `exports/markdown` | `test_efficiency.py::test_deterministic_modules_import_no_llm_code`, `test_m4_flow.py::test_report_modules_are_deterministic_and_import_no_llm_code` | Partial: `deck` claim checks and `weekly/diff` remain (M6, M7) |
| E-04 | Bounded budgets, retries, timeouts, LLM-call cap | `config.RunLimits`, `tools.py`, `runner.py` | `test_tools.py`, `test_runner.py`, `test_efficiency.py::test_llm_call_limit_stops_the_run` | **Done (M3)** |
| E-05 | Reuse evidence and structured outputs | `evidence.py`, `reporting.py`, `links.py` | `test_m4_flow.py` (re-validation from artifacts), `test_exports.py::test_pages_read_during_research_are_not_requested_again` | Partial: M4 reuses ledger and structured outputs with no new searches; task-to-task structured hand-off and cross-run cache remain (M5, M7) |
| E-06 | Deck never repeats research | — | — | Not started (M6) |
| E-07 | Weekly rerun deterministic-first | — | — | Not started (M7) |
| E-08 | Per-agent calls, tokens, outcomes, latency measured | `events.py`, `progress.agent_metrics`, `tools.py` | `test_efficiency.py::test_tool_outcomes_and_per_agent_metrics_are_measured`; live run L5 | **Done**; first live per-agent token table recorded (L5) |
| E-09 | Quality preserved when optimizing | `docs/LLM_EFFICIENCY_AUDIT.md` baseline | — | Process rule; applied from M4 |
| E-10 | Each standard has an automated test | `tests/test_efficiency.py` | 17 tests | Partial (E-06, E-07 pending their milestones) |
| SR-01 | Saved runs reopenable in Streamlit with zero model/search calls, after restart; states distinguished; historical runs unchanged | `launchscout/saved_runs.py`, `runner.snapshot_from_disk`, `ui/research_tab.py` | `tests/test_saved_runs.py` (12) incl. restart recovery, zero-call traps, hash comparison, real `runs/` replay | **Done (M4 add-on)**; how-to in `docs/REVIEWING_SAVED_RUNS.md` |
| PR-01 | Partial-report behaviour | `reporting.py`, `exports/markdown.py`, `report.py`, `ui/research_tab.py` | `test_m4_flow.py::test_partial_run_uses_partial_names_header_and_tags`, `::test_missing_report_is_failed_no_report_without_files`, `::test_revalidation_is_deterministic_and_has_no_override`, `test_exports.py::test_partial_report_never_written_as_validated_name` | **Done (M4)**; deck refusal for partial reports is M6 |
| SA-01 | Hierarchical + Manager | `launchscout/crew.py`, `agents.py`, `runner.py`, `ui/workflow.py` | `tests/test_hierarchical.py` (26), `test_crew_structure.py` | **Implemented and verified offline (M5)**; live delegation not yet measured |
| SA-02 | Mode selector in Research Workspace | `ui/research_tab.py` | `test_ui_structure.py::test_selector_in_research_tab`, `test_hierarchical.py::test_selecting_hierarchical_renders_manager_and_runs_through_cockpit` | **Done (M5)** |
| SA-03 | Manager guards: budgets, delegation cap, undelegated-task guard, cancellation | `events.py`, `runner.py`, `crew.py` | `test_hierarchical.py` | **Done offline (M5)** |
| SA-04 | Sequential vs hierarchical comparison from recorded runs | `launchscout/comparison.py`, `ui/cockpit.py` | `test_hierarchical.py::test_comparison_*` | **Done (M5)**; hierarchical column is Not yet measured until a live run |
| E-11 | Remaining tool budgets exposed to agents | `tools.py`, `tasks.py` | `test_hierarchical.py::test_budgets_are_stated_in_prompts_and_tool_results` | **Done (M5)**; effect on refusals to be measured live |
| SB-01..SB-03 | Deck agent, PPTX, claim validation | — | — | Not started (M6) |
| SB-04 | Deck tab disabled without report | `ui/deck_tab.py` | `test_ui_structure.py::test_deck_tab_disabled_without_report` | Partial (partial-report refusal in M6) |
| SC-01..SC-07 | Weekly tracking | `ui/weekly_tab.py` (placeholder) | — | Not started (M7) |
| UI-02 | Research Intelligence Cockpit replaces Results and Behind the Scenes; saved and live runs, all run states, zero extra calls, responsive | `ui/cockpit.py`, `ui/trace.py`, `ui/research_tab.py` | `tests/test_cockpit.py` (16), `test_m4_flow.py`, `test_saved_runs.py`; responsive check at five widths | **Done (M4)** |
| UI-01 | Exactly three tabs | `app.py`, `ui/theme.py` | `test_ui_structure.py::test_three_tabs_only` | **Done** |
| D-01 | README setup | — | — | Not started (M8; replaces template README per D1) |
| D-02 | Docs | `docs/BUILD_LOG.md`, `QUALITY_REPORT.md`, this file | `docs/` present | Partial |
| D-03 | Live sample + alternate runs | — | — | Not started / blocked on TD-1, TD-2 |

Counts: Done 4 · Partial 6 · Not started remainder · Blocked: live gates (TD-1, TD-2).

## Acceptance criteria (INITIAL.md section 10)
Not marked complete. Live runs L1-L4 (see `BUILD_LOG.md`) exercised the sequential crew; acceptance validation and exports are M4.

- SA-02/SA-03 live check: executed once as L6 (hierarchical delegation worked, 4 delegations, all tasks completed, limits respected); research acceptance still not met in either mode.

## M6 Pitch Deck (Stretch B) - offline status
| ID | Requirement | Evidence | Status |
|---|---|---|---|
| SB-01 | Dedicated Pitch Deck agent, no tools, reuses saved research | `tests/test_deck.py::test_agent_has_no_tools_and_no_delegation`, `::test_generate_uses_one_agent_call_and_exports_editable_pptx` | Offline pass; live not run |
| SB-02 | Exactly six slides, fixed titles | `::test_parse_accepts_fenced_json_and_rejects_wrong_slide_count`, `::test_wrong_title_is_a_violation` | Offline pass |
| SB-03 | Editable native PPTX (no pictures) | `::test_generate_uses_one_agent_call_and_exports_editable_pptx` | Offline pass |
| SB-04 | Claims grounded; prices/URLs/stats/names/years checked; violations block export | `::test_deck_blocks_*`, `::test_violations_block_export_but_keep_spec_and_meta` | Offline pass |
| SB-05 | Unknown prices, recommendations, assumptions, partial evidence labelled | `::test_labels_mark_*` | Offline pass |
| SB-06 | No automatic research rerun; no model call on view/download | `::test_tab_uses_saved_run_without_model_calls_until_clicked`, `::test_generation_does_not_touch_research_files` | Offline pass |
| SB-07 | Live deck generation from a real saved run | not executed (needs approval) | Not yet measured |

| SB-08 | Multiline label banners stay inside their highlight and above the footer | `tests/test_deck.py::test_multiline_warning_banner_grows_to_contain_its_text`, `::test_short_labels_keep_a_compact_banner`, `::test_bounds_check_flags_a_banner_too_small_for_its_text` | Offline pass; visual re-check pending |
| SB-01..SB-06 | Live check L6 deck | 1 call, 4,486 tokens, claim check 0 violations after rule correction, PPTX 6 slides | Executed; time unavailable |

| SB-09 | Enterprise infographic deck: dashboard, matrix, evidence grid, flow, pricing dashboard, roadmap; logo on every slide | `tests/test_deck.py::test_every_slide_has_logo_status_footer_and_native_shapes`, `::test_visual_components_present_and_editable`, `::test_layout_adapts_to_competitor_count`, `::test_layout_has_no_overflow_collisions_or_footer_hits`, `::test_space_utilisation_is_high_on_every_slide` | Offline pass; real-render check pending |
| SB-10 | Layout engine not hardcoded to one idea | `::test_layout_engine_is_not_hardcoded_to_one_idea` | Offline pass |

| WF-01 | Connector animation driven by recorded transitions/delegations; none when idle/finished; reduced motion | `tests/test_workflow_motion.py::test_sequential_connector_follows_recorded_task_transitions`, `::test_manager_links_are_driven_only_by_recorded_delegations`, `::test_idle_and_finished_workflows_have_no_moving_connector`, `::test_reduced_motion_disables_every_animation` | Pass; browser-verified once (headless Edge) |
| WF-02 | All Manager delegations visible in recorded order | `::test_all_delegations_are_listed_in_recorded_order_and_kept_apart`, `::test_saved_l6_shows_all_four_recorded_delegations` | Pass |
| WF-03 | Offline replay (play/pause/restart/step), same final state as saved view, zero calls | `::test_replay_preserves_event_order_and_is_monotonic`, `::test_replay_final_state_equals_saved_run_view`, `::test_replay_controls_step_play_restart_with_zero_calls` | Pass |

| TR-01 | Same-scope comparison; incompatible runs rejected with reasons | `tests/test_tracking.py::test_same_scope_runs_are_compared`, `::test_different_scope_is_rejected_with_a_reason`, `::test_same_run_or_older_latest_and_missing_runs_are_rejected` | Pass |
| TR-02 | New / not-observed competitors, careful labels | `::test_new_and_absent_competitors_use_careful_labels`, `::test_competitors_match_by_name_or_non_generic_host_only` | Pass |
| TR-03 | Price change only when comparable and evidence-backed | `::test_verified_price_change_needs_comparable_evidence_backed_amounts`, `::test_incomparable_prices_are_insufficient_evidence_not_a_change`, `::test_verification_gained_or_lost_is_not_a_price_change` | Pass |
| TR-04 | Offering, subscription, channel, evidence changes; partial runs; empty data | `::test_offering_subscription_and_channel_changes`, `::test_evidence_availability_changes_are_inconclusive_coverage_notes`, `::test_partial_runs_are_compared_with_honest_limitations`, `::test_empty_and_incomplete_data_are_reported_not_guessed` | Pass |
| TR-05 | Deterministic Markdown export; zero model/search calls; UI empty state | `::test_markdown_export_is_deterministic_and_evidence_referenced`, `::test_tracking_module_has_no_model_or_network_dependencies`, `::test_ui_*` | Pass |

## M8 Public demo mode and deployment package - local status (15 Oct 2026)

Deployment to the VPS is **not executed**; rows below cover what was verified locally.

| Req | Requirement | Implementation | Test / check evidence | Status |
|---|---|---|---|---|
| D-01 | Public demo cannot start paid work (run, model, search, scrape, crew, deck, model check) | `launchscout/demo.py::require_live` at each execution boundary | `tests/test_demo_mode.py::test_run_manager_refuses_to_start_a_run_in_demo`, `::test_model_search_scrape_crew_deck_and_model_check_are_blocked`, UI submit tests | Pass |
| D-02 | Fails closed: only explicit `LAUNCHSCOUT_MODE=live` enables live | `launchscout/demo.py::configured_mode` | `::test_mode_fails_closed_and_live_needs_an_explicit_setting`, `::test_live_can_come_from_a_local_env_file_but_the_environment_wins` | Pass |
| D-03 | Demo data holds no secrets or paths; expected files only | `demo_data/saved_runs` (L5, L6) | `tests/test_demo_mode.py` (file-set, offender and secret scans); key values from local `.env` searched in tracked and demo files: none found | Pass |
| D-04 | Image has no credentials; non-root; read-only rootfs; caps dropped | `Dockerfile`, `docker-compose.yml`, `.dockerignore` | `docker inspect`: ReadonlyRootfs=true, CapDrop=[ALL], no-new-privileges, user app; in-container: no `.env`, no `secrets.toml`, no API key variables, writes to `/app` and demo data blocked | Pass (local) |
| D-05 | Container serves the app: health, three tabs, saved runs, replay, tracking | Docker image | health 200 via `/_stcore/health`; in-container Streamlit AppTest: no exception, 3 tabs, demo banner, run button disabled, newest run selected, replay step, tracking comparison eligible, tracking Markdown export 7024 chars, saved deck loads | Pass (local) |
| D-06 | Browser-level downloads in the container | `ui/*` `st.download_button` (reads saved files) | Files verified present and readable; button clicks not exercised (AppTest cannot click downloads) | Partial |
| D-07 | Publish behind existing Traefik, no public 8501 | `deploy/docker-compose.traefik.yml`, `docs/DEPLOYMENT.md` | `compose config` fails without the four required variables; renders with no `ports:` | Prepared, not deployed |
| D-08 | Verify Traefik network, entrypoint, resolver names on the VPS | `docs/DEPLOYMENT.md` step 2 | not executed (no VPS access in this session) | Not started |
