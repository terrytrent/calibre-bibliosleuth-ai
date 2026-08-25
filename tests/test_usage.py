import pytest

from calibre_ai_plugin.usage import estimate_cost_usd, format_usage


def sample_usage():
    return {
        "input_tokens": 1200, "cached_tokens": 800, "output_tokens": 500,
        "reasoning_tokens": 100, "total_tokens": 1700, "web_search_calls": 1,
    }


def test_estimates_standard_model_and_search_cost():
    assert estimate_cost_usd("gpt-5.5", sample_usage()) == pytest.approx(0.0274)
    assert estimate_cost_usd("gpt-5.6-luna", sample_usage()) == pytest.approx(0.010696)


def test_unknown_model_keeps_tokens_but_not_cost():
    usage = sample_usage()
    usage["estimated_cost_usd"] = estimate_cost_usd("custom-model", usage)
    assert usage["estimated_cost_usd"] is None
    assert "estimated cost unavailable" in format_usage("custom-model", usage)


def test_cache_hit_reports_no_new_usage():
    assert format_usage("model", {"cache_hit": True}) == "Session cache hit · no new API call or cost"
