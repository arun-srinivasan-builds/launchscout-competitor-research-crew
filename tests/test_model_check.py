import pytest

from launchscout.config import Settings, load_settings
from launchscout.llm import ConfigError, build_llm, crewai_model_string
from launchscout.model_check import check_model

FAKE = "sk-test-FAKE0000000000000000"


class _NotFound(Exception):
    status_code = 404


class _Models:
    def __init__(self, known: set[str]):
        self.known = known

    def retrieve(self, name: str):
        if name not in self.known:
            raise _NotFound("no such model")
        return {"id": name}


class _Client:
    def __init__(self, known: set[str]):
        self.models = _Models(known)


def _settings(model: str | None, key: str | None = FAKE) -> Settings:
    env = {"MODEL_NAME": model or "", "OPENAI_API_KEY": key or ""}
    return load_settings(env=env)


def test_no_model_name_is_not_configured_and_never_defaults():
    result = check_model(_settings(None))
    assert result.status == "not_configured"
    assert result.model_name is None
    assert result.live_call_made is False


def test_no_key_skips_live_call():
    result = check_model(_settings("some-model", key=None))
    assert result.status == "skipped_no_key"
    assert result.live_call_made is False


def test_available_model_mocked():
    # Mocked provider response; "gpt-4o-mini" is only a recognizable id for CrewAI construction.
    result = check_model(
        _settings("gpt-4o-mini"), client_factory=lambda key: _Client({"gpt-4o-mini"})
    )
    assert result.status == "available"
    assert result.live_call_made is True
    assert result.crewai_construction == "ok"


def test_unrecognized_model_id_fails_crewai_construction_without_litellm():
    """Characterizes crewai 1.15.28: unknown ids need the optional LiteLLM fallback.

    Availability can be 'available' while CrewAI construction fails; both are reported
    separately and the model is never replaced.
    """
    result = check_model(_settings("m-1"), client_factory=lambda key: _Client({"m-1"}))
    assert result.status == "available"
    assert result.crewai_construction == "failed"
    assert result.model_name == "m-1"


def test_unavailable_model_is_not_substituted():
    result = check_model(_settings("missing"), client_factory=lambda key: _Client({"other"}))
    assert result.status == "unavailable"
    assert result.model_name == "missing"
    assert result.crewai_construction == "not_attempted"


def test_errors_do_not_leak_key():
    def boom(key: str):
        raise RuntimeError(f"auth failed for {key}")

    result = check_model(_settings("m"), client_factory=boom)
    assert result.status == "error"
    assert FAKE not in result.model_dump_json()


def test_build_llm_refuses_without_model_name():
    with pytest.raises(ConfigError):
        build_llm(_settings(None))


def test_model_string_prefix():
    assert crewai_model_string("abc") == "openai/abc"
    assert crewai_model_string("azure/abc") == "azure/abc"
