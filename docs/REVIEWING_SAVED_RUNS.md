# Reviewing saved research runs

Every research run is kept under `runs/<run_id>/` and can be reopened in Streamlit at any time,
including after restarting the server. Reopening a run is **read-only**: it makes no model
calls, no Serper or page-read calls, never starts a research run, and never changes a file.

## What is saved per run

| File | Content |
|---|---|
| `input.json` | The research request (idea, city, customer, known competitors, mode) |
| `metadata.json` | Status, timestamps, model name, measured usage (tokens, searches, page reads, cache hits, model calls), acceptance result |
| `events.jsonl` | Every recorded run event (agents, tasks, tool calls and outcomes, model calls with tokens, errors, grounding notes) |
| `evidence.json` | Evidence ledger: every URL a tool returned, with the page text the model saw |
| `competitors.json`, `reviews.json`, `strategy.json` | Structured agent outputs after grounding |
| `grounding.json` | Guardrail findings and report URLs no tool returned |
| `validation.json` | Rule results R1-R8, gate counts, link status, report state |
| `report.writer.md` | The Report Writer's original text, untouched |
| `report.md` + `report.pdf` | Validated report and PDF (only when acceptance passed) |
| `report-PARTIAL.md` + `report-PARTIAL.pdf` | Partial report and PDF (acceptance failed) |

Runs made before M4 (L1-L4) have no `validation.json` or PDF. They are shown as saved and are
never regenerated or re-validated by the viewer.

## Steps

1. Start the app with the project environment:
   `.venv\Scripts\python -m streamlit run app.py`
   (if another Streamlit is already on port 8501, stop it first with Ctrl+C in its terminal; a
   server started from a different Python will not have this code or these dependencies).
2. Open `http://localhost:8501` and stay on the **Research Workspace** tab.
3. In the left panel, under the input card, open **Saved research runs**.
4. Choose a run. Each entry starts with its state:
   `VALIDATED`, `PARTIAL (failed acceptance)`, `FAILED`, `CANCELLED`, `TIMED OUT`,
   `INTERRUPTED`, `LEGACY (not validated)` or `RUNNING NOW`, followed by time, idea and city.
5. The center panel switches to that run through the Research Intelligence Cockpit: the
   connected agent workflow with the final status of each agent, the executive summary, the six
   areas (R1-R8 and gate counts are under **Evidence & Quality**), the collapsed full report, the download
   buttons and **Engineering Trace** (events, tool calls, evidence ledger, usage per agent).
6. Choose **Current session / latest run** to return to the live view. Starting a new run also
   returns to the live view.
7. Download buttons read the stored files. Partial reports are labelled `(PARTIAL)`, saved
   drafts from before validation are labelled `(UNVALIDATED)`.

## Reading the states

| Label | Meaning |
|---|---|
| VALIDATED | All deterministic checks passed; report and PDF are the validated files |
| PARTIAL (failed acceptance) | Crew finished but the evidence did not meet the gate or a rule failed; items are tagged unverified |
| FAILED | The crew produced nothing usable, or no report |
| CANCELLED / TIMED OUT | Stopped by you or by the run limit; only completed task outputs exist |
| INTERRUPTED | The server stopped while the run was in progress |
| LEGACY (not validated) | Created before report validation existed; acceptance was never evaluated |
| RUNNING NOW | Being executed by this server; selecting saved runs is disabled until it ends |

## Cost guarantee

Listing, selecting, switching, scrolling, downloading and rerunning the page only read local
files. This is enforced by automated tests that fail if any model, Serper, page-read or crew
execution is triggered, and that compare file hashes of every saved run before and after replay.
