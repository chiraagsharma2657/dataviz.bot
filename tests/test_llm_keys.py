"""Per-caller API keys.

When the app is hosted, every visitor brings their own key, so a key must
travel as an argument and never through shared global state.
"""

import pytest

from dataviz.llm import ModelError, build_model, verify_key


def key_of(model):
    """The key LangChain stored, unwrapped from its SecretStr."""
    secret = model.google_api_key
    return secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)


def test_key_argument_is_used(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert key_of(build_model(api_key="caller-key")) == "caller-key"


def test_two_callers_get_independent_models(monkeypatch):
    """The bug this guards: one visitor's key leaking into another's client."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    a = build_model(api_key="key-a")
    b = build_model(api_key="key-b")
    assert key_of(a) == "key-a"
    assert key_of(b) == "key-b"


def test_environment_is_the_fallback_not_the_override(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
    assert key_of(build_model(api_key="caller-key")) == "caller-key"
    assert key_of(build_model()) == "env-key"


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="No API key"):
        build_model()


def test_verify_key_reports_a_bad_key(monkeypatch):
    """A rejected key comes back as a message, not an exception to leak."""
    def boom(*a, **k):
        raise ModelError("Gemini rejected the API key.")

    monkeypatch.setattr("dataviz.llm.ask", boom)
    problem = verify_key("nonsense")
    assert problem and "rejected the API key" in problem


def test_verify_key_survives_a_non_model_exception(monkeypatch):
    """A malformed key can fail before any request is made."""
    def boom(*a, **k):
        raise ValueError("not a valid key format")

    monkeypatch.setattr("dataviz.llm.ask", boom)
    problem = verify_key("???")
    assert problem and "Could not verify that key" in problem


def test_verify_key_returns_none_when_it_works(monkeypatch):
    monkeypatch.setattr("dataviz.llm.ask", lambda *a, **k: "ok")
    assert verify_key("good-key") is None
