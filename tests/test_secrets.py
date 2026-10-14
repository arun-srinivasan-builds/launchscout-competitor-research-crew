import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), re.compile(r"serper.{0,20}[0-9a-f]{40}")]
SCAN_SUFFIXES = {".py", ".md", ".txt", ".toml", ".ini", ".example", ".json"}
SKIP_DIRS = {".venv", ".git", "runs", "data", "__pycache__", ".pytest_cache", ".ruff_cache"}


def test_env_example_has_no_values():
    for line in (ROOT / ".env.example").read_text("utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            key, _, value = line.partition("=")
            assert key.strip().isupper()
            assert value.strip() == "", f"{key} must be empty in .env.example"


def test_gitignore_protects_required_paths():
    text = (ROOT / ".gitignore").read_text("utf-8")
    for entry in (".venv/", ".env", "runs/", "data/", ".streamlit/secrets.toml"):
        assert entry in text.splitlines(), f"{entry} missing from .gitignore"
    assert "!.env.example" in text.splitlines()


def test_no_secret_patterns_in_source():
    offenders = []
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or path.suffix not in SCAN_SUFFIXES
            or SKIP_DIRS & set(path.relative_to(ROOT).parts)
            or path.name == "test_secrets.py"
            or path.name.startswith("test_")  # tests use obviously fake keys
        ):
            continue
        content = path.read_text("utf-8", errors="ignore")
        if any(p.search(content) for p in SECRET_PATTERNS):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_secret_files_are_git_ignored():
    for name in (".env", ".env.local", "runs/x/report.md", "data/weekly/x.json"):
        result = subprocess.run(
            ["git", "check-ignore", "-q", name], cwd=ROOT, capture_output=True, check=False
        )
        assert result.returncode == 0, f"{name} is not ignored"
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".env.example"], cwd=ROOT, capture_output=True, check=False
    )
    assert result.returncode == 1


def test_no_print_calls_in_package():
    for folder in ("launchscout", "ui"):
        for path in (ROOT / folder).rglob("*.py"):
            assert not re.search(r"^\s*print\(", path.read_text("utf-8"), re.M), path
