import pytest

from launchscout.inputs import InputValidationError, parse_known_competitors, validate_input
from launchscout.schemas import ResearchMode

SAMPLE = (
    "Healthy millet meal boxes delivered for lunch",
    "Coimbatore",
    "office workers aged 25-40",
)
ALT = ("Cold-pressed juice subscription", "Pune", "gym-goers aged 20-35")


def test_required_fields_reported_together():
    with pytest.raises(InputValidationError) as exc:
        validate_input("", "  ", None)
    assert set(exc.value.errors) == {"idea", "city", "target_customer"}


def test_whitespace_and_length():
    with pytest.raises(InputValidationError) as exc:
        validate_input("x" * 301, "C", "ab")
    assert set(exc.value.errors) == {"idea", "city", "target_customer"}
    assert "at most 300" in exc.value.errors["idea"]
    assert "at least 2" in exc.value.errors["city"]


def test_sample_and_alt_inputs():
    for idea, city, customer in (SAMPLE, ALT):
        result = validate_input(idea, city, customer)
        assert (result.idea, result.city, result.target_customer) == (idea, city, customer)
        assert result.mode is ResearchMode.SEQUENTIAL


def test_known_competitors_parsing_and_dedupe():
    names = parse_known_competitors("Acme, acme;  Beta Foods \n\n Gamma,")
    assert names == ["Acme", "Beta Foods", "Gamma"]


def test_known_competitors_optional_and_limits():
    assert validate_input(*SAMPLE, known_competitors="").known_competitors == []
    many = ",".join(f"c{i}" for i in range(11))
    with pytest.raises(InputValidationError) as exc:
        validate_input(*SAMPLE, known_competitors=many)
    assert "known_competitors" in exc.value.errors


def test_control_characters_stripped():
    result = validate_input("Great\x00 idea here", "Pune\x07", "gym-goers")
    assert result.idea == "Great idea here"
    assert result.city == "Pune"


def test_mode_values():
    assert validate_input(*SAMPLE, mode="hierarchical").mode is ResearchMode.HIERARCHICAL
    with pytest.raises(InputValidationError) as exc:
        validate_input(*SAMPLE, mode="parallel")
    assert "mode" in exc.value.errors
