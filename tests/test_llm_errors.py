"""Turning model failures into messages a user can act on.

A spent key used to surface as a raw traceback mid-page. These cover the
classification, including the wrapped case - LangChain does not always let the
SDK error through untouched.
"""

import pytest

from dataviz.llm import ModelError, QuotaExceeded, ask


class FakeModel:
    def __init__(self, error):
        self.error = error

    def invoke(self, prompt):
        raise self.error


class FakeReply:
    """Stands in for a LangChain message."""
    def __init__(self, content):
        self.content = content


class SdkError(Exception):
    """Shaped like google.genai.errors.APIError: a code and a status."""
    def __init__(self, code, status, message=""):
        self.code = code
        self.status = status
        super().__init__(f"{code} {status}. {message}")


def test_quota_error_by_status_code():
    model = FakeModel(SdkError(429, "RESOURCE_EXHAUSTED", "quota exceeded"))
    with pytest.raises(QuotaExceeded, match="used up its API requests"):
        ask(model, "hi")


@pytest.mark.parametrize("message", [
    "429 RESOURCE_EXHAUSTED. You exceeded your current quota",
    "Rate limit reached for this key",
    "Too many requests, please retry",
    "RESOURCE_EXHAUSTED",
])
def test_quota_error_by_message_when_wrapped(message):
    """No usable status code - only the text, as when LangChain re-wraps it."""
    with pytest.raises(QuotaExceeded):
        ask(FakeModel(RuntimeError(message)), "hi")


def test_quota_message_does_not_leak_the_traceback():
    model = FakeModel(SdkError(429, "RESOURCE_EXHAUSTED", "quota metric xyz"))
    with pytest.raises(QuotaExceeded) as caught:
        ask(model, "hi")
    text = str(caught.value)
    assert "RESOURCE_EXHAUSTED" not in text
    assert "429" not in text
    assert caught.value.__cause__ is not None   # original kept for debugging


@pytest.mark.parametrize("error", [
    SdkError(401, "UNAUTHENTICATED"),
    SdkError(403, "PERMISSION_DENIED"),
    RuntimeError("API_KEY_INVALID"),
    RuntimeError("API key not valid. Please pass a valid API key."),
])
def test_bad_key_is_its_own_message(error):
    with pytest.raises(ModelError, match="rejected the API key") as caught:
        ask(FakeModel(error), "hi")
    assert not isinstance(caught.value, QuotaExceeded)


def test_other_failures_still_surface():
    with pytest.raises(ModelError, match="Could not reach the model"):
        ask(FakeModel(ConnectionError("network down")), "hi")


def test_quota_is_catchable_as_model_error():
    """The app catches QuotaExceeded first, so ordering matters."""
    assert issubclass(QuotaExceeded, ModelError)


def test_successful_call_returns_text():
    class Ok:
        def invoke(self, prompt):
            return FakeReply("SELECT 1")

    assert ask(Ok(), "hi") == "SELECT 1"
