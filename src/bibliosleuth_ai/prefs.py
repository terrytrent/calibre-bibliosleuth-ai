import os

from calibre.utils.config import JSONConfig, config_dir

from .constants import DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT, SCHEMA_VERSION
from . import credentials
from .prompt_validation import validation_matches_prompt
from .metrics import MetricsStore
from .diagnostic_journal import DiagnosticJournal

OPTIMIZATION_PRESETS = {
    "economy": {"front_matter_chars": 4000, "search_context_size": "low", "reasoning_effort": "none", "max_output_tokens": 1600, "evidence_url_limit": 2},
    "balanced": {"front_matter_chars": 6000, "search_context_size": "low", "reasoning_effort": "low", "max_output_tokens": 2000, "evidence_url_limit": 3},
    "thorough": {"front_matter_chars": 12000, "search_context_size": "medium", "reasoning_effort": "medium", "max_output_tokens": 3000, "evidence_url_limit": 4},
}

prefs = JSONConfig("plugins/bibliosleuth_ai")
prefs.defaults.update({
    "model": DEFAULT_MODEL,
    "timeout": 60,
    "optimization_preset": "balanced",
    "search_context_size": "low",
    "front_matter_chars": 6000,
    "reasoning_effort": "low",
    "max_output_tokens": 2000,
    "evidence_url_limit": 3,
    "tag_limit": 20,
    "description_limit": 5000,
    "system_prompt_override": "",
    "prompt_validation": {},
    "default_model_version": "",
    "model_catalog_cache": {},
    "remember_api_key": True,
    "onboarding_complete": False,
    "statistics_enabled": True,
    "statistics_retention_days": 90,
    "statistics_max_records": 1000,
})

metrics_store = MetricsStore(
    os.path.join(config_dir, "plugins", "bibliosleuth-ai-statistics.json"),
    max_records=prefs["statistics_max_records"],
    retention_days=prefs["statistics_retention_days"],
    enabled=prefs["statistics_enabled"],
)
diagnostic_journal = DiagnosticJournal(
    os.path.join(config_dir, "plugins", "bibliosleuth-ai-diagnostics.json"),
)

# API keys are deliberately session-only. Older versions stored this value in
# JSONConfig; clear it during upgrade so it does not remain in backups or on disk.
if "api_key" in prefs:
    del prefs["api_key"]
_session_api_key = ""
_vault_load_attempted = False

# Upgrade installations that still use the previous bundled default while
# preserving any other explicitly selected model.
if prefs["default_model_version"] != DEFAULT_MODEL:
    if prefs["model"] in ("", "gpt-5.5"):
        prefs["model"] = DEFAULT_MODEL
    prefs["default_model_version"] = DEFAULT_MODEL


def effective_optimization_settings(values=None):
    values = values or prefs
    preset = values["optimization_preset"]
    if preset in OPTIMIZATION_PRESETS:
        return dict(OPTIMIZATION_PRESETS[preset])
    return {key: values[key] for key in ("front_matter_chars", "search_context_size", "reasoning_effort", "max_output_tokens", "evidence_url_limit")}


def api_key():
    global _session_api_key, _vault_load_attempted
    environment = os.environ.get("OPENAI_API_KEY", "").strip()
    if environment:
        return environment
    if _session_api_key:
        return _session_api_key
    if not _vault_load_attempted and prefs["remember_api_key"] and credentials.available():
        _vault_load_attempted = True
        try:
            _session_api_key = credentials.load().strip()
            return _session_api_key
        except credentials.CredentialStoreError:
            return ""
    return ""


def set_session_api_key(value):
    global _session_api_key, _vault_load_attempted
    _session_api_key = (value or "").strip()
    if _session_api_key:
        _vault_load_attempted = True


def forget_session_api_key():
    global _session_api_key, _vault_load_attempted
    _session_api_key = ""
    _vault_load_attempted = True


def effective_prompt():
    return prefs["system_prompt_override"].strip() or DEFAULT_SYSTEM_PROMPT


def prompt_needs_revalidation():
    if not prefs["system_prompt_override"].strip():
        return False
    status = prefs["prompt_validation"] or {}
    prompt = prefs["system_prompt_override"].strip()
    return (
        status.get("schema_version") != SCHEMA_VERSION
        or not validation_matches_prompt(prompt, status)
    )
