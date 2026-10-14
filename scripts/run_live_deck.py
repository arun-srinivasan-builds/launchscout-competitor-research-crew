"""Single approved live Pitch Deck generation from a saved run (paid, one model call max).

Usage: python -m scripts.run_live_deck <run_id>
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import launchscout.llm as llm_mod
from launchscout import deck
from launchscout.config import load_settings

CALLS: list[float] = []


def _guard(llm: object) -> object:
    cls = type(llm)
    original = cls.call

    def counted(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        if CALLS:
            raise RuntimeError("deck generation is limited to one model call")
        CALLS.append(time.time())
        return original(self, *args, **kwargs)

    cls.call = counted
    return llm


def main(run_id: str) -> int:
    real_build = llm_mod.build_llm
    llm_mod.build_llm = lambda settings: _guard(real_build(settings))
    settings = load_settings()
    runs = Path("runs")
    source = deck.load_deck_source(runs, run_id)
    started = time.time()
    error = None
    result = None
    try:
        result = deck.generate_deck(source, settings)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {str(exc)[:300]}"
    seconds = round(time.time() - started, 1)
    out = {"run_id": run_id, "seconds": seconds, "llm_calls_observed": len(CALLS), "error": error}
    if result is not None:
        path = deck.save_deck(runs, source, result, settings.model_name)
        out.update(
            usage=result.usage,
            violations=[v.model_dump() for v in result.violations],
            pptx=str(path) if path else None,
        )
    sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=True, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
