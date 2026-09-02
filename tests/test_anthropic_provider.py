import json

import pytest

from bibliosleuth_ai.anthropic_provider import AnthropicProvider
from bibliosleuth_ai.constants import DEFAULT_SYSTEM_PROMPT, FIELD_NAMES
from bibliosleuth_ai.prompt_validation import validate_and_repair_prompt
from bibliosleuth_ai.provider_base import ProviderCancelled, ProviderError
from bibliosleuth_ai.schema import (
    METADATA_SCHEMA, SchemaValidationError, metadata_schema,
)
from tests.http_helpers import Response
from tests.test_schema import valid_result


def test_structured_call_uses_native_json_schema_and_effort():
    captured = {}

    def opener(request, timeout):
        captured.update(json.loads(request.data))
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps({"ok": True})}],
            "usage": {"input_tokens": 10, "output_tokens": 3},
        }).encode())

    provider = AnthropicProvider("secret", "claude-sonnet-4-6", opener=opener)
    assert provider.test_connection()
    assert captured["output_config"]["format"]["type"] == "json_schema"
    assert captured["output_config"]["format"]["schema"]["required"] == ["ok"]
    assert captured["output_config"]["effort"] == "low"
    assert provider.last_usage["total_tokens"] == 13


def test_workspace_id_is_sent_on_every_anthropic_request():
    captured = {}

    def opener(request, timeout):
        captured.update(dict(request.header_items()))
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps({"ok": True})}],
            "usage": {},
        }).encode())

    AnthropicProvider(
        "secret", "claude-sonnet-5", workspace_id="wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
        opener=opener,
    ).test_connection()
    assert captured["Anthropic-workspace-id"] == "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"


def test_unsupported_claude_model_omits_effort():
    captured = {}
    def opener(request, timeout):
        captured.update(json.loads(request.data))
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps({"ok": True})}],
            "usage": {},
        }).encode())
    AnthropicProvider("secret", "claude-3-5-sonnet-latest", opener=opener).test_connection()
    assert "effort" not in captured["output_config"]


def test_max_tokens_failure_retains_claude_usage():
    def opener(request, timeout):
        return Response(json.dumps({
            "content": [], "stop_reason": "max_tokens",
            "usage": {"input_tokens": 12, "output_tokens": 8},
        }).encode())
    provider = AnthropicProvider("secret", "claude-sonnet-4-6", opener=opener)
    with pytest.raises(Exception, match="output limit"):
        provider.test_connection()
    assert provider.last_usage["total_tokens"] == 20


def test_refusal_is_reported_directly_and_retains_usage():
    def opener(request, timeout):
        return Response(json.dumps({
            "content": [{"type": "text", "text": "refusal details"}],
            "stop_reason": "refusal",
            "usage": {"input_tokens": 12, "output_tokens": 3},
        }).encode())
    provider = AnthropicProvider("secret", "claude-sonnet-4-6", opener=opener)
    with pytest.raises(Exception, match="refused"):
        provider.test_connection()
    assert provider.last_usage["total_tokens"] == 15


def test_none_reasoning_omits_unsupported_anthropic_effort_value():
    captured = {}

    def opener(request, timeout):
        captured.update(json.loads(request.data))
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps({"ok": True})}],
            "usage": {},
        }).encode())

    AnthropicProvider(
        "secret", "claude-test", reasoning_effort="none", opener=opener
    ).test_connection()
    assert "effort" not in captured["output_config"]


def test_anthropic_generation_schema_is_compact_but_keeps_required_shape():
    original = json.dumps(METADATA_SCHEMA, sort_keys=True)
    transformed = AnthropicProvider._generation_schema(METADATA_SCHEMA)
    encoded = json.dumps(transformed, sort_keys=True)
    for keyword in ("maxLength", "maxItems", "minimum", "maximum", "pattern", "$schema"):
        assert '"%s"' % keyword not in encoded
    compact = json.dumps(transformed, separators=(",", ":"))
    assert "description" not in compact
    assert len(compact) < 4000
    assert transformed["required"] == ["match", "fields"]
    assert transformed["additionalProperties"] is False
    assert json.dumps(METADATA_SCHEMA, sort_keys=True) == original


def test_claude_hosted_search_then_uses_native_structured_output():
    payloads = []

    def opener(request, timeout):
        payload = json.loads(request.data)
        payloads.append(payload)
        if len(payloads) == 1:
            return Response(json.dumps({
                "content": [{
                    "type": "text",
                    "text": "Publisher evidence",
                    "citations": [{
                        "url": "https://example.test/book", "title": "Book",
                        "cited_text": "Edition evidence",
                    }],
                }, {
                    "type": "web_search_tool_result",
                    "content": [{"encrypted_content": "opaque-secret-search-state"}],
                }],
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "server_tool_use": {"web_search_requests": 2},
                },
            }).encode())
        result = valid_result()
        requested = payload["output_config"]["format"]["schema"]["properties"]["fields"]["required"]
        result["fields"] = {name: result["fields"][name] for name in requested}
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(result)}],
            "usage": {"input_tokens": 30, "output_tokens": 20},
        }).encode())

    provider = AnthropicProvider("secret", "claude-test", opener=opener)
    result = provider.research(
        {"opf": {"titles": ["Book"]}, "page_evidence": "edition"}, "prompt"
    )
    assert set(result["fields"]) == set(valid_result()["fields"])
    assert len(payloads) == 3
    assert payloads[0]["tools"][0]["type"].startswith("web_search_")
    assert payloads[0]["max_tokens"] == provider.hosted_research_min_tokens
    assert "output_config" not in payloads[0]
    assert payloads[1]["max_tokens"] == provider.max_output_tokens
    assert payloads[2]["max_tokens"] == provider.max_output_tokens
    generated_fields = [
        set(payload["output_config"]["format"]["schema"]["properties"]["fields"]["required"])
        for payload in payloads[1:]
    ]
    assert not generated_fields[0].intersection(generated_fields[1])
    assert set.union(*generated_fields) == set(valid_result()["fields"])
    assert payloads[1]["output_config"]["format"]["type"] == "json_schema"
    second_input = payloads[1]["messages"][0]["content"]
    assert "https://example.test/book" in second_input
    assert "opaque-secret-search-state" not in second_input
    assert len(second_input) < provider.max_research_chars + 2000
    assert provider.last_usage["hosted_web_search_calls"] == 2
    assert provider.last_usage["total_tokens"] == 130


def test_hosted_capability_test_verifies_actual_search_usage():
    calls = 0
    def opener(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Response(json.dumps({
                "content": [{"type": "text", "text": "Found the project."}],
                "usage": {
                    "input_tokens": 5,
                    "output_tokens": 2,
                    "server_tool_use": {"web_search_requests": 1},
                },
            }).encode())
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps({"ok": True})}],
            "usage": {"input_tokens": 3, "output_tokens": 1},
        }).encode())

    result = AnthropicProvider(
        "secret", "claude-sonnet-4-6", opener=opener
    ).test_capabilities()
    assert result["structured_output"] is True
    assert result["web_search"] is True
    assert result["reasoning"] is True


def _partial_result(payload, omit=None):
    result = valid_result()
    schema = payload["output_config"]["format"]["schema"]
    requested = schema["properties"]["fields"]["required"]
    result["fields"] = {
        name: result["fields"][name] for name in requested if name != omit
    }
    if "match" not in schema.get("required", ()):
        result.pop("match")
    return result


@pytest.mark.parametrize(("count", "expected_calls"), [
    (1, 1), (4, 1), (5, 2), (8, 2),
])
def test_claude_metadata_schema_split_boundaries(count, expected_calls):
    payloads = []

    def opener(request, timeout):
        payload = json.loads(request.data); payloads.append(payload)
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(_partial_result(payload))}],
            "usage": {"input_tokens": 2, "output_tokens": 1},
        }).encode())

    fields = FIELD_NAMES[:count]
    result = AnthropicProvider(
        "secret", "claude-sonnet-5", opener=opener
    ).structured_call("instructions", "input", metadata_schema(requested_fields=fields), "test")
    assert len(payloads) == expected_calls
    assert set(result["fields"]) == set(fields)


def test_second_claude_schema_chunk_failure_retains_first_chunk_usage_only():
    calls = 0

    def opener(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ProviderError("second chunk failed")
        payload = json.loads(request.data)
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(_partial_result(payload))}],
            "usage": {"input_tokens": 12, "output_tokens": 3},
        }).encode())

    provider = AnthropicProvider("secret", "claude-sonnet-5", opener=opener)
    with pytest.raises(ProviderError, match="second chunk"):
        provider.structured_call("instructions", "input", METADATA_SCHEMA, "test")
    assert provider.last_usage["input_tokens"] == 12
    assert provider.last_usage["output_tokens"] == 3
    assert provider.last_usage["total_tokens"] == 15


def test_cancellation_between_claude_schema_chunks_prevents_second_request():
    calls = 0

    def opener(request, timeout):
        nonlocal calls
        calls += 1
        payload = json.loads(request.data)
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(_partial_result(payload))}],
            "usage": {},
        }).encode())

    provider = AnthropicProvider(
        "secret", "claude-sonnet-5", opener=opener,
        cancellation_callback=lambda: calls == 1,
    )
    with pytest.raises(ProviderCancelled):
        provider.structured_call("instructions", "input", METADATA_SCHEMA, "test")
    assert calls == 1


class _FakeSearXNG:
    last_search_calls = 0

    def search(self, query):
        self.last_search_calls += 1
        return []


def test_claude_searxng_searches_once_then_splits_full_generation():
    payloads = []
    search = _FakeSearXNG()

    def opener(request, timeout):
        payload = json.loads(request.data); payloads.append(payload)
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(_partial_result(payload))}],
            "usage": {"input_tokens": 2, "output_tokens": 1},
        }).encode())

    result = AnthropicProvider(
        "secret", "claude-sonnet-5", search_mode="searxng",
        searxng_client=search, opener=opener,
    ).research({"opf": {"titles": ["Book"]}}, "prompt")
    assert len(payloads) == 2
    assert search.last_search_calls == 1
    assert set(result["fields"]) == set(FIELD_NAMES)


def test_missing_field_from_split_claude_result_is_rejected_after_merge():
    payloads = []
    search = _FakeSearXNG()

    def opener(request, timeout):
        payload = json.loads(request.data); payloads.append(payload)
        requested = payload["output_config"]["format"]["schema"]["properties"]["fields"]["required"]
        omit = requested[0] if len(payloads) == 2 else None
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(_partial_result(payload, omit))}],
            "usage": {},
        }).encode())

    provider = AnthropicProvider(
        "secret", "claude-sonnet-5", search_mode="searxng",
        searxng_client=search, opener=opener,
    )
    with pytest.raises(ProviderError, match="missing or unexpected"):
        provider.research({"opf": {"titles": ["Book"]}}, "prompt")


def test_unexpected_overlap_from_second_claude_chunk_is_rejected():
    calls = 0

    def opener(request, timeout):
        nonlocal calls
        calls += 1
        payload = json.loads(request.data)
        response = _partial_result(payload)
        if calls == 2:
            response["fields"][FIELD_NAMES[0]] = valid_result()["fields"][FIELD_NAMES[0]]
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(response)}],
            "usage": {},
        }).encode())

    with pytest.raises(ProviderError, match="missing or unexpected"):
        AnthropicProvider(
            "secret", "claude-sonnet-5", opener=opener
        ).structured_call("instructions", "input", METADATA_SCHEMA, "test")


def test_later_claude_chunks_reuse_first_match_without_regenerating_it():
    payloads = []

    def opener(request, timeout):
        payload = json.loads(request.data)
        payloads.append(payload)
        response = _partial_result(payload)
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(response)}],
            "usage": {},
        }).encode())

    result = AnthropicProvider(
        "secret", "claude-sonnet-5", opener=opener
    ).structured_call("instructions", "input", METADATA_SCHEMA, "test")
    assert result["match"]["candidate_identity"] == "Example"
    second_schema = payloads[1]["output_config"]["format"]["schema"]
    assert "match" not in second_schema["properties"]
    assert "match" not in second_schema["required"]
    assert "APPLICATION-SELECTED EDITION MATCH" in payloads[1]["messages"][0]["content"]
    assert '"candidate_identity": "Example"' in payloads[1]["messages"][0]["content"]


def test_wrong_field_type_after_claude_chunk_merge_is_locally_rejected():
    search = _FakeSearXNG()

    def opener(request, timeout):
        payload = json.loads(request.data)
        response = _partial_result(payload)
        if "authors" in response["fields"]:
            response["fields"]["authors"]["value"] = "Not an author array"
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(response)}],
            "usage": {},
        }).encode())

    provider = AnthropicProvider(
        "secret", "claude-sonnet-5", search_mode="searxng",
        searxng_client=search, opener=opener,
    )
    with pytest.raises(SchemaValidationError, match="string array"):
        provider.research({"opf": {"titles": ["Book"]}}, "prompt")


def test_claude_prompt_validation_splits_full_synthetic_schema():
    payloads = []

    def opener(request, timeout):
        payload = json.loads(request.data); payloads.append(payload)
        schema = payload["output_config"]["format"]["schema"]
        if "valid" in schema.get("properties", {}):
            response = {
                "valid": True, "issues": [], "repaired_prompt": None,
                "change_summary": "No changes",
            }
        else:
            response = _partial_result(payload)
        return Response(json.dumps({
            "content": [{"type": "text", "text": json.dumps(response)}],
            "usage": {},
        }).encode())

    result = validate_and_repair_prompt(
        AnthropicProvider("secret", "claude-sonnet-5", opener=opener),
        DEFAULT_SYSTEM_PROMPT,
    )
    assert result.repaired is False
    assert len(payloads) == 3
