# LLM Efficiency Audit (M3 baseline)

Scope: the four M3 live runs recorded in `runs/` (events.jsonl, metadata.json, evidence.json).
**No additional API calls were made for this audit.** Figures are measured from those logs unless
marked *inferred*. Runs are one idea (millet meal boxes, Coimbatore); sample size is small, so
treat numbers as a baseline, not a benchmark.

## Baseline

| Run | Status | LLM calls | Tokens (prompt + completion) | Prompt share | Serper | Page reads (executed) |
|---|---|---|---|---|---|---|
| L1 | complete | 13 | 74,401 (67,377 + 7,024) | 90.6% | 12 | 10 |
| L2 | complete | 10 | 53,462 (46,019 + 7,443) | 86.1% | 11 | 8 |
| L3 | cancelled (cancel did not stop the crew; defect, fixed) | 11 | 39,797 (34,793 + 5,004) | 87.4% | 6 | 5 |
| L4 | cancelled (after fix) | 6 | 17,475 (15,496 + 1,979) | 88.7% | 6 | 5 |

Mean of the two complete runs: 11.5 LLM calls, 63,932 tokens, 11.5 searches, 9 page reads.
Observed range for the same input: 53k-74k tokens (a 28% spread).

### LLM calls per agent (from `llm_completed` events)

| Run | Market Researcher | Review Analyst | Strategy Analyst | Report Writer |
|---|---|---|---|---|
| L1 | 7 | 3 | 1 | 2 |
| L2 | 3 | 4 | 1 | 2 |
| L3 | 5 | 2 | 1 | 3 |
| L4 | 6 | - | - | - |

### Task latency (task_started to task_completed)

| Run | Research | Reviews | Strategy | Report | Total |
|---|---|---|---|---|---|
| L1 | 49.6 s | 14.0 s | 15.4 s | 24.9 s | 1m46s |
| L2 | 26.8 s | 28.3 s | 16.6 s | 22.6 s | 1m35s |

Per-agent **tokens** were not recorded per call in M3 (only run totals), so they cannot be
attributed to agents from these logs. Instrumentation added after the audit (below) closes this gap.

### Run L5 (M4 live acceptance; the first with per-agent tokens)

| Metric | Value |
|---|---|
| Input | Cold-pressed juice subscription / Pune / gym-goers aged 20-35 |
| Outcome | `status=complete`, acceptance fail (2 competitors with evidence, 0 verified prices) |
| LLM calls | 13 (Market Researcher 5, Review Analyst 5, Strategy Analyst 1, Report Writer 2) |
| Tokens | 69,095 (61,872 prompt + 7,223 completion) |
| Tokens per agent | Market Researcher 22,847; Review Analyst 32,816; Strategy Analyst 3,111; Report Writer 10,321 |
| Tools | 12 searches, 10 page reads, 2 cache answers, 9 budget refusals, 1 read error |
| Latency (task seconds) | 33.7 / 24.7 / 15.0 / 33.7 |
| Post-run actions | 3 fresh page loads and 2 download rounds: 0 events appended, no file changed |

Compared with L2 (53,462 tokens, 10 calls) L5 spent 29 percent more tokens for a weaker evidence
result (no verified price). Variance across inputs is large, so the per-agent figures, not the
totals, are the useful baseline: the Review Analyst is the largest consumer (47 percent) because
scraped pages are re-sent on every turn.

## Findings

| # | Finding | Evidence | Impact |
|---|---|---|---|
| F1 | Repeated or avoidable *identical* searches: none | 0 exact duplicate queries in L1-L4; 0-3 near-duplicate pairs (token overlap >= 0.7) in the cancelled runs | Good: search budget was not wasted on repeats |
| F2 | Budget refusals cost model turns | L1: 6 page-read refusals; L3: 5 refusals (3 search, 2 read); the model asked for 14 page reads in one step against a budget of 10 (L1) | Each refusal is a tool round that returns no evidence but is fed back to the model; prompts should state the budget up front |
| F3 | Shared budget starved the Review Analyst | L1: Review Analyst produced 0 findings | Quality defect, fixed in L2 with per-agent budgets (10 findings, 6 sourced) |
| F4 | Pages re-requested | L1: 2, L2: 2, L3: 1 URL requested twice; `cache_hits` showed 0 | *Inferred*: answered by CrewAI's own tool cache before our wrapper ran (executed + refused + errors is 2 short of started calls in L1 and L2). Free, but it was not counted. Fixed: derived count added to usage |
| F5 | Prompt tokens dominate | 86-91% of tokens are prompt | Cost is driven by accumulated context (6,000-character pages, raw upstream outputs passed to later tasks), not by generation |
| F6 | Fetched pages not used in the final competitor set | L1: 6 of 10 scraped pages, L2: 4 of 8 not referenced by final competitors (some may have informed reviews) | Candidate for deterministic pre-filtering of which pages are worth reading |
| F7 | Duplicate report write | L3: Report Writer called the write tool twice | One avoidable tool round plus model turn; prompt already says "once" |
| F8 | Cancel did not stop spending | L3: all four tasks ran to completion after the cancel click (39.8k tokens) | Defect, fixed: callbacks raise to stop; L4 stopped within ~18 s |
| F9 | Observability gaps | No per-call tokens, no per-call tool outcome, CrewAI cache answers uncounted, no hard cap on model calls | Fixed in code (below) |
| F10 | UI actions and LLM calls | Polling, reruns and tab rendering only read `RunManager` snapshots; no code path from them to an agent or LLM | Now enforced by tests |

## Standards (also recorded in PRP section 9a and the checklist)
See `PRPs/launchscout-prp.md` section 9a. Summary: no model call without an explicit Run or Re-run
action; deterministic Python for validation, formatting, exports and price comparison; bounded
budgets and a hard LLM-call cap; reuse of verified evidence and structured outputs; the deck never
repeats research; every standard has an automated test.

## Implemented after the audit (no live calls)
| Change | Where | Test |
|---|---|---|
| Per-call tokens recorded in `llm_completed` events; per-agent efficiency table (LLM calls, tokens, tool calls, executed, cache hits, refused, errors, task seconds) in Behind the Scenes | `events.py`, `progress.agent_metrics`, `ui/research_tab.py` | `test_efficiency.py::test_tool_outcomes_and_per_agent_metrics_are_measured` |
| Per-call tool outcome events (`executed`, `cache_hit`, `refused_budget`, `error`) with latency | `tools.py` | same |
| CrewAI cache answers counted in usage (started calls minus wrapper invocations) | `runner.py` | `test_crewai_cache_answers_are_counted_not_hidden` |
| Hard model-call cap `max_llm_calls` (default 40; observed 6-13) stops the run with a stated reason | `config.py`, `events.py`, `runner.py` | `test_llm_call_limit_stops_the_run` |
| Explicit reuse: identical input (case/spacing/competitor order ignored) shows the completed run and makes no calls until "Run again" is clicked | `runner.find_reusable`, `ui/research_tab.py` | `test_identical_input_reuses_completed_run_until_explicit_rerun`, `test_input_identity_ignores_case_spacing_and_competitor_order`, `test_failed_or_cancelled_runs_are_never_reused` |
| Non-AI actions make zero LLM calls: reruns, polling, tab rendering, deck/weekly tabs | sentinels on `build_llm` and `crewai.LLM.call`, executor call counter | `test_reruns_polling_and_tab_rendering_make_no_llm_calls`, `test_polling_an_active_run_does_not_restart_it`, `test_deck_and_weekly_tabs_never_start_runs` |
| Deterministic modules may not import LLM code | AST import scan | `test_deterministic_modules_import_no_llm_code` |
| Artifacts persisted before a run is reported finished | `runner.py` | `test_state_survives_new_manager_via_disk` |

## Outstanding optimizations for M4-M8 (not yet implemented)
| Milestone | Optimization | Expected effect / guard |
|---|---|---|
| M4 | Validation, link checks, acceptance gate, Markdown/PDF export, price formatting are pure Python | Zero model calls; test with the LLM sentinel |
| M4 | Verify price amounts against scraped text deterministically (store a bounded text window per page) instead of asking a model to re-check | Fewer review turns; stronger evidence |
| M4/M5 | Pass structured fields (JSON subset) between tasks instead of full raw outputs; cap context size | Attacks the 86-91% prompt share |
| M4/M5 | State the remaining tool budget in the task prompt and ask for batched, prioritised calls | Fewer refusals (F2) |
| M4/M5 | Deterministic page selection: rank candidate URLs (official domain, menu/price paths) before the model reads them | Fewer wasted reads (F6) |
| M4/M5 | Reduce `scrape_max_chars` or extract price/menu windows deterministically | Lower prompt tokens; check quality on the same inputs first |
| M5 | Hierarchical Manager: bound delegations; count Manager calls separately; compare against the sequential baseline before accepting | Manager overhead must be measured, not assumed |
| M6 | Pitch deck consumes the validated report and stored structured outputs only; no search or scrape tools in the deck crew; one model call to produce `DeckSpec`; PPTX rendering and claim validation deterministic | Deck cost is a single bounded call; test asserts zero tool calls |
| M7 | Weekly rerun re-checks prices of already-known competitors by deterministic fetch + price extraction first; invoke the model only for new-competitor discovery or when extraction fails; diff is pure Python | Largest recurring saving; snapshot diff makes zero model calls |
| M7 | Cross-run evidence cache keyed by URL with a freshness window; reuse unchanged pages | Fewer page reads on reruns; staleness must be labelled |
| M8 | Re-measure on the sample and alternate inputs; record before/after per agent; ship only changes that do not reduce verified-price coverage or sourced-finding counts | Quality-preserving gate |

## M4 efficiency result
- Validation, tagging, link status, Markdown and PDF generation, the quality evaluation and
  downloads are pure Python: **0 model calls, 0 searches** (tests with `build_llm` and
  `crewai.LLM.call` sentinels; AST import scan of every report module).
- Reuse: the report is assembled from the stored ledger and structured outputs; pages read during
  research are not requested again for link status (E-05).
- Unchanged: the Report Writer agent still costs 2-3 model calls (15 to 27 percent of a run's
  calls in L1-L3). Replacing it with deterministic assembly would save those calls and their prompt tokens,
  but the assignment requires the agent, so this is a decision for the user, not an automatic change.

## Quality guard
Efficiency changes are accepted only if, on the same inputs, they do not reduce: number of
competitors with evidence URLs, verified-price count, sourced review findings, or report-section
completeness. Baselines for L2 (complete run): 5 competitors, 1 verified price, 10 findings (6 sourced).
