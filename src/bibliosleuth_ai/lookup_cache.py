"""Bounded, process-local cache for successful metadata research results."""

import copy
import hashlib
import json
import threading
import os
from collections import OrderedDict

from .constants import FIELD_NAMES


def epub_fingerprint(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def epub_file_signature(path):
    status = os.stat(path)
    return (int(status.st_size), int(status.st_mtime_ns))


def research_cache_key(fingerprint, settings):
    material = {
        "epub": fingerprint,
        "provider": settings.get("provider", "openai"),
        "model": settings["model"],
        "endpoint": str(settings.get("endpoint") or "").strip().rstrip("/") or None,
        "allow_remote_endpoints": bool(settings.get("allow_remote_endpoints", False)),
        "search_mode": settings.get("search_mode", "hosted"),
        "searxng_url": settings.get("searxng_url") if settings.get("search_mode") == "searxng" else None,
        "searxng_results": settings.get("searxng_results"),
        "max_searches": settings.get("max_searches"),
        "search": settings["search"],
        "front": settings["front"],
        "reasoning": settings["reasoning"],
        "output_cap": settings["output_cap"],
        "evidence_urls": settings["evidence_urls"],
        "prompt": settings["prompt"],
        "requested_fields": sorted(settings.get("requested_fields") or FIELD_NAMES),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class SessionLookupCache:
    def __init__(self, max_entries=128):
        self.max_entries = max(1, int(max_entries))
        self._items = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key):
        with self._lock:
            value = self._items.get(key)
            if value is None:
                return None
            self._items.move_to_end(key)
            return copy.deepcopy(value)

    def put(self, key, value):
        with self._lock:
            self._items[key] = copy.deepcopy(value)
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def clear(self):
        with self._lock:
            count = len(self._items)
            self._items.clear()
            return count

    def contains(self, key):
        with self._lock:
            return key in self._items

    def __len__(self):
        with self._lock:
            return len(self._items)


SESSION_LOOKUP_CACHE = SessionLookupCache()
