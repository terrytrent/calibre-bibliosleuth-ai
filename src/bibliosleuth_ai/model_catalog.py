"""Validated, seven-day provider model catalog cache."""

import re
import time

from .constants import DEFAULT_MODEL
from .model_ids import is_anthropic_research_model, is_model_id


CACHE_SECONDS = 7 * 24 * 60 * 60
MAX_MODELS = 200
SNAPSHOT_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")
FALLBACK_MODELS = (DEFAULT_MODEL, "gpt-5.6-terra", "gpt-5.6-sol")
ANTHROPIC_FALLBACK_MODELS = (
    "claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5",
    "claude-fable-5", "claude-sonnet-4-6", "claude-opus-4-8",
    "claude-opus-4-7", "claude-opus-4-6", "claude-opus-4-5",
    "claude-sonnet-4-5", "claude-haiku-4-5-20251001",
)


def is_relevant_model(model):
    model = str(model or "")
    if not is_model_id(model) or SNAPSHOT_SUFFIX.search(model):
        return False
    lowered = model.casefold()
    if not lowered.startswith("gpt-"):
        return False
    excluded = (
        "audio", "chat", "codex", "image", "realtime", "search-preview",
        "transcribe", "tts", "whisper",
    )
    return not any(token in lowered for token in excluded)


def safe_model_id(model):
    value = str(model or "unknown")[:128]
    if value in ("unknown", "not applicable"):
        return value
    if value.casefold().startswith(("sk-", "sess-")) or not is_model_id(value):
        return "[REDACTED_INVALID_MODEL]"
    return value


def normalize_models(models, current=None):
    values = set(FALLBACK_MODELS)
    values.update(str(model) for model in (models or []) if is_relevant_model(model))
    if is_relevant_model(current):
        values.add(str(current))
    return sorted(values, key=lambda value: (value != DEFAULT_MODEL, value.casefold()))[:MAX_MODELS]


def _provider_cache(preferences, provider="openai"):
    cache = preferences.get("model_catalog_cache", {}) or {}
    providers = cache.get("providers") or {}
    if provider in providers:
        return providers[provider]
    return cache if provider == "openai" else {}


def cached_models(preferences, current=None, provider="openai"):
    cache = _provider_cache(preferences, provider)
    if provider != "openai":
        predicate = is_anthropic_research_model if provider == "anthropic" else is_model_id
        values = {str(model) for model in cache.get("models", []) if predicate(model)}
        if provider == "anthropic":
            values.update(ANTHROPIC_FALLBACK_MODELS)
        if predicate(current):
            values.add(str(current))
        return sorted(values, key=str.casefold)[:MAX_MODELS]
    return normalize_models(cache.get("models", []), current)


def cache_is_fresh(preferences, now=None, provider="openai"):
    cache = _provider_cache(preferences, provider)
    try:
        fetched = float(cache.get("fetched_at", 0))
    except (TypeError, ValueError):
        return False
    return bool(cache.get("models")) and 0 <= float(now or time.time()) - fetched < CACHE_SECONDS


def store_models(preferences, models, now=None, provider="openai"):
    normalized = (
        normalize_models(models) if provider == "openai"
        else sorted(
            {str(model) for model in models if is_anthropic_research_model(model)},
            key=str.casefold,
        )[:MAX_MODELS] if provider == "anthropic"
        else sorted({str(model) for model in models if is_model_id(model)}, key=str.casefold)[:MAX_MODELS]
    )
    existing = preferences.get("model_catalog_cache", {}) or {}
    providers = dict(existing.get("providers") or {})
    if not providers and existing.get("models"):
        providers["openai"] = {
            "fetched_at": existing.get("fetched_at", 0),
            "models": existing.get("models", []),
        }
    providers[provider] = {"fetched_at": float(now or time.time()), "models": normalized}
    preferences["model_catalog_cache"] = {"providers": providers}
    return normalized
