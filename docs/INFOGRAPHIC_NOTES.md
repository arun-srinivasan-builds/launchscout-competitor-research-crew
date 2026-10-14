# Material for the final engineering-and-learning infographic (running notes)

Kept factual; every number below is recorded in `docs/BUILD_LOG.md` or the run artifacts.

## Architecture in one line each
- Streamlit cockpit (3 tabs) -> run manager (one background run) -> CrewAI crew (4 specialists;
  optional Manager) -> guarded tools (Serper, page read, file write) -> evidence ledger ->
  deterministic validation (R1-R8 + gate) -> Markdown/PDF -> saved run replay.
- Same pipeline for sequential and hierarchical; only the coordinator changes.

## Design decisions worth showing
1. Evidence first: URLs, prices and quotes must come from a tool result or stay unknown.
2. Validation is plain Python; the model never grades itself.
3. Partial is a first-class state (files, banner, tags), not a failure to hide.
4. Reachability is not verification (L5: a mutated URL returned HTTP 200 and was still caught).
5. Efficiency is a requirement with tests (zero model calls from viewing, navigating, replay).
6. Hierarchical delegation is constrained: each task offers the Manager one specialist.

## Failures and fixes (selected)
| Failure | Fix |
|---|---|
| Shared tool budget starved the Review Analyst (0 findings, L1) | Per-agent budgets |
| Cancel only blocked tools; crew kept spending (L3, 39.8k tokens) | Callback-based stop (L4 17.5k) |
| Test suite started a live run | Autouse stub manager, live-call guard |
| Writer mutated a cited URL (L5) | R3 caught it; tagged `[unverified link]` |
| R4 flagged an honest "unknown; amounts X" sentence | Acknowledged-unknown window |
| Heading misalignment from a notice inside one column | Notices above both columns |
| Stray control character from shell escaping in three files | Byte-level repair, scripts via files |

## Guardrails
Per-agent and total tool budgets, LLM-call cap (45 hierarchical, 16 Manager), delegation cap,
untrusted-content envelope, ledger grounding, undelegated-task guard, cancellation through
callbacks, read-only replay with hash checks.

## Measured usage so far (live runs)
| Run | Mode | Calls | Tokens | Searches | Page reads | Outcome |
|---|---|---|---|---|---|---|
| L1 | sequential | 13 | 74,401 | 12 | 10 | complete, 0 review findings (budget starvation) |
| L2 | sequential | 10 | 53,462 | 11 | 8 | complete, 10 findings |
| L3 | sequential, cancelled early | 11 | 39,797 | 6 | 5 | cancel did not stop (fixed) |
| L4 | sequential, cancelled | 6 | 17,475 | 6 | 5 | cancelled in ~18 s |
| L5 | sequential (M4 acceptance) | 13 | 69,095 | 12 | 10 | partial: 2 competitors, 0 verified prices |
| L6 | hierarchical | - | - | - | - | Not yet measured |

## Lessons so far
- Make the unhappy path a designed state: partial, cancelled, interrupted, legacy.
- Instrument before optimizing; the audit found counters that were missing, not just waste.
- Test doubles prove your accounting, not the vendor's behaviour; say so out loud.
- Real data finds rule bugs that fixtures do not (R4 false positive).
