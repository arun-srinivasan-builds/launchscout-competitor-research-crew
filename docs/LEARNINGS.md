# LaunchScout learnings

## M5: sequential (L5) vs hierarchical (L6), one controlled comparison

Same input (Cold-pressed juice subscription, Pune, gym-goers aged 20-35), same model, same search/read budgets.

| | L5 sequential | L6 hierarchical |
|---|---|---|
| Model calls | 13 | 18 |
| Total tokens | 69,095 | 75,446 |
| Wall time | 108 s | 178 s |
| Validation checks passed | 6 / 8 | 5 / 8 |
| Outcome | partial acceptance | partial acceptance |

- Four genuine Manager delegations occurred in L6, one per task, each to the correct specialist; every task completed.
- Neither run reached verified-price acceptance (0 verified prices; 2 competitors with evidence each).
- In this single controlled comparison sequential was more efficient (fewer calls, fewer tokens, less time) and passed one more check.

### Limitations
- One run per mode: no variance estimate, so no statistically established superiority of either mode.
- One input and one model; results may differ for other ideas or models.
- Manager overhead and delegation fidelity are measured for this run only.
- Failure to find verified prices is a search/evidence limit shared by both modes, not evidence about orchestration.
