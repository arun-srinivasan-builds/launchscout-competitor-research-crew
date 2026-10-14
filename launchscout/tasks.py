"""Task definitions with checkable expected outputs and an explicit context chain."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from crewai import Agent, Task

from launchscout.agents import ROLE_MARKET, ROLE_REVIEWS, ROLE_STRATEGY, ROLE_WRITER
from launchscout.schemas import ResearchInput

TASK_RESEARCH = "Competitor research"
TASK_REVIEWS = "Customer review analysis"
TASK_STRATEGY = "Strategy and positioning"
TASK_REPORT = "Report writing"
TASK_ORDER = (TASK_RESEARCH, TASK_REVIEWS, TASK_STRATEGY, TASK_REPORT)

_COMPETITOR_SCHEMA = (
    '{"competitors": [{"name": str, "url": str (official site or best public page), '
    '"location_relevance": str, "offer": str, "price": {"status": "verified"|"unknown", '
    '"amount": number|null, "currency": str|null, "unit": str|null, "pack_size": str|null, '
    '"evidence_url": str|null, "accessed_on": "YYYY-MM-DD"|null}, "channels": [str], '
    '"evidence_urls": [str], "accessed_on": "YYYY-MM-DD", "unknowns": [str]}], '
    '"notes": str, "shortfall_reason": str|null}'
)
_REVIEW_SCHEMA = (
    '{"findings": [{"competitor": str, "kind": "praise"|"complaint", "text": str, '
    '"basis": "quoted"|"reported"|"inferred", "source_url": str|null}], '
    '"per_competitor_summary": [str], "gaps": [str]}'
)
_STRATEGY_SCHEMA = (
    '{"comparison_matrix": [{"competitor": str, "price": str, "channel": str, '
    '"strength": str, "weakness": str}], "market_gap": str, "evidence_refs": [str], '
    '"recommended_offer": str, "positioning_line": str, "recommended_price": str, '
    '"rationale": str, "price_label": "recommendation"}'
)


def _clean(text: str) -> str:
    """User text goes into task descriptions; neutralise braces used by CrewAI templating."""
    return " ".join(text.replace("{", "(").replace("}", ")").split())


def build_tasks(
    agents: dict[str, Agent],
    research_input: ResearchInput,
    today: date,
    callback_factory: Callable[[str], Callable[[Any], None]] | None = None,
) -> list[Task]:
    """Four tasks, in order. Context passes each output to every later task that needs it."""
    idea = _clean(research_input.idea)
    city = _clean(research_input.city)
    customer = _clean(research_input.target_customer)
    seeds = ", ".join(_clean(c) for c in research_input.known_competitors) or "none supplied"
    day = today.isoformat()

    def cb(name: str) -> Callable[[Any], None] | None:
        return callback_factory(name) if callback_factory else None

    research = Task(
        name=TASK_RESEARCH,
        description=(
            f"Today is {day}. Business idea: {idea}. Target market/city: {city}. Target "
            f"customer: {customer}. User-supplied known competitors (starting points only, "
            f"NOT verified facts): {seeds}.\n"
            "Use the web search and page-reading tools to find 3-5 real competitors that "
            "serve this market. For each, record the offer, sales channels, and the price "
            "ONLY if a page you retrieved states it (status 'verified' requires amount, "
            "currency, unit, evidence_url and accessed_on; otherwise status 'unknown'). "
            "Every competitor needs at least one evidence URL that appeared in a tool result. "
            "Use as few tool calls as you can; the number of searches is capped. If fewer "
            "than 3 competitors have public evidence, return what you found and explain why "
            "in shortfall_reason. Do not invent anything."
        ),
        expected_output=(
            "ONLY a JSON object (no prose, no code fence) with this shape: "
            + _COMPETITOR_SCHEMA
        ),
        agent=agents[ROLE_MARKET],
        callback=cb(TASK_RESEARCH),
    )
    reviews = Task(
        name=TASK_REVIEWS,
        description=(
            f"Today is {day}. Using the competitors from the previous task, find verifiable "
            "customer praise and complaints for each (reviews, ratings pages, social posts, "
            "articles). Quote or summarise only text you actually retrieved and give its "
            "source_url; label anything you infer as 'inferred' with no source. List "
            "competitors or topics you could not find feedback for under 'gaps'. The number "
            "of searches and page reads is capped; spend them wisely."
        ),
        expected_output=(
            "ONLY a JSON object (no prose, no code fence) with this shape: " + _REVIEW_SCHEMA
        ),
        agent=agents[ROLE_REVIEWS],
        context=[research],
        callback=cb(TASK_REVIEWS),
    )
    strategy = Task(
        name=TASK_STRATEGY,
        description=(
            f"Today is {day}. Using ONLY the competitor research and customer findings you "
            f"were given for the idea '{idea}' in {city}, build a comparison, identify one "
            "specific, evidence-grounded market gap (never claim 'nobody offers this'), and "
            "recommend an offer, a positioning line and a price. The price is a "
            "recommendation, not a fact. Reference evidence URLs from the research in "
            "evidence_refs. Say plainly where evidence is thin."
        ),
        expected_output=(
            "ONLY a JSON object (no prose, no code fence) with this shape: " + _STRATEGY_SCHEMA
        ),
        agent=agents[ROLE_STRATEGY],
        context=[research, reviews],
        callback=cb(TASK_STRATEGY),
    )
    report = Task(
        name=TASK_REPORT,
        description=(
            f"Today is {day}. Write the final report for the idea '{idea}' in {city} (target "
            f"customer: {customer}) using ONLY the previous outputs. Then call the report "
            "writing tool ONCE with the complete Markdown. The report must contain exactly "
            "these six top-level sections, in order, as '## ' headings: 1. Key Competitors "
            "(table: competitor, price per unit, channel, strength, weakness, evidence link; "
            "prices that are not verified must say 'unknown'), 2. What Customers Complain "
            "About (attributed, with source links and uncertainty wording), 3. Market Gap, "
            "4. Recommended Positioning (one-line offer; the price labelled "
            "**Recommendation**; assumptions), 5. 30-Day Launch Plan (Week 1, Week 2, Week 3, "
            "Week 4 actions), 6. Sources (clickable URLs covering every competitor and every "
            "price). Use only URLs that appear in the previous outputs."
        ),
        expected_output=(
            "A short confirmation that the report was written, naming the file. The report "
            "itself must have been saved with the report writing tool."
        ),
        agent=agents[ROLE_WRITER],
        context=[research, reviews, strategy],
        callback=cb(TASK_REPORT),
    )
    return [research, reviews, strategy, report]
