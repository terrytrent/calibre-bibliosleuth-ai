"""Contract test against a real, disposable SearXNG service."""

import json
import os

import pytest

from bibliosleuth_ai.searxng import SearXNGClient


SEARXNG_URL = os.environ.get("BIBLIOSLEUTH_TEST_SEARXNG_URL")
pytestmark = pytest.mark.skipif(
    not SEARXNG_URL,
    reason="set BIBLIOSLEUTH_TEST_SEARXNG_URL to run the live SearXNG contract test",
)


def test_real_searxng_json_contract():
    client = SearXNGClient(SEARXNG_URL, timeout=30, result_limit=3)
    results = client.search("Calibre ebook management")

    if os.environ.get("BIBLIOSLEUTH_TEST_DEBUG") == "1":
        print("SearXNG returned %d normalized result(s):" % len(results))
        print(json.dumps(results, indent=2, ensure_ascii=False))

    assert isinstance(results, list)
    assert client.last_search_calls == 1
    assert len(results) <= 3
    assert all(set(item) == {"title", "url", "snippet"} for item in results)
    assert all(item["url"].startswith(("http://", "https://")) for item in results)
