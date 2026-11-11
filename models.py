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


def make_model(model_id: str):
    timeout, retries = settings.REQUEST_TIMEOUT_S, settings.MAX_RETRIES
    if model_id.startswith("openrouter:"):
        timeout, retries = timeout * 1000, 1            # OpenRouter counts the timeout in milliseconds
    return init_chat_model(model_id, timeout=timeout, max_retries=retries,
                           max_tokens=settings.MAX_OUTPUT_TOKENS,
                           rate_limiter=InMemoryRateLimiter(requests_per_second=0.5))


def build_model():
    model = make_model(settings.MODEL)
    if settings.FALLBACK and has_key(settings.FALLBACK):
        return model.with_fallbacks([make_model(settings.FALLBACK)])
    return model


def load_prompt(name: str) -> tuple[str, str]:
    """(prompt text, version label)."""
    data = yaml.safe_load((ROOT / "prompts.yml").read_text(encoding="utf-8"))
    return data[name], data[f"{name}_version"]
