# syntax=docker/dockerfile:1
# LaunchScout public demo image: saved research only, paid execution disabled.
FROM python:3.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install -r /tmp/requirements.txt

FROM python:3.11-slim
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/app \
    LAUNCHSCOUT_MODE=demo \
    LAUNCHSCOUT_RUNS_DIR=/app/demo_data/saved_runs
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app app.py ./
COPY --chown=app:app launchscout ./launchscout
COPY --chown=app:app ui ./ui
COPY --chown=app:app static ./static
COPY --chown=app:app .streamlit ./.streamlit
COPY --chown=app:app demo_data ./demo_data
USER app
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).status == 200 else 1)"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
