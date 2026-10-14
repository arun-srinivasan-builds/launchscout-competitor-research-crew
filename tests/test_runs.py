import json
from datetime import datetime

from launchscout.runs import create_run_dir, slugify
from launchscout.schemas import ResearchInput, RunMetadata


def _input() -> ResearchInput:
    return ResearchInput(
        idea="Healthy millet meal boxes!", city="Coimbatore", target_customer="x y"
    )


def test_unique_dirs_same_second(tmp_path):
    fixed = datetime(2026, 10, 14, 11, 0, 0).astimezone()
    runs = [create_run_dir(_input(), tmp_path, now=lambda: fixed) for _ in range(25)]
    assert len({r.run_id for r in runs}) == 25
    assert all(r.root.is_dir() for r in runs)


def test_files_written_and_valid(tmp_path):
    paths = create_run_dir(_input(), tmp_path)
    saved = ResearchInput.model_validate_json(paths.input_json.read_text("utf-8"))
    assert saved.city == "Coimbatore"
    meta = RunMetadata.model_validate(json.loads(paths.metadata_json.read_text("utf-8")))
    assert meta.run_id == paths.run_id
    assert meta.status == "created"
    assert meta.acceptance.result == "not_evaluated"
    assert meta.usage.basis == "unavailable"


def test_existing_dir_not_overwritten(tmp_path, monkeypatch):
    first = create_run_dir(_input(), tmp_path)
    marker = first.root / "marker.txt"
    marker.write_text("keep", encoding="utf-8")
    # Force the next allocation to collide once with the existing directory name.
    tokens = iter([first.run_id.rsplit("-", 1)[1], "ffff"])
    monkeypatch.setattr("launchscout.runs.secrets.token_hex", lambda n: next(tokens))
    fixed = datetime.strptime(first.run_id[:15], "%Y%m%d-%H%M%S").astimezone()
    second = create_run_dir(_input(), tmp_path, now=lambda: fixed)
    assert second.run_id != first.run_id
    assert marker.read_text("utf-8") == "keep"


def test_slugify():
    assert slugify("Healthy Millet Meal Boxes!!") == "healthy-millet-meal-boxes"
    assert slugify("???") == "run"
