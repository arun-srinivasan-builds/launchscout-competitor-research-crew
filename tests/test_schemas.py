from datetime import date

import pytest
from pydantic import ValidationError

from launchscout.schemas import (
    Competitor,
    CompetitorSet,
    DeckSpec,
    Price,
    ReviewFinding,
    SlideSpec,
)


def _verified_price(**overrides):
    data = {
        "status": "verified",
        "amount": 149.0,
        "currency": "INR",
        "unit": "per meal",
        "evidence_url": "https://example.com/menu",
        "accessed_on": date(2026, 10, 14),
    }
    data.update(overrides)
    return Price(**data)


def test_verified_price_requires_evidence():
    assert _verified_price().status == "verified"
    with pytest.raises(ValidationError):
        _verified_price(evidence_url=None)
    with pytest.raises(ValidationError):
        _verified_price(accessed_on=None)


def test_unknown_price_allows_empty_fields():
    assert Price().amount is None


def _competitor(i: int) -> Competitor:
    return Competitor(name=f"C{i}", url=f"https://c{i}.example")


def test_shortfall_reason_required_under_three():
    with pytest.raises(ValidationError):
        CompetitorSet(competitors=[_competitor(1), _competitor(2)])
    ok = CompetitorSet(competitors=[_competitor(1)], shortfall_reason="Only one verified.")
    assert len(ok.competitors) == 1


def test_competitor_set_max_five():
    with pytest.raises(ValidationError):
        CompetitorSet(competitors=[_competitor(i) for i in range(6)])
    assert len(CompetitorSet(competitors=[_competitor(i) for i in range(3)]).competitors) == 3


def test_quoted_findings_need_source():
    with pytest.raises(ValidationError):
        ReviewFinding(competitor="A", kind="complaint", text="Late", basis="quoted")
    ok = ReviewFinding(competitor="A", kind="complaint", text="Late", basis="inferred")
    assert ok.source_url is None


def test_deck_requires_exactly_six_slides():
    slides = [SlideSpec(title=f"S{i}") for i in range(6)]
    assert len(DeckSpec(slides=slides).slides) == 6
    with pytest.raises(ValidationError):
        DeckSpec(slides=slides[:5])
