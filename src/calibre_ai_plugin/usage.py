"""Token formatting and conservative standard-tier cost estimates."""

PRICING_AS_OF = "2026-08-20"
WEB_SEARCH_USD_PER_CALL = 0.01

# USD per 1M tokens: uncached input, cached input, output.
MODEL_PRICING = {
    "gpt-5.5": (5.00, 0.50, 30.00),
    "gpt-5.4": (2.50, 0.25, 15.00),
    "gpt-5.6-sol": (5.00, 0.50, 30.00),
    "gpt-5.6": (5.00, 0.50, 30.00),
    "gpt-5.6-terra": (2.00, 0.20, 12.00),
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
}


def _rates_for_model(model):
    model = (model or "").lower()
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]
    for base in sorted(MODEL_PRICING, key=len, reverse=True):
        suffix = model[len(base) + 1:] if model.startswith(base + "-") else ""
        if suffix and suffix[0].isdigit():
            rates = MODEL_PRICING[base]
            return rates
    return None


def estimate_cost_usd(model, usage):
    rates = _rates_for_model(model)
    if rates is None or not usage:
        return None
    input_rate, cached_rate, output_rate = rates
    cached = max(0, int(usage.get("cached_tokens") or 0))
    total_input = max(cached, int(usage.get("input_tokens") or 0))
    uncached = total_input - cached
    output = max(0, int(usage.get("output_tokens") or 0))
    searches = max(0, int(usage.get("web_search_calls") or 0))
    return (
        uncached * input_rate / 1_000_000
        + cached * cached_rate / 1_000_000
        + output * output_rate / 1_000_000
        + searches * WEB_SEARCH_USD_PER_CALL
    )


def format_usage(model, usage):
    if not usage:
        return "Token usage unavailable"
    if usage.get("cache_hit"):
        return "Session cache hit · no new API call or cost"
    text = (
        "%(input_tokens)d input (%(cached_tokens)d cached) · %(output_tokens)d output "
        "(%(reasoning_tokens)d reasoning) · %(total_tokens)d total · "
        "%(web_search_calls)d web search call(s)" % usage
    )
    cost = usage.get("estimated_cost_usd")
    if cost is None:
        return text + " · estimated cost unavailable for model %s" % model
    return text + " · estimated cost $%.4f USD" % cost
