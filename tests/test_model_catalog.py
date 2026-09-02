from bibliosleuth_ai.model_catalog import (
    ANTHROPIC_FALLBACK_MODELS, cache_is_fresh, cached_models, normalize_models,
    safe_model_id, store_models,
)
from bibliosleuth_ai.providers import provider_spec


def test_catalog_filters_snapshots_and_non_research_models():
    models = normalize_models([
        "gpt-5.6-luna", "gpt-5.6-terra-2026-01-01", "gpt-image-2",
        "text-embedding-3-small", "gpt-5.3-codex",
    ])
    assert "gpt-5.6-luna" in models
    assert "gpt-5.6-terra-2026-01-01" not in models
    assert "gpt-image-2" not in models
    assert "gpt-5.3-codex" not in models


def test_catalog_cache_expires_after_seven_days():
    preferences = {}
    store_models(preferences, ["gpt-5.6-luna"], now=100)
    assert cache_is_fresh(preferences, now=100 + 7 * 86400 - 1)
    assert not cache_is_fresh(preferences, now=100 + 7 * 86400)


def test_model_id_redacts_accidental_secret():
    assert safe_model_id("sk-secretvalue123456789") == "[REDACTED_INVALID_MODEL]"


def test_local_model_ids_with_namespaces_are_preserved_and_cached_per_provider():
    preferences = {}
    store_models(preferences, ["library/qwen3:8b"], provider="ollama", now=100)
    store_models(preferences, ["gpt-5.6-luna"], provider="openai", now=100)
    assert safe_model_id("library/qwen3:8b") == "library/qwen3:8b"
    assert cached_models(preferences, provider="ollama") == ["library/qwen3:8b"]
    assert "library/qwen3:8b" not in cached_models(preferences, provider="openai")


def test_incompatible_anthropic_catalog_is_not_fresh():
    preferences = {}
    store_models(preferences, ["claude-3-5-sonnet-latest"], provider="anthropic", now=100)
    choices = cached_models(preferences, provider="anthropic")
    assert "claude-3-5-sonnet-latest" not in choices
    assert "claude-sonnet-5" in choices
    assert not cache_is_fresh(preferences, provider="anthropic", now=101)


def test_anthropic_catalog_always_offers_current_supported_models():
    choices = cached_models({}, "claude-sonnet-4-6", provider="anthropic")
    assert "claude-sonnet-5" in choices
    assert "claude-opus-5" in choices
    assert "claude-haiku-4-5" in choices
    assert "claude-sonnet-4-6" in choices


def test_claude_default_and_every_bundled_choice_are_available():
    choices = cached_models({}, provider= "anthropic")
    assert provider_spec("anthropic").default_model == "claude-sonnet-5"
    assert set(ANTHROPIC_FALLBACK_MODELS) <= set(choices)
