"""Privacy-safe, bounded lookup timing history and statistical summaries."""

import csv
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import secrets
import statistics as std_statistics
import threading
import time
import uuid
from datetime import datetime, timezone

from .model_catalog import safe_model_id


TIMING_KEYS = (
    "queue_wait_seconds", "fingerprint_seconds", "cache_lookup_seconds",
    "epub_extraction_seconds", "openai_seconds", "validation_seconds",
    "retrieval_seconds", "review_wait_seconds", "apply_seconds",
)
USAGE_KEYS = (
    "input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens",
    "total_tokens", "web_search_calls", "estimated_cost_usd",
    "estimated_avoided_cost_usd",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def percentile(values, percentage):
    values = sorted(float(value) for value in values if value is not None)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * float(percentage) / 100.0
    lower = int(position); upper = min(len(values) - 1, lower + 1); fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def filter_records(records, period="all", model="all", preset="all", source="all", outcome="all", session_id=None, now=None):
    now = float(now or time.time())
    period_name = str(period).lower(); model_all = str(model).lower() == "all"; preset_all = str(preset).lower() == "all"
    source = str(source).lower(); outcome = str(outcome).lower()
    days = {"7 days": 7, "30 days": 30, "90 days": 90}.get(period_name)
    result = []
    for record in records:
        if period_name == "session" and record.get("session_id") != session_id: continue
        if days and float(record.get("timestamp_epoch", 0)) < now - days * 86400: continue
        if not model_all and record.get("model") != model: continue
        if not preset_all and record.get("preset") != preset: continue
        if source == "live" and record.get("cache_hit"): continue
        if source == "cache" and not record.get("cache_hit"): continue
        if outcome != "all" and record.get("outcome") != outcome: continue
        result.append(record)
    return result


def summarize(records):
    total = len(records)
    successful = [r for r in records if r.get("outcome") not in ("failed", "cancelled")]
    retrievals = [r.get("retrieval_seconds") for r in successful if r.get("retrieval_seconds") is not None]
    timing = {}
    for key in TIMING_KEYS:
        values = [float(r.get(key) or 0) for r in records if r.get(key) is not None]
        timing[key] = sum(values) / len(values) if values else None
    usage = {}
    for key in USAGE_KEYS:
        values = [r.get(key) for r in records if r.get(key) is not None]
        usage[key] = sum(values) if values else (None if "cost" in key else 0)
    return {
        "records": total,
        "successful": len(successful),
        "failed": sum(r.get("outcome") == "failed" for r in records),
        "cancelled": sum(r.get("outcome") == "cancelled" for r in records),
        "applied": sum(r.get("outcome") == "applied" for r in records),
        "skipped": sum(r.get("outcome") == "skipped" for r in records),
        "discarded": sum(r.get("outcome") == "discarded" for r in records),
        "live": sum(not r.get("cache_hit") for r in records),
        "cache_hits": sum(bool(r.get("cache_hit")) for r in records),
        "total_retrieval_seconds": sum(retrievals),
        "average_seconds": (sum(retrievals) / len(retrievals)) if retrievals else None,
        "median_seconds": std_statistics.median(retrievals) if retrievals else None,
        "fastest_seconds": min(retrievals) if retrievals else None,
        "slowest_seconds": max(retrievals) if retrievals else None,
        "p90_seconds": percentile(retrievals, 90),
        "p95_seconds": percentile(retrievals, 95),
        "books_per_minute": (len(retrievals) * 60 / sum(retrievals)) if retrievals and sum(retrievals) else None,
        "timing": timing,
        "usage": usage,
        "average_tokens": (usage["total_tokens"] / total) if total else None,
        "average_cost": (usage["estimated_cost_usd"] / total) if total and usage["estimated_cost_usd"] is not None else None,
        "tokens_per_success": (usage["total_tokens"] / len(successful)) if successful else None,
        "cost_per_success": (usage["estimated_cost_usd"] / len(successful)) if successful and usage["estimated_cost_usd"] is not None else None,
    }


def group_summaries(records, group_by):
    groups = {}
    for record in records:
        if group_by == "date": key = record.get("timestamp", "")[:10] or "unknown"
        elif group_by == "source": key = "Cache hit" if record.get("cache_hit") else "Live lookup"
        elif group_by == "batch_type": key = "Single book" if int(record.get("batch_size") or 1) == 1 else "Batch"
        else: key = str(record.get(group_by) or "unknown")
        groups.setdefault(key, []).append(record)
    return [(key, summarize(value)) for key, value in sorted(groups.items())]


class MetricsStore:
    VERSION = 1

    def __init__(self, path, max_records=1000, retention_days=90, enabled=True):
        self.path = os.fspath(path); self.max_records = max(1, int(max_records)); self.retention_days = max(1, int(retention_days))
        self.enabled = bool(enabled); self.session_id = uuid.uuid4().hex; self._lock = threading.RLock()
        self._defer_depth = 0; self._save_pending = False
        self._data = self._load()

    def _load(self):
        try:
            if os.path.getsize(self.path) > 8 * 1024 * 1024: raise ValueError("statistics file exceeds limit")
            with open(self.path, "r", encoding="utf-8") as stream: data = json.load(stream)
            if not isinstance(data, dict) or not isinstance(data.get("records"), list): raise ValueError("invalid statistics history")
            salt = data.get("salt")
            if not isinstance(salt, str) or len(salt) != 64:
                raise ValueError("invalid statistics salt")
            bytes.fromhex(salt)
            data["records"] = [record for record in data["records"] if isinstance(record, dict)]
            for record in data["records"]:
                record["model"] = safe_model_id(record.get("model"))
            return data
        except (OSError, ValueError, TypeError, AttributeError):
            return {"version": self.VERSION, "salt": secrets.token_hex(32), "records": []}

    def configure(self, enabled, max_records, retention_days):
        with self._lock:
            self.enabled = bool(enabled); self.max_records = max(1, int(max_records)); self.retention_days = max(1, int(retention_days))
            self._prune(); self._save()

    def anonymized_book_id(self, fingerprint):
        return hmac.new(bytes.fromhex(self._data["salt"]), str(fingerprint).encode("ascii", "ignore"), hashlib.sha256).hexdigest()[:16]

    def add(self, fingerprint, record):
        if not self.enabled: return None
        with self._lock:
            item = {key: value for key, value in record.items() if key in set(TIMING_KEYS + USAGE_KEYS) | {
                "model", "preset", "search_context", "reasoning", "front_matter_chars", "output_cap",
                "evidence_urls", "cache_hit", "outcome", "failure_category", "batch_size",
            }}
            item["model"] = safe_model_id(item.get("model"))
            item.update({"id": uuid.uuid4().hex, "book": self.anonymized_book_id(fingerprint), "timestamp": _utc_now(),
                         "timestamp_epoch": time.time(), "session_id": self.session_id})
            self._data["records"].append(item); self._prune(); self._save(); return item["id"]

    @contextmanager
    def batch(self):
        """Coalesce multiple record mutations into one atomic disk write."""
        with self._lock:
            self._defer_depth += 1
            try:
                yield self
            finally:
                self._defer_depth -= 1
                if self._defer_depth == 0 and self._save_pending:
                    self._save_pending = False
                    self._write()

    def update(self, record_id, **changes):
        allowed = set(TIMING_KEYS) | {"outcome", "failure_category"}
        with self._lock:
            for record in self._data["records"]:
                if record.get("id") == record_id:
                    record.update({key: value for key, value in changes.items() if key in allowed}); self._save(); return True
        return False

    def records(self):
        with self._lock: return json.loads(json.dumps(self._data["records"]))

    def get(self, record_id):
        with self._lock:
            record = next((item for item in self._data["records"] if item.get("id") == record_id), None)
            return json.loads(json.dumps(record)) if record is not None else None

    def clear(self):
        with self._lock:
            count = len(self._data["records"]); self._data["records"] = []; self._save(); return count

    def export_csv(self, path, records=None):
        records = records if records is not None else self.records()
        fields = ["timestamp", "book", "model", "preset", "cache_hit", "outcome", "failure_category", "batch_size"] + list(TIMING_KEYS) + list(USAGE_KEYS)
        with open(path, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(records)
        try: os.chmod(path, 0o600)
        except OSError: pass

    def _prune(self):
        cutoff = time.time() - self.retention_days * 86400
        valid = []
        for record in self._data["records"]:
            try:
                if float(record.get("timestamp_epoch", 0)) >= cutoff:
                    valid.append(record)
            except (TypeError, ValueError):
                continue
        self._data["records"] = valid[-self.max_records:]

    def _save(self):
        if self._defer_depth:
            self._save_pending = True
            return
        self._write()

    def _write(self):
        directory = os.path.dirname(self.path); os.makedirs(directory, exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as stream: json.dump(self._data, stream, separators=(",", ":"), sort_keys=True)
        try: os.chmod(temporary, 0o600)
        except OSError: pass
        os.replace(temporary, self.path)
