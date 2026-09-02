"""Shared validation for provider model identifiers."""

import re


MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
ANTHROPIC_VERSION = re.compile(
    r"^claude-(opus|sonnet|haiku|fable|mythos)-(\d+)(?:-(\d+))?(?:-|$)"
)


def is_model_id(value):
    return bool(MODEL_ID.fullmatch(str(value or "").strip()))


def anthropic_model_version(value):
    match = ANTHROPIC_VERSION.match(str(value or "").strip().casefold())
    return (
        match.group(1), int(match.group(2)),
        int(match.group(3)) if match and match.group(3) is not None else None,
    ) if match else None


def is_anthropic_research_model(value):
    version = anthropic_model_version(value)
    if not version:
        return False
    family, major, minor = version
    if major >= 5:
        return True
    return bool(
        major == 4 and minor is not None and minor >= 5
        and family in ("opus", "sonnet", "haiku")
    )


def anthropic_supports_effort(value):
    version = anthropic_model_version(value)
    if not version:
        return False
    family, major, minor = version
    if major >= 5:
        return True
    return bool(
        major == 4 and minor is not None
        and ((family == "opus" and minor >= 5) or (family == "sonnet" and minor >= 6))
    )
