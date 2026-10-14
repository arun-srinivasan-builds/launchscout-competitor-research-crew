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


MENU_URLS = (
    "https://millet-kitchen.example/menu",
    "https://greentiffin.example/",
    "https://hearty-bowls.example/pricing",
)


def fake_search(query: str, n: int) -> list[dict[str, Any]]:
    names = ("Millet Kitchen", "Green Tiffin", "Hearty Bowls")
    prices = (180, 150, 200)
    return [
        {"title": name, "link": url, "snippet": f"{name} lunch box Rs {price} per box"}
        for name, url, price in zip(names, MENU_URLS, prices, strict=True)
    ]


def fake_scrape(url: str) -> str:
    return f"Page text for {url}. Lunch box price Rs 180 per box."


def _competitor(name: str, site: str, evidence: str, amount: float) -> dict[str, Any]:
    return {
        "name": name,
        "url": site,
        "offer": "Lunch box",
        "price": {
            "status": "verified",
            "amount": amount,
            "currency": "INR",
            "unit": "per box",
            "evidence_url": evidence,
            "accessed_on": "2026-10-14",
        },
        "channels": ["website"],
        "evidence_urls": [evidence],
        "accessed_on": "2026-10-14",
    }


COMPETITORS_JSON = json.dumps(
    {
        "competitors": [
            _competitor("Millet Kitchen", "https://millet-kitchen.example/", MENU_URLS[0], 180),
            _competitor("Green Tiffin", "https://greentiffin.example/", MENU_URLS[1], 150),
            _competitor("Hearty Bowls", "https://hearty-bowls.example/", MENU_URLS[2], 200),
        ],
        "notes": "",
        "shortfall_reason": None,
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
                "source_url": MENU_URLS[1],
            },
            {
                "competitor": "Green Tiffin",
                "kind": "praise",
                "text": "Fresh food",
                "basis": "inferred",
                "source_url": None,
            },
        ],
        "per_competitor_summary": [],
        "gaps": [],
    }
)
STRATEGY_JSON = json.dumps(
    {
        "comparison_matrix": [],
        "market_gap": "Few office-focused millet subscriptions.",
        "evidence_refs": [MENU_URLS[0]],
        "recommended_offer": "Weekly millet lunch plan",
        "positioning_line": "Millet lunches, on time.",
        "recommended_price": "Rs 170 per box",
        "rationale": "Priced just under the verified competitors.",
        "price_label": "recommendation",
    }
)
PASS_REPORT_MD = f"""## 1. Key Competitors
| Competitor | Price per unit | Channel | Strength | Weakness | Evidence |
|---|---|---|---|---|---|
| Millet Kitchen | ₹180 per box | website | menu | slow | {MENU_URLS[0]} |
| Green Tiffin | ₹150 per box | website | cheap | small | {MENU_URLS[1]} |
| Hearty Bowls | ₹200 per box | website | large | pricey | {MENU_URLS[2]} |

## 2. What Customers Complain About
Late deliveries were reported ({MENU_URLS[1]}).

## 3. Market Gap
Few office-focused millet subscriptions.

## 4. Recommended Positioning
Millet lunches, on time. **Recommendation:** Rs 170 per box.

## 5. 30-Day Launch Plan
Week 1: research. Week 2: menu. Week 3: pilot. Week 4: launch.

## 6. Sources
- {MENU_URLS[0]}
- {MENU_URLS[1]}
- {MENU_URLS[2]}
"""
PARTIAL_REPORT_MD = PASS_REPORT_MD.replace("₹150 per box", "₹99 per box").replace(
    "## 6. Sources", "## 6. Sources\n- https://made-up.example/source"
)
REPORT_MD = PASS_REPORT_MD


def make_executor(
    gate: threading.Event | None = None,
    fail_after: str | None = None,
    raise_error: bool = False,
    skip_report: bool = False,
    steps: tuple[str, ...] = (TASK_RESEARCH, TASK_REVIEWS, TASK_STRATEGY, TASK_REPORT),
    report: str | None = None,
    competitors_json: str | None = None,
) -> Callable[[ResearchRun], None]:
    """Executor that behaves like the crew: real tool context, events, outputs, report file.

    `gate` holds the run open (cancel/duplicate tests); `fail_after` raises after that task.
    """
    payloads = {
        TASK_RESEARCH: competitors_json or COMPETITORS_JSON,
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
                c.emit(
                    "tool_started",
                    f"search_the_web: {query}",
                    role,
                    tool="search_the_web",
                    arg=query,
                )
                scope = "market" if task == TASK_RESEARCH else "reviews"
                run.ctx.search(query, scope)
                c.emit(
                    "tool_finished",
                    "search_the_web finished",
                    role,
                    status="ok",
                    tool="search_the_web",
                )
                c.emit(
                    "tool_started",
                    "read_web_page: https://millet-kitchen.example/menu",
                    role,
                    tool="read_web_page",
                    arg="https://millet-kitchen.example/menu",
                )
                run.ctx.read("https://millet-kitchen.example/menu", scope)
            if task == TASK_REPORT and not skip_report:
                run.ctx.write_report(report or PASS_REPORT_MD)
            if gate is not None:
                while not gate.wait(0.02):
                    if run.ctx.cancel_event.is_set():
                        break
            if run.ctx.cancel_event.is_set():
                return
            c.add_usage({"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120})
            c.emit(
                "llm_completed",
                "Model call completed",
                role,
                status="ok",
                prompt_tokens=100,
                completion_tokens=20,
                total_tokens=120,
            )
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
