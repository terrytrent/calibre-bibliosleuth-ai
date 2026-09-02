import json
import time
import zipfile

from bibliosleuth_ai.diagnostic_journal import DiagnosticJournal, sanitize_diagnostic_text


def test_sanitizer_removes_keys_urls_and_home_paths():
    text = sanitize_diagnostic_text("Authorization: Bearer secret sk-abcdefghijk https://example.com /Users/person/book.epub")
    assert "secret" not in text
    assert "sk-abcdefghijk" not in text
    assert "https://example.com" not in text
    assert "/Users/person/book.epub" not in text


def test_journal_is_bounded_and_bundle_can_exclude_details(tmp_path):
    journal = DiagnosticJournal(tmp_path / "journal.json", max_entries=2, retention_days=7)
    for number in range(3):
        journal.add({
            "outcome": "failed", "stage": "epub", "provider": "anthropic",
            "search_provider": "searxng",
            "model": "model", "preset": "balanced",
            "batch_size": 1, "failed_books": 1,
            "failures": [{"anonymous_book": "abc", "category": "epub", "message": "error %d" % number,
                          "traceback": "trace", "epub_structure": {"member_count": 2}}],
        })
    assert len(journal.entries()) == 2
    assert {entry["provider"] for entry in journal.entries()} == {"anthropic"}
    assert {entry["search_provider"] for entry in journal.entries()} == {"searxng"}
    target = tmp_path / "bundle.zip"
    names = journal.export_zip(target, {"plugin_version": "test"}, include_details=False)
    assert set(names) == {"README.txt", "manifest.json", "environment.json", "recent-journal.json"}
    with zipfile.ZipFile(target) as archive:
        entries = json.loads(archive.read("recent-journal.json"))
        assert "message" not in entries[0]["failures"][0]
        assert json.loads(archive.read("manifest.json"))["automatic_upload"] is False


def test_clear_removes_journal_entries(tmp_path):
    journal = DiagnosticJournal(tmp_path / "journal.json")
    journal.add({"outcome": "success"})
    assert journal.clear() == 1
    assert journal.entries() == []


def test_legacy_entries_default_to_openai_provider(tmp_path):
    path = tmp_path / "journal.json"
    path.write_text(json.dumps({"version": 1, "entries": [{
        "timestamp_epoch": time.time(), "model": "gpt-test"
    }]}), encoding="utf-8")

    assert DiagnosticJournal(path).entries()[0]["provider"] == "openai"
