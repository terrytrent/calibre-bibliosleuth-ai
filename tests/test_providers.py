import pytest

from bibliosleuth_ai.provider_base import ProviderError
from bibliosleuth_ai.providers import (
    model_id_for_discovery, resolve_anthropic_workspace_id, sanitize_anthropic_models,
    sanitize_anthropic_workspace_id, sanitize_model_id, sanitize_model_list,
)


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
