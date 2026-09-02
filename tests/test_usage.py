import pytest

from bibliosleuth_ai.usage import MODEL_PRICING, estimate_cost_usd, format_usage


def sample_usage():
    return {
        "input_tokens": 1200, "cached_tokens": 800, "output_tokens": 500,
        "reasoning_tokens": 100, "total_tokens": 1700, "web_search_calls": 1,
    }


def test_estimates_standard_model_and_search_cost():
    assert estimate_cost_usd("gpt-5.5", sample_usage()) == pytest.approx(0.0274)
    assert estimate_cost_usd("gpt-5.6-luna", sample_usage()) == pytest.approx(0.010696)


@pytest.mark.parametrize(("model", "expected"), [
    ("claude-sonnet-5", 0.01596),
    ("claude-sonnet-5-20260801", 0.01596),
    ("claude-opus-5", 0.0249),
    ("claude-fable-5-1", 0.0398),
    ("claude-haiku-4-5-20251001", 0.01298),
    ("claude-sonnet-4-6", 0.01894),
])
def test_estimates_claude_models_and_hosted_search(model, expected):
    assert estimate_cost_usd(model, sample_usage(), provider="anthropic") == pytest.approx(expected)


def test_searxng_calls_do_not_receive_openai_hosted_search_pricing():
    usage = dict(
        sample_usage(), hosted_web_search_calls=0, searxng_search_calls=3,
        web_search_calls=3,
    )
    assert estimate_cost_usd("gpt-5.6-luna", usage) == pytest.approx(0.000696)


def test_searxng_calls_do_not_receive_anthropic_hosted_search_pricing():
    usage = dict(sample_usage(), hosted_web_search_calls=0,
                 searxng_search_calls=3, web_search_calls=3)
    assert estimate_cost_usd(
        "claude-sonnet-5", usage, provider="anthropic"
    ) == pytest.approx(0.00596)


def test_unknown_model_keeps_tokens_but_not_cost():
    usage = sample_usage()
    usage["estimated_cost_usd"] = estimate_cost_usd("custom-model", usage)
    assert usage["estimated_cost_usd"] is None
    assert "estimated cost unavailable" in format_usage("custom-model", usage)


def test_cache_hit_reports_no_new_usage():
    assert format_usage("model", {"cache_hit": True}) == "Session cache hit · no new API call or cost"


def test_usage_infers_local_provider_from_lookup_detail():
    usage = dict(sample_usage(), provider="ollama", estimated_cost_usd=None)
    assert "local inference" in format_usage("qwen", usage)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_every_priced_model_and_dated_snapshot_has_an_estimate(provider):
    for model in MODEL_PRICING[provider]:
        assert estimate_cost_usd(model, sample_usage(), provider=provider) is not None
        assert estimate_cost_usd(
            model + "-2026-08-01", sample_usage(), provider=provider
        ) is not None


def test_local_providers_never_receive_hosted_price_estimates():
    assert estimate_cost_usd("claude-sonnet-5", sample_usage(), provider="ollama") is None
    assert estimate_cost_usd("gpt-5.6-luna", sample_usage(), provider="lmstudio") is None
