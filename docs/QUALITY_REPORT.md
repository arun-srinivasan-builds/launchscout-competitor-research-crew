# QUALITY REPORT — LaunchScout

> Measured results only. Anything not executed is marked `not executed`. No live API check has been run.

## Milestone M2 (scaffold and configuration), 14 Oct 2026

### Requirements
| Metric | Value |
|---|---|
| Matrix rows targeted by M2 | 8 (F-01, F-02, F-03, R-07, G-05, UI-01, SA-02 placement, SB-04 disabled state) |
| Done | 4 (F-01, F-03, G-05, UI-01) |
| Partial (M2 portion complete, rest in later milestones) | 4 (F-02, R-07, SA-02, SB-04) |
| Total matrix rows | 40 (unchanged; 4 Done after M2) |

### Test results
| Gate | Run | Result |
|---|---|---|
| ruff | 1 | 5 E501 line-length findings |
| pytest | 1 | 3 collection errors (defect 1) |
| ruff | 2 | 1 E501 finding |
| pytest | 2 | 40 passed, 1 failed (finding 3) |
| ruff | 3 | All checks passed |
| pytest | 3 | 42 passed, 0 failed |
| *UI confirmation change: palette, workflow area, Behind the Scenes, config.toml* | | |
| ruff | 4 | 8 E501 findings (CSS block lines + 1 reflow) |
| pytest | 4 | 49 passed, 0 failed |
| ruff | 5 | All checks passed (per-file E501 ignore for the embedded CSS block; one line reflowed) |
| pytest | 5 | **49 passed, 0 failed** |
| `pip check` | 1 | No broken requirements |
| `pip install --dry-run -r requirements.txt` | 1 | Already satisfied (no changes) |
| Streamlit smoke (headless, port 8599), final build | 2 runs | `/_stcore/health` 200, `/` 200, no `runs/` directory created |
| Contrast ratios (computed) | 1 | All 8 text/background pairs >= 4.7:1 (listed in `ui/theme.py`) |

First-pass success: **no**. The core gate needed 3 iterations (2 rework cycles); the UI confirmation change needed 1 more lint rework (3 rework cycles total).

Not executed: visual/browser review of the rendered page (no browser tool used). Layout was verified structurally (AppTest assertions on tabs, selector, workflow area, expander, disabled states) and by HTTP 200 only, not by screenshot.

### Defects and findings
| # | Type | Description | Status |
|---|---|---|---|
| 1 | Code defect | `PriceChange.date: date | None` field name shadowed the `date` type, breaking import of `launchscout.schemas` | Fixed (field renamed `observed_on`); regression covered by schema/test imports |
| 2 | Style | 5 lines exceeded the 100-char Ruff limit (then 8 more in the CSS block after the UI change) | Fixed (reflow; per-file E501 ignore for the CSS data block) |
| 4 | Documentation inaccuracy | User instruction cited the navy/steel/teal/soft-white palette as "documented in the PRP"; the PRP only said "restrained palette". Also my first draft of contrast numbers in `ui/theme.py` were estimates | Palette recorded in PRP v1.2; contrast numbers recomputed and corrected |
| 3 | Finding (test assumption) | crewai 1.15.28 will not construct an LLM for a model id it does not recognize unless LiteLLM is installed (`crewai[litellm]`). My first mocked test used an invented id and failed | Test split: recognizable id → `ok`; unrecognized id → `failed` is asserted as characterization. **Relevant to the unresolved model id (TD-1)** |

Defects found: 1 code defect, 1 lint class (13 findings), 1 test-assumption finding, 1 documentation inaccuracy. Resolved: all 4. Open: 0.
Rework cycles: 3.

### Source verification and unsupported claims
Not applicable in M2 (no research executed). Verified source coverage: n/a. Unsupported claims detected: n/a.

### API usage
| Item | Value |
|---|---|
| LLM calls | 0 |
| Serper calls | 0 |
| Provider model-list calls | 0 (`not executed`: no `.env`/key present) |
| Usage basis | none measured |

### Live checks
| Check | Status |
|---|---|
| Model identifier availability (`python -m launchscout.model_check`) | **not executed** — output: `status=not_configured`, `live_call_made=False` |
| CrewAI LLM construction for the requested model | **not executed** (requires availability check first) |

### Unresolved / caveats
- TD-1 model id, TD-2 keys, TD-3 original assignment reconciliation remain unresolved. `INITIAL.md`-derived requirement rows keep the `unverified vs original` caveat.
- Deck, weekly, and research execution are placeholders by design in M2; the UI says so.

### Regression log
| Milestone | Full suite | Result |
|---|---|---|
| M2 | 49 tests | 49 passed |
| M2 UI | 51 tests | 51 passed |
| M3 (commit 440acc7) | 112 tests | 112 passed |
| M3 efficiency follow-up | 129 tests | 129 passed (run twice) |
| M4 (uncommitted) | 169 tests | 169 passed (after the live acceptance run and evidence-text rule) |
| M4 saved-run replay (uncommitted) | 181 tests | 181 passed |
| M4 cockpit prototype | 195 tests | 195 passed |
| M4 cockpit integration (M4 gate) | 197 tests | 197 passed; ruff clean; responsive check at 1440/1280/1024/768/390 |
| M5 hierarchical (offline) | 221 tests | 221 passed; ruff clean; no API calls |

## M5 live hierarchical result (L6)
Hierarchical run reached the same acceptance outcome as sequential L5 (partial_failed_acceptance; 2 competitors, 0 verified prices) with 18 vs 13 model calls, +9.2% tokens, 178 s vs 108 s, and an extra R7 failure. Single run; no variance claim. See M5_HIERARCHICAL_LIVE_TEST_PLAN.md.

## M6 Pitch Deck (offline)
Deck claim check is deterministic and covers URLs, currency amounts, statistics, competitor names and years. Known limits: it cannot judge whether a paraphrased qualitative claim is faithful (only that numbers, names, URLs and prices are grounded); slide layout was not visually inspected (no PowerPoint/LibreOffice available); no live model output has been validated yet.

### M6 live deck outcome (L6 source)
One live generation (1 call, 4,486 tokens; time unavailable). First claim check blocked slide 6 for "proposed ₹699" (rule too narrow); rule corrected with regression tests and the stored spec revalidated offline: 0 violations, PPTX exported with six editable slides. Structure and labels verified programmatically; text-fit checked only by a heuristic estimate. Visual rendering inspection is still pending and no claim is made that layout is clean.

### M6 closure
Banner overflow on long recommendation labels fixed and covered by regression tests (`test_multiline_warning_banner_grows_to_contain_its_text`, `test_bounds_check_flags_a_banner_too_small_for_its_text`). Fit is verified by estimate only; the revised deck has not been rendered or visually inspected by me. Live metrics unchanged: 1 call, 4,486 tokens, time unavailable.

### M6 enterprise deck (V2)
Layout is deterministic and evidence-grounded; visuals show missing evidence as missing (unknown prices, zero complaints, unreadable sources). Verified programmatically: six slides, logo on each, native shapes/chart/connectors, labels, notes, no text overflow or collisions by estimate, utilisation 0.78-0.92. NOT verified: true PowerPoint rendering (no Office/LibreOffice here); a Pillow geometry preview using Calibri metrics was inspected, which is not a substitute. Known limits: text is auto-shrunk to 11 pt then shortened with an ellipsis in dense cells (full text in notes); extremely long banners with many labels can still crowd content; utilisation is a coarse grid estimate that counts cards, not information density.

### Workflow visualization (post-M6)
Connector motion is a pure function of recorded state (see `active_links`); idle, finished, cancelled and failed workflows have none. In sequential mode a link stays lit while the receiving specialist is active; that shows the recorded handoff, not a message. Limits: the HTML (and therefore the animation) restarts only when a new recorded event changes the canvas, not on every 1.5 s poll; delegation summaries are truncated at record time (~100 characters); the Manager still lists its own `write_report_file` call as a Manager tool call because CrewAI runs the task with the task's tools; replay steps through every recorded event (126 for L6), so the accelerated play takes about 75 s.

### M7 change tracking
Pure comparison of saved snapshots; findings describe research output, not the market. Known limits: offering and subscription differences are text comparisons of research summaries, so rewording by a different run appears as a change (stated in the limitations, and an evidence-only difference is "needs review"); competitor matching uses names and non-generic hosts, so a renamed competitor appears as one absent plus one new; only the fields stored in `competitors.json` are compared (no report prose); the L5/L6 pair is the only same-scope saved pair and was produced hours apart, so no real market change can be inferred from it.

### M7 classification correction
Wording differences between research runs are never counted as changed competitors: the "Changed" KPI requires a verified price change on comparable evidence. Regression tests cover synthetic wording noise, wording noise next to a genuine price change, the UI KPI, and the real L5 vs L6 pair (0 changed, 2 needs review). This corrects the earlier statement that L5/L6 showed two changed competitors.
