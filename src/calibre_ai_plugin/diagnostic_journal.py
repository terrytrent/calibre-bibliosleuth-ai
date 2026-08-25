"""Bounded, sanitized diagnostic history and local support-bundle export."""

import json
import os
import re
import time
import uuid
import zipfile
from datetime import datetime, timezone

from .model_catalog import safe_model_id


MAX_ENTRIES = 20
RETENTION_DAYS = 7
MAX_DETAIL_CHARS = 16_000


def sanitize_diagnostic_text(value):
    text = str(value or "")
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[REDACTED_API_KEY]", text)
    text = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"https?://\S+", "[REDACTED_URL]", text)
    home = os.path.expanduser("~")
    if home and home != "~": text = text.replace(home, "<HOME>")
    text = re.sub(r"(?i)\b[A-Z]:\\(?:Users\\)?[^\s\"']+", "[REDACTED_PATH]", text)
    text = re.sub(r"/(?:Users|home|private/var|tmp)/[^\s\"']+", "[REDACTED_PATH]", text)
    return text[:MAX_DETAIL_CHARS]


class DiagnosticJournal:
    def __init__(self, path, max_entries=MAX_ENTRIES, retention_days=RETENTION_DAYS):
        self.path = os.fspath(path); self.max_entries = max(1, int(max_entries)); self.retention_days = max(1, int(retention_days))
        self._data = self._load(); self._prune()

    def _load(self):
        try:
            if os.path.getsize(self.path) > 2 * 1024 * 1024: raise ValueError("diagnostic journal exceeds limit")
            with open(self.path, "r", encoding="utf-8") as stream: data = json.load(stream)
            if not isinstance(data, dict) or not isinstance(data.get("entries"), list): raise ValueError("invalid diagnostic journal")
            data["entries"] = [entry for entry in data["entries"] if isinstance(entry, dict)]
            for entry in data["entries"]:
                entry["model"] = safe_model_id(entry.get("model"))
            return data
        except (OSError, ValueError, TypeError, AttributeError):
            return {"version": 1, "entries": []}

    def add(self, summary):
        entry = {
            "id": uuid.uuid4().hex,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timestamp_epoch": time.time(),
            "outcome": str(summary.get("outcome") or "unknown")[:40],
            "stage": str(summary.get("stage") or "unknown")[:80],
            "model": safe_model_id(summary.get("model")),
            "preset": str(summary.get("preset") or "unknown")[:40],
            "batch_size": max(0, int(summary.get("batch_size") or 0)),
            "successful_books": max(0, int(summary.get("successful_books") or 0)),
            "failed_books": max(0, int(summary.get("failed_books") or 0)),
            "cancelled_books": max(0, int(summary.get("cancelled_books") or 0)),
            "usage": dict(summary.get("usage") or {}),
            "timing": dict(summary.get("timing") or {}),
            "failures": [],
        }
        for failure in list(summary.get("failures") or [])[:50]:
            entry["failures"].append({
                "anonymous_book": str(failure.get("anonymous_book") or "unavailable")[:32],
                "category": str(failure.get("category") or "other")[:80],
                "stage": str(failure.get("stage") or "unknown")[:80],
                "message": sanitize_diagnostic_text(failure.get("message")),
                "traceback": sanitize_diagnostic_text(failure.get("traceback")),
                "epub_structure": dict(failure.get("epub_structure") or {}),
            })
        self._data["entries"].append(entry); self._prune(); self._save(); return entry["id"]

    def entries(self):
        self._prune(); return json.loads(json.dumps(self._data["entries"]))

    def clear(self):
        count = len(self._data["entries"]); self._data["entries"] = []; self._save(); return count

    def export_zip(self, path, context, include_details=True):
        entries = self.entries()
        if not include_details:
            for entry in entries:
                for failure in entry.get("failures", []):
                    failure.pop("message", None); failure.pop("traceback", None)
        manifest = {
            "bundle_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
            "automatic_upload": False, "entry_count": len(entries),
            "detailed_errors_included": bool(include_details),
            "privacy": "No API keys, headers, titles, authors, paths, library IDs, EPUB text, prompts, responses, or evidence URLs.",
        }
        files = {
            "README.txt": (
                "BiblioSleuth AI diagnostic bundle\n\nThis archive was saved locally and was not uploaded automatically.\n"
                "Review its contents before sharing. Book identifiers are salted and anonymous.\n"
            ),
            "manifest.json": json.dumps(manifest, indent=2, sort_keys=True),
            "environment.json": json.dumps(context, indent=2, sort_keys=True),
            "recent-journal.json": json.dumps(entries, indent=2, sort_keys=True),
        }
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items(): archive.writestr(name, content.encode("utf-8"))
        try: os.chmod(path, 0o600)
        except OSError: pass
        return list(files)

    def _prune(self):
        cutoff = time.time() - self.retention_days * 86400
        valid = []
        for entry in self._data["entries"]:
            try:
                if float(entry.get("timestamp_epoch", 0)) >= cutoff:
                    valid.append(entry)
            except (TypeError, ValueError):
                continue
        self._data["entries"] = valid[-self.max_entries:]

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True); temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as stream: json.dump(self._data, stream, separators=(",", ":"), sort_keys=True)
        try: os.chmod(temporary, 0o600)
        except OSError: pass
        os.replace(temporary, self.path)
