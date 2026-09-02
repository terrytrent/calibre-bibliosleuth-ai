"""Provider registry, typed settings, and provider construction."""

import os
import re
from dataclasses import dataclass

from .anthropic_provider import AnthropicProvider
from .constants import DEFAULT_MODEL
from .local_provider import LocalProvider
from .model_ids import is_anthropic_research_model, is_model_id
from .openai_provider import OpenAIProvider
from .provider_base import ProviderError
from .searxng import SearXNGClient


@dataclass(frozen=True)
class ProviderSpec:
    label: str
    default_model: str
    default_endpoint: str = ""
    environment_variable: str = ""
    requires_key: bool = True
    hosted_search: bool = True
    reasoning: bool = True


PROVIDER_SPECS = {
    "openai": ProviderSpec("OpenAI", DEFAULT_MODEL, environment_variable="OPENAI_API_KEY"),
    "anthropic": ProviderSpec(
        "Claude", "claude-sonnet-5", environment_variable="ANTHROPIC_API_KEY"
    ),
    "ollama": ProviderSpec(
        "Ollama", "", "http://127.0.0.1:11434/v1",
        requires_key=False, hosted_search=False, reasoning=False,
    ),
    "lmstudio": ProviderSpec(
        "LM Studio", "", "http://127.0.0.1:1234/v1", "LM_STUDIO_API_KEY",
        requires_key=False, hosted_search=False, reasoning=False,
    ),
}

# Kept as derived aliases for existing UI and third-party integrations.
PROVIDER_LABELS = {key: spec.label for key, spec in PROVIDER_SPECS.items()}
DEFAULT_ENDPOINTS = {
    key: spec.default_endpoint for key, spec in PROVIDER_SPECS.items() if spec.default_endpoint
}


@dataclass(frozen=True)
class ProviderSettings:
    provider: str
    api_key: str
    model: str
    endpoint: str = ""
    workspace_id: str = ""
    search_mode: str = "hosted"
    searxng_url: str = ""
    timeout: int = 60
    search: str = "low"
    reasoning: str = "low"
    output_cap: int = 2000
    evidence_urls: int = 3
    max_searches: int = 3
    searxng_results: int = 6
    allow_remote_endpoints: bool = False
    cancellation_callback: object = None

    @classmethod
    def from_mapping(cls, values):
        return cls(
            provider=values.get("provider", "openai"),
            api_key=values.get("api_key", ""),
            model=values.get("model", ""),
            endpoint=values.get("endpoint", ""),
            workspace_id=values.get("workspace_id", ""),
            search_mode=values.get("search_mode", "hosted"),
            searxng_url=values.get("searxng_url", ""),
            timeout=values.get("timeout", 60),
            search=values.get("search", "low"),
            reasoning=values.get("reasoning", "low"),
            output_cap=values.get("output_cap", 2000),
            evidence_urls=values.get("evidence_urls", 3),
            max_searches=values.get("max_searches", 3),
            searxng_results=values.get("searxng_results", 6),
            allow_remote_endpoints=values.get("allow_remote_endpoints", False),
            cancellation_callback=values.get("cancellation_callback"),
        )


def provider_spec(provider_id):
    try:
        return PROVIDER_SPECS[provider_id]
    except KeyError as exc:
        raise ProviderError("Unknown AI provider: %s" % provider_id) from exc


def sanitize_model_id(value):
    value = str(value or "").strip()
    if not is_model_id(value):
        raise ProviderError("The selected model identifier is invalid")
    return value


def model_id_for_discovery(value):
    """Supply a harmless constructor value before a local model is selected."""
    value = str(value or "").strip()
    return value if is_model_id(value) else "model-discovery"


def sanitize_model_list(values):
    return sorted({str(value).strip() for value in values if is_model_id(value)})


def sanitize_anthropic_workspace_id(value):
    value = str(value or "").strip()
    if value and not re.fullmatch(r"wrkspc_[A-Za-z0-9]{8,120}", value):
        raise ProviderError("The Anthropic workspace ID must start with 'wrkspc_'")
    return value


def resolve_anthropic_workspace_id(configured="", environment=None):
    """Prefer the process environment without persisting its value."""
    environment = os.environ if environment is None else environment
    return str(environment.get("ANTHROPIC_WORKSPACE_ID", "")).strip() or str(
        configured or ""
    ).strip()


def sanitize_anthropic_models(values):
    return sorted({
        str(value).strip() for value in values if is_anthropic_research_model(value)
    })


def create_provider(settings):
    settings = settings if isinstance(settings, ProviderSettings) else ProviderSettings.from_mapping(settings)
    spec = provider_spec(settings.provider)
    search_mode = "hosted" if spec.hosted_search and settings.search_mode == "hosted" else "searxng"
    searxng = None
    if search_mode == "searxng":
        searxng = SearXNGClient(
            settings.searxng_url,
            timeout=settings.timeout,
            result_limit=settings.searxng_results,
            allow_remote=settings.allow_remote_endpoints,
        )
    common = {
        "model": sanitize_model_id(settings.model),
        "timeout": settings.timeout,
        "reasoning_effort": settings.reasoning,
        "max_output_tokens": settings.output_cap,
        "evidence_url_limit": settings.evidence_urls,
        "searxng_client": searxng,
        "max_searches": settings.max_searches,
        "cancellation_callback": settings.cancellation_callback,
    }
    if settings.provider == "openai":
        return OpenAIProvider(
            settings.api_key,
            search_context_size=settings.search,
            search_mode=search_mode,
            **common,
        )
    if settings.provider == "anthropic":
        return AnthropicProvider(
            settings.api_key, search_mode=search_mode,
            workspace_id=sanitize_anthropic_workspace_id(settings.workspace_id),
            **common,
        )
    return LocalProvider(
        settings.provider,
        settings.endpoint or spec.default_endpoint,
        api_key=settings.api_key,
        allow_remote=settings.allow_remote_endpoints,
        **common,
    )
