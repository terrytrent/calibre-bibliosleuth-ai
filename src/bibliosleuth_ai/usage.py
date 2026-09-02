"""Token formatting and conservative standard-tier cost estimates."""

PRICING_AS_OF = "2026-09-01"
HOSTED_SEARCH_USD_PER_CALL = {"openai": 0.01, "anthropic": 0.01}

# USD per 1M tokens: uncached input, cached input, output.
OPENAI_MODEL_PRICING = {
    "gpt-5.5": (5.00, 0.50, 30.00),
    "gpt-5.4": (2.50, 0.25, 15.00),
    "gpt-5.6-sol": (4.00, 0.40, 20.00),
    "gpt-5.6": (4.00, 0.40, 20.00),
    "gpt-5.6-terra": (2.00, 0.20, 12.00),
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
}

# First-party Claude API standard/global rates. Cached input is a cache read;
# BiblioSleuth does not currently request the separately billed cache writes.
ANTHROPIC_MODEL_PRICING = {
    "claude-fable-5": (10.00, 1.00, 50.00),
    "claude-mythos-5": (10.00, 1.00, 50.00),
    "claude-opus-5": (5.00, 0.50, 25.00),
    "claude-opus-4-8": (5.00, 0.50, 25.00),
    "claude-opus-4-7": (5.00, 0.50, 25.00),
    "claude-opus-4-6": (5.00, 0.50, 25.00),
    "claude-opus-4-5": (5.00, 0.50, 25.00),
    "claude-sonnet-5": (2.00, 0.20, 10.00),
    "claude-sonnet-4-6": (3.00, 0.30, 15.00),
    "claude-sonnet-4-5": (3.00, 0.30, 15.00),
    "claude-haiku-4-5": (1.00, 0.10, 5.00),
}

MODEL_PRICING = {
    "openai": OPENAI_MODEL_PRICING,
    "anthropic": ANTHROPIC_MODEL_PRICING,
}


def _rates_for_model(model, provider="openai"):
    model = (model or "").lower()
    pricing = MODEL_PRICING.get(provider, {})
    if model in pricing:
        return pricing[model]
    # Provider APIs may return dated snapshots such as
    # claude-haiku-4-5-20251001 or gpt-5.6-luna-2026-08-01.
    for base in sorted(pricing, key=len, reverse=True):
        suffix = model[len(base) + 1:] if model.startswith(base + "-") else ""
        if suffix and suffix[0].isdigit():
            return pricing[base]
    return None


def estimate_cost_usd(model, usage, provider="openai"):
    rates = _rates_for_model(model, provider)
    if rates is None or not usage:
        return None
    input_rate, cached_rate, output_rate = rates
    cached = max(0, int(usage.get("cached_tokens") or 0))
    total_input = max(cached, int(usage.get("input_tokens") or 0))
    uncached = total_input - cached
    output = max(0, int(usage.get("output_tokens") or 0))
    # New provider-aware records distinguish billable hosted search from
    # application-managed SearXNG. Fall back only for legacy OpenAI records.
    searches = max(0, int(
        usage.get("hosted_web_search_calls")
        if "hosted_web_search_calls" in usage else usage.get("web_search_calls") or 0
    ))
    return (
        uncached * input_rate / 1_000_000
        + cached * cached_rate / 1_000_000
        + output * output_rate / 1_000_000
        + searches * HOSTED_SEARCH_USD_PER_CALL.get(provider, 0.0)
    )


def format_usage(model, usage, provider=None):
    if not usage:
        return "Token usage unavailable"
    provider = provider or usage.get("provider") or "openai"
    if usage.get("cache_hit"):
        return "Session cache hit · no new API call or cost"
    text = (
        "%(input_tokens)d input (%(cached_tokens)d cached) · %(output_tokens)d output "
        "(%(reasoning_tokens)d reasoning) · %(total_tokens)d total · "
        "%(web_search_calls)d web search call(s)" % usage
    )
    hosted = int(usage.get("hosted_web_search_calls") or 0)
    searxng = int(usage.get("searxng_search_calls") or 0)
    if hosted or searxng:
        text += " · %d hosted / %d SearXNG" % (hosted, searxng)
    cost = usage.get("estimated_cost_usd")
    if cost is None:
        if provider in ("ollama", "lmstudio"):
            return text + " · local inference; no API cost reported"
        return text + " · estimated cost unavailable for %s model %s" % (provider, model)
    return text + " · estimated cost $%.4f USD" % cost
