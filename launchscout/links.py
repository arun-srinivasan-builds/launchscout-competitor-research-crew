"""Link status checks. Plain public HTTP, no model, no paid API.

URLs already fetched successfully during research are not requested again (evidence reuse).
Only the remaining URLs get a short, bounded HEAD request. Results are recorded, never hidden.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel

from launchscout.evidence import EvidenceLedger

LinkState = Literal["ok", "blocked", "broken", "not_checked"]
Fetcher = Callable[[str, float], int]

_BLOCKED = {401, 403, 429, 999}
_USER_AGENT = "LaunchScoutLinkCheck/1.0 (+public research tool; HEAD request)"


class LinkStatus(BaseModel):
    url: str
    status: LinkState
    code: int | None = None
    detail: str = ""
    source: Literal["research", "checked", "skipped"] = "checked"


def default_fetcher(url: str, timeout: float) -> int:
    """HTTP status code for `url` (HEAD, falling back to GET when HEAD is refused)."""
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return int(response.status)
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (405, 501):
                continue
            return int(exc.code)
    return 0


def classify(code: int) -> LinkState:
    if 200 <= code < 400:
        return "ok"
    if code in _BLOCKED:
        return "blocked"
    return "broken"


def check_links(
    urls: list[str],
    ledger: EvidenceLedger,
    fetcher: Fetcher | None = None,
    timeout: float = 6.0,
    max_checks: int = 12,
    workers: int = 4,
) -> list[LinkStatus]:
    """Status for each distinct URL. Fetched-during-research pages are `ok` without a request."""
    if fetcher is None and os.environ.get("LAUNCHSCOUT_NO_LIVE"):
        return [
            LinkStatus(url=u, status="not_checked", detail="network checks disabled",
                       source="skipped")
            for u in dict.fromkeys(urls)
        ]
    use = fetcher or default_fetcher
    results: dict[str, LinkStatus] = {}
    pending: list[str] = []
    scraped_ok = {
        e.url: e for e in ledger.entries() if e.kind == "scraped" and e.status == "ok"
    }
    for url in dict.fromkeys(urls):
        entry = next((e for u, e in scraped_ok.items() if ledger_same(u, url)), None)
        if entry is not None:
            results[url] = LinkStatus(
                url=url, status="ok", detail="page was read during research", source="research"
            )
        elif len(pending) < max_checks:
            pending.append(url)
        else:
            results[url] = LinkStatus(
                url=url, status="not_checked", detail="check limit reached", source="skipped"
            )

    def run(url: str) -> LinkStatus:
        try:
            code = use(url, timeout)
        except Exception as exc:  # noqa: BLE001 - timeouts, DNS failures: recorded as broken
            return LinkStatus(url=url, status="broken", detail=type(exc).__name__)
        if code == 0:
            return LinkStatus(url=url, status="broken", detail="no response")
        return LinkStatus(url=url, status=classify(code), code=code, detail=f"HTTP {code}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for status in pool.map(run, pending):
            results[status.url] = status
    return [results[u] for u in dict.fromkeys(urls)]


def ledger_same(a: str, b: str) -> bool:
    from launchscout.evidence import normalize_url

    return normalize_url(a) == normalize_url(b)
