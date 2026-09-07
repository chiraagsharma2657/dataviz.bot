"""Talking to the model and parsing what comes back."""

import json
import os

from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_MODEL = "gemini-3.6-flash"


class ModelError(RuntimeError):
    """A model call failed for a reason worth explaining to the user."""


class QuotaExceeded(ModelError):
    """The API key is out of requests for now."""


def _status_code(exc):
    """The HTTP status of a failed call, wherever the SDK hung it."""
    for candidate in (exc, getattr(exc, "__cause__", None)):
        if candidate is None:
            continue
        for attr in ("code", "status_code"):
            value = getattr(candidate, attr, None)
            if isinstance(value, int):
                return value
    return None


def _looks_like_quota(exc):
    """Quota errors arrive as 429 / RESOURCE_EXHAUSTED.

    LangChain sometimes re-raises the SDK error wrapped in something else, so
    the text is checked as well as the status code.
    """
    if _status_code(exc) == 429:
        return True
    text = f"{getattr(exc, 'status', '')} {exc}".lower()
    return any(marker in text for marker in (
        "resource_exhausted", "quota", "rate limit", "ratelimit",
        "too many requests",
    ))


def _looks_like_bad_key(exc):
    if _status_code(exc) in (401, 403):
        return True
    text = f"{exc}".lower()
    return "api_key_invalid" in text or "api key not valid" in text


def ask(model, prompt):
    """Send one prompt and return the reply text, or raise a ModelError.

    Without this, a spent API key surfaced as a raw traceback in the middle of
    the page - accurate, but it tells the user nothing they can act on.
    """
    try:
        response = model.invoke(prompt)
    except Exception as exc:
        if _looks_like_quota(exc):
            raise QuotaExceeded(
                "DataViz has used up its API requests for now. "
                "The Gemini free tier refills after a short wait - try again in "
                "a minute, or put a different key in your .env file."
            ) from exc
        if _looks_like_bad_key(exc):
            raise ModelError(
                "Gemini rejected the API key. Check GOOGLE_API_KEY in your .env "
                "file - a new key takes a moment to become active."
            ) from exc
        raise ModelError(f"Could not reach the model: {exc}") from exc

    return reply_text(response)


def build_model(api_key=None, model_name=None):
    """Create the chat model for one caller's API key.

    The key is passed in rather than read from the environment, because when
    the app is hosted each visitor brings their own and they must never share
    one. It falls back to the environment so local runs and a single-owner
    deployment keep working unchanged.
    """
    key = api_key or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "No API key. Copy .env.example to .env and add your key."
        )
    return ChatGoogleGenerativeAI(
        model=model_name or os.getenv("MODEL_NAME", DEFAULT_MODEL),
        google_api_key=key,
    )


def verify_key(api_key):
    """Check a key with one tiny request, so a typo is caught at the door.

    Returns None when the key works, otherwise a message to show the user.
    """
    try:
        ask(build_model(api_key=api_key), "Reply with: ok")
    except ModelError as e:
        return str(e)
    except Exception as e:                       # malformed key, no network
        return f"Could not verify that key: {e}"
    return None


def reply_text(response):
    """Get the plain text out of a model reply.

    Newer Gemini models return `content` as a list of content blocks rather
    than a plain string, so read `.text` when it is available.
    """
    text = getattr(response, "text", None)
    if callable(text):
        text = text()
    if isinstance(text, str) and text:
        return text

    content = response.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


def strip_fences(text):
    text = text.strip()
    for fence in ("```json", "```sql", "```"):
        text = text.removeprefix(fence)
    return text.removesuffix("```").strip()


def parse_chart_reply(text):
    """Pull the chart-spec JSON object out of the model reply."""
    text = strip_fences(text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
