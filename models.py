"""The chat model: one string picks the provider, a second one is the fallback (course session 4).

    from models import build_model
    model = build_model()           # Gemini, plus the fallback if its key is in .env

If the primary model fails after its retries (outage, spent quota), LangChain sends the same
request to the fallback automatically: model.with_fallbacks([...]). Milestone M7 tests it.
"""
import os

import yaml
from langchain.chat_models import init_chat_model
from langchain_core.rate_limiters import InMemoryRateLimiter

from config import ROOT, settings

KEY_NAMES = {"google_genai": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}


def has_key(model_id: str) -> bool:
    return bool(os.getenv(KEY_NAMES.get(model_id.split(":", 1)[0], "")))


_LIMITERS: dict[str, InMemoryRateLimiter] = {}


def make_model(model_id: str):
    """One chat model. ONE rate limiter per provider is shared by every model object of that provider:
    the classifier, the answerer, the tool loop and the explainer all spend the same free-tier quota
    (Gemini's is 15 requests a minute), so they must queue behind the same limiter."""
    provider = model_id.split(":", 1)[0]
    limiter = _LIMITERS.setdefault(provider, InMemoryRateLimiter(requests_per_second=settings.REQUESTS_PER_SECOND))
    timeout, retries = settings.REQUEST_TIMEOUT_S, settings.MAX_RETRIES
    if model_id.startswith("openrouter:"):
        timeout, retries = timeout * 1000, 1            # OpenRouter counts the timeout in milliseconds
    return init_chat_model(model_id, timeout=timeout, max_retries=retries,
                           max_tokens=settings.MAX_OUTPUT_TOKENS, rate_limiter=limiter)


def build_model(schema=None, tools=None):
    """The assistant's model, with the fallback attached.

    schema -> structured output (a Pydantic class); tools -> tool calling. Either is applied to
    the primary AND the fallback BEFORE they are joined: a fallback that only returned plain text
    would break the caller exactly when it is needed."""
    def prepared(model_id: str):
        m = make_model(model_id)
        if schema is not None:
            m = m.with_structured_output(schema)
        if tools is not None:
            m = m.bind_tools(tools)
        return m

    primary = prepared(settings.MODEL)
    if settings.FALLBACK and has_key(settings.FALLBACK):
        return primary.with_fallbacks([prepared(settings.FALLBACK)])
    return primary


def load_prompt(name: str) -> tuple[str, str]:
    """(prompt text, version label)."""
    data = yaml.safe_load((ROOT / "prompts.yml").read_text(encoding="utf-8"))
    return data[name], data[f"{name}_version"]
