from bibliosleuth_ai.provider_config import ProviderConfigurationState, migrate_provider_models


def test_provider_state_preserves_each_provider_values():
    state = ProviderConfigurationState("openai")
    state.capture("gpt-test", replacement_key="openai-secret")
    selected = state.switch("ollama")
    assert selected["endpoint"] == "http://127.0.0.1:11434/v1"
    state.capture("qwen3:8b", endpoint="http://127.0.0.1:9999/v1")
    selected = state.switch("openai")
    assert selected["model"] == "gpt-test"
    assert selected["replacement_key"] == "openai-secret"


def test_legacy_openai_model_is_preserved_during_provider_migration():
    migrated = migrate_provider_models(
        {"openai": "new-default", "anthropic": "claude-test"}, "gpt-custom"
    )
    assert migrated == {"openai": "gpt-custom", "anthropic": "claude-test"}
