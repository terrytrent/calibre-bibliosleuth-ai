import hashlib
import platform
import sys

from .constants import PROMPT_VERSION, SCHEMA_VERSION
from .model_catalog import safe_model_id


def diagnostic_report(preferences, plugin_version, cache_entries=0, statistics_entries=0):
    prompt = (preferences["system_prompt_override"] or "").strip()
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12] if prompt else "bundled"
    validation = preferences["prompt_validation"] or {}
    lines = [
        "BiblioSleuth AI redacted diagnostics",
        "Plugin version: %s" % plugin_version,
        "Python: %s" % platform.python_version(),
        "OS: %s %s" % (platform.system(), platform.release()),
        "Architecture: %s" % platform.machine(),
        "Model: %s" % safe_model_id(preferences["model"]),
        "Optimization preset: %s" % preferences["optimization_preset"],
        "Timeout: %s seconds" % preferences["timeout"],
        "Prompt: %s (hash %s)" % ("custom" if prompt else "bundled", prompt_hash),
        "Prompt/schema versions: %s/%s" % (PROMPT_VERSION, SCHEMA_VERSION),
        "Prompt validated model: %s" % safe_model_id(validation.get("validated_model", "not applicable")),
        "Session cache entries: %d" % cache_entries,
        "Statistics: %s; %d records; retention %d days / %d maximum" % (
            "enabled" if preferences["statistics_enabled"] else "disabled", statistics_entries,
            preferences["statistics_retention_days"], preferences["statistics_max_records"],
        ),
        "API key: [REDACTED; presence not reported]",
    ]
    return "\n".join(lines)
