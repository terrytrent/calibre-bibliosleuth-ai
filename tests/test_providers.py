import pytest

from bibliosleuth_ai.provider_base import ProviderError, ServicePreflightError
from bibliosleuth_ai.providers import (
    SERVICE_PREFLIGHT_TIMEOUT_SECONDS, effective_reasoning, model_id_for_discovery,
    preflight_research_services, resolve_anthropic_workspace_id,
    sanitize_anthropic_models, sanitize_anthropic_workspace_id, sanitize_model_id,
    sanitize_model_list,
)


def test_effective_reasoning_is_disabled_for_local_integrations():
    assert effective_reasoning("ollama", "high") == "none"
    assert effective_reasoning("lmstudio", "high") == "none"
    assert effective_reasoning("openai", "high") == "high"
    assert effective_reasoning("anthropic", "medium") == "medium"


def test_model_ids_are_sanitized_for_every_provider():
    assert sanitize_model_id("library/qwen3:8b") == "library/qwen3:8b"
    assert sanitize_model_list(["claude-sonnet-4-6", "bad model\nheader", "x" * 200]) == ["claude-sonnet-4-6"]
    with pytest.raises(ProviderError, match="identifier"):
        sanitize_model_id("bad model\nheader")


def test_anthropic_catalog_keeps_only_structured_output_families():
    assert sanitize_anthropic_models([
        "claude-3-5-sonnet-latest", "claude-sonnet-4-5-20250929",
        "claude-opus-5", "claude-fable-5-0", "claude-mythos-5-preview",
        "not a model",
    ]) == [
        "claude-fable-5-0", "claude-mythos-5-preview", "claude-opus-5",
        "claude-sonnet-4-5-20250929",
    ]


def test_anthropic_workspace_id_is_optional_and_sanitized():
    assert sanitize_anthropic_workspace_id("") == ""
    assert sanitize_anthropic_workspace_id("wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ").startswith("wrkspc_")
    with pytest.raises(ProviderError, match="workspace ID"):
        sanitize_anthropic_workspace_id("bad\nheader")


def test_anthropic_workspace_environment_takes_precedence_without_leaking_whitespace():
    assert resolve_anthropic_workspace_id(
        "wrkspc_saved123", {"ANTHROPIC_WORKSPACE_ID": " wrkspc_environment456 "}
    ) == "wrkspc_environment456"
    assert resolve_anthropic_workspace_id(
        " wrkspc_saved123 ", {}
    ) == "wrkspc_saved123"


def test_empty_first_run_model_can_construct_provider_for_discovery():
    assert model_id_for_discovery("") == "model-discovery"
    assert model_id_for_discovery(" qwen3:0.6b ") == "qwen3:0.6b"
    assert model_id_for_discovery("bad model\nheader") == "model-discovery"


class _SearchProbe:
    def __init__(self, error=None):
        self.error = error
        self.timeouts = []

    def test_connection(self, timeout=None):
        self.timeouts.append(timeout)
        if self.error:
            raise self.error
        return True


class _ProviderProbe:
    def __init__(self, model="qwen", models=None, search=None, error=None):
        self.model = model
        self.models = [model] if models is None else models
        self.searxng_client = search
        self.error = error
        self.timeouts = []

    def list_models(self, timeout=None):
        self.timeouts.append(timeout)
        if self.error:
            raise self.error
        return self.models


def test_hosted_research_does_not_run_local_service_preflight():
    assert preflight_research_services(object(), "openai", "hosted") is True


def test_searxng_preflight_uses_a_short_timeout_without_model_generation():
    search = _SearchProbe()
    provider = _ProviderProbe(search=search)
    assert preflight_research_services(provider, "openai", "searxng") is True
    assert search.timeouts == [SERVICE_PREFLIGHT_TIMEOUT_SECONDS]
    assert provider.timeouts == []


@pytest.mark.parametrize("provider_id", ["ollama", "lmstudio"])
def test_local_preflight_checks_searxng_then_the_selected_model(provider_id):
    search = _SearchProbe()
    provider = _ProviderProbe(search=search)
    assert preflight_research_services(provider, provider_id, "searxng") is True
    assert search.timeouts == [SERVICE_PREFLIGHT_TIMEOUT_SECONDS]
    assert provider.timeouts == [SERVICE_PREFLIGHT_TIMEOUT_SECONDS]


def test_failed_searxng_preflight_is_actionable_and_stops_local_probe():
    search = _SearchProbe(OSError("connection refused"))
    provider = _ProviderProbe(search=search)
    with pytest.raises(ServicePreflightError, match="Start the configured SearXNG") as raised:
        preflight_research_services(provider, "ollama", "searxng")
    assert raised.value.service == "searxng"
    assert "connection refused" in str(raised.value)
    assert provider.timeouts == []


@pytest.mark.parametrize("provider_id,label", [("ollama", "Ollama"), ("lmstudio", "LM Studio")])
def test_failed_local_server_preflight_names_the_service(provider_id, label):
    provider = _ProviderProbe(search=_SearchProbe(), error=OSError("connection refused"))
    with pytest.raises(ServicePreflightError, match=label) as raised:
        preflight_research_services(provider, provider_id, "searxng")
    assert raised.value.service == provider_id
    assert "connection refused" in str(raised.value)


def test_local_preflight_rejects_an_unloaded_selected_model():
    provider = _ProviderProbe(model="qwen:8b", models=["gemma3:4b"], search=_SearchProbe())
    with pytest.raises(ServicePreflightError, match="selected model 'qwen:8b' is not available"):
        preflight_research_services(provider, "ollama", "searxng")
