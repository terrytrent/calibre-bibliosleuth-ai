from bibliosleuth_ai.lookup_cache import SessionLookupCache, epub_file_signature, epub_fingerprint, research_cache_key


def settings(**updates):
    value = {
        "model": "model", "search": "low", "front": 6000, "reasoning": "low",
        "output_cap": 2000, "evidence_urls": 3, "prompt": "prompt",
    }
    value.update(updates)
    return value


def test_epub_fingerprint_changes_with_content(tmp_path):
    path = tmp_path / "book.epub"
    path.write_bytes(b"one")
    first = epub_fingerprint(path)
    path.write_bytes(b"two")
    assert epub_fingerprint(path) != first


def test_file_signature_changes_with_size(tmp_path):
    path = tmp_path / "book.epub"; path.write_bytes(b"one")
    first = epub_file_signature(path); path.write_bytes(b"longer")
    assert first != epub_file_signature(path)


def test_cache_key_covers_research_inputs_but_not_control_flags():
    first = research_cache_key("fingerprint", settings(force_refresh=False))
    assert research_cache_key("fingerprint", settings(force_refresh=True)) == first
    assert research_cache_key("fingerprint", settings(model="other")) != first
    assert research_cache_key("other", settings()) != first
    assert research_cache_key("fingerprint", settings(requested_fields=["comments"])) != first
    assert research_cache_key("fingerprint", settings(requested_fields=["comments", "authors"])) == research_cache_key(
        "fingerprint", settings(requested_fields=["authors", "comments"])
    )


def test_cache_is_copying_bounded_lru():
    cache = SessionLookupCache(max_entries=2)
    original = {"value": [1]}
    cache.put("a", original)
    original["value"].append(2)
    assert cache.get("a") == {"value": [1]}
    returned = cache.get("a"); returned["value"].append(3)
    assert cache.get("a") == {"value": [1]}
    cache.put("b", {"value": 2}); cache.put("c", {"value": 3})
    assert cache.get("a") is None
    assert cache.clear() == 2
    assert len(cache) == 0


def test_cache_contains_does_not_return_or_mutate_value():
    cache = SessionLookupCache()
    assert not cache.contains("book")
    cache.put("book", {"value": 1})
    assert cache.contains("book")
