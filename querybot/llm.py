"""Talking to the model and parsing what comes back."""

import json
import os

from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_MODEL = "gemini-3.6-flash"


def build_model(model_name=None):
    """Create the chat model, reading the model name from the environment.

    Raises a clear error when GOOGLE_API_KEY is missing, rather than letting
    the first request fail deep inside the client.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return ChatGoogleGenerativeAI(model=model_name or os.getenv("MODEL_NAME", DEFAULT_MODEL))


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
