import json
from datetime import date

from launchscout.evidence import EvidenceEntry, EvidenceLedger, normalize_url
from launchscout.grounding import (
    amount_in_text,
    extract_json,
    ground_competitors,
    parse_competitors,
    parse_reviews,
    parse_strategy,
    report_unsupported_urls,
)

TODAY = date(2026, 10, 14)


def ledger_with(*urls: str, excerpt: str = "Lunch box Rs 99 per box") -> EvidenceLedger:
    ledger = EvidenceLedger()
    for url in urls:
        ledger.add(EvidenceEntry(url=url, kind="search_result", excerpt=excerpt, accessed_on=TODAY))
    return ledger


def competitor(name="Acme", url="https://acme.example/", evidence=None, price=None):
    return {
        "name": name,
        "url": url,
        "offer": "box",
        "price": price or {"status": "unknown"},
        "channels": [],
        "evidence_urls": evidence if evidence is not None else [],
        "accessed_on": "2026-10-14",
    }


def test_normalize_url_ignores_scheme_www_fragment_slash():
    assert normalize_url("HTTPS://www.Acme.example/menu/#top") == "acme.example/menu"


def test_extract_json_handles_fences_and_prose():
    raw = 'Here you go:\n```json\n{"a": 1}\n```'
    assert extract_json(raw) == {"a": 1}
    assert extract_json('noise {"b": 2} tail') == {"b": 2}
    assert extract_json("no json here") is None


def test_unparseable_competitor_output_reports_issue():
    result = parse_competitors("sorry, I could not")
    assert result.value is None and result.issues


def test_verified_price_without_evidence_is_downgraded_at_parse():
    price = {"status": "verified", "amount": 10, "currency": "INR"}
    raw = json.dumps({"competitors": [competitor(price=price)], "shortfall_reason": "one"})
    result = parse_competitors(raw)
    assert result.value.competitors[0].price.status == "unknown"
    assert any("incomplete" in i for i in result.issues)


def test_shortfall_reason_auto_added_and_flagged():
    raw = json.dumps({"competitors": [competitor()]})
    result = parse_competitors(raw)
    assert result.value.shortfall_reason
    assert any("no reason" in i for i in result.issues)


def test_more_than_five_competitors_are_capped():
    raw = json.dumps({"competitors": [competitor(name=f"C{i}") for i in range(7)]})
    result = parse_competitors(raw)
    assert len(result.value.competitors) == 5


def test_ungrounded_competitor_is_tagged_not_dropped():
    price = {
        "status": "verified",
        "amount": 99,
        "currency": "INR",
        "unit": "per box",
        "evidence_url": "https://invented.example/price",
        "accessed_on": "2026-10-14",
    }
    raw = json.dumps(
        {
            "competitors": [
                competitor(
                    url="https://ghost.example/",
                    evidence=["https://invented.example/price"],
                    price=price,
                )
            ],
            "shortfall_reason": "one",
        }
    )
    grounded = ground_competitors(parse_competitors(raw), ledger_with("https://real.example/"))
    comp = grounded.value.competitors[0]
    assert comp.name == "Acme"
    assert comp.price.status == "unknown"
    assert comp.evidence_urls == []
    assert any("unverified" in u for u in comp.unknowns)
    assert grounded.issues


def test_grounded_competitor_keeps_verified_price():
    url = "https://acme.example/menu"
    price = {
        "status": "verified",
        "amount": 99,
        "currency": "INR",
        "unit": "per box",
        "evidence_url": url,
        "accessed_on": "2026-10-14",
    }
    raw = json.dumps(
        {"competitors": [competitor(evidence=[url], price=price)], "shortfall_reason": "one"}
    )
    grounded = ground_competitors(parse_competitors(raw), ledger_with(url, "https://acme.example/"))
    comp = grounded.value.competitors[0]
    assert comp.price.status == "verified" and comp.evidence_urls == [url]


def test_reviews_without_ledger_source_relabelled_inferred():
    raw = json.dumps(
        {
            "findings": [
                {
                    "competitor": "Acme",
                    "kind": "complaint",
                    "text": "slow",
                    "basis": "quoted",
                    "source_url": "https://made-up.example/r",
                },
                {
                    "competitor": "Acme",
                    "kind": "praise",
                    "text": "tasty",
                    "basis": "reported",
                    "source_url": "https://real.example/r",
                },
            ]
        }
    )
    result = parse_reviews(raw, ledger_with("https://real.example/r"))
    first, second = result.value.findings
    assert first.basis == "inferred" and first.source_url is None
    assert second.basis == "reported" and second.source_url
    assert result.issues


def test_strategy_refs_filtered_to_ledger():
    raw = json.dumps(
        {
            "market_gap": "gap",
            "evidence_refs": ["https://real.example/a", "https://fake.example/b"],
            "price_label": "recommendation",
        }
    )
    result = parse_strategy(raw, ledger_with("https://real.example/a"))
    assert result.value.evidence_refs == ["https://real.example/a"]
    assert result.issues


def test_report_unsupported_urls_detected():
    md = "See https://real.example/a, and https://fake.example/z."
    assert report_unsupported_urls(md, ledger_with("https://real.example/a")) == [
        "https://fake.example/z"
    ]


def test_amount_in_text_formats():
    assert amount_in_text(180, "Lunch box Rs 180 per box")
    assert amount_in_text(1200, "Plan costs Rs. 1,200/- monthly")
    assert amount_in_text(149.5, "only 149.50 today")
    assert amount_in_text(99, "price: 99.00")
    assert not amount_in_text(99, "call 1999 or 0991")  # not a standalone number
    assert not amount_in_text(50, "rated 4.50 stars")
    assert not amount_in_text(180, "")


def test_verified_price_without_amount_in_evidence_text_is_downgraded():
    url = "https://acme.example/menu"
    price = {
        "status": "verified",
        "amount": 250,
        "currency": "INR",
        "unit": "per box",
        "evidence_url": url,
        "accessed_on": "2026-10-14",
    }
    raw = json.dumps(
        {"competitors": [competitor(evidence=[url], price=price)], "shortfall_reason": "one"}
    )
    led = ledger_with(url, "https://acme.example/", excerpt="Menu: lunch box Rs 99 per box")
    grounded = ground_competitors(parse_competitors(raw), led)
    comp = grounded.value.competitors[0]
    assert comp.price.status == "unknown"
    assert any("not found in the stored text" in i for i in grounded.issues)
    assert any("amount not found" in u for u in comp.unknowns)


def test_scraped_page_text_beyond_excerpt_supports_the_price():
    url = "https://acme.example/menu"
    price = {
        "status": "verified",
        "amount": 250,
        "currency": "INR",
        "unit": "per box",
        "evidence_url": url,
        "accessed_on": "2026-10-14",
    }
    raw = json.dumps(
        {"competitors": [competitor(evidence=[url], price=price)], "shortfall_reason": "one"}
    )
    led = EvidenceLedger()
    led.add(EvidenceEntry(url="https://acme.example/", kind="search_result", accessed_on=TODAY))
    led.add(
        EvidenceEntry(
            url=url,
            kind="scraped",
            excerpt="intro",
            text="intro ... lunch box Rs 250 per box",
            accessed_on=TODAY,
        )
    )
    grounded = ground_competitors(parse_competitors(raw), led)
    assert grounded.value.competitors[0].price.status == "verified"
