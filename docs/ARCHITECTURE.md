# LaunchScout architecture (through M5)

## Layers

| Layer | Modules | Responsibility |
|---|---|---|
| UI | `app.py`, `ui/research_tab.py`, `ui/cockpit.py`, `ui/trace.py`, `ui/workflow.py`, `ui/theme.py`, `ui/deck_tab.py`, `ui/weekly_tab.py` | Three tabs; input panel, live workflow, cockpit; no business logic |
| Orchestration | `launchscout/runner.py`, `crew.py`, `agents.py`, `tasks.py` | One run manager, one crew builder for both modes, background thread, limits |
| Tools and evidence | `tools.py`, `evidence.py`, `grounding.py` | Guarded Serper / page read / file write, evidence ledger, grounding |
| Events and progress | `events.py`, `progress.py` | CrewAI event bridge, typed run events, per-agent state reducer, metrics |
| Validation and exports | `validation.py`, `report.py`, `reporting.py`, `links.py`, `exports/` | Deterministic R1-R8, gate, tagging, Markdown and PDF |
| Persistence and replay | `runs.py`, `saved_runs.py` | `runs/<id>/` artifacts, read-only replay, labels |
| Analysis | `comparison.py` | Sequential vs hierarchical comparison from recorded runs |

Deterministic modules (validation, report, links, reporting, exports, saved_runs, comparison,
grounding, evidence, progress) import no LLM code; tests enforce it.

## One pipeline, two processes

```
ResearchInput(mode) -> RunManager.start -> worker thread -> run_crew
   -> build_crew:  specialists (Market, Review, Strategy, Writer) + 4 tasks + guarded tools
        sequential   : Process.sequential
        hierarchical : Process.hierarchical + manager_agent (same LLM, no tools, delegates)
   -> CrewAI event bus -> EventCollector -> events.jsonl + reducer -> AgentState -> UI
   -> finalize: ground outputs -> validate/gate -> report + PDF -> metadata/validation.json
```

Everything after `run_crew` (grounding, ledger, validation, exports, persistence, replay) is
shared; the mode only changes who coordinates the specialists.

## Hierarchical delegation (M5)

```
Research Manager (LLM = MODEL_NAME, tools = [], allow_delegation)
  for each of the 4 tasks (CrewAI executes the task with the Manager):
     Delegate work to coworker  ->  the task's specialist (only coworker offered for that task)
         specialist runs with its own guarded tools and budgets
     Manager reviews the result and returns it verbatim (instructions), task callback records it
```

Verified offline against the installed CrewAI 1.15.28: the Manager has no tools of its own,
each task offers it exactly one coworker, and specialists cannot delegate. Not verified without
a paid run: that the live model actually delegates and returns specialist output unchanged. The
run guards for that (below).

## Guards and budgets

| Concern | Control |
|---|---|
| Manager fabricating results | Task outputs pass through the same grounding and R1-R8; Manager text is not evidence |
| Manager skipping delegation | Task completed without the specialist's `agent_started` -> guard issue, status `partial` |
| Endless delegation | `max_delegations`; exceeding stops the run |
| Excess Manager calls | `max_manager_llm_calls` and the total `max_llm_calls_hierarchical` |
| Budget refusal loops | Remaining budget in prompts and in every tool result |
| Prompt injection | Untrusted-content envelope on tool results; Manager rules treat specialist and web text as data |
| Cancellation | Cancel flag blocks tools; `step_callback` and task callbacks raise to stop the crew, Manager included |

## Observability

Per agent role (including `Research Manager`): model calls, tokens, tool calls and outcomes,
cache hits, refusals, errors, delegations and delegation latency, task seconds. Shown in the
cockpit's Engineering Trace and used by the comparison panel.

## Pitch Deck (M6)
saved run files -> `deck.load_deck_source` -> `deck_prompt` (facts only) -> Pitch Deck agent (no tools, one call) -> `parse_deck_spec` -> `apply_labels` (code) -> `validate_deck_claims` -> `exports/pptx_builder.build_pptx` -> `runs/<id>/deck/`. Violations keep `deck_spec.json`/`deck_meta.json` but block the PPTX.
