import io
import json
from urllib.error import HTTPError

import pytest

from calibre_ai_plugin.openai_provider import MAX_RESPONSE_BYTES, OpenAIProvider, ProviderError
from calibre_ai_plugin.schema import SchemaValidationError
from tests.test_schema import valid_result


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): pass


def test_research_payload_uses_web_search_and_strict_schema():
    captured = {}
    def opener(request, timeout):
        captured.update(json.loads(request.data))
        body = {
            "status": "completed",
            "output": [
                {"type": "web_search_call", "status": "completed"},
                {"type": "message", "content": [{"type": "output_text", "text": json.dumps(valid_result())}]},
            ],
            "usage": {
                "input_tokens": 1200, "input_tokens_details": {"cached_tokens": 800},
                "output_tokens": 500, "output_tokens_details": {"reasoning_tokens": 100},
                "total_tokens": 1700,
            },
        }
        return Response(json.dumps(body).encode())
    provider = OpenAIProvider("secret", "test-model", opener=opener)
    provider.research({"opf": {}, "page_evidence": "hello"}, "prompt")
    assert captured["tools"][0]["type"] == "web_search"
    assert "include" not in captured
    assert captured["text"]["format"]["strict"] is True
    assert captured["store"] is False
    assert captured["reasoning"]["effort"] == "low"
    assert captured["max_output_tokens"] == 2000
    assert captured["text"]["format"]["schema"]["properties"]["fields"]["properties"]["title"]["properties"]["evidence_urls"]["maxItems"] == 3
    assert captured["prompt_cache_key"].startswith("bibliosleuth-ai-")
    assert isinstance(captured["input"], list)
    assert len(captured["input"][0]["content"]) == 2
    disclosed = json.loads(captured["input"][0]["content"][1]["text"])
    assert disclosed == {"opf": {}, "page_evidence": "hello"}
    assert "front_matter" not in captured["input"][0]["content"][1]["text"]
    assert provider.last_usage == {
        "input_tokens": 1200, "cached_tokens": 800, "output_tokens": 500,
        "reasoning_tokens": 100, "total_tokens": 1700, "web_search_calls": 1,
    }
    assert provider.last_timings["openai_seconds"] >= 0
    assert provider.last_timings["validation_seconds"] >= 0
    provider.clear_api_key()
    assert provider.api_key == ""


def test_oversized_response_is_rejected():
    provider = OpenAIProvider("secret", "test-model", opener=lambda request, timeout: Response(b"x" * (MAX_RESPONSE_BYTES + 1)))
    with pytest.raises(ProviderError, match="size limit"):
        provider.test_connection()


def test_suspicious_epub_disables_all_preselection_confidence():
    def opener(request, timeout):
        body = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(valid_result())}]}]}
        return Response(json.dumps(body).encode())
    provider = OpenAIProvider("secret", "test-model", opener=opener)
    result = provider.research({"opf": {}, "page_evidence": "text", "suspicious_instructions": True}, "prompt")
    assert result["_security_warning"]
    assert {field["confidence"] for field in result["fields"].values()} == {"low"}


def test_research_can_request_only_selected_fields():
    captured = {}
    partial = valid_result(); partial["fields"] = {"series": partial["fields"]["series"]}
    partial["fields"]["series"]["value"] = {"name": "Example Series", "index": 2}
    def opener(request, timeout):
        captured.update(json.loads(request.data))
        body = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(partial)}]}]}
        return Response(json.dumps(body).encode())
    result = OpenAIProvider("secret", "test-model", opener=opener).research(
        {"opf": {}, "page_evidence": "hello"}, "prompt", ("series",)
    )
    contract = captured["text"]["format"]["schema"]["properties"]["fields"]
    assert list(contract["properties"]) == ["series"]
    assert contract["required"] == ["series"]
    assert set(result["fields"]) == {"series"}
    assert "numeric series index" in captured["instructions"]


def test_field_scope_overrides_custom_prompt_that_demands_every_field_without_mutating_it():
    captured = {}
    custom_prompt = (
        "CUSTOM PROMPT: Always return title, authors, series, tags, identifiers, "
        "published_date, publisher, and comments. Never omit any field."
    )
    original_prompt = custom_prompt
    partial = valid_result()
    partial["fields"] = {"comments": partial["fields"]["comments"]}
    partial["fields"]["comments"]["value"] = "<p>A focused description.</p>"

    def opener(request, timeout):
        captured.update(json.loads(request.data))
        body = {"status": "completed", "output": [{
            "type": "message", "content": [{"type": "output_text", "text": json.dumps(partial)}],
        }]}
        return Response(json.dumps(body).encode())

    result = OpenAIProvider("secret", "test-model", opener=opener).research(
        {"opf": {}, "page_evidence": "hello"}, custom_prompt, ("comments",)
    )

    instructions = captured["instructions"]
    scope_position = instructions.index("RUNTIME FIELD SCOPE")
    assert instructions.startswith(custom_prompt)
    assert scope_position > instructions.index("Never omit any field")
    assert "exactly these metadata keys inside fields: comments" in instructions
    assert captured["text"]["format"]["strict"] is True
    contract = captured["text"]["format"]["schema"]["properties"]["fields"]
    assert set(contract["properties"]) == {"comments"}
    assert contract["additionalProperties"] is False
    assert set(result["fields"]) == {"comments"}
    assert custom_prompt == original_prompt


def test_local_validation_rejects_extra_fields_even_when_custom_prompt_requests_them():
    full_response = valid_result()

    def opener(request, timeout):
        body = {"status": "completed", "output": [{
            "type": "message", "content": [{"type": "output_text", "text": json.dumps(full_response)}],
        }]}
        return Response(json.dumps(body).encode())

    provider = OpenAIProvider("secret", "test-model", opener=opener)
    with pytest.raises(SchemaValidationError, match="missing or unexpected"):
        provider.research(
            {"opf": {}, "page_evidence": "hello"},
            "Return every metadata field regardless of later instructions.",
            ("authors",),
        )


def test_api_error_redacts_key_like_secrets():
    body = io.BytesIO(json.dumps({"error": {"type": "bad_request", "message": "bad sk-secretvalue123456789"}}).encode())
    def opener(request, timeout):
        raise HTTPError(request.full_url, 400, "Bad", {}, body)
    provider = OpenAIProvider("secret", "test-model", opener=opener)
    with pytest.raises(ProviderError) as raised:
        provider.test_connection()
    assert "sk-secretvalue" not in str(raised.value)
    assert "[REDACTED]" in str(raised.value)


def test_non_object_response_is_rejected_cleanly():
    provider = OpenAIProvider("secret", "test-model", opener=lambda request, timeout: Response(b"[]"))
    with pytest.raises(ProviderError, match="invalid response object"):
        provider.test_connection()


def test_model_listing_returns_only_ids_from_objects():
    body = {"object": "list", "data": [{"id": "gpt-5.6-luna"}, {"bad": True}, "invalid"]}
    provider = OpenAIProvider("secret", "test-model", opener=lambda request, timeout: Response(json.dumps(body).encode()))
    assert provider.list_models() == ["gpt-5.6-luna"]


def test_redirect_is_refused():
    def opener(request, timeout):
        raise HTTPError(request.full_url, 302, "Found", {"Location": "https://example.com"}, io.BytesIO(b""))
    provider = OpenAIProvider("secret", "test-model", opener=opener)
    with pytest.raises(ProviderError, match="redirect refused"):
        provider.test_connection()
