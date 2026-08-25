import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from .constants import FIELD_NAMES, MAX_PROMPT_CHARS, PROMPT_REVIEW_INSTRUCTIONS, PROMPT_VERSION, SCHEMA_VERSION
from .schema import METADATA_SCHEMA, PROMPT_REVIEW_SCHEMA, SchemaValidationError, validate_metadata, validate_prompt_review


class PromptValidationError(ValueError):
    pass


def prompt_digest(prompt):
    return hashlib.sha256((prompt or "").strip().encode("utf-8")).hexdigest()


def validation_matches_prompt(prompt, status):
    return bool(status) and status.get("prompt_hash") == prompt_digest(prompt)


@dataclass
class PromptValidationResult:
    accepted_prompt: str
    repaired: bool
    change_summary: str
    validation_timestamp: str
    prompt_hash: str
    validated_model: str
    prompt_version: str = PROMPT_VERSION
    schema_version: str = SCHEMA_VERSION


def local_prompt_issues(prompt):
    issues = []
    prompt = (prompt or "").strip()
    if not prompt:
        return ["The custom prompt is empty"]
    if len(prompt) > MAX_PROMPT_CHARS:
        issues.append("The custom prompt exceeds %d characters" % MAX_PROMPT_CHARS)
    lower = prompt.casefold()
    missing = [name for name in FIELD_NAMES if name not in lower]
    if missing:
        issues.append("Missing required field concepts: " + ", ".join(missing))
    for concept in ("confidence", "evidence", "inferred"):
        if concept not in lower:
            issues.append("Missing required concept: " + concept)
    return issues


def _review_message(prompt, local_issues):
    return json.dumps({
        "candidate_prompt": prompt,
        "local_issues": local_issues,
        "required_fields": list(FIELD_NAMES),
        "required_envelope": ["value", "confidence", "evidence_urls", "inferred"],
        "canonical_schema": METADATA_SCHEMA,
    }, ensure_ascii=False)


def _synthetic_input():
    return json.dumps({
        "opf": {"titles": ["The Example Book"], "authors": ["Ada Example"], "identifiers": ["9780000000002"], "publisher": "Example Press", "date": "2024"},
        "page_evidence": "Copyright 2024 Example Press. First EPUB edition. ISBN 978-0-00-000000-2.",
        "instruction": "This is synthetic evidence. Do not use web search.",
    })


def validate_and_repair_prompt(provider, prompt):
    prompt = (prompt or "").strip()
    issues = local_prompt_issues(prompt)
    review = validate_prompt_review(
        provider.structured_call(PROMPT_REVIEW_INSTRUCTIONS, _review_message(prompt, issues), PROMPT_REVIEW_SCHEMA, "prompt_review")
    )
    candidate = prompt
    repaired = False
    summary = review.get("change_summary", "")
    if issues or not review.get("valid"):
        candidate = (review.get("repaired_prompt") or "").strip()
        repaired = True
        if not candidate:
            raise PromptValidationError("The reviewer did not return a repaired prompt")
        remaining = local_prompt_issues(candidate)
        if remaining:
            raise PromptValidationError("Repaired prompt failed local validation: " + "; ".join(remaining))
    try:
        synthetic = provider.structured_call(candidate, _synthetic_input(), METADATA_SCHEMA, "prompt_synthetic_test")
        validate_metadata(synthetic)
    except (SchemaValidationError, Exception) as exc:
        if repaired:
            raise PromptValidationError("Repaired prompt failed its synthetic test: %s" % exc)
        second = validate_prompt_review(
            provider.structured_call(PROMPT_REVIEW_INSTRUCTIONS, _review_message(candidate, ["Synthetic schema test failed: %s" % exc]), PROMPT_REVIEW_SCHEMA, "prompt_repair")
        )
        candidate = (second.get("repaired_prompt") or "").strip()
        summary = second.get("change_summary", "")
        if not candidate or local_prompt_issues(candidate):
            raise PromptValidationError("AI repair did not produce a locally valid prompt")
        repaired = True
        try:
            validate_metadata(provider.structured_call(candidate, _synthetic_input(), METADATA_SCHEMA, "prompt_synthetic_test"))
        except Exception as final_exc:
            raise PromptValidationError("Repaired prompt failed its synthetic test: %s" % final_exc)
    return PromptValidationResult(
        accepted_prompt=candidate,
        repaired=repaired,
        change_summary=summary,
        validation_timestamp=datetime.now(timezone.utc).isoformat(),
        prompt_hash=prompt_digest(candidate),
        validated_model=getattr(provider, "model", "unknown"),
    )
