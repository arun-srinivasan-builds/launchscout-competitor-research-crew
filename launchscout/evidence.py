"""Per-run evidence ledger: every URL the tools actually returned or fetched.

The ledger is the single source of truth for "was this URL seen". Anything an agent claims
that is not in the ledger is flagged unverified downstream; nothing is invented here.
"""

from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel


class EvidenceEntry(BaseModel):
    url: str
    kind: Literal["search_result", "scraped"]
    title: str = ""
    excerpt: str = ""
    status: Literal["ok", "error"] = "ok"
    accessed_on: date
    via: str = ""


def normalize_url(url: str) -> str:
    """Lower-case host, drop scheme, `www.`, fragment and trailing slash for comparison."""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    query = f"?{parts.query}" if parts.query else ""
    return f"{host}{path}{query}"


def host_of(url: str) -> str:
    return urlsplit(url.strip()).netloc.lower().removeprefix("www.")


class EvidenceLedger:
    """Thread-safe URL ledger. Later entries for the same URL upgrade, never duplicate."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, EvidenceEntry] = {}

    def add(self, entry: EvidenceEntry) -> None:
        key = normalize_url(entry.url)
        with self._lock:
            existing = self._entries.get(key)
            if existing is None or (existing.kind == "search_result" and entry.kind == "scraped"):
                self._entries[key] = entry

    def contains(self, url: str | None) -> bool:
        return bool(url) and normalize_url(url) in self._entries  # type: ignore[arg-type]

    def host_seen(self, url: str | None) -> bool:
        if not url:
            return False
        host = host_of(url)
        with self._lock:
            return any(key.split("/", 1)[0] == host for key in self._entries)

    def entries(self) -> list[EvidenceEntry]:
        with self._lock:
            return list(self._entries.values())

    def __len__(self) -> int:
        return len(self._entries)

    def save(self, path: Path) -> None:
        payload = [e.model_dump(mode="json") for e in self.entries()]
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
