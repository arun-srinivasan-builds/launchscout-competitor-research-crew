"""Shared test doubles: fake search/scrape tools and controllable crew executors."""

from __future__ import annotations

import json
import threading
import time
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


MANAGER = "Research Manager"


def make_hierarchical_executor(
    gate: threading.Event | None = None,
    undelegated: tuple[str, ...] = (),
    manager_calls_per_task: int = 2,
    delegations_per_task: int = 1,
    report: str | None = None,
    competitors_json: str | None = None,
) -> Callable[[ResearchRun], None]:
    """Offline stand-in for a hierarchical crew: Manager delegates to the real specialists.

    It reproduces the *event shape* CrewAI emits (Manager task, delegation tool call, specialist
    execution, Manager review) with a real tool context. It proves our accounting and guards,
    not that live CrewAI delegation works.
    """
    payloads = {
        TASK_RESEARCH: competitors_json or COMPETITORS_JSON,
        TASK_REVIEWS: REVIEWS_JSON,
        TASK_STRATEGY: STRATEGY_JSON,
        TASK_REPORT: "Report written to report.md",
    }

    def llm(c, role: str) -> None:
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

    def execute(run: ResearchRun) -> None:
        c = run.collector
        c.emit("crew_started", "Crew started (hierarchical)")
        for task, specialist in ROLES.items():
            c.emit("task_started", f"Task started: {task}", MANAGER, task)
            c.emit("agent_started", f"{MANAGER} started", MANAGER)
            if run.ctx.cancel_event.is_set():
                return
            llm(c, MANAGER)
            if task not in undelegated:
                for _ in range(delegations_per_task):
                    arg = f"{specialist}: {task}"
                    c.emit(
                        "tool_started",
                        f"Delegate work to coworker: {arg}",
                        MANAGER,
                        tool="Delegate work to coworker",
                        arg=arg,
                    )
                    c.emit("agent_started", f"{specialist} started", specialist)
                    scope = {TASK_RESEARCH: "market", TASK_REVIEWS: "reviews"}.get(task)
                    if scope:
                        run.ctx.search("millet lunch box Coimbatore", scope)
                        run.ctx.read("https://millet-kitchen.example/menu", scope)
                    if task == TASK_REPORT:
                        run.ctx.write_report(report or PASS_REPORT_MD)
                    if gate is not None:
                        while not gate.wait(0.02):
                            if run.ctx.cancel_event.is_set():
                                break
                    if run.ctx.cancel_event.is_set():
                        return
                    llm(c, specialist)
                    c.emit(
                        "agent_completed",
                        f"{specialist} produced its answer",
                        specialist,
                        status="ok",
                    )
                    c.emit(
                        "tool_finished",
                        "Delegate work to coworker finished",
                        MANAGER,
                        status="ok",
                        tool="Delegate work to coworker",
                        ms=1200,
                    )
            for _ in range(manager_calls_per_task - 1):
                if run.ctx.cancel_event.is_set():
                    return  # step callback stops the Manager after a budget stop
                llm(c, MANAGER)
            run.record_output(task, payloads[task])
            c.emit("agent_completed", f"{MANAGER} produced its answer", MANAGER, status="ok")
            c.emit("task_completed", f"Task complete: {task}", MANAGER, task, status="ok")
        c.emit("crew_completed", "Crew finished all tasks", status="ok")

    return execute


def wait_finished(manager: Any, run_or_id: Any, timeout: float = 90.0) -> Any:
    """Block until a run's worker thread has ended, then return its final snapshot.

    Event-based (thread join), not a polling deadline that silently falls through: if the run
    never ends the test fails here with the run's state instead of asserting on a half-finished
    run further down.
    """
    run = run_or_id
    if isinstance(run_or_id, str):
        run = manager._runs[run_or_id]
    run.thread.join(timeout)
    if run.thread.is_alive():
        raise AssertionError(
            f"run {run.paths.run_id} did not finish within {timeout:.0f}s "
            f"(phase={run.phase}, status={run.status})"
        )
    snap = manager.snapshot(run.paths.run_id)
    assert snap is not None and snap.phase == "finished", (
        f"run {run.paths.run_id} worker ended without reaching 'finished': "
        f"phase={snap.phase if snap else None}"
    )
    return snap


def wait_idle(manager: Any, timeout: float = 90.0) -> None:
    """Block until the manager has no live worker thread (fails loudly otherwise)."""
    deadline = time.monotonic() + timeout
    while True:
        run = manager.active_run()
        if run is None:
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f"run {run.paths.run_id} still active after {timeout:.0f}s")
        run.thread.join(min(remaining, 1.0))


def wait_until(predicate: Any, timeout: float = 15.0, what: str = "condition") -> None:
    """Poll `predicate` and raise with a clear message if it never becomes true."""
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError(f"{what} not reached within {timeout:.0f}s")
        time.sleep(0.02)


def tracking_values(elements) -> dict[str, str]:
    """Counts shown on the Weekly Tracking dashboard, read from its rendered markup.

    KPI cards give Verified changes / Needs review / Saved research runs / Monitoring status;
    the verification panel gives per-status counts (e.g. "Newly observed").
    """
    import re

    text = " ".join(m.value for m in elements)
    values: dict[str, str] = {}
    for key, label in (
        ("verified", "Verified changes"),
        ("review", "Needs review"),
        ("runs", "Saved research runs"),
        ("monitoring", "Monitoring status"),
    ):
        found = re.search(rf'data-kpi="{key}".*?data-value="([^"]*)"', text, re.S)
        if found:
            values[label] = found.group(1)
    for found in re.finditer(r'<progress value="(\d+)" max="\d+" aria-label="([^"]+)">', text):
        values.setdefault(found.group(2), found.group(1))
    return values
