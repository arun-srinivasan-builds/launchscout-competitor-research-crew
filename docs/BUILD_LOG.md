# BUILD LOG — LaunchScout

> Actual events only. Times are IST. Each timestamp is tagged with its source.
> No durations, effort totals or productivity comparisons are calculated here until the user asks. Missing times are left as `not provided`, never estimated. Overlapping activities are listed once under the planning window and are not double-counted.

Source tags: `user-confirmed` (stated by the user) · `system-clock` (read from the machine clock by a command in this session) · `not provided`.

---

## Planning window (user-confirmed)

| Window | Date | Start (IST) | End (IST) | Source | Covers |
|---|---|---|---|---|---|
| Planning / requirements / PRP | 14 Oct 2026 | 10:20 AM | 10:56 AM | user-confirmed | Requirement gathering, template clone verification, repository assessment, PRP command adaptation, PRP generation and revision, listed below as activities **inside** this window |

No breaks were reported for this window and none are assumed.

### Activities inside the planning window (listed for traceability; not additive)

| # | Activity | Time point(s) | Source | Notes |
|---|---|---|---|---|
| 1 | Requirement gathering | starts 10:20 AM | user-confirmed | Per `INITIAL.md` §11 |
| 2 | Template clone verification | ≈10:28 AM | user-confirmed | "approximately" per `INITIAL.md` |
| 3 | `.venv` creation / package install (environment only) | interpreter check clock read 10:37:16 AM | system-clock | Occurred before implementation authorization; PRP conflict C8 |
| 4 | Repository assessment, PRP command adaptation, PRP v1.0 and v1.1 | within window | — | No separate clock readings |

## Implementation timeline

| # | Activity | Date | Start (IST) | Start source | End (IST) | End source | Notes |
|---|---|---|---|---|---|---|---|
| 5 | M2 authorization and preflight (PRP boxes, `.gitignore`, ignore verification, log update) | 14 Oct 2026 | 11:00:25 AM | system-clock | not provided | — | First clock reading after authorization; user-confirmed planning window ended 10:56 AM |
| 6 | M2 implementation (scaffold, config, schemas, validation, run dirs, three-tab UI, tests) | 14 Oct 2026 | after 11:00:25 AM (exact start not recorded) | system-clock bound | 11:07:16 AM (final gate run completed) | system-clock | Core gate passed ~11:04 (Streamlit server log line 11:04:32); UI confirmation change applied afterwards; final gate 11:07:16 |
| 7 | M2 documentation and commits | 14 Oct 2026 | after 11:07:16 AM | system-clock bound | not provided | — | Commit times recorded in git log, not duplicated here |
| 8 | Pre-M3 verification (venv relocation, keys, model list, model_check) | 14 Oct 2026 | not recorded | — | not recorded | — | Ran after relocation to `D:\agentic-coding-labs`; no code changes |
| 9 | M2 UI refinement cycle (width/typography; dark workflow design from approved reference; two-panel layout; alignment corrections) | 14 Oct 2026 | not recorded (earliest system-clock reading in this phase: 11:37:46 AM) | system-clock bound | 12:24 PM (final gate) | — | Exact start/end per sub-step not recorded; final gate and this commit read from system clock at 12:24:05 PM |

## Milestone status

| Milestone | Status | Start (IST) | End (IST) | Commit |
|---|---|---|---|---|
| M1 Requirements/repository assessment + PRP | Complete; PRP v1.1 approved by user | 10:20 AM (user-confirmed) | 10:56 AM (user-confirmed, planning window end) | none |
| M2 Scaffold, configuration and approved UI | Complete; UI visually approved by user; ruff clean, 51 tests, smoke 200; live `gpt-6-luna` call verified | after 11:00:25 AM | final gate 12:24 PM (system-clock) | see git log |
| M3 Real sequential CrewAI execution | Implemented; live runs L1-L4 executed; awaiting user acceptance review (uncommitted) | not recorded | not recorded | none yet |
| M3 efficiency follow-up | Audit complete; standards added; code and tests done; awaiting review | not recorded | not recorded | see git log |
| M4–M8 | Not authorized | — | — | none |

## Breaks and pauses
None reported by the user.

## Errors and resolutions
| # | Event | Resolution |
|---|---|---|
| 1 | Process deviation: `.venv` created and dependencies installed before PRP approval | Environment-only; no application code written then. Recorded as PRP conflict C8. `.gitignore` now created and verified (M2 preflight) |
| 2 | `PriceChange.date` field shadowed `date` type; schemas import failed (3 collection errors) | Renamed to `observed_on`; suite re-run |
| 3 | Mocked model test used an id CrewAI 1.15.28 cannot construct without LiteLLM | Test split into recognizable-id and unrecognized-id cases; finding relevant to TD-1 |
| 4 | Ruff E501 findings (5, then 8 after UI change) | Reflowed lines; per-file ignore for embedded CSS block |
| 5 | User message cited a palette as "documented in the PRP" but it was not | Palette recorded in PRP v1.2 (flagged to user) |
| 6 | UI refinement 1: narrow, small text; workflow cards of unequal height | Wider container, larger type, equal-height cards (CSS only); verified by Streamlit smoke, not by browser screenshot |
| 7 | Reference-design adoption replaced the approved light palette with a dark theme; fabricated sample data in the reference (charts, percentages, avatar) not reproduced | Truthful idle content only; dark palette confirmed by user's later approval |
| 8 | Header misalignment: "MARKET RESEARCHER" wrapped and pushed card 1 body down; later "RESEARCHER" broke mid-word | Fixed header block; step number moved to a badge on the icon; no forced word breaks |
| 9 | Stacked layout used instead of the agreed left-panel/central-workspace layout | Two-panel layout restored (columns 3:8), sticky left card, stacked below 960 px |
| 10 | Heading offset: hidden marker element produced a 16 px offset; first fix only hid the wrapper with `display:none` (workaround) | Marker removed; keyed container used |
| 11 | Second alignment defect (not caught by heading coordinates alone): left form card top 437.7 vs canvas top 384.1 (53.6 px) from unequal caption heights, selector placement and an 8 px canvas margin | Section headers reserve two caption lines (`.ls-head`); selector moved into the card; canvas top margin removed; card and canvas tops both 376.1 at 1440 and 1366 px |
| 12 | Early headless screenshots captured mid-render (blank/partial) and the dev server did not always reload imported CSS | Switched to DevTools-driven capture that waits for the canvas; server restarted before each measurement |
| 13 | Broad `taskkill /IM python.exe` used once to stop the smoke server; could have ended unrelated Python processes | Replaced by command-line-filtered process stop; user informed |

## Validation results
| Date | Check | Result |
|---|---|---|
| 14 Oct 2026 | Import smoke test in `.venv` (Python 3.11): crewai 1.15.28, crewai_tools tool classes, streamlit, python-pptx, pydantic, reportlab | Passed |
| 14 Oct 2026 | `.gitignore` verification: `.venv/`, `.env`, `.env.*`, `runs/`, `data/`, `.streamlit/secrets.toml` ignored; `.env.example` not ignored; `git diff --cached` empty | Passed |
| 14 Oct 2026 | M2 gate: `ruff check .` | Passed (after 3 rework cycles) |
| 14 Oct 2026 | M2 gate: `pytest` | 49 passed |
| 14 Oct 2026 | Streamlit headless smoke (health 200, `/` 200, no `runs/` created) | Passed |
| 14 Oct 2026 | `python -m launchscout.model_check` | `status=not_configured`, `live_call_made=False`; LLM model identifier / API availability **not verified** (no `.env`, no key) |
| 14 Oct 2026 | Visual browser review | Executed with headless Edge via DevTools at 1440, 1366, 820 and 390 px; user visually approved the final two-panel screen |
| 14 Oct 2026 | Layout measurements (DOM rects, full refresh, cache ignored) | Headings 275.5/275.5; caption 313.5-364.1 both; form card top 376.1 = canvas top 376.1 at 1440 and 1366; no horizontal scroll; four cards equal height at all widths |
| 14 Oct 2026 | Final M2 gate: `ruff check .` | Passed |
| 14 Oct 2026 | Final M2 gate: `pytest` | 51 passed |
| 14 Oct 2026 | `python -m launchscout.model_check` | `status=available`, `model=gpt-6-luna`, `live_call_made=True` (models.retrieve); CrewAI LLM construction ok |
| 14 Oct 2026 | Live invocation of `gpt-6-luna` (chat completions, 1 prompt "Reply with exactly: ok", max 200 completion tokens) | Returned model `gpt-6-luna`, finish_reason `stop`, reply `ok`, usage 11 prompt + 4 completion = 15 tokens, ~4.1 s; same via `crewai.LLM.call` |

## Tracked dependencies (unresolved)
| ID | Dependency | Status |
|---|---|---|
| TD-1 | Exact API model id for requested "GPT-6 Luna" | Resolved: `gpt-6-luna` listed for the account and invoked live; no substitution |
| TD-2 | Local `.env` with LLM key and `SERPER_API_KEY` | Resolved for names/presence; Serper key not yet exercised against the live API |
| TD-3 | Original Assignment 02 text reconciliation | Unresolved; traceability caveat retained |

## Decisions recorded
| ID | Decision | Source |
|---|---|---|
| D1 | Rewrite `CLAUDE.md` for LaunchScout; replace `README.md` at M8 | user |
| D2 | Original Assignment 02 spec authoritative; flag unavailable source text | user |
| D3 | Models-list verification with local key permitted; no silent substitution | user |
| D4 | One centralized Streamlit CSS/theme implementation | user |
| D5 | Alternate test: Cold-pressed juice subscription / Pune / gym-goers aged 20–35 | user |
| D6 | Scheduler docs: Windows Task Scheduler first, cron second | user |
| D7 | JSON snapshot storage | user |
| D9 | PRP v1.1 approved; implementation authorized for **M2 only** | user |

## M2 UI design (frozen)
Dark navy/steel-blue/teal theme; left control card (about 25% width) and central Live Agent Workflow canvas (about 72%); four connected agent nodes with truthful Idle states; Manager placeholder in Hierarchical mode (M5); results and Behind the Scenes beneath the canvas; stacked below 960 px. No redesign unless a functional issue requires it.

## M3 - Real sequential CrewAI execution (implemented; awaiting acceptance review)

Authorized by the user on 14 Oct 2026 (M3 only). Times are system-clock readings (IST).

| Item | Detail |
|---|---|
| Pre-M3 | Old working-directory path corrected in `INITIAL.md` (1) and the PRP (2) by exact-string replacement only; user edits preserved. Recreated `.venv` verified (Python 3.11.9; launchers `pytest.exe`, `streamlit.exe`, `ruff.exe`, `crewai.exe` run). `MODEL_NAME=gpt-6-luna` and key presence confirmed by name; live model call verified earlier |
| Modules | `launchscout/{tools,agents,tasks,crew,events,progress,evidence,grounding,runner}.py`; UI wired in `ui/research_tab.py`; `ui/workflow.py` consumes `AgentState` from `launchscout/progress.py` |
| Agents | Four CrewAI agents (Market Researcher, Review Analyst, Strategy Analyst, Report Writer); strategist has no tools; no delegation; `max_iter` 8, 420 s agent timeout |
| Tools | Guarded wrappers over `SerperDevTool`, `ScrapeWebsiteTool`, `FileWriterTool`: per-agent budgets (6 searches / 5 page reads), run totals (12 / 10), identical-call cache, bounded retry (search 1, reads 0), untrusted-content envelope, cancel awareness, evidence ledger |
| Execution | Daemon worker thread owned by a process-wide `RunManager`; one active run; Streamlit polls via `st.fragment(run_every=1.5)`; run state mirrored to `runs/<id>/` |
| States | complete / partial / failed / cancelled / timeout (run limit 1200 s); acceptance is `not_evaluated` (validation is M4) |
| Guardrails | Prompts; ledger grounding downgrades price/evidence/source claims the tools never returned (tagged, not dropped); report URLs not in ledger flagged; untrusted-content envelope |
| Not implemented (by scope) | Acceptance gate and report validators, PDF/Markdown export, hierarchical Manager, deck, weekly (M4-M8) |

### M3 live verification (real credentials; real Serper and OpenAI calls)

| # | Run | Result | Measured usage |
|---|---|---|---|
| L0 | Accidental: first M3 pytest run started a live run because an existing UI test clicked Run with real keys and no stub; interpreter exit ended it | 5 searches and 5 page-read attempts issued, 2 model calls, no completion; directory deleted | not recorded (run killed; metadata unfinished) |
| L1 | Driven in Edge via DevTools: filled the form, clicked Run Research | complete in 1m46s; 4/4 tasks; UI updated live (Idle, Active, tool labels, Complete); Review Analyst produced 0 findings because the shared page-read budget was exhausted by the Market Researcher | 74,401 tokens (67,377 + 7,024); 12 Serper, 10 page reads |
| L2 | Same input after per-agent budgets | complete in 1m35s; 10 review findings (6 with ledger-verified sources); 5 competitors, 1 verified price, 4 unknown; 0 grounding issues; 0 report URLs outside the ledger | 53,462 tokens (46,019 + 7,443); 11 Serper, 8 page reads |
| L3 | Cancel clicked at ~25 s, before the callback-based stop existed | status cancelled, but agents still ran all 4 tasks to completion (cancel only blocked tools): defect | 39,797 tokens; 6 Serper, 5 page reads |
| L4 | Cancel clicked at ~20 s after the callback stop | cancelled ~18 s after the click (waited for the in-flight step); Market Researcher Cancelled, others Not started | 17,475 tokens; 6 Serper, 5 page reads |

Total measured across L1-L4: 185,135 tokens, 35 Serper searches, 28 page reads (plus unmeasured L0). Content observations (not acceptance): all competitor URLs came from tool results; most prices were left `unknown`, the intended behaviour when pages do not state a price.

### M3 defects and rework (actual)

| # | Defect | Fix |
|---|---|---|
| 1 | Stray bell character (0x07) written into the path in `INITIAL.md`, the PRP and this log by a shell-escaping slip | Located by byte search and repaired; files verified |
| 2 | Test suite could start live billable runs | `tests/conftest.py` autouse stub manager, `LAUNCHSCOUT_NO_LIVE` guard in tools and executor, runs redirected to tmp |
| 3 | Agent role missing on task/agent start events; tool labels did not match CrewAI snake_case tool names | Role fallback (agent object, task name); normalised label lookup |
| 4 | CrewAI console emoji raised `charmap` handler errors on Windows | stdout/stderr reconfigured to UTF-8 with replace |
| 5 | Shared tool budget starved the Review Analyst (L1) | Per-agent budgets with run totals |
| 6 | Cancel only blocked tools; crew kept running (L3) | `step_callback` and task callbacks raise `RunCancelled`; reducer maps post-cancel errors to Cancelled |
| 7 | Budget messages quoted totals when the per-agent cap triggered | Messages reworded |
| 8 | Event list font inherited the global list size and made cards tall | Scoped CSS for `.ls-events li` |
| 9 | Test assumption wrong: identical queries are cache hits, not two Serper calls | Test corrected (1 call, 2 cache hits) |

Rework cycles: 3 (budgets, cancellation, test isolation). Known limits: cancel/timeout are cooperative and wait for the in-flight model or tool call; page-read prices are not machine-checked against page text (M4 validators); a restarted server does not auto-display previous runs (artifacts remain in `runs/`; `snapshot_from_disk` restores them programmatically); Streamlit reload of changed `launchscout` modules resets the in-process manager (development only).

## M3 close-out and LLM efficiency audit (14 Oct 2026)

| Item | Result |
|---|---|
| Part A checks | `ruff check .` clean; `pytest` 112 passed at the M3 commit; no listeners on ports 8599/9333-9335 and no streamlit/python run processes remained (stale headless Edge debug instances from the browser drivers were stopped); the run manager lives only in the (stopped) server process, so no research job was active |
| M3 commit | `440acc7` ("M3: real sequential CrewAI execution with live workflow, guarded tools and run lifecycle"); staged files reviewed: no `.env`, `runs/`, `shots/`, `.venv` or temp files; key values absent from the staged diff (fake `sk-` fixtures in tests only); `INITIAL.md` included with the path correction and the user's existing edits |
| Efficiency audit | `docs/LLM_EFFICIENCY_AUDIT.md`: baseline from existing logs only, no additional API calls |
| Standards | PRP section 9a (E-01..E-10) and checklist rows E-01..E-10 |
| Code changes after the audit | per-call tokens and tool outcomes with latency in events; per-agent efficiency table; CrewAI cache answers counted; hard `max_llm_calls` (40); explicit reuse of identical completed runs; artifacts persisted before a run is reported finished |
| Tests | 129 passed (17 new in `tests/test_efficiency.py`, run twice for stability); ruff clean |
| Audit defects found in M3 code | (a) cache answers from CrewAI's own cache uncounted; (b) no per-call tokens; (c) no hard model-call cap; (d) run reported finished before artifacts were written (found by a flaky test) |
| Not done (by instruction) | No live calls; M4 not started; efficiency changes are a separate commit after `440acc7` (see git log) |

Note on per-agent tokens: they were not recorded in L1-L4, so the first live run after this change
is needed to populate them; this was not run because the audit forbade new API calls.

## Requirements carried into M4+ (unchanged)
- Acceptance gate, report validators and link checks, `-PARTIAL` naming, PDF/Markdown export (M4).
- Hierarchical Manager delegation using the same `AgentState` contract (M5).

## Open items
- `INITIAL.md` still has uncommitted user edits (path corrected only).

## Proposed, not approved
None.
