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
| M3 efficiency follow-up | Audit complete; standards added; code and tests done | not recorded | not recorded | `d9ea22e` |
| M4 Evidence-validated reports | Complete: validators, gate, PDF/Markdown, saved-run replay, cockpit in production; 197 tests; one controlled live run (L5) returned `partial_failed_acceptance` on actual evidence; awaiting user review | not recorded | not recorded | see git log |
| M5 Hierarchical Manager | Offline implementation complete; 221 tests; no live run; awaiting user review (uncommitted) | not recorded | 7:20 PM (offline tests passed) | none yet |
| M6–M8 | Not authorized | — | — | none |

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

## M4 - Evidence-validated reports (complete; committed at the M4 gate)

Authorized by the user on 14 Oct 2026 (M4 only; E-01..E-10 apply). No paid live research run was
made for M4; verification used the stub crew plus offline re-validation of two stored live runs.

| Area | Implementation |
|---|---|
| Report flow | The Report Writer agent still writes the draft. Finalization (pure Python) preserves it as `report.writer.md`, validates it, tags unsupported items in place, adds a warning or pass header, appends a generated `### Verification status` subsection under Sources (keeps exactly six top-level sections) and writes `report.md`/`report.pdf` or `report-PARTIAL.md`/`report-PARTIAL.pdf` |
| Validators | R1 six sections in order and no extras; R2 at least 3 competitor rows; R3 every URL was returned by a tool; R4 report prices match verified evidence (an amount the text itself labels unknown is allowed); R5 Weeks 1-4; R6 price labelled Recommendation; R7 Sources cover competitor and price evidence; R8 links (broken fails; blocked or unchecked is flagged, not failed) |
| Acceptance gate | Pass only if at least 3 competitors have name, URL and evidence URL and at least 3 have a verified price whose evidence URL is in the ledger, and no rule fails. `RunMetadata.acceptance` and `validation.json` are the single source of truth; the UI only displays them |
| States | `validated_pass`, `partial_failed_acceptance`, `failed_no_report`. Run `status` (crew outcome) is kept separate from acceptance |
| Labels | Verified facts, unknown (not evidenced), inferred (no source) and Recommendation are labelled in the generated section; unsupported links and prices are tagged `[unverified link]` / `[unverified price]` and never dropped |
| Quality evaluation | UI panel: rule table with results, gate counts, unsupported items, link table. Deterministic; no model |
| Exports | Markdown and PDF (reportlab; Segoe UI/Arial/DejaVu TTF so the rupee sign renders, Helvetica ASCII fallback). Clickable links, tables, lists, partial banner. Download buttons read stored files |
| Links | Pages already read during research are not requested again; at most 12 HEAD requests (6 s timeout) for the rest; network checks are disabled under `LAUNCHSCOUT_NO_LIVE` |
| Re-validation | `revalidate_run(paths)` re-runs the rules on stored artifacts; no override exists |
| Efficiency | M4 adds zero model calls and zero searches. The Report Writer's own 2-3 model calls are unchanged (assignment requires the agent) |

### M4 controlled live acceptance run (L5; approved by the user, run exactly once)

| Item | Result |
|---|---|
| Input | Cold-pressed juice subscription / Pune / gym-goers aged 20-35 (alternate test input D5) |
| Pre-run checks | Limits active and printed from the real code path: 12 searches / 10 page reads per run (6 / 5 per agent), `max_llm_calls` 40, `max_iter` 8, 420 s per agent, 1200 s run limit, `Process.sequential`, Strategy Analyst without tools; keys present by name; `LAUNCHSCOUT_NO_LIVE` unset |
| Execution | One click, no retry. 1m48s, 4/4 tasks complete, run `status=complete`, acceptance **fail** (`partial_failed_acceptance`) |
| Model calls | 13 (Market Researcher 5, Review Analyst 5, Strategy Analyst 1, Report Writer 2) |
| Tokens (measured) | 69,095 = 61,872 prompt + 7,223 completion; per agent: Market Researcher 22,847; Review Analyst 32,816; Strategy Analyst 3,111; Report Writer 10,321 |
| Tools | 12 Serper searches, 10 page reads, 2 cache answers, 9 budget refusals (8 Market Researcher, 1 Review Analyst), 1 page-read error |
| Link checker | 8 distinct URLs: 6 already read during research (no request), 2 real HEAD requests (cap 12, 6 s timeout): both HTTP 200 |
| Gate | 2 competitors with name, URL and evidence URL (3 required), 0 verified prices (3 required) |
| Rules | R1 PASS, R2 FAIL (2 rows), R3 FAIL (1 URL not returned by a tool), R4 PASS, R5 PASS, R6 PASS, R7 PASS, R8 PASS |
| Report | Six sections in order; 9,535 characters; `report-PARTIAL.md` and `report-PARTIAL.pdf` (3 pages, 40 links, rupee sign rendered); no `report.md` |
| View/download | Three fresh browser loads and two rounds of download clicks: events.jsonl, metadata.json, validation.json, evidence.json and competitors.json unchanged (size, mtime, line count). Tests with LLM sentinels cover the same actions |

Findings from L5:
1. **Reachability is not verification (demonstrated).** The Report Writer rewrote a cited Reddit URL (underscores to hyphens). Both versions returned HTTP 200, so R8 passed, but only the original was ever returned by a tool; R3 caught the mutated one and the report was tagged `[unverified link]`.
2. **Prices were not published for this niche.** Competitors take orders through Instagram and WhatsApp; the only amount found was a 3-day trial price in a Facebook post, which the agent correctly left as `unknown` for per-unit price. The acceptance gate therefore failed on evidence, as it should. The idea was a reasonable but not sufficient choice for finding published prices.
3. **Budget refusals cost turns.** The Market Researcher asked for more page reads in one parallel step than its budget of 5; 8 calls were refused. Stating the remaining budget in the task prompt is the next efficiency step.
4. **Prompt tokens dominate again** (90 percent). The Review Analyst used 32.8k tokens for 5 calls because scraped pages are re-sent each turn.
5. **Reason list repeats a fact** (gate reason plus R2 for the same shortfall). Harmless; could be merged.
6. **Review quality.** 6 findings, all praise, all with ledger sources (4 reported, 2 quoted); the agent stated that no complaints were retrievable instead of inventing any.

Added before the run (so the live test could distinguish reachability from evidence): the ledger now stores the page text the model was shown (bounded to 6,000 characters); a "verified" price is downgraded to `unknown` unless its amount appears in the stored text of its evidence URL (commas, `.00` and `Rs`/`₹` forms tolerated); link status is labelled "HTTP reachability only" in the UI and in the generated report section. Three tests added (169 total).

Defects in this phase: (a) a generated driver script contained a stray control character from shell escaping and failed to start; no run or cost resulted, replaced with a plain script; (b) first draft of the amount matcher rejected `149.50` for 149.5, fixed with a trailing-zero tolerance; (c) one grounding fixture needed evidence text after the new rule.
Budget used by the phase: exactly one paid run (L5) as approved; no retries.

### Saved runs: persistence, selector and replay (M4 add-on)

Requested after the L5 live test; no paid run was made for it.

| Item | Implementation |
|---|---|
| Persistence | Already complete per run: `input.json`, `metadata.json` (status, usage, acceptance), `events.jsonl`, `evidence.json`, structured outputs, `grounding.json`, `validation.json`, `report.writer.md`, `report.md`/`report.pdf` or `-PARTIAL` pair (see `docs/REVIEWING_SAVED_RUNS.md`) |
| Selector | **Saved research runs** select box in the left panel under the input card (layout unchanged); lists every readable run, newest first, with a state label |
| Replay | Selecting a run restores workflow status per agent, results, quality evaluation, report preview, Behind the Scenes and downloads from disk. Completed-task count is rebuilt from the saved events |
| Restart | State comes from files only; verified by a fresh manager with empty memory and by the real app on the real `runs/` |
| Labels | VALIDATED, PARTIAL (failed acceptance), FAILED, CANCELLED, TIMED OUT, INTERRUPTED, LEGACY (not validated), RUNNING NOW |
| Legacy runs | L1-L4 (pre-validation) are shown as saved drafts with an explicit banner; nothing is regenerated, validated or written; downloads say `(UNVALIDATED)` and no PDF is invented |
| Zero calls | `saved_runs.py` and the replay path import no LLM, search or crew code paths; tests trap `build_llm`, `LLM.call`, Serper, page read and `run_sequential`, count executor calls and compare SHA-256 of every saved file before and after |
| Disk reuse | Identical input now also matches a completed saved run after a restart (efficiency E-02): the saved result is shown and a new run needs an explicit "Run again" |
| While running | The selector is disabled during a run, and the live run is labelled RUNNING NOW instead of INTERRUPTED |

Saved-run decisions: read-only by construction (no write path); run ids are validated against
path traversal; unreadable directories are skipped, not repaired; a run left `running` on disk is
reported as interrupted, never as live.

Defects found while building it: (1) the live run appeared as INTERRUPTED in the list because
its metadata is only finalized at the end (fixed with an active-run override); (2) completed-task
count was 0 for restored runs (rebuilt from events); (3) a test asserted option ids while
Streamlit exposes the formatted labels (test corrected); (4) the headless browser needed the
select box scrolled into view before clicking (driver only).

Verification on the real `runs/` (five runs: L1, L2, L3, L4 and the M4 live run): all load,
labels are PARTIAL (L5), CANCELLED (L3, L4) and LEGACY (L1, L2); a SHA-256 over all files was
identical before and after listing, loading and browser selection; the real browser selection of
a partial, a legacy and a cancelled run showed the right banners, workflow, downloads and
Behind the Scenes. Tests: 181 passed (12 new); ruff clean.

Environment note: a Streamlit on port 8501 was already running from the global Python
(`...\Python311\python.exe -m streamlit run app.py`, started 13:52), not the project `.venv`.
It was not touched; it should be restarted with the `.venv` interpreter to pick up this code.

### Research Intelligence Cockpit: design prototype (approved; integrated below)

Requested after the saved-run work. Production results UI is **not** replaced.

| Item | Detail |
|---|---|
| Files | `ui/cockpit.py` (view), `prototype_cockpit.py` (isolated entry; removed at integration), cockpit CSS block in `ui/theme.py` (loaded only by the cockpit), `docs/COCKPIT.md` |
| Production touch points | `research_tab.render()` gained optional `results_renderer`, `show_behind_the_scenes`, `blocked_note` (defaults reproduce the existing behaviour; a test asserts the production page has no cockpit markup) |
| Data | Saved run L5 (`...140643-cold-pressed-juice-subscriptio-3824`), read from disk; no model, Serper or research call |
| Areas | Executive summary, Competitor Landscape, Customer Voice, Market Opportunity, 30-Day Launch Roadmap, Evidence & Quality, Engineering Trace (collapsed) |
| Honesty | Crew completion and report acceptance are separate chips; acceptance reasons appear once (de-duplicated); strategy and roadmap are labelled Recommendation / proposals; source links show provenance (page read, search result, not in ledger) |
| Responsive | Verified at 1440 px and 390 px: no horizontal page scroll, pills wrap, cards and KPI tiles reflow |
| Tests | `tests/test_cockpit.py` (14): roadmap and table parsing, source labelling and escaping, de-duplicated reasons, six areas switch content, Engineering Trace and full report collapsed, run button disabled, zero-call traps and file-hash comparison across all areas and reruns, legacy run rendering, production view unchanged. Full suite 195 passed, ruff clean |

Defects found while prototyping: (1) pills clipped on the right (BaseWeb flex container did not wrap; CSS now targets the inner container); (2) strategy text in the takeaway was long and mixed with unrelated sentences (first sentence only, clipped at a word, leading article lowercased); (3) a regex replacement turned a helper into a recursive call (caught immediately by the test run); (4) channel tags contained whole sentences with URLs (cleaned and clipped); (5) inline "Week 1: research." was treated as a title (sentence versus label rule).

Open design questions are listed in `docs/COCKPIT.md`. Nothing replaces the current results UI until approved.

#### Cockpit review round 1 (user visual review; fixes applied to the prototype and shared layout CSS)

| # | Review item | Change |
|---|---|---|
| 1 | Heading alignment | Root cause: the saved-run notice sat inside the center column and pushed only the workflow down. Notices now render in a keyed full-width container above the two-column row (structural), so both headings always share one top. Measured: 377.2 px for both at 1440 and 1280 |
| 2 | Workflow | Cards, colours and events unchanged. Layout breakpoints changed so the four connected cards stay in one row at 1024 px and wider (panels stack at 1200 px; cards stack only below 820 px) |
| 3 | Downloads | One bordered actions row directly under the summary card with a status label; two equal-width buttons (measured identical, 43 px high) that stay side by side down to 521 px |
| 4 | Navigation | Same six pills; CSS-only: first four teal-outlined (business intelligence), last two violet with a small gap (trust and engineering); no headings, no extra row |
| 5 | Report | Collapsed by default. Opening it: long URLs and cells wrap, tables scroll inside themselves on tablets and use a fixed wrapping layout on phones; no page-level horizontal scroll. Generated verification section now uses a list instead of a wide table for new runs (stored historical reports are untouched) |
| 6 | Responsive validation | See table below |
| 7 | Read-only | Unchanged; zero-call and file-hash tests extended (197 tests passed, ruff clean) |

Responsive validation at 100 percent zoom (device scale 1, headless Edge; prototype at L5):

| Width | Page h-scroll | Headings aligned | Workflow | Pills | Downloads (w x h) | Report opened: overflow |
|---|---|---|---|---|---|---|
| 1440 | none | 377.2 / 377.2 | 4 across | 1 row | 458x43, 458x43 | none |
| 1280 | none | 377.2 / 377.2 | 4 across | 2 rows | 400x43, 400x43 | none |
| 1024 | none | panels stacked | 4 across | 1 row | 464x43, 464x43 | none |
| 768 | none | panels stacked | 1 column | 2 rows | 336x43, 336x43 | none |
| 390 | none | panels stacked | 1 column | 3 rows | 337x43, 337x43 | none |

Defects found during this round: (1) the two download columns inherited the page-level column
stacking and became full width at 1024; fixed with a scoped override; (2) `overflow-wrap:anywhere`
broke table cells letter by letter on phones; fixed with word wrapping in cells and anywhere only
for links; (3) a wide Evidence column sat behind an inner scroll on phones; fixed with a fixed
table layout and, for new runs, a list in the generated section.

### Cockpit production integration (M4 completion; user-approved design)

| Item | Result |
|---|---|
| Decisions applied | Pills may wrap (two rows at 1280 px, labels unchanged); cockpit replaces Results and Behind the Scenes; workflow, left panel and Saved runs selector unchanged; KPIs read "URLs discovered" and "Pages read"; full six-section report collapsed with Markdown and PDF downloads |
| Reuse | The prototype's tested components were moved, not rebuilt: `research_tab.render()` now calls `cockpit.render(snap)` for every finished run (live or reopened). Shared trace content moved to `ui/trace.py`. Prototype entry `prototype_cockpit.py` removed; old `_render_results`, banner, quality and download code removed |
| States | No run, running, stopping, completed validated, completed partial, failed, cancelled, timed out, no report and legacy all render (idle and running show a collapsed Engineering Trace; finished runs show the cockpit) |
| Accuracy | Header has separate crew and acceptance chips; failed, cancelled, timed-out and partial-crew runs state their reason and error; KPI no longer labels discovered URLs as "sources retrieved" |
| Zero calls | Viewing, navigation, saved-run switching, reruns and downloads: sentinels on `build_llm`, `LLM.call`, Serper, page read and crew execution; saved-run file hashes unchanged (tests and the real `runs/`) |
| Responsive | Verified on the production app at 1440, 1280, 1024, 768 and 390 px (100 percent zoom) for the partial (L5), legacy and cancelled saved runs: no page-level horizontal scroll, no clipped text, equal download buttons, opened report without overflow |
| Tests | 197 passed (suite), ruff clean. Old-UI tests were migrated to the cockpit (markdown/chips, collapsed expanders, Engineering Trace) instead of being deleted |
| Defects and rework | KPI row left "Pages read" orphaned on a second row (grid now 6 columns, 3 on tablet, 2 on phone); reasons block previously could hide a failure reason for runs without validation (now stated); `ruff format` also reformatted older test files (formatting only) |

### M4 engineering decisions
1. Validate and tag the Writer's text instead of regenerating it: deterministic, free, and the original is kept for audit.
2. Generated verification section is `###` under Sources so the six-section contract holds.
3. Prices are judged against structured, ledger-grounded competitor data, not parsed from prose alone.
4. An amount explicitly labelled unknown/unverified within a 70-character window is not a violation (found on real output; see defect 2).
5. Blocked (401/403/429) is not broken: bot protection is common and says nothing about the link; it is reported.
6. `report.md` is never written for a partial result; stale variants are removed.
7. Link checks run once at finalization (bounded), not on every view, so viewing and reruns stay network-free.

### M4 test results
`ruff check .` clean; `pytest` 169 passed (40 new: validation 19, exports/links 6, flow and UI 12, evidence-text grounding 3 -- stable across two consecutive runs); previous suites unchanged except fixtures (competitors now three verified prices; pass and partial report fixtures).

Offline re-validation of the stored live runs (copies; no network, no model): L1 and L2 both `partial_failed_acceptance` because only 1 competitor has a verified price (gate needs 3); all structural rules passed. This is the truthful outcome for those runs, not a validator fault.

### M4 defects and resolutions
| # | Defect | Resolution |
|---|---|---|
| 1 | Per-agent efficiency table (added in `d9ea22e`) mixed ints and the string "unavailable" in one column; pyarrow raised and the results UI would have crashed once events carried tokens | Column always string; regression caught by the new UI test |
| 2 | R4 false positive on real L2 output: the Writer wrote "unknown; search-result amounts Rs 199 and Rs 249 were not reliably attributable" and the rule failed it | Amounts labelled unknown/unverified/not attributable within a short window are acknowledged; unlabelled amounts still fail and are tagged |
| 3 | `TTFFont` import error (reportlab class is `TTFont`) | Import corrected |
| 4 | Run reported finished before artifacts existed (flaky restore test) | Fixed in the efficiency follow-up; M4 relies on it |
| 5 | Tests initially expected tag position wrong ("amount **[unverified price]** per box") and a link-limit boundary off by one | Test expectations corrected, behaviour unchanged |
| 6 | Escaped newline written literally into a test fixture by an editing slip | Fixture corrected |
| 7 | PDF blockquote header collapsed its list into one paragraph | Bulleted lines preserved with line breaks |

Rework cycles: 3 (R4 acknowledgement, PDF font/import and header formatting, fixture and test corrections). Known limits: link checks were not exercised against the real network (disabled in tests); a fresh live run is needed to see real link statuses and a real new PDF; the Writer's free-form table is parsed by header-agnostic row matching (competitor name in a row), so unusual layouts could fail R2/R4 and would then be flagged, not passed.

## M5 - Hierarchical CrewAI Manager (offline implementation complete; awaiting review; uncommitted)

Authorized by the user on 14 Oct 2026: implement genuine hierarchical execution, **no paid call**.
Baseline: M4 `20786ed`, 197 tests. System clock at the end of offline implementation and tests:
7:20 PM IST (start time was not recorded; no elapsed time is claimed).

| Item | Detail |
|---|---|
| Process | `Process.hierarchical` with `manager_agent` (role "Research Manager"), same `MODEL_NAME` client as the specialists, no tools, `allow_delegation`; the four specialists are unchanged and cannot delegate |
| One pipeline | `crew.build_crew` serves both modes; tasks, tools, budgets, callbacks, grounding, R1-R8, gate, exports, persistence, replay are shared. `run_sequential` kept as an alias of `run_crew` |
| Installed-CrewAI facts verified offline | Manager executes each task; per task it receives only the delegation and ask-question tools, restricted to that task's specialist; a Manager with tools is rejected by CrewAI; specialists keep their own tools and budgets |
| Events | `agent_completed` is now a first-class event (CrewAI emits no task lifecycle for delegated work); delegation tool events carry `<specialist>: <task>` and latency; Manager is attributed by role |
| Budgets | Total model calls 45 (Manager included), Manager calls 16, delegations 8, plus existing tool, iteration, agent and run limits; breach -> `run_budget_stop` with the reason |
| Guards | Task finished without its specialist having started -> guard issue, status `partial` (never `complete`); cancellation reaches the Manager through the same step and task callbacks; Manager rules forbid research, embellishment and following untrusted text |
| Budget exposure | Prompts state the per-agent search and page-read allowance; every search/read result ends with a trusted "[Budget remaining ...]" line (outside the untrusted envelope); cache hits spend nothing and show the same line |
| UI | Hierarchical selection shows the Research Manager node with real Delegations and Manager events, dashed delegation connectors to all four specialist cards (vertical connector when stacked), no fake progress; sequential workflow unchanged; cockpit chip names the mode; Engineering Trace gains Manager tiles and the comparison panel |
| Comparison | `launchscout/comparison.py`: sequential vs hierarchical from recorded runs with identical input; missing run -> "Not yet measured"; groups keep task completion apart from research quality |
| Tests | 221 passed, ruff clean; 26 new in `tests/test_hierarchical.py`; no API calls (traps on LLM, Serper, page read, crew) |
| Not claimed | Live delegation behaviour, Manager output fidelity, token overhead: unmeasured until the approved single live test |

Defects and rework (actual): (1) a generic `ruff format` of tests again reformatted unrelated files
(formatting only); (2) tests that asserted the old budget-free tool output needed the trusted
budget line allowed outside the untrusted envelope; (3) first Manager-cap test expected
instant stops, the stand-in executor now honours the cancel flag as the real step callback does;
(4) status text "Not yet implemented" assertion matched the Weekly tab, narrowed to the M5
phrase. Decision: keep each task bound to its specialist (CrewAI then offers the Manager only
that coworker), trading free routing for deterministic, budget-safe delegation.

Live-test proposal: `docs/M5_HIERARCHICAL_LIVE_TEST_PLAN.md` (not executed).

### M5 UI polish: LS logo and Back to top (uncommitted)

| Item | Detail |
|---|---|
| Logo | Supplied artwork stored unmodified as `static/ls_logo.png` (1060x803, SHA-256 `bb95f5caaa07...`), served by Streamlit static serving (`enableStaticServing = true`) at the relative URL `app/static/ls_logo.png`; header shows it at 44 px height (40 px on phones), width from the original aspect ratio (1.32 measured), replacing the single-letter mark; title, subtitle, tagline, colours and typography unchanged |
| Artwork issue (reported, not altered) | The image has an opaque off-white background (RGB 252,252,252) and blurred ghost duplicate letters. On the dark navy header it reads as a light tile with the maroon L and navy S clearly visible, but the tile clashes with the dark styling. A transparent or light-on-dark variant from the artwork owner would fix it; no edit was made |
| Back to top | `ui/assets/back_to_top.js`, injected once from `app.py` with `st.html(..., unsafe_allow_javascript=True)`; 44x44 px rounded square, navy with teal outline, fixed bottom-right (1 rem), visible after 400 px of scrolling, smooth scroll (instant under reduced motion), accessible name "Back to top", visible 3 px teal focus outline; client-side only (no rerun, no network, no state); styles in `ui/theme.py` |
| Defect found and fixed | The first version built the icon from an HTML string; Streamlit's sanitiser (DOMPurify) removed the whole script, leaving an empty element. Icon is now built with DOM calls and a test forbids markup-looking text in the script |
| Verified in a real browser (100 percent zoom) | 1440, 1280, 1024, 768, 390 px: logo loaded at natural 1060x803, aspect preserved, no horizontal scroll; button hidden at the top, visible after scrolling, 44x44 at 16 px from the right and bottom, one instance on all three tabs and after a real rerun, click returns to scrollTop 0, real Tab key reaches it and Enter activates it, focus outline solid 3 px teal; no interactive element lay under it at the 600 px scroll position |
| Tests | 11 focused tests in `tests/test_chrome.py` (artwork hash and dimensions, static URL and config, header markup, CSS sizing, single injection, script contract, sanitiser safety, no model/research calls); full suite and ruff reported with the completion message |
| Not touched | Orchestration, Manager logic, workflow cards, cockpit, saved runs, validation, exports, efficiency controls |

## Requirements carried into M6+ (unchanged)
- Hierarchical Manager delegation using the same `AgentState` contract and the same validators (M5).
- Deck from the validated report only; partial reports refused (M6). Weekly deterministic-first reruns (M7).

## Open items
- `INITIAL.md` still has uncommitted user edits (path corrected only).

## Proposed, not approved
None.

## M5 pre-commit review: transparent logo and intermittent test (uncommitted)
- Logo: `static/ls_logo.png` (supplied, SHA-256 bb95f5ca...) kept unmodified; `static/ls_logo_transparent.png` derived by `scripts/make_ls_logo_transparent.py` (background and ghost letters removed, edges un-blended to the letter colours, cropped; no redraw). Header shows it at 44px / 40px on a plain soft-white tile because the navy S is unreadable directly on the navy header. Reproducibility and halo tests in `tests/test_chrome.py`.
- Intermittent cockpit test: the test helper polled with a 10s deadline and fell through silently, so a slow machine asserted on a run that had not finished. Tests now join the worker thread (`wait_finished`/`wait_idle`/`wait_until` in `tests/helpers.py`) and fail loudly. Product defect found while probing: if finalization raised, the run stayed "running" forever; `runner._finalize_failed` now ends it as failed/partial with a visible reason (tested). The original single failure was not reproduced; the slow-finalization mechanism was reproduced by probe.

## M5 live hierarchical test L6 (about 8:15 PM IST (machine clock), uncommitted)
- Single authorized paid run, identical input to L5, agreed limits (30 calls / 12 Manager / 6 delegations / 12 searches / 10 reads / 12 min) set in `scripts/run_live_hierarchical.py`. Result: complete, partial_failed_acceptance; 18 calls, 75,446 tokens, 12 searches, 9 reads, 4 delegations, 178 s. Details and comparison in `docs/M5_HIERARCHICAL_LIVE_TEST_PLAN.md`. Evidence preserved in `runs/20261014-201109-...-c0fe/` (gitignored). No second run. UI frozen per instruction.

## M6 Editable Pitch Deck generation (offline implementation, uncommitted)
- M5 committed as 266977d before M6 began. L5 vs L6 comparison recorded in docs/LEARNINGS.md.
- New: `launchscout/deck.py` (DeckSource loader, facts prompt, Pitch Deck agent with no tools, parsing, deterministic claim check, deterministic labels, persistence under `runs/<id>/deck/`), `launchscout/exports/pptx_builder.py` (python-pptx, native text boxes, real bullets, notes carry sources, dark navy/teal), `ui/deck_tab.py` (saved-run selector, one explicit Generate click, stored-deck preview, claim-check reasons, PPTX download), `SlideSpec.labels`.
- Decision (differs from PRP 7.1): partial_failed_acceptance reports ARE allowed as deck sources per the M6 instruction, with every slide labelled PARTIAL EVIDENCE; failed_no_report and legacy runs are refused.
- No paid deck-generation call has been made. Tests: full suite passes, Ruff clean. No renderer (PowerPoint/LibreOffice) is installed here, so slide layout was not visually inspected.

## M6 live deck validation D1 (about 8:28 PM IST, uncommitted)
- One authorized paid deck generation from saved L6 (`...-c0fe`, partial_failed_acceptance) via `scripts/run_live_deck.py`; no research rerun, no specialists/Manager. Hard guard: second model call would raise. Measured: 1 model call, 4,486 tokens (2,242 prompt / 2,244 completion). Wall time not captured (the driver crashed printing the result on a cp1252 console after saving; the script is fixed, generation was not repeated).
- Result: six slides with correct titles, sources and labels; claim check raised 1 violation (slide 6, rule `price`): "validate the proposed ₹699 test price". ₹699 is the report's recommended price, but the bullet says "proposed", not "recommended", so the checker blocked the export. No PPTX was produced. Research evidence and spec were not altered.
- Assessment: probable checker false positive (the rule only accepts the word "recommend"); not changed pending review. Visual rendering validation outstanding (no PowerPoint/LibreOffice; and no PPTX exists to render).

## M6 claim-validation correction (uncommitted)
- Price rule: "propos*", "suggest*" and "recommend*" now count as recommendation wording only when (a) the amount equals the saved strategy's recommended price, (b) the wording is within 70 characters of the amount, and (c) the slide is not a competitor slide (2, 3). A verified competitor price described with recommendation wording immediately before it is now a violation (new strictness). Unsupported or competitor-unverified amounts are still blocked.
- Added `deck.revalidate_saved_deck` (offline; keeps original generation record; no model call) and `pptx_builder.check_text_bounds` (heuristic fit estimate, not a render).
- Applied to saved L6 deck spec: 0 violations, PPTX exported (`launchscout-pitch-deck-PARTIAL.pptx`, 6 slides, 0 pictures, speaker notes with sources on every slide, PARTIAL EVIDENCE label on all slides, unknown-price label on slide 2, recommendation label on slide 5). Text-bounds estimate: no issues. Research files byte-identical before/after. No LLM call, no research rerun.
- Deck execution time: unavailable (not captured; not estimated). Visual inspection of rendered slides: PENDING (no PowerPoint/LibreOffice here).
- Tests: 269 pass, Ruff clean.

## M6 final layout correction and closure
- Defect (found by user review of the generated deck): on slide 5 the long recommendation label wrapped outside its highlighted banner (fixed 0.4 in height).
- Fix (`exports/pptx_builder.py` only): banner height now derives from the estimated wrapped line count of all labels (with padding and vertical centring); body starts below the banner; footer box height raised from 0.4 to 0.55 in so a wrapped footer stays on the slide. Colours, fonts, sizes, content and editable structure unchanged.
- `check_text_bounds` now also flags a banner too small for its text, banner/body overlap and banner/footer collision (heuristic estimate, not a render).
- Rebuilt offline from the saved L6 spec: 0 claim violations, 6 slides, 0 pictures, notes with sources on every slide, banners 0.59 in (0.79 in on slide 5), footers end at 7.35 of 7.5 in. No LLM, no research, research files byte-identical.
- Metrics preserved: 1 model call, 4,486 tokens (2,242 / 2,244), execution time unavailable.
- Test fix: `test_real_saved_runs_load_read_only_if_present` failed only because PowerPoint held an Office lock file (`~$...pptx`) in the deck folder; the copy now ignores `~$*`.
- Tests: 272 pass, Ruff clean. Visual rendering of the revised deck was NOT performed here (no renderer); the user's earlier visual review of the generated deck is what found the defect. The revised file needs a fresh look.

## M6 enterprise presentation enhancement: Pitch Deck V2 (uncommitted; baseline aadda00)
- Scope: deterministic PowerPoint layout/design only, built on the saved L6 deck spec. No LLM call, no research rerun, no Manager/specialist call, no paid API; saved research files byte-identical before/after. Preserved original live metrics: 1 model call, 4,486 tokens, execution time unavailable.
- New `launchscout/exports/pptx_components.py` (content-agnostic primitives: fitted text boxes, panels, KPI tiles, chips, badges, connectors; font shrink to an 11 pt floor then ellipsis, full text kept in notes) and rewritten `launchscout/exports/pptx_builder.py` (six slide layouts, chrome, bounds and utilisation checks).
- Slides: (1) KPI dashboard with native gate-progress chart, (2) comparison matrix that adapts to 1-5 competitors, (3) evidence-coverage grid with supported/unverified/access-limit/validation cards, (4) four-stage evidence-to-opportunity flow with connectors and a verified/limitation/assumption/recommendation legend, (5) pricing dashboard ("RECOMMENDATION — NOT A VERIFIED MARKET PRICE", derived calculation labelled), (6) four-week roadmap with milestones and PROPOSED tags. Approved LS logo (transparent derivative on the soft-white tile) on every slide; it is the only picture.
- Content comes from the saved structured research and the validated spec; competitor/price/week data are never hardcoded. "Seven juices per plan" is not stated as a separate figure because the saved text only says "seven-day plan of one juice per day". "Expected deliverables" on slide 6 reuse the report's own planned actions; none were invented.
- Offline validation: 0 claim violations (unchanged checker), 6 slides, native shapes/connectors/chart, notes with sources on every slide, PARTIAL EVIDENCE on every slide, programmatic bounds check clean, estimated content utilisation 0.78-0.92 per slide (grid estimate).
- Dev aid `scripts/preview_pptx.py` redraws the PPTX with real Calibri metrics for inspection. It is NOT PowerPoint rendering: real PowerPoint/LibreOffice rendering is still pending (not installed). The native chart is only roughly drawn by the preview.
- Tests: 284 pass, Ruff clean (12 existing deck tests updated for the new structure; about 15 new).

## M6 V2 badge correction (uncommitted)
- Defect (seen in LibreOffice rendering): the RECOMMENDATION badges on slides 4 and 5 wrapped their last letter. Cause: chip width was estimated with an average glyph width, too narrow for bold capitals and wrapping was enabled.
- Fix in the reusable component: chips/badges size to the whole label (`CAPS_EM` 0.65 plus padding), `word_wrap` disabled, panel-heading reserve and week-tag reserve follow `chip_width`; legend caveat shortened. No research content, layout structure, branding or claim validation changed. Deck rebuilt offline from the saved L6 spec: 0 violations, research files unchanged, no LLM/paid calls.
- Regression tests: label never wraps and fits (heuristic and measured Calibri Bold width with 15% margin), long labels widen the chip. 287 tests pass, Ruff clean. LibreOffice re-render of the corrected file is for the reviewer to confirm.

## Post-M6 workflow visualization enhancement (uncommitted; baseline 10f9e66)
- Not a research milestone: presentation of recorded events only. No orchestration, prompt, evidence, acceptance, deck, report, export or comparison change.
- `launchscout/progress.py`: `AgentState.delegations` (Manager: every recorded delegation, in order, apart from other tool calls) and `delegated`; pure `active_links` (a `flow-i-j` connector is active when specialist i is Complete and j is Active; a `delegate-n` connector when the Manager recorded a delegation to n, the Manager is Active and n is Active) and `replay_states` (state after the first N recorded events; N = all equals the saved-run view).
- `ui/workflow.py` / `ui/theme.py`: `ls-live` modifier on active connectors only, teal travelling dot on arcs, pulse on delegation drops, moving gradient on stacked vertical links; `prefers-reduced-motion` removes motion but keeps the static highlight; "About this view" note with the required wording; Manager card lists all delegations (ordered list).
- `ui/research_tab.py`: replay of any finished or saved run: Restart, Step back, Play/Pause, Step forward; defaults to the final saved state; one recorded event per 0.6 s tick, labelled as accelerated visualization; shows the current recorded event line. Replay only reads saved events: no manager.start, no crew, no LLM, no search.
- Browser check (headless Edge, L6): all four delegations visible; during play connectors lit in recorded order (delegate-1, flow-1-2, delegate-2...), animation names present, emulated reduced motion gave no animation with the highlight kept. Screenshot: shots/replay_live.png.
- Tests: tests/test_workflow_motion.py (13) plus existing suites: 300 passed, Ruff clean. API calls made: none.

## M7 Lightweight competitor change tracking (uncommitted)
- Deterministic, offline comparison of two saved runs of the same scope. New: `launchscout/tracking.py`, `tests/test_tracking.py`; Weekly Tracking tab now hosts the comparison (still exactly three tabs; the scheduler card and the disabled "Rerun now" are unchanged). No LLM, search, scrape, CrewAI or paid API call; no research started.
- Rules: verified price change only for two complete, evidence-backed prices with the same currency, unit and pack size; otherwise "Price verification changed" or "Insufficient evidence". Absent competitor = "Not observed in latest run", never "closed". Evidence differences are labelled coverage notes (inconclusive). Partial/legacy runs are compared with explicit limitations.
- Real saved data: the only same-scope pair is L5 vs L6 (same idea, six hours apart, different modes). It is eligible and shows wording-level differences with the limitation that they reflect research variance. No synthetic change is shown in the app; synthetic fixtures exist only in tests and are labelled.
- Tests: 325 pass, Ruff clean.

### M7 classification correction
- Text differences in research descriptions (offering, subscription, channels) and evidence coverage are now "Needs review" with the label "Research description differs — real-world change not verified"; both original descriptions stay visible. Only a verified, comparable, evidence-backed price difference counts as "Changed". New / not-observed classifications, scope checks, evidence rules and the Markdown export are unchanged.
- Saved L5 vs L6 (offline): eligible; KPIs: newly observed 0, not observed 0, changed 0, needs review 2 (both competitors), unchanged 0. Tests: 329 pass, Ruff clean.

## M8 Final QA, public demo mode and deployment preparation (uncommitted; baseline 39bab14)
- Date: 15 Oct 2026. Wall-clock start/end times were not recorded, so no elapsed time is stated. The only timestamp available is the container's own log clock (2026-10-15 03:12 UTC) during the in-container check.
- Scope: validation, hardening, packaging and documentation only. No product feature, no research run, no model/search/scrape call, no commit, no push, no VPS deployment.
- Reviewed the existing uncommitted M8 draft (demo mode, Dockerfile, compose, demo data). Kept it; changes below are additive.
- **Demo mode now fails closed.** `launchscout/demo.py`: `is_demo()` is true unless `LAUNCHSCOUT_MODE` is exactly `live` (case/space-insensitive). Unset, empty, `demo` or any other value is demo. The process environment wins over a local `.env`. `tests/conftest.py` sets `live` so the existing suite keeps injecting fakes. A local developer must now add `LAUNCHSCOUT_MODE=live` to `.env` to run live research.
- `.dockerignore` hardened: `.streamlit/secrets*`, `secrets`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `id_rsa*`, `id_ed25519*`, `credentials*`, `*.log`, compose files and `deploy/`.
- `.env.example` documents the fail-closed setting.
- New `deploy/docker-compose.traefik.yml`: no published port, external Traefik network, labels for `Host(...)`, entrypoint and certificate resolver. All four values are required variables with no defaults, so Compose refuses to render without them. The real names are not known yet and must be read from the VPS Traefik (docs/DEPLOYMENT.md step 2).
- New `docs/DEPLOYMENT.md`; README replaced (MicroSaaS template text removed).
- Git: `origin` changed locally from the template repository to `arun-srinivasan-builds/launchscout-competitor-research-crew` (verified public and empty beforehand). Nothing pushed.
- Validation: Ruff clean; pytest 341 passed (329 at M7 + 11 demo-mode tests + 1 added for fail-closed `.env` handling). Docker image built; container healthy; checks listed in QUALITY_REPORT.
- Environment note: host port 8501 was already held by another local container (not touched), so the local run used 127.0.0.1:18501 through a temporary override kept outside the repository.

### M8 public-repository cleanup (15 Oct 2026)
- Removed unused template files (`skills/`, `agents/`, `.claude/commands/setup-project.md`) after confirming no code, test or doc link depended on them; replaced local absolute paths in three documents with placeholders. History not rewritten; template attribution preserved.

### M8 demo-data privacy cleanup (15 Oct 2026)
- Scope: `evidence.json` of the two bundled runs (the only artifacts containing contact details; PDFs, PPTX, Markdown reports and other JSON were scanned and contained none). Offline text redaction only; no research, model, search or scrape call.
- Redacted 3 email addresses and 10 phone/WhatsApp numbers (including one truncated number) as `[email removed]` / `[phone removed]` inside excerpt text. URLs, titles, findings, prices, validation, metrics and file format are unchanged (9 JSON lines changed across 2 files).
- Verification: Ruff clean; 341 tests pass; Docker demo image rebuilt and re-checked (health, three tabs, replay, tracking, saved deck); strict scan of all tracked and demo files finds no email addresses or phone numbers outside URLs.
- Earlier public commit `6d82caa` still contains the unredacted text; history was not rewritten.

### M8 public-demo messaging refinement (15 Oct 2026, not yet pushed)
- UI only (`app.py`, `ui/theme.py`, `ui/research_tab.py`, `ui/deck_tab.py`); shown only when `LAUNCHSCOUT_MODE` resolves to demo. Header DEMO MODE indicator, rose announcement banner, blue Research Workspace guidance and compact notices under the disabled Run Research / Generate pitch deck buttons replace the previous `st.info` and captions. No agent, evidence, report, deck, tracking, Docker or deployment change; no API call.
- Checks: Ruff clean; 343 tests pass (2 new: demo notices present, live mode shows none); headless Edge via CDP at 1480, 1280, 820 and 390 px: no horizontal overflow (document scroll width equals client width), notices visible; Docker image rebuilt and healthy.
