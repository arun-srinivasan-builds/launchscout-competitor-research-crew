"""Single approved hierarchical live run (L6): identical input to L5, agreed hard limits.

Paid. Run only with explicit user approval. Writes a run directory under runs/ like the UI does.
"""

from __future__ import annotations

import json
import sys

from launchscout.config import RunLimits
from launchscout.runner import RunManager
from launchscout.schemas import ResearchInput, ResearchMode

LIMITS = RunLimits(
    max_llm_calls_hierarchical=30,
    max_manager_llm_calls=12,
    max_delegations=6,
    max_searches=12,
    max_scrapes=10,
    run_timeout_s=720,
)


def main() -> int:
    manager = RunManager(limits=LIMITS)
    run = manager.start(
        ResearchInput(
            idea="Cold-pressed juice subscription",
            city="Pune",
            target_customer="gym-goers aged 20-35",
            known_competitors=[],
            mode=ResearchMode.HIERARCHICAL,
        )
    )
    run.thread.join(LIMITS.run_timeout_s + 180)
    snap = manager.snapshot(run.paths.run_id)
    out = {
        "run_id": snap.run_id,
        "status": snap.status,
        "phase": snap.phase,
        "error": snap.error,
        "usage": snap.usage.model_dump(),
        "metrics": snap.agent_metrics(),
        "acceptance": snap.acceptance.model_dump(),
        "report_state": snap.report_state,
        "grounding_issues": snap.grounding_issues,
        "run_dir": snap.run_dir,
    }
    sys.stdout.write(json.dumps(out, indent=2, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
