"""Run-directory management. Each run gets its own directory; existing runs are never reused."""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from launchscout.config import PROJECT_ROOT
from launchscout.schemas import ResearchInput, RunMetadata

DEFAULT_RUNS_DIR = PROJECT_ROOT / "runs"
_MAX_ATTEMPTS = 10


class RunPaths(BaseModel):
    run_id: str
    root: Path

    @property
    def input_json(self) -> Path:
        return self.root / "input.json"

    @property
    def metadata_json(self) -> Path:
        return self.root / "metadata.json"

    @property
    def events_jsonl(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def report_md(self) -> Path:
        return self.root / "report.md"

    @property
    def report_pdf(self) -> Path:
        return self.root / "report.pdf"

    @property
    def deck_pptx(self) -> Path:
        return self.root / "deck.pptx"


def slugify(text: str, max_len: int = 30) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")
    return (slug[:max_len].strip("-")) or "run"


def create_run_dir(
    research_input: ResearchInput,
    base_dir: Path | None = None,
    now: Callable[[], datetime] | None = None,
) -> RunPaths:
    """Create a new, unique run directory and write `input.json` and `metadata.json`.

    Directory creation is exclusive (`exist_ok=False`); a collision draws a new random suffix.
    """
    base = Path(base_dir) if base_dir is not None else DEFAULT_RUNS_DIR
    base.mkdir(parents=True, exist_ok=True)
    clock = now or (lambda: datetime.now().astimezone())
    started = clock()
    stamp = started.strftime("%Y%m%d-%H%M%S")
    slug = slugify(research_input.idea)

    for _ in range(_MAX_ATTEMPTS):
        run_id = f"{stamp}-{slug}-{secrets.token_hex(2)}"
        root = base / run_id
        try:
            root.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            continue
        paths = RunPaths(run_id=run_id, root=root)
        paths.input_json.write_text(research_input.model_dump_json(indent=2), encoding="utf-8")
        metadata = RunMetadata(run_id=run_id, mode=research_input.mode, started_at=started)
        paths.metadata_json.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        return paths
    raise RuntimeError("could not allocate a unique run directory")
