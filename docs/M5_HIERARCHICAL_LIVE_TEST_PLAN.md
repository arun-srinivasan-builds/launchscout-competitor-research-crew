# M5 controlled live hierarchical test - PROPOSAL ONLY (not executed)

Status: **proposal for approval. No paid call has been made and none will be made without your
explicit authorization.** The historical sequential run L5 is a baseline, not evidence of what
hierarchical execution will achieve.

## 1. Test definition

| Item | Value |
|---|---|
| Input | Cold-pressed juice subscription / Pune / gym-goers aged 20-35 (identical to L5) |
| Mode | Hierarchical, once, no automatic retry of the whole crew |
| Model | `MODEL_NAME` = `gpt-6-luna` through the existing model factory (one client shared by Manager and specialists) |
| Baseline | L5 `20261014-140643-cold-pressed-juice-subscriptio-3824`: sequential, 13 model calls, 69,095 tokens, 12 searches, 10 page reads, 2 competitors with evidence, 0 verified prices, `partial_failed_acceptance` |
| Pre-flight (no cost) | Limits printed from the real code path (as before M4's live test); `LAUNCHSCOUT_NO_LIVE` unset; Run disabled for a second click; Evidence/budget values below confirmed |

## 2. Budgets that will be active

| Budget | Limit | Enforcement |
|---|---|---|
| Total model calls (Manager included) | 45 | collector counts every `llm_completed`; the 46th stops the run (`run_budget_stop`) |
| Manager model calls | 16 | per-role cap; exceeding stops the run |
| Delegations (delegate + ask-question tool calls) | 8 (minimum expected: 4) | counted from Manager tool events; exceeding stops the run |
| Searches | 12 total, 6 per specialist | tool wrapper |
| Page reads | 10 total, 5 per specialist | tool wrapper |
| Specialist `max_iter` / Manager `max_iter` | 8 / 10 | CrewAI |
| Agent timeout | 420 s | CrewAI `max_execution_time` |
| Run timeout | 1200 s | watchdog; cooperative cancel |
| Retries | search 1, page read 0 | tool wrapper |

Remaining tool budgets are stated in every task prompt and appended to every search/read result,
to avoid the budget-refusal loops seen in L1-L5 (9 refusals in L5).

## 3. Expected and maximum usage

Measured baseline (L5): 13 model calls, 69,095 tokens (prompt 61,872), Manager absent.

Expected for hierarchical (**estimate, not measured**): specialists should need about the same
work as L5; the Manager adds at least two calls per task (delegate, then finalize), so roughly
21-27 model calls, with token growth mainly from Manager prompts that carry task text and
prior results. Anything between about 80k and 120k tokens would be unsurprising; a clearly
larger figure indicates Manager overhead to investigate.

Maximum possible under the configured limits: 45 model calls (16 of them Manager), 8
delegations, 12 searches, 10 page reads, 20 minutes. A loose token ceiling derived from observed
per-call prompt sizes (about 6k average, 10k worst seen) is 45 x 10k = about 450k tokens. This
is a ceiling for planning, not a prediction. Monetary cost is not computed (no price data in the
project).

## 4. How genuine delegation is inspected (after the run, from stored data)

1. `events.jsonl`: Manager `tool_started` events whose tool is "Delegate work to coworker" with
   `arg` "<Specialist>: <task summary>"; each followed by that specialist's `agent_started`,
   its own tool calls and `agent_completed`, then the Manager's `tool_finished` (with latency).
2. Cockpit -> Engineering Trace: Manager model calls, delegations, per-agent table
   (calls, tokens, executed/cache/refused/errors, seconds). The Manager row must show zero
   search/read calls.
3. Guard result: no "completed without delegating" finding in Evidence & Quality.
4. Mode comparison panel: sequential L5 next to the hierarchical run.

## 5. Detecting unnecessary Manager calls

| Signal | Threshold for concern |
|---|---|
| Manager calls per task | more than 2 |
| Manager share of total tokens | above one third |
| Delegations beyond one per task | any (re-delegation of the same task) |
| `llm_completed` for the Manager with no following delegation or task completion | any |
| Total calls vs L5 | more than double |

## 6. Evaluation

Compare recorded values only (see the comparison panel): task completion is reported
separately from research quality. Hierarchical is acceptable only if research quality is no
worse than L5 (competitors with evidence at least 2, verified prices at least 0, same R1-R8
standards) and the extra model calls and tokens are reported next to it. Cost and quality are
both stated; there is no pre-agreed "win". A hierarchical run that completes all tasks but
produces weaker evidence is a failed quality result even though the crew finished.

## 7. Conditions that require cancellation or count as failure

- Manager call cap, total call cap, delegation cap or run timeout reached (automatic stop).
- Any task reported complete without its specialist having run (guard; status becomes partial).
- Manager text containing competitors, prices or URLs absent from the evidence ledger
  (R3/R4 failure; reported as unverified, not hidden).
- More than 2 Manager calls on a task with no delegation, or repeated delegation of the same
  task (manual cancel from the UI).
- No event progress for 3 minutes.

## 8. After the test

No second run without a new approval. Results are recorded as run L6 in the build log with
measured calls, tokens, tool usage, validation results, defects and fixes, and the comparison
panel is read from the saved run.


## Result: L6 (executed once, user-authorized; ended about 8:15 PM IST (machine clock))

Run `20261014-201109-cold-pressed-juice-subscriptio-c0fe`, input identical to L5, driver `scripts/run_live_hierarchical.py`.
Limits used (agreed, set explicitly in the driver; app defaults of 45 calls / 16 Manager / 8 delegations / 20 min were NOT used): 30 model calls, 12 Manager calls, 6 delegations, 12 searches, 10 page reads, 12-minute runtime. Preflight: no earlier hierarchical run existed; keys present by name; limits above confirmed in code (collector enforces per-role and delegation caps).

| Measure | L5 sequential | L6 hierarchical |
|---|---|---|
| Status / state | complete / partial_failed_acceptance | complete / partial_failed_acceptance |
| Model calls | 13 | 18 (Manager 9, specialists 9) |
| Total tokens | 69,095 | 75,446 (+9.2%) |
| Prompt / completion | not split here | 60,147 / 15,299 |
| Searches / page reads | 12 / 10 | 12 / 9 |
| Delegations | n/a | 4 (one per task, 101.7 s delegated time) |
| Wall time (start to finish) | 108 s | 178 s (+65%) |
| Evidence entries | 53 | 59 |
| Competitors with evidence | 2 (Earth Organic Juices, iBites) | 2 (same) |
| Verified prices | 0 | 0 |
| Rules failed | R2, R3 | R2, R3, R7 |
| Grounding issues | none recorded | 1 strategy evidence ref not in tool results |

Limits: none reached (18/30 calls, 9/12 Manager calls, 4/6 delegations, 12/12 searches, 9/10 reads, 178 s/720 s). No cancel or budget stop.

Findings: the Manager delegated exactly once per task to the right specialist and every task completed. Hierarchical mode cost more calls, tokens and time and produced no better acceptance result: same two competitors, still no verified prices, and one more failed rule (R7: one source missing from Sources) plus one ungrounded strategy reference. Not measurable from one run: variance between runs, Manager quality on other inputs. Conclusion supported by this single pair only: sequential remains the better default for this input.
