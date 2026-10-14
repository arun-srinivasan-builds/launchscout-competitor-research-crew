from launchscout.config import load_settings
from launchscout.logging_utils import RedactingFilter, redact

FAKE_KEY = "sk-test-FAKE0000000000000000"


def test_missing_keys_reported_by_name():
    settings = load_settings(env={})
    assert settings.missing() == ["OPENAI_API_KEY", "SERPER_API_KEY", "MODEL_NAME"]


def test_placeholder_and_blank_values_treated_as_missing():
    env = {"OPENAI_API_KEY": "your-key-here", "SERPER_API_KEY": "  ", "MODEL_NAME": ""}
    assert len(load_settings(env=env).missing()) == 3


def test_no_secret_in_repr():
    settings = load_settings(env={"OPENAI_API_KEY": FAKE_KEY, "SERPER_API_KEY": FAKE_KEY})
    text = repr(settings) + str(settings) + settings.model_dump_json()
    assert FAKE_KEY not in text
    assert settings.key_presence()["OPENAI_API_KEY"] is True


def test_dotenv_file_loaded_and_process_env_wins(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("MODEL_NAME=from-file\nSERPER_API_KEY=file-serper-value\n", encoding="utf-8")
    monkeypatch.setenv("MODEL_NAME", "from-process")
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    settings = load_settings(dotenv_path=dotenv)
    assert settings.model_name == "from-process"
    assert settings.serper_api_key is not None


def test_redaction():
    assert FAKE_KEY not in redact(f"calling with {FAKE_KEY}")
    assert "abc123" not in redact("api_key=abc123 other")


def test_redacting_filter_on_log_record():
    import logging

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "key %s", (FAKE_KEY,), None)
    RedactingFilter().filter(record)
    assert FAKE_KEY not in record.getMessage()
