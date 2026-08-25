import re
import ipaddress
from datetime import date
from copy import deepcopy
from urllib.parse import urlparse

from .constants import FIELD_NAMES, MAX_PROMPT_CHARS, SCHEMA_VERSION


class SchemaValidationError(ValueError):
    pass


MAX_EVIDENCE_URLS = 10
MAX_URL_LENGTH = 2048
MAX_SHORT_TEXT = 1000
MAX_RATIONALE_LENGTH = 4000
MAX_COMMENTS_LENGTH = 30_000
MAX_AUTHORS = 50
MAX_TAGS = 100
MAX_IDENTIFIERS = 50


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


STRING_FIELD = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": _nullable({"type": "string", "maxLength": MAX_SHORT_TEXT}),
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "evidence_urls": {"type": "array", "items": {"type": "string", "maxLength": MAX_URL_LENGTH}, "maxItems": MAX_EVIDENCE_URLS},
        "inferred": {"type": "boolean"},
    },
    "required": ["value", "confidence", "evidence_urls", "inferred"],
}


def _array_field(item_schema, max_items):
    ans = dict(STRING_FIELD)
    ans["properties"] = dict(STRING_FIELD["properties"])
    ans["properties"]["value"] = _nullable({"type": "array", "items": item_schema, "maxItems": max_items})
    return ans


SERIES_VALUE = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"name": {"type": "string", "maxLength": MAX_SHORT_TEXT}, "index": _nullable({"type": "number", "minimum": 0, "maximum": 100000})},
    "required": ["name", "index"],
}

IDENTIFIER_VALUE = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "type": {"type": "string", "pattern": "^[a-z0-9][a-z0-9._-]{0,31}$"},
        "value": {"type": "string", "maxLength": 512},
    },
    "required": ["type", "value"],
}

FIELD_SCHEMAS = {
    "title": STRING_FIELD,
    "authors": _array_field({"type": "string", "maxLength": MAX_SHORT_TEXT}, MAX_AUTHORS),
    "series": dict(STRING_FIELD, properties=dict(STRING_FIELD["properties"], value=_nullable(SERIES_VALUE))),
    "tags": _array_field({"type": "string", "maxLength": MAX_SHORT_TEXT}, MAX_TAGS),
    "identifiers": _array_field(IDENTIFIER_VALUE, MAX_IDENTIFIERS),
    "published_date": STRING_FIELD,
    "publisher": STRING_FIELD,
    "comments": STRING_FIELD,
}
FIELD_SCHEMAS["comments"] = dict(
    STRING_FIELD,
    properties=dict(STRING_FIELD["properties"], value=_nullable({"type": "string", "maxLength": MAX_COMMENTS_LENGTH})),
)

METADATA_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "match": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "candidate_identity": {"type": "string", "maxLength": MAX_SHORT_TEXT},
                "edition_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "rationale": {"type": "string", "maxLength": MAX_RATIONALE_LENGTH},
            },
            "required": ["candidate_identity", "edition_confidence", "rationale"],
        },
        "fields": {
            "type": "object",
            "additionalProperties": False,
            "properties": FIELD_SCHEMAS,
            "required": list(FIELD_NAMES),
        },
    },
    "required": ["match", "fields"],
}

PROMPT_REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "valid": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string", "maxLength": MAX_SHORT_TEXT}, "maxItems": 100},
        "repaired_prompt": _nullable({"type": "string", "maxLength": MAX_PROMPT_CHARS}),
        "change_summary": {"type": "string", "maxLength": MAX_RATIONALE_LENGTH},
    },
    "required": ["valid", "issues", "repaired_prompt", "change_summary"],
}


def _is_url(value):
    try:
        parsed = urlparse(value)
        if len(value) > MAX_URL_LENGTH or parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        if parsed.username or parsed.password or parsed.hostname.casefold() in ("localhost", "localhost.localdomain"):
            return False
        try:
            address = ipaddress.ip_address(parsed.hostname.strip("[]"))
            if not address.is_global:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


def normalize_requested_fields(requested_fields=None):
    """Return a non-empty, canonical-order subset of metadata field names."""
    if requested_fields is None:
        return tuple(FIELD_NAMES)
    requested = set(requested_fields)
    unknown = requested.difference(FIELD_NAMES)
    if unknown:
        raise SchemaValidationError("unknown requested metadata field(s): %s" % ", ".join(sorted(unknown)))
    fields = tuple(name for name in FIELD_NAMES if name in requested)
    if not fields:
        raise SchemaValidationError("at least one metadata field must be requested")
    return fields


def metadata_schema(evidence_url_limit=MAX_EVIDENCE_URLS, requested_fields=None):
    limit = max(1, min(MAX_EVIDENCE_URLS, int(evidence_url_limit)))
    schema = deepcopy(METADATA_SCHEMA)
    requested = normalize_requested_fields(requested_fields)
    field_contract = schema["properties"]["fields"]
    field_contract["properties"] = {name: field_contract["properties"][name] for name in requested}
    field_contract["required"] = list(requested)
    fields = field_contract["properties"]
    for field in fields.values():
        field["properties"]["evidence_urls"]["maxItems"] = limit
    return schema


def validate_prompt_review(data):
    if not isinstance(data, dict) or set(data) != {"valid", "issues", "repaired_prompt", "change_summary"}:
        raise SchemaValidationError("prompt review contains missing or unexpected properties")
    if not isinstance(data["valid"], bool):
        raise SchemaValidationError("prompt review valid flag must be boolean")
    if not isinstance(data["issues"], list) or len(data["issues"]) > 100 or not all(
        isinstance(item, str) and len(item) <= MAX_SHORT_TEXT for item in data["issues"]
    ):
        raise SchemaValidationError("prompt review issues are invalid")
    repaired = data["repaired_prompt"]
    if repaired is not None and (not isinstance(repaired, str) or len(repaired) > MAX_PROMPT_CHARS):
        raise SchemaValidationError("prompt review repaired prompt is invalid")
    if not isinstance(data["change_summary"], str) or len(data["change_summary"]) > MAX_RATIONALE_LENGTH:
        raise SchemaValidationError("prompt review change summary is invalid")
    return data


def validate_metadata(data, evidence_url_limit=MAX_EVIDENCE_URLS, requested_fields=None):
    evidence_url_limit = max(1, min(MAX_EVIDENCE_URLS, int(evidence_url_limit)))
    requested_fields = normalize_requested_fields(requested_fields)
    errors = []
    if not isinstance(data, dict):
        raise SchemaValidationError("response must be an object")
    if set(data) != {"match", "fields"}:
        errors.append("response contains missing or unexpected properties")
    match = data.get("match")
    if not isinstance(match, dict):
        errors.append("match must be an object")
    else:
        if set(match) != {"candidate_identity", "edition_confidence", "rationale"}:
            errors.append("match contains missing or unexpected properties")
        for key in ("candidate_identity", "edition_confidence", "rationale"):
            if key not in match:
                errors.append("match.%s is required" % key)
        if match.get("edition_confidence") not in ("high", "medium", "low"):
            errors.append("match.edition_confidence is invalid")
        for key, limit in (("candidate_identity", MAX_SHORT_TEXT), ("rationale", MAX_RATIONALE_LENGTH)):
            if not isinstance(match.get(key), str) or len(match.get(key, "")) > limit:
                errors.append("match.%s is invalid or too long" % key)
    fields = data.get("fields")
    if not isinstance(fields, dict):
        errors.append("fields must be an object")
    else:
        if set(fields) != set(requested_fields):
            errors.append("fields contains missing or unexpected properties")
        for name in requested_fields:
            field = fields.get(name)
            if not isinstance(field, dict):
                errors.append("fields.%s must be an object" % name)
                continue
            if set(field) != {"value", "confidence", "evidence_urls", "inferred"}:
                errors.append("fields.%s contains missing or unexpected properties" % name)
            for key in ("value", "confidence", "evidence_urls", "inferred"):
                if key not in field:
                    errors.append("fields.%s.%s is required" % (name, key))
            if field.get("confidence") not in ("high", "medium", "low"):
                errors.append("fields.%s.confidence is invalid" % name)
            urls = field.get("evidence_urls")
            if not isinstance(urls, list) or any(not _is_url(url) for url in urls):
                errors.append("fields.%s.evidence_urls contains an invalid URL" % name)
            elif len(urls) > evidence_url_limit:
                errors.append("fields.%s.evidence_urls must contain at most %d URLs" % (name, evidence_url_limit))
            if not isinstance(field.get("inferred"), bool):
                errors.append("fields.%s.inferred must be boolean" % name)
            value = field.get("value")
            if name in ("authors", "tags") and value is not None and not (
                isinstance(value, list) and all(isinstance(x, str) for x in value)
            ):
                errors.append("fields.%s.value must be a string array or null" % name)
            elif name == "authors" and value is not None and (len(value) > MAX_AUTHORS or any(len(x) > MAX_SHORT_TEXT for x in value)):
                errors.append("fields.authors.value is too large")
            elif name == "tags" and value is not None and (len(value) > MAX_TAGS or any(len(x) > MAX_SHORT_TEXT for x in value)):
                errors.append("fields.tags.value is too large")
            if name == "identifiers" and value is not None and not (
                isinstance(value, list)
                and len(value) <= MAX_IDENTIFIERS
                and all(
                    isinstance(x, dict) and set(x) == {"type", "value"}
                    and isinstance(x.get("type"), str) and re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,31}", x["type"])
                    and isinstance(x.get("value"), str) and len(x["value"]) <= 512
                    for x in value
                )
            ):
                errors.append("fields.identifiers.value is invalid")
            if name == "series" and value is not None and not (
                isinstance(value, dict) and isinstance(value.get("name"), str)
                and set(value) == {"name", "index"} and len(value["name"]) <= MAX_SHORT_TEXT
                and (value.get("index") is None or (
                    isinstance(value.get("index"), (int, float)) and not isinstance(value.get("index"), bool)
                    and 0 <= value["index"] <= 100000
                ))
            ):
                errors.append("fields.series.value is invalid")
            if name in ("title", "published_date", "publisher", "comments") and value is not None and not isinstance(value, str):
                errors.append("fields.%s.value must be a string or null" % name)
            elif name in ("title", "publisher") and value is not None and len(value) > MAX_SHORT_TEXT:
                errors.append("fields.%s.value is too long" % name)
            elif name == "comments" and value is not None and len(value) > MAX_COMMENTS_LENGTH:
                errors.append("fields.comments.value is too long")
            elif name == "published_date" and not validate_iso_partial_date(value):
                errors.append("fields.published_date.value must be a valid ISO partial date")
    if errors:
        raise SchemaValidationError("; ".join(errors))
    return data


def schema_fingerprint():
    return SCHEMA_VERSION


def validate_iso_partial_date(value):
    if value is None:
        return True
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value):
        return False
    try:
        parts = [int(part) for part in value.split("-")]
        if len(parts) == 1:
            return 1 <= parts[0] <= 9999
        if len(parts) == 2:
            return 1 <= parts[0] <= 9999 and 1 <= parts[1] <= 12
        date(*parts)
        return True
    except ValueError:
        return False
