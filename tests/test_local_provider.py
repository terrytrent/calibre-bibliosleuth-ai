import json

import pytest

from bibliosleuth_ai.local_provider import LocalProvider
from bibliosleuth_ai.provider_base import ProviderCancelled
from bibliosleuth_ai.searxng import SearXNGError
from tests.http_helpers import Response
from tests.test_schema import valid_result


class Search:
    last_search_calls = 0
    def search(self, query):
        self.last_search_calls += 1
        return [{"title": "Source", "url": "https://example.test", "snippet": "edition"}]
    def test_connection(self): return True


class FailingSearch:
    last_search_calls = 0
    def search(self, query):
        raise SearXNGError("search failed")


def test_local_provider_uses_chat_schema_and_searxng_evidence():
    captured = {}
    def opener(request, timeout):
        captured.update(json.loads(request.data))
        return Response(json.dumps({
            "choices": [{"message": {"content": json.dumps(valid_result())}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }).encode())
    provider = LocalProvider("ollama", "http://127.0.0.1:11434/v1", "qwen", opener=opener, searxng_client=Search())
    result = provider.research({"opf": {"titles": ["Book"], "identifiers": ["9781234567890"]}}, "prompt")
    assert set(result["fields"]) == set(valid_result()["fields"])
    assert captured["response_format"]["type"] == "json_schema"
    assert "SearXNG results" in captured["messages"][1]["content"]
    assert provider.last_usage["searxng_search_calls"] == 2


def test_local_provider_discards_citations_not_returned_by_searxng():
    raw = valid_result()
    raw["fields"]["title"]["evidence_urls"] = [
        "Source 1", "https://invented.example/book", "https://example.test",
    ]

    def opener(request, timeout):
        return Response(json.dumps({
            "choices": [{"message": {"content": json.dumps(raw)}}],
            "usage": {},
        }).encode())

    provider = LocalProvider(
        "ollama", "http://127.0.0.1:11434/v1", "qwen",
        opener=opener, searxng_client=Search(),
    )
    result = provider.research({"opf": {"titles": ["Book"]}}, "prompt")
    assert result["fields"]["title"]["evidence_urls"] == ["https://example.test"]


def test_failed_search_cannot_reuse_previous_local_usage():
    provider = LocalProvider(
        "ollama", "http://127.0.0.1:11434/v1", "qwen",
        searxng_client=FailingSearch(), opener=lambda *_args, **_kwargs: None,
    )
    provider.last_usage = {"total_tokens": 999}
    with pytest.raises(SearXNGError, match="search failed"):
        provider.research({"opf": {"titles": ["Book"]}}, "prompt")
    assert provider.last_usage == {}


def test_invalid_local_output_retains_reported_usage():
    def opener(request, timeout):
        return Response(json.dumps({
            "choices": [{"message": {"content": "not json"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        }).encode())
    provider = LocalProvider(
        "ollama", "http://127.0.0.1:11434/v1", "qwen", opener=opener,
    )
    with pytest.raises(Exception, match="invalid structured output"):
        provider.test_connection()
    assert provider.last_usage["total_tokens"] == 20


@pytest.mark.parametrize("provider_id", ["ollama", "lmstudio"])
def test_invalid_local_output_retains_completed_searxng_usage(provider_id):
    search = Search()

    def opener(request, timeout):
        return Response(json.dumps({
            "choices": [{"message": {"content": ""}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        }).encode())

    provider = LocalProvider(
        provider_id, "http://127.0.0.1:1234/v1", "qwen",
        opener=opener, searxng_client=search,
    )
    with pytest.raises(Exception, match="invalid structured output"):
        provider.research({
            "opf": {"titles": ["Book"], "identifiers": ["9781234567890"]}
        }, "prompt")
    assert provider.last_usage["total_tokens"] == 20
    assert provider.last_usage["web_search_calls"] == 2
    assert provider.last_usage["searxng_search_calls"] == 2
    assert provider.last_usage["hosted_web_search_calls"] == 0
    assert provider.last_timings["search_seconds"] >= 0


def test_cancellation_after_search_prevents_local_model_request():
    checks = iter((False, True))
    model_called = []
    provider = LocalProvider(
        "ollama", "http://127.0.0.1:11434/v1", "qwen",
        searxng_client=Search(), cancellation_callback=lambda: next(checks),
        opener=lambda *args, **kwargs: model_called.append(True),
    )
    with pytest.raises(ProviderCancelled):
        provider.research({"opf": {"titles": ["Book"]}}, "prompt")
    assert model_called == []
    assert provider.last_request_started is False
    assert provider.last_usage["searxng_search_calls"] == 1


def test_ollama_disables_default_thinking_for_bounded_structured_output():
    captured = {}

    def opener(request, timeout):
        captured.update(json.loads(request.data))
        return Response(json.dumps({
            "choices": [{"message": {"content": '{"ok":true}'}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        }).encode())

    provider = LocalProvider(
        "ollama", "http://127.0.0.1:11434/v1", "qwen3:0.6b", opener=opener,
    )
    assert provider.test_connection() is True
    assert captured["reasoning_effort"] == "none"


def test_lmstudio_receives_compact_generation_schema():
    captured = {}

    def opener(request, timeout):
        captured.update(json.loads(request.data))
        return Response(json.dumps({
            "choices": [{"message": {"content": '{"ok":true}'}}],
            "usage": {},
        }).encode())

    provider = LocalProvider(
        "lmstudio", "http://127.0.0.1:1234/v1", "qwen", opener=opener,
    )
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean", "maxLength": 10}},
        "required": ["ok"],
    }
    assert provider.structured_call("Return JSON", "test", schema, "test") == {"ok": True}
    sent = captured["response_format"]["json_schema"]["schema"]
    assert sent["properties"]["ok"] == {"type": "boolean"}
