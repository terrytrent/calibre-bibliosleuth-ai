from bibliosleuth_ai.model_catalog import cache_is_fresh, normalize_models, safe_model_id, store_models


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
