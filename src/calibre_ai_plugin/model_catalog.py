"""Validated, seven-day cache for account-visible OpenAI model aliases."""

import re
import time

from .constants import DEFAULT_MODEL


CACHE_SECONDS = 7 * 24 * 60 * 60
MAX_MODELS = 200
MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SNAPSHOT_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")
FALLBACK_MODELS = (DEFAULT_MODEL, "gpt-5.6-terra", "gpt-5.6-sol")


def is_relevant_model(model):
    model = str(model or "")
    if not MODEL_ID.fullmatch(model) or SNAPSHOT_SUFFIX.search(model):
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
    if value.casefold().startswith(("sk-", "sess-")) or not MODEL_ID.fullmatch(value):
        return "[REDACTED_INVALID_MODEL]"
    return value


def normalize_models(models, current=None):
    values = set(FALLBACK_MODELS)
    values.update(str(model) for model in (models or []) if is_relevant_model(model))
    if is_relevant_model(current):
        values.add(str(current))
    return sorted(values, key=lambda value: (value != DEFAULT_MODEL, value.casefold()))[:MAX_MODELS]


def cached_models(preferences, current=None):
    cache = preferences.get("model_catalog_cache", {}) or {}
    return normalize_models(cache.get("models", []), current)


def cache_is_fresh(preferences, now=None):
    cache = preferences.get("model_catalog_cache", {}) or {}
    try:
        fetched = float(cache.get("fetched_at", 0))
    except (TypeError, ValueError):
        return False
    return bool(cache.get("models")) and 0 <= float(now or time.time()) - fetched < CACHE_SECONDS


def store_models(preferences, models, now=None):
    normalized = normalize_models(models)
    preferences["model_catalog_cache"] = {
        "fetched_at": float(now or time.time()),
        "models": normalized,
    }
    return normalized
