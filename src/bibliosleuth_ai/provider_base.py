"""Provider-neutral research contracts and bookkeeping."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time

from .constants import RESEARCH_GUARDRAIL
from .schema import metadata_schema, normalize_requested_fields, validate_metadata
from .searxng import collect_search_evidence


class ProviderError(RuntimeError):
    pass


class ProviderCancelled(ProviderError):
    pass


UNSUPPORTED_GENERATION_SCHEMA_KEYWORDS = frozenset({
    "$schema", "maxLength", "minLength", "pattern", "format",
    "maximum", "minimum", "exclusiveMaximum", "exclusiveMinimum",
    "multipleOf", "maxItems", "minItems", "uniqueItems",
    "maxProperties", "minProperties",
})


def compact_generation_schema(value):
    """Remove costly decoder constraints while canonical validation stays local."""
    if isinstance(value, dict):
        return {
            key: compact_generation_schema(item) for key, item in value.items()
            if key not in UNSUPPORTED_GENERATION_SCHEMA_KEYWORDS
        }
    if isinstance(value, list):
        return [compact_generation_schema(item) for item in value]
    return value


@dataclass(frozen=True)
class ResearchContext:
    evidence: dict
    requested_fields: tuple
    schema: dict
    instructions: str
    suspicious: bool
    evidence_url_limit: int


@dataclass
class ProviderUsage:
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    web_search_calls: int = 0
    hosted_web_search_calls: int = 0
    searxng_search_calls: int = 0

    def as_dict(self):
        return dict(vars(self))


@dataclass
class ProviderTimings:
    provider_seconds: float = 0.0
    search_seconds: float = 0.0
    validation_seconds: float = 0.0
    extra: dict = field(default_factory=dict)

    def as_dict(self):
        return {
            "provider_seconds": self.provider_seconds,
            "search_seconds": self.search_seconds,
            "validation_seconds": self.validation_seconds,
            **self.extra,
        }


class MetadataResearchProvider(ABC):
    @abstractmethod
    def research(self, local_book, system_prompt, requested_fields=None):
        raise NotImplementedError


def prepare_research(local_book, system_prompt, evidence_url_limit, requested_fields=None):
    requested = normalize_requested_fields(requested_fields)
    evidence = dict(local_book)
    suspicious = bool(evidence.pop("suspicious_instructions", None))
    scope = (
        "RUNTIME FIELD SCOPE (fixed by the application): Research and return exactly these metadata "
        "keys inside fields: %s. Do not return unrequested metadata keys. When series is requested, "
        "research both the series name and numeric series index; return both in series.value as defined "
        "by the supplied schema. The supplied strict schema overrides broader field lists in the research prompt."
    ) % ", ".join(requested)
    return ResearchContext(
        evidence=evidence,
        requested_fields=requested,
        schema=metadata_schema(evidence_url_limit, requested),
        instructions=system_prompt.rstrip() + "\n\n" + scope + "\n\n" + RESEARCH_GUARDRAIL,
        suspicious=suspicious,
        evidence_url_limit=int(evidence_url_limit),
    )


def ensure_not_cancelled(cancelled):
    if cancelled is not None and cancelled():
        raise ProviderCancelled("Research was cancelled")


def searxng_evidence(client, evidence, maximum, cancelled=None):
    if client is None:
        raise ProviderError("SearXNG is selected but no server is configured")
    previous_calls = client.last_search_calls
    started = time.perf_counter()
    try:
        searches = collect_search_evidence(
            client, evidence, maximum, cancelled=cancelled
        )
    except Exception as exc:
        exc.completed_calls = max(0, client.last_search_calls - previous_calls)
        exc.elapsed_seconds = time.perf_counter() - started
        raise
    return searches, client.last_search_calls - previous_calls, time.perf_counter() - started


def constrain_searxng_citations(raw, searches):
    """Keep only exact citations supplied by the application-managed search."""
    allowed = {
        result.get("url")
        for search in searches if isinstance(search, dict)
        for result in search.get("results", ()) if isinstance(result, dict)
        if isinstance(result.get("url"), str)
    }
    fields = raw.get("fields") if isinstance(raw, dict) else None
    if not isinstance(fields, dict):
        return raw
    for field in fields.values():
        if not isinstance(field, dict) or not isinstance(field.get("evidence_urls"), list):
            continue
        field["evidence_urls"] = [url for url in field["evidence_urls"] if url in allowed]
    return raw


def finalize_research(raw, context, started, search_seconds=0.0, extra_timings=None):
    request_finished = time.perf_counter()
    result = validate_metadata(raw, context.evidence_url_limit, context.requested_fields)
    timings = ProviderTimings(
        provider_seconds=request_finished - started,
        search_seconds=search_seconds,
        validation_seconds=time.perf_counter() - request_finished,
        extra=extra_timings or {},
    )
    if context.suspicious:
        result["_security_warning"] = (
            "Instruction-like text was detected in the EPUB. No fields are preselected; "
            "verify every value and source manually."
        )
        for metadata_field in result["fields"].values():
            metadata_field["confidence"] = "low"
    return result, timings.as_dict()


CONNECTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}
