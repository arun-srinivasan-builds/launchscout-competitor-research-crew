"""Shared test doubles: fake search/scrape tools and controllable crew executors."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

from pydantic import SecretStr

from launchscout.config import Settings
from launchscout.runner import ResearchRun
from launchscout.tasks import TASK_REPORT, TASK_RESEARCH, TASK_REVIEWS, TASK_STRATEGY

ROLES = {
    TASK_RESEARCH: "Market Researcher",
    TASK_REVIEWS: "Review Analyst",
    TASK_STRATEGY: "Strategy Analyst",
    TASK_REPORT: "Report Writer",
}

FAKE_SETTINGS = Settings(
    openai_api_key=SecretStr("sk-test-not-a-real-key"),
    serper_api_key=SecretStr("serper-test-not-real"),
    model_name="test-model",
)


def fake_search(query: str, n: int) -> list[dict[str, Any]]:
    return [
        {
            "title": "Millet Kitchen",
            "link": "https://millet-kitchen.example/menu",
            "snippet": "Millet lunch box Rs 180 per box",
        },
        {
            "title": "Green Tiffin",
            "link": "https://greentiffin.example/",
            "snippet": "Healthy tiffin service",
        },
    ]


def fake_scrape(url: str) -> str:
    return f"Page text for {url}. Lunch box price Rs 180 per box."


COMPETITORS_JSON = json.dumps(
    {
        "competitors": [
            {
                "name": "Millet Kitchen",
                "url": "https://millet-kitchen.example/",
                "offer": "Millet lunch box",
                "price": {
                    "status": "verified",
                    "amount": 180,
                    "currency": "INR",
                    "unit": "per box",
                    "evidence_url": "https://millet-kitchen.example/menu",
                    "accessed_on": "2026-10-14",
                },
                "channels": ["website"],
                "evidence_urls": ["https://millet-kitchen.example/menu"],
                "accessed_on": "2026-10-14",
            }
        ],
        "notes": "",
        "shortfall_reason": "Only one competitor had public evidence.",
    }
)
REVIEWS_JSON = json.dumps(
    {
        "findings": [
            {
                "competitor": "Millet Kitchen",
                "kind": "complaint",
                "text": "Late deliveries",
                "basis": "reported",
                "source_url": "https://greentiffin.example/",
            }
        ],
        "per_competitor_summary": [],
        "gaps": [],
    }
)
STRATEGY_JSON = json.dumps(
    {
        "comparison_matrix": [],
        "market_gap": "Few office-focused millet subscriptions.",
        "evidence_refs": ["https://millet-kitchen.example/menu"],
        "recommended_offer": "Weekly millet lunch plan",
        "positioning_line": "Millet lunches, on time.",
        "recommended_price": "Rs 170 per box",
        "rationale": "Priced just under the one verified competitor.",
        "price_label": "recommendation",
    }
)
REPORT_MD = (
    "## 1. Key Competitors\nMillet Kitchen https://millet-kitchen.example/menu\n"
    "## 6. Sources\nhttps://millet-kitchen.example/menu\n"
)


def make_executor(
    gate: threading.Event | None = None,
    fail_after: str | None = None,
    raise_error: bool = False,
    skip_report: bool = False,
    steps: tuple[str, ...] = (TASK_RESEARCH, TASK_REVIEWS, TASK_STRATEGY, TASK_REPORT),
) -> Callable[[ResearchRun], None]:
    """Executor that behaves like the crew: real tool context, events, outputs, report file.

    `gate` holds the run open (cancel/duplicate tests); `fail_after` raises after that task.
    """
    payloads = {
        TASK_RESEARCH: COMPETITORS_JSON,
        TASK_REVIEWS: REVIEWS_JSON,
        TASK_STRATEGY: STRATEGY_JSON,
        TASK_REPORT: "Report written to report.md",
    }

    def execute(run: ResearchRun) -> None:
        c = run.collector
        c.emit("crew_started", "Crew started (sequential)")
        for task in steps:
            role = ROLES[task]
            c.emit("task_started", f"Task started: {task}", role, task)
            if task in (TASK_RESEARCH, TASK_REVIEWS):
                query = "millet lunch box Coimbatore"
                c.emit("tool_started", f"search_the_web: {query}", role, tool="search_the_web",
                       arg=query)
                scope = "market" if task == TASK_RESEARCH else "reviews"
                run.ctx.search(query, scope)
                c.emit("tool_finished", "search_the_web finished", role, status="ok",
                       tool="search_the_web")
                c.emit("tool_started", "read_web_page: https://millet-kitchen.example/menu", role,
                       tool="read_web_page", arg="https://millet-kitchen.example/menu")
                run.ctx.read("https://millet-kitchen.example/menu", scope)
            if task == TASK_REPORT and not skip_report:
                run.ctx.write_report(REPORT_MD)
            if gate is not None:
                while not gate.wait(0.02):
                    if run.ctx.cancel_event.is_set():
                        break
            if run.ctx.cancel_event.is_set():
                return
            c.add_usage({"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120})
            c.emit("llm_completed", "Model call completed", role, status="ok",
                   prompt_tokens=100, completion_tokens=20, total_tokens=120)
            run.record_output(task, payloads[task])
            c.emit("task_completed", f"Task complete: {task}", role, task, status="ok")
            if fail_after == task:
                raise RuntimeError("simulated crew failure")
        if raise_error:
            raise RuntimeError("simulated crew failure")
        c.emit("crew_completed", "Crew finished all tasks", status="ok")

    return execute


def write_report_impl(run_dir: Any, content: str) -> str:
    (run_dir / "report.md").write_text(content, encoding="utf-8")
    return "written"
