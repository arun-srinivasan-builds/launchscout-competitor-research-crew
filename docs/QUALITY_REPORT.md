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
