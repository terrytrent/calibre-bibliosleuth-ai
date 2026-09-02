import csv
import json
import os

from bibliosleuth_ai.metrics import (
    MetricsStore, build_lookup_record, filter_records, group_summaries, percentile,
    summarize,
)


def sample(seconds=10, outcome="applied", cache=False, preset="balanced"):
    return {
        "timestamp": "2026-08-20T12:00:00+00:00", "timestamp_epoch": 1_787_228_800,
        "session_id": "session", "model": "model", "preset": preset,
        "cache_hit": cache, "outcome": outcome, "retrieval_seconds": seconds,
        "provider_seconds": 0 if cache else seconds - 1, "total_tokens": 100,
        "estimated_cost_usd": 0 if cache else 0.01, "batch_size": 2,
    }


def test_summary_percentiles_timing_and_cost():
    records = [sample(10), sample(20), sample(30, cache=True), sample(5, outcome="failed")]
    result = summarize(records)
    assert result["records"] == 4
    assert result["successful"] == 3
    assert result["failed"] == 1
    assert result["median_seconds"] == 20
    assert result["p90_seconds"] == 28
    assert result["cache_hits"] == 1
    assert result["usage"]["estimated_cost_usd"] == 0.03  # failed API work can still incur usage
    assert percentile([1, 2, 3], 95) == 2.9


def test_filters_and_grouping():
    records = [sample(preset="economy"), sample(cache=True), sample(outcome="failed")]
    for record in records: record["session_id"] = "current"
    assert len(filter_records(records, period="session", session_id="current")) == 3
    assert len(filter_records(records, period="Session", model="All", preset="All", source="All", outcome="All", session_id="current")) == 3
    assert len(filter_records(records, source="cache")) == 1
    assert len(filter_records(records, outcome="failed")) == 1
    assert {name for name, _ in group_summaries(records, "preset")} == {"balanced", "economy"}


def test_provider_filter_and_search_grouping():
    openai = sample(); openai.update({"provider": "openai", "search_provider": "hosted"})
    local = sample(); local.update({"provider": "ollama", "search_provider": "searxng"})
    assert filter_records([openai, local], provider="ollama") == [local]
    assert {name for name, _ in group_summaries([openai, local], "search_provider")} == {"hosted", "searxng"}


def test_mixed_known_and_unknown_cost_is_not_presented_as_a_total():
    known = sample()
    unknown = sample(); unknown["estimated_cost_usd"] = None
    result = summarize([known, unknown])
    assert result["usage"]["estimated_cost_usd"] is None
    assert result["known_cost_records"] == 1
    assert result["unknown_cost_records"] == 1


def test_lookup_record_builder_normalizes_completed_and_cancelled_records():
    payload = {
        "model": "claude-test", "provider": "anthropic", "search_mode": "searxng",
        "batch_size": 3,
        "metrics_context": {
            "preset": "balanced", "search": "medium", "reasoning": "low",
            "front": 12000, "output_cap": 2000, "evidence_urls": 3,
        },
    }
    detail = {
        "cache_hit": True, "total_tokens": 42, "estimated_cost_usd": 0.01,
        "_timing": {"provider_seconds": 1.25}, "ignored": "private",
    }
    ready = build_lookup_record(payload, detail, outcome="ready")
    assert ready == {
        "model": "claude-test", "provider": "anthropic", "search_provider": "searxng",
        "preset": "balanced", "search_context": "medium", "reasoning": "low",
        "front_matter_chars": 12000, "output_cap": 2000, "evidence_urls": 3,
        "cache_hit": True, "outcome": "ready", "failure_category": "",
        "batch_size": 3, "provider_seconds": 1.25, "total_tokens": 42,
        "estimated_cost_usd": 0.01,
    }
    cancelled = build_lookup_record(
        payload, {"estimated_cost_usd": 0.0}, outcome="cancelled",
        failure_category="user_cancelled", cache_hit=False,
    )
    assert cancelled["outcome"] == "cancelled"
    assert cancelled["failure_category"] == "user_cancelled"
    assert cancelled["cache_hit"] is False
    assert cancelled["estimated_cost_usd"] == 0.0


def test_store_is_bounded_anonymized_updateable_and_exportable(tmp_path):
    path = tmp_path / "metrics.json"
    store = MetricsStore(path, max_records=2, retention_days=99999)
    first = store.add("secret-fingerprint", sample())
    store.add("second", sample(20)); store.add("third", sample(30))
    records = store.records()
    assert len(records) == 2
    assert all("secret-fingerprint" not in str(record) for record in records)
    assert store.update(first, outcome="skipped") is False  # pruned
    current = records[-1]["id"]
    assert store.update(current, outcome="applied", apply_seconds=0.2)
    export = tmp_path / "metrics.csv"; store.export_csv(export)
    with export.open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2 and "title" not in rows[0]
    assert store.clear() == 2


def test_disabled_store_does_not_record(tmp_path):
    store = MetricsStore(tmp_path / "metrics.json", enabled=False)
    assert store.add("fingerprint", sample()) is None
    assert store.records() == []


def test_batch_coalesces_writes_and_gets_one_record(tmp_path, monkeypatch):
    store = MetricsStore(tmp_path / "metrics.json", max_records=10, retention_days=99999)
    writes = []
    original = store._write
    monkeypatch.setattr(store, "_write", lambda: (writes.append(True), original())[1])
    with store.batch():
        first = store.add("one", sample())
        store.add("two", sample())
    assert len(writes) == 1
    assert store.get(first)["model"] == "model"


def test_export_is_private_and_corrupt_history_is_ignored(tmp_path):
    path = tmp_path / "metrics.json"
    path.write_text('{"salt":"bad","records":[{"timestamp_epoch":"bad"}]}')
    store = MetricsStore(path, retention_days=99999)
    assert store.records() == []
    store.add("one", sample())
    export = tmp_path / "metrics.csv"; store.export_csv(export)
    if os.name == "posix":
        assert export.stat().st_mode & 0o077 == 0


def test_legacy_openai_timing_is_normalized_on_load(tmp_path):
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps({
        "version": 1,
        "salt": "00" * 32,
        "records": [{"model": "gpt-test", "openai_seconds": 1.25}],
    }))
    record = MetricsStore(path, retention_days=99999).records()[0]
    assert record["provider_seconds"] == 1.25
    assert "openai_seconds" not in record
