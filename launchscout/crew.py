"""Build and run the sequential CrewAI crew. Hierarchical execution is a later milestone (M5)."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import date
from typing import Any

from launchscout.agents import (
    ROLE_MARKET,
    ROLE_REVIEWS,
    ROLE_WRITER,
    build_agents,
    build_manager,
)
from launchscout.config import RunLimits, Settings
from launchscout.demo import require_live
from launchscout.events import install_listeners
from launchscout.llm import build_llm
from launchscout.schemas import ResearchInput, ResearchMode
from launchscout.tasks import build_tasks
from launchscout.tools import ToolContext, build_tools

OnTaskOutput = Callable[[str, str], None]


class RunCancelled(Exception):
    """Raised from crew callbacks to stop the crew promptly once cancel/timeout is requested."""


def _quiet_telemetry() -> None:
    """Opt out of CrewAI telemetry/tracing and make console output encoding-safe."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    for name in ("CREWAI_DISABLE_TELEMETRY", "OTEL_SDK_DISABLED", "CREWAI_DISABLE_TRACKING"):
        os.environ.setdefault(name, "true")


def build_crew(
    research_input: ResearchInput,
    llm: Any,
    ctx: ToolContext,
    limits: RunLimits,
    today: date,
    on_task_output: OnTaskOutput | None = None,
) -> Any:
    """Assemble the four specialists, the four tasks and a CrewAI crew for the requested mode.

    Sequential: `Process.sequential`. Hierarchical: `Process.hierarchical` with a real Manager
    agent (same LLM, no tools, delegation to the same four specialists). Tasks, tools, budgets,
    callbacks and evidence handling are identical in both modes.
    """
    from crewai import Crew, Process

    tools = {
        ROLE_MARKET: build_tools(ctx, scope="market"),
        ROLE_REVIEWS: build_tools(ctx, scope="reviews"),
        ROLE_WRITER: build_tools(ctx, scope="writer"),
    }
    agents = build_agents(llm, tools, limits)

    def check_cancel(*_args: Any) -> None:
        if ctx.cancel_event.is_set():
            raise RunCancelled("run cancelled")

    def callback_factory(task_name: str) -> Callable[[Any], None]:
        def _callback(output: Any) -> None:
            if on_task_output is not None:
                on_task_output(task_name, str(getattr(output, "raw", output) or ""))
            check_cancel()  # do not start the next task after a cancel request

        return _callback

    tasks = build_tasks(agents, research_input, today, callback_factory, limits)
    common: dict[str, Any] = {
        "agents": list(agents.values()),
        "tasks": tasks,
        "verbose": False,
        "memory": False,
        "cache": True,
        "tracing": False,
        "step_callback": check_cancel,  # checked after every agent step, Manager included
    }
    if research_input.mode is ResearchMode.HIERARCHICAL:
        return Crew(
            process=Process.hierarchical,
            manager_agent=build_manager(llm, limits),
            **common,
        )
    return Crew(process=Process.sequential, **common)


def run_crew(
    research_input: ResearchInput,
    settings: Settings,
    ctx: ToolContext,
    limits: RunLimits,
    today: date,
    on_task_output: OnTaskOutput | None = None,
) -> Any:
    """Run the crew to completion in the calling (worker) thread; returns CrewAI's output."""
    require_live("Crew execution")
    _quiet_telemetry()
    install_listeners()
    llm = build_llm(settings)  # the single, configured MODEL_NAME client for every agent
    crew = build_crew(research_input, llm, ctx, limits, today, on_task_output)
    return crew.kickoff()


run_sequential = run_crew  # backwards-compatible name used by earlier milestones and tests
