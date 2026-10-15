"""Rebuild a saved run's PPTX offline from its stored deck spec (no model, search or network).

Only the PPTX is rewritten: the stored spec, the generation record (deck_meta.json) and every
research file are left untouched. Usage:
    python scripts/rebuild_saved_deck.py <runs_dir> <run_id> [<run_id> ...]
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from launchscout import deck  # noqa: E402
from launchscout.exports.pptx_builder import build_pptx, check_text_bounds  # noqa: E402


def rebuild(runs_dir: Path, run_id: str) -> Path:
    source = deck.load_deck_source(runs_dir, run_id)
    stored = deck.load_saved_deck(runs_dir, run_id)
    if stored is None:
        raise SystemExit(f"{run_id}: no stored deck specification")
    spec, meta, _ = stored
    when = meta.get("generated_at")
    generated_on = datetime.fromisoformat(when).date() if when else date.today()
    target = deck.deck_dir(runs_dir, run_id)
    path = target / deck.pptx_name(source.partial)
    for old in target.glob("*.pptx"):
        if old != path:
            old.unlink()
    build_pptx(spec, source, path, generated_on)
    problems = check_text_bounds(path)
    record = {"run": run_id, "pptx": path.name, "layout_problems": problems}
    sys.stdout.write(json.dumps(record) + chr(10))
    return path


if __name__ == "__main__":
    runs = Path(sys.argv[1])
    for rid in sys.argv[2:]:
        rebuild(runs, rid)
