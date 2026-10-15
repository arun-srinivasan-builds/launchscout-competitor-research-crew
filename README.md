# LaunchScout — Competitor Research Crew

LaunchScout turns a new business idea into a sourced competitor analysis, a market gap,
positioning, a 30-day launch plan and an optional six-slide pitch deck. A CrewAI research crew
does the work; a Streamlit app (three tabs: **Research Workspace**, **Pitch Deck**, **Weekly
Tracking**) runs it and shows what each agent did.

Every price, competitor and claim carries its source. Unknown stays unknown: nothing is
estimated or invented, and a report that fails validation is labelled **partial** rather than
hidden.

## What it does

- **Research crew** (CrewAI): sequential or hierarchical *Manager* mode, Serper search and
  page scraping, evidence capture and deterministic validation of the final report.
- **Reports**: Markdown and PDF, with an evidence and grounding record per run.
- **Pitch deck**: six editable slides exported to PPTX, with a claim check against the saved
  evidence.
- **Workflow view and replay**: recorded agent events can be replayed offline.
- **Change tracking**: deterministic comparison of two saved runs of the same scope.

## Public demo mode (default)

The app **fails closed**. Unless `LAUNCHSCOUT_MODE=live` is set explicitly, it runs in demo
mode: you can browse the bundled saved runs, replay workflows, compare runs and download the
existing reports and deck, but research, model access, web search, scraping and deck generation
are disabled where they would start (not just hidden in the UI). No API keys are needed.

The Docker image is demo-only and contains no credentials.

## Run it

Requires Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt        # Windows
.venv\Scripts\python -m streamlit run app.py                   # demo mode (default)
```

Live research (local, trusted machine only, **uses paid APIs**):

```bash
copy .env.example .env      # then fill in OPENAI_API_KEY, SERPER_API_KEY, MODEL_NAME
# add LAUNCHSCOUT_MODE=live to .env, then:
.venv\Scripts\python -m launchscout.model_check                 # verify the configured model
.venv\Scripts\python -m streamlit run app.py
```

Configuration comes only from environment variables / `.env` (names in `.env.example`).
Secret values are never displayed or logged.

## Docker (public demo)

```bash
docker compose build
docker compose up -d        # http://127.0.0.1:8501, read-only filesystem, no keys
```

To publish behind an existing Traefik, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Develop

```bash
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m pytest          # external services are mocked; no paid calls
```

## Documentation

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, run artifacts |
| [docs/QUALITY_REPORT.md](docs/QUALITY_REPORT.md) | Measured test and validation results |
| [docs/BUILD_LOG.md](docs/BUILD_LOG.md) | Milestone-by-milestone build record |
| [docs/REQUIREMENTS_CHECKLIST.md](docs/REQUIREMENTS_CHECKLIST.md) | Requirement traceability and test evidence |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Docker, Traefik, DNS, firewall, rollback |

## Limits

- Research output describes what was found in public sources at run time, not the market.
- Scheduled weekly reruns are not implemented; tracking compares saved runs only.
- The bundled demo runs are real saved runs; one is labelled partial evidence.
