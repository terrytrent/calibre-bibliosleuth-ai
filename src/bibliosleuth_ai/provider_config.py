"""Pure state management for switching provider configuration in the Qt UI."""

from dataclasses import dataclass, field

from .providers import provider_spec


def migrate_provider_models(provider_models, legacy_model):
    """Seed provider-specific choices from the pre-provider OpenAI setting."""
    models = dict(provider_models or {})
    models["openai"] = str(legacy_model or "").strip()
    return models


@dataclass
class ProviderConfigurationState:
    active: str
    models: dict = field(default_factory=dict)
    endpoints: dict = field(default_factory=dict)
    replacement_keys: dict = field(default_factory=dict)

    def capture(self, model="", endpoint="", replacement_key=""):
        self.models[self.active] = str(model or "").strip()
        if replacement_key:
            self.replacement_keys[self.active] = str(replacement_key).strip()
        if provider_spec(self.active).default_endpoint:
            self.endpoints[self.active] = str(endpoint or "").strip()

    def switch(self, provider):
        self.active = provider
        spec = provider_spec(provider)
        return {
            "model": self.models.get(provider) or spec.default_model,
            "endpoint": self.endpoints.get(provider) or spec.default_endpoint,
            "replacement_key": self.replacement_keys.get(provider, ""),
        }
