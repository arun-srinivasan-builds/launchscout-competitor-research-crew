# Generate PRP Command (LaunchScout: Streamlit + CrewAI + Python 3.11)

You are the **PRP Generator** for LaunchScout. Produce one implementation blueprint (PRP) for a Streamlit + CrewAI research application. This command **plans only**. It writes the PRP file and nothing else: no application code, no installs, no edits to `INITIAL.md`.

## Input
Read the product definition: $ARGUMENTS (defaults to `INITIAL.md`).

## Authority and scope rules (apply to every step)
1. The Social Eagle AI Academy Assignment 02 specification (sections 2.1-2.8) is the authoritative source for product scope. `INITIAL.md` guides implementation but must not expand or override the assignment's functional requirements. If the assignment text itself is not in the repo, treat `INITIAL.md` sections 3-7 as the transcription and say so in the PRP.
2. Scope = every mandatory requirement + the three requested stretch goals (A: hierarchical manager, B: six-slide pitch deck, C: weekly rerun + price-change highlighting). Nothing else.
3. Any proposed feature that is not traceable to an assignment requirement or stretch goal is **excluded** unless the user explicitly approves it. List excluded ideas under "Out of scope".
4. Security, testing, observability and source verification are supporting practices, not new features.
5. CrewAI runtime agents (Market Researcher, Review Analyst, Strategy Analyst, Report Writer, Manager, Pitch Deck) are application code. They are distinct from Claude Code subagents, which only help build.
6. This command adapts the template workflow to the assignment's stack. It never changes the assignment.

## Context files to read first
- `CLAUDE.md`, `INITIAL.md`
- `docs/*.md` if present
- Reuse only the general practices from the template: type hints, `logging` not `print`, secrets via env vars, ruff + pytest, mocked external services, success + error test cases. Ignore every template instruction that names a different stack.

## Step 1: Requirement analysis
Extract into the PRP:
- Product identity, users, business problem (2.1)
- Inputs and UI behaviour (2.2, 2.5), including the sample test case and a second, different idea/city
- The 4 agents with role / goal / backstory / tools / output contract, and every task's description, expected_output, agent, context
- The six required report sections and the Markdown/PDF export contract (2.6-2.7)
- Acceptance criteria (2.8) as a checklist
- Stretch A / B / C requirements as separate sections
- Guardrails: evidence-first, no fabrication, untrusted web content, bounded retries, cost discipline, secrets

## Step 2: Conflict detection (do before planning)
Compare assignment vs `INITIAL.md` vs `CLAUDE.md` vs template files. Write every conflict in a **Conflicts** table with: item, sources in conflict, proposed resolution, needs-user-decision (Y/N). Known candidates:
- Stack, structure, forbidden-list and validation commands in `CLAUDE.md` and `README.md` that describe the template product rather than LaunchScout (propose: LaunchScout rules win; ask before editing those files)
- Assignment text not present in the repo (only the `INITIAL.md` transcription)
- Requested LLM identifier and availability vs what the user's account and CrewAI actually accept
- Version drift in CrewAI tool imports (`SerperDevTool`, `ScrapeWebsiteTool`, `FileWriterTool`)
Do not silently resolve any conflict that changes scope.

## Step 3: Dependency verification plan
The PRP must list, with an exact verification command for each:
- Python 3.11 interpreter and project-local `.venv` (never touch global Python)
- Pinned versions of `crewai`, `crewai-tools`, `streamlit`, `python-pptx`, `pydantic`, a PDF library, `pytest`, `ruff`
- Import smoke test for each CrewAI tool class used
- LLM model identifier availability via the user's API account and CrewAI compatibility; **no silent substitution**: if unavailable, request approval for an alternative
- `SERPER_API_KEY` and LLM key presence checked by name only; values never printed or logged

## Step 4: Architecture and implementation plan
Include a module map (UI, agents, tasks, crew, tools, events, validation, report, exports, deck, weekly store/diff/CLI, observability), data schemas (Pydantic), the agent/task handoff diagram, event flow for the Behind the Scenes panel, run-directory layout, and the weekly rerun flow. Keep it simple: single-user local app, no accounts, no billing, no server-side database.

### Approved UI architecture: premium three-tab Streamlit app
The PRP must specify exactly three top-level tabs, restrained and accessible styling, and responsive layout:
1. **Research Workspace**
   - Input form: business idea, city/target market, target customer, optional known competitors; Run Research action with validation messages.
   - **Research mode selector (Sequential | Hierarchical) lives here**, inside the form area. It is not a separate tab.
   - Live progress from real CrewAI events (active agent, completed tasks, retries, errors, completion state).
   - Rendered six-section report, Markdown and PDF downloads, and the **Behind the Scenes** expander (agent/task status, tool calls and status, source retrieval, validation/guardrail results, measured usage where available, timestamps; no chain-of-thought).
2. **Pitch Deck**
   - Generates the six-slide editable PPTX from the completed report only; shows slide titles/preview and a download. Disabled with an explanation until a validated report exists.
3. **Weekly Tracking**
   - Save/load research configurations, **Rerun now**, price-change table (changed / unchanged / new competitor / missing-unverified / not comparable) with source and date, and documented scheduler instructions. States plainly whether a scheduler is actually configured.
The PRP must map each tab to modules, tests, and traceability rows, and must not add a fourth tab or extra pages.

## Step 5: Traceability matrix (mandatory)
| Req ID | Assignment/INITIAL section | Implementation (module) | Test (file::name) | Milestone | Status |
Every requirement and stretch item gets a row. Status starts as `Not started`. A row may become `Done` only after its test passes.

## Step 6: Milestones with validation gates
Use M1-M8 from `INITIAL.md` section 11. For each milestone give: scope, files, tasks, validation commands (`ruff check .`, `pytest ...`, import checks, mocked and live runs), exit criteria, doc updates (`docs/BUILD_LOG.md`, `docs/REQUIREMENTS_CHECKLIST.md`, `docs/QUALITY_REPORT.md`), and a commit point after the gate passes. Live-run gates are marked `requires keys` and are never replaced with fake data.

## Step 7: Quality and measurement plan
Define what gets recorded in `docs/QUALITY_REPORT.md`: requirements done vs required, first-pass test result, defects found/resolved, rework cycles, verified source coverage, unsupported claims detected, regression results, measured (not estimated) API usage.
Timing: record real IST clock times for milestone start and finish. Never invent timestamps. Do not compute durations or productivity until the user asks.

## Step 8: Write the PRP
Save to `PRPs/launchscout-prp.md` with sections: Metadata, Scope and authority, Conflicts, Dependencies and verification, Architecture, Agents and tasks, Report contract, Stretch A/B/C, Guardrails, Traceability matrix, Milestones and gates, Quality plan, Open questions, Out of scope, Approval block.

## Output to the user
Report: file path, counts (requirements, tests planned, milestones, conflicts, open questions), the conflicts needing a decision, and end with:
`PRP generated. Awaiting your review and approval before /execute-prp.`
Do not begin implementation.
