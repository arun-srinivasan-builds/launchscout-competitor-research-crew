"""Pydantic contracts shared by agents, validators, exports and weekly tracking."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ResearchMode(StrEnum):
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"


class ResearchInput(BaseModel):
    idea: str = Field(min_length=1)
    city: str = Field(min_length=1)
    target_customer: str = Field(min_length=1)
    known_competitors: list[str] = Field(default_factory=list)
    mode: ResearchMode = ResearchMode.SEQUENTIAL


class Price(BaseModel):
    """A competitor price. `verified` requires amount, currency, evidence URL and access date."""

    status: Literal["verified", "unknown"] = "unknown"
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    unit: str | None = None
    pack_size: str | None = None
    evidence_url: str | None = None
    accessed_on: date | None = None

    @model_validator(mode="after")
    def _verified_needs_evidence(self) -> Price:
        if self.status == "verified":
            missing = [
                name
                for name in ("amount", "currency", "unit", "evidence_url", "accessed_on")
                if getattr(self, name) in (None, "")
            ]
            if missing:
                raise ValueError(f"verified price is missing: {', '.join(missing)}")
        return self


class Competitor(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    location_relevance: str = ""
    offer: str = ""
    price: Price = Field(default_factory=Price)
    channels: list[str] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)
    accessed_on: date | None = None
    unknowns: list[str] = Field(default_factory=list)


class CompetitorSet(BaseModel):
    competitors: list[Competitor] = Field(default_factory=list, max_length=5)
    notes: str = ""
    shortfall_reason: str | None = None

    @model_validator(mode="after")
    def _shortfall_explained(self) -> CompetitorSet:
        if len(self.competitors) < 3 and not (self.shortfall_reason or "").strip():
            raise ValueError("fewer than 3 competitors requires a shortfall_reason")
        return self


class ReviewFinding(BaseModel):
    competitor: str
    kind: Literal["praise", "complaint"]
    text: str = Field(min_length=1)
    basis: Literal["quoted", "reported", "inferred"]
    source_url: str | None = None

    @model_validator(mode="after")
    def _attributed_needs_source(self) -> ReviewFinding:
        if self.basis in ("quoted", "reported") and not self.source_url:
            raise ValueError("quoted/reported findings require a source_url")
        return self


class ReviewSet(BaseModel):
    findings: list[ReviewFinding] = Field(default_factory=list)
    per_competitor_summary: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class StrategyOutput(BaseModel):
    comparison_matrix: list[dict[str, str]] = Field(default_factory=list)
    market_gap: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    recommended_offer: str = ""
    positioning_line: str = ""
    recommended_price: str = ""
    rationale: str = ""
    price_label: Literal["recommendation"] = "recommendation"


class Acceptance(BaseModel):
    result: Literal["pass", "fail", "not_evaluated"] = "not_evaluated"
    reasons: list[str] = Field(default_factory=list)


class Usage(BaseModel):
    """Usage is either measured or explicitly unavailable; never estimated."""

    basis: Literal["measured", "unavailable"] = "unavailable"
    total_tokens: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    serper_calls: int | None = None
    scrape_calls: int | None = None
    cache_hits: int | None = None
    llm_calls: int | None = None


class RunMetadata(BaseModel):
    run_id: str
    mode: ResearchMode
    model_name: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    status: Literal[
        "created", "running", "complete", "partial", "failed", "cancelled", "timeout"
    ] = "created"
    error: str | None = None
    acceptance: Acceptance = Field(default_factory=Acceptance)
    usage: Usage = Field(default_factory=Usage)


class SlideSpec(BaseModel):
    title: str = Field(min_length=1)
    bullets: list[str] = Field(default_factory=list)
    notes: str = ""
    source_refs: list[str] = Field(default_factory=list)


class DeckSpec(BaseModel):
    slides: list[SlideSpec]

    @field_validator("slides")
    @classmethod
    def _exactly_six(cls, v: list[SlideSpec]) -> list[SlideSpec]:
        if len(v) != 6:
            raise ValueError(f"deck must have exactly 6 slides, got {len(v)}")
        return v


class WeeklyConfig(BaseModel):
    config_id: str
    input: ResearchInput
    created_at: datetime
    schedule_note: str = ""


class SnapshotCompetitor(BaseModel):
    name: str
    url: str
    price: Price = Field(default_factory=Price)


class Snapshot(BaseModel):
    config_id: str
    run_id: str
    taken_at: datetime
    trigger: Literal["manual", "scheduled"] = "manual"
    acceptance: Literal["pass", "fail"] = "fail"
    competitors: list[SnapshotCompetitor] = Field(default_factory=list)


class PriceChange(BaseModel):
    competitor: str
    status: Literal[
        "changed", "unchanged", "new_competitor", "missing_unverified", "not_comparable"
    ]
    old_price: float | None = None
    new_price: float | None = None
    delta: float | None = None
    pct: float | None = None
    reason: str = ""
    source_url: str | None = None
    observed_on: date | None = None
