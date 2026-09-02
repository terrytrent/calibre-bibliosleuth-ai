import json

import pytest

from bibliosleuth_ai.searxng import SearXNGClient, SearXNGError, normalize_searxng_url, research_queries
from bibliosleuth_ai.provider_base import searxng_evidence
from tests.http_helpers import Response


def test_loopback_http_and_remote_https_policy():
    assert normalize_searxng_url("http://127.0.0.1:8080/") == "http://127.0.0.1:8080"
    assert normalize_searxng_url("https://search.example.test") == "https://search.example.test"
    with pytest.raises(SearXNGError, match="Plain HTTP"):
        normalize_searxng_url("http://search.example.test")
    with pytest.raises(SearXNGError, match="credentials"):
        normalize_searxng_url("https://user:secret@example.test")


def test_search_is_bounded_and_drops_unsafe_result_urls():
    captured = {}
    payload = {"results": [
        {"title": " Publisher   page ", "url": "https://publisher.example/book", "content": " useful   result "},
        {"title": "local", "url": "file:///etc/passwd", "content": "bad"},
        {"title": "credentials", "url": "https://user:secret@example.test/book", "content": "bad"},
    ]}
    def opener(request, timeout):
        captured["url"] = request.full_url
        return Response(json.dumps(payload).encode())
    client = SearXNGClient("http://localhost:8080", opener=opener)
    assert client.search(" an ISBN ") == [{"title": "Publisher page", "url": "https://publisher.example/book", "snippet": "useful result"}]
    assert "format=json" in captured["url"]
    assert client.last_search_calls == 1


def test_empty_valid_search_response_is_a_successful_connection():
    client = SearXNGClient(
        "http://localhost:8080", opener=lambda request, timeout: Response(b'{"results":[]}')
    )
    assert client.test_connection() is True


def test_queries_prioritize_identifier_then_title_author():
    queries = research_queries({"opf": {"titles": ["Example Book"], "authors": ["A. Writer"], "identifiers": ["978-1-2345-6789-0"]}})
    assert "9781234567890" in queries[0]
    assert "Example Book" in queries[1]


def test_partial_search_failure_reports_completed_calls_and_time():
    class PartialClient:
        last_search_calls = 0
        def search(self, query):
            if self.last_search_calls:
                raise SearXNGError("second query failed")
            self.last_search_calls += 1
            return []

    with pytest.raises(SearXNGError) as raised:
        searxng_evidence(PartialClient(), {
            "opf": {"identifiers": ["9781234567890"], "title": "Book"}
        }, 3)
    assert raised.value.completed_calls == 1
    assert raised.value.elapsed_seconds >= 0
