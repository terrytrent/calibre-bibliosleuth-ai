"""Small, credential-free update manifest client and scheduling policy."""

import json
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


UPDATE_MANIFEST_URL = "https://bibliosleuthai-updates.trentathome.xyz/latest.json"
UPDATE_MANIFEST_HOST = "bibliosleuthai-updates.trentathome.xyz"
UPDATE_MANIFEST_PATH = "/latest.json"
RELEASE_TAG_BASE = "https://github.com/terrytrent/calibre-bibliosleuth-ai/releases/tag/v"
UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
UPDATE_REMINDER_SECONDS = 24 * 60 * 60
UPDATE_TIMEOUT_SECONDS = 5
UPDATE_RESPONSE_LIMIT = 4096

_SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
_UTC_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_MANIFEST_KEYS = {
    "schema", "product", "channel", "version", "published", "minimum_calibre",
    "changelog",
}
_CHANGELOG_KEYS = {"summary", "items"}
_CHANGELOG_ITEM_KEYS = {"category", "text"}
_CHANGELOG_CATEGORIES = {
    "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security",
}
_UNSAFE_CHANGELOG_TEXT = re.compile(r"[\x00-\x1f\x7f<>]|(?:https?://|www\.)", re.IGNORECASE)


class UpdateCheckError(RuntimeError):
    """A safe, user-facing update check failure without response details."""


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class ChangelogItem:
    category: str
    text: str


@dataclass(frozen=True)
class ReleaseChangelog:
    summary: str
    items: tuple


@dataclass(frozen=True)
class UpdateManifest:
    version: str
    published: str
    minimum_calibre: str
    changelog: ReleaseChangelog


def parse_version(value):
    if not isinstance(value, str) or len(value) > 32 or not _SEMVER.fullmatch(value):
        raise UpdateCheckError("The update service returned an invalid version.")
    parts = tuple(int(part) for part in value.split("."))
    if any(part > 999999 for part in parts):
        raise UpdateCheckError("The update service returned an invalid version.")
    return parts


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise UpdateCheckError("The update service returned duplicate fields.")
        result[key] = value
    return result


def _plain_changelog_text(value, maximum, label):
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or _UNSAFE_CHANGELOG_TEXT.search(value)
    ):
        raise UpdateCheckError(
            "The update service returned invalid %s text." % label
        )
    return value


def parse_changelog(value):
    if not isinstance(value, dict) or set(value) != _CHANGELOG_KEYS:
        raise UpdateCheckError("The update service returned an invalid changelog.")
    summary = _plain_changelog_text(value["summary"], 300, "changelog summary")
    items = value["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= 8:
        raise UpdateCheckError("The update service returned an invalid changelog.")
    parsed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != _CHANGELOG_ITEM_KEYS:
            raise UpdateCheckError("The update service returned an invalid changelog item.")
        category = item["category"]
        if not isinstance(category, str) or category not in _CHANGELOG_CATEGORIES:
            raise UpdateCheckError("The update service returned an invalid changelog category.")
        parsed.append(ChangelogItem(
            category, _plain_changelog_text(item["text"], 240, "changelog item")
        ))
    return ReleaseChangelog(summary, tuple(parsed))


def changelog_dict(changelog):
    return {
        "summary": changelog.summary,
        "items": [
            {"category": item.category, "text": item.text}
            for item in changelog.items
        ],
    }


def parse_manifest(payload):
    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    except UnicodeDecodeError as exc:
        raise UpdateCheckError("The update service returned invalid text.") from exc
    if not isinstance(text, str):
        raise UpdateCheckError("The update service returned an invalid response.")
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except UpdateCheckError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise UpdateCheckError("The update service returned invalid JSON.") from exc
    if not isinstance(value, dict) or set(value) != _MANIFEST_KEYS:
        raise UpdateCheckError("The update service returned an unsupported manifest.")
    if type(value["schema"]) is not int or value["schema"] != 1:
        raise UpdateCheckError("The update service returned an unsupported manifest.")
    if value["product"] != "BiblioSleuth AI" or value["channel"] != "stable":
        raise UpdateCheckError("The update service returned an unsupported product or channel.")
    parse_version(value["version"])
    parse_version(value["minimum_calibre"])
    published = value["published"]
    if not isinstance(published, str) or not _UTC_TIMESTAMP.fullmatch(published):
        raise UpdateCheckError("The update service returned an invalid publication date.")
    try:
        datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise UpdateCheckError("The update service returned an invalid publication date.") from exc
    return UpdateManifest(
        value["version"], published, value["minimum_calibre"],
        parse_changelog(value["changelog"]),
    )


def _validate_manifest_url(url):
    try:
        parsed = urlsplit(url)
    except (TypeError, ValueError):
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == UPDATE_MANIFEST_HOST
        and parsed.port is None
        and parsed.path == UPDATE_MANIFEST_PATH
        and not parsed.query
        and not parsed.fragment
        and parsed.username is None
        and parsed.password is None
    )


def fetch_update_manifest(opener=None, timeout=UPDATE_TIMEOUT_SECONDS):
    if not _validate_manifest_url(UPDATE_MANIFEST_URL):
        raise UpdateCheckError("The configured update service address is invalid.")
    request = Request(
        UPDATE_MANIFEST_URL,
        headers={"Accept": "application/json", "User-Agent": "BiblioSleuth-AI-Update-Check"},
        method="GET",
    )
    client = opener or build_opener(_NoRedirects())
    try:
        with client.open(request, timeout=timeout) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else UPDATE_MANIFEST_URL
            if not _validate_manifest_url(final_url):
                raise UpdateCheckError("The update service redirected unexpectedly.")
            payload = response.read(UPDATE_RESPONSE_LIMIT + 1)
    except UpdateCheckError:
        raise
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            raise UpdateCheckError("The update service redirected unexpectedly.") from exc
        raise UpdateCheckError("The update service returned an HTTP error.") from exc
    except (OSError, URLError, TimeoutError) as exc:
        raise UpdateCheckError("The update service could not be reached.") from exc
    except Exception as exc:
        raise UpdateCheckError("The update service returned an invalid response.") from exc
    if len(payload) > UPDATE_RESPONSE_LIMIT:
        raise UpdateCheckError("The update service response was too large.")
    return parse_manifest(payload)


def classify_update(manifest, installed_version, calibre_version):
    if parse_version(calibre_version) < parse_version(manifest.minimum_calibre):
        return "incompatible"
    if parse_version(manifest.version) > parse_version(installed_version):
        return "available"
    return "current"


def release_url(version):
    parse_version(version)
    return RELEASE_TAG_BASE + version


def automatic_check_due(preferences, now=None):
    if not preferences.get("automatic_update_checks", True):
        return False
    now = time.time() if now is None else float(now)
    try:
        last_attempt = float(preferences.get("last_update_attempt", 0) or 0)
    except (TypeError, ValueError):
        return True
    if not math.isfinite(last_attempt):
        return True
    return last_attempt <= 0 or now < last_attempt or now - last_attempt >= UPDATE_CHECK_INTERVAL_SECONDS


def notification_due(preferences, version, now=None):
    parse_version(version)
    if preferences.get("skipped_update_version") == version:
        return False
    if preferences.get("update_remind_version") != version:
        return True
    now = time.time() if now is None else float(now)
    try:
        remind_after = float(preferences.get("update_remind_after", 0) or 0)
    except (TypeError, ValueError):
        return True
    if not math.isfinite(remind_after):
        return True
    return remind_after <= now


def known_update_available(preferences, installed_version, calibre_version):
    """Return whether retained manifest state represents a compatible update."""
    try:
        version = preferences.get("latest_known_version", "")
        minimum_calibre = preferences.get("latest_known_minimum_calibre", "")
        return (
            parse_version(version) > parse_version(installed_version)
            and parse_version(calibre_version) >= parse_version(minimum_calibre)
        )
    except (AttributeError, TypeError, ValueError, UpdateCheckError):
        return False


def update_check_job(
    installed_version, calibre_version, log=None, abort=None, notifications=None
):
    """Calibre ThreadedJob entry point; always returns a sanitized result."""
    if abort is not None and abort.is_set():
        return {"status": "cancelled"}
    if notifications is not None:
        notifications.put((0.1, "Checking the BiblioSleuth AI release manifest"))
    try:
        manifest = fetch_update_manifest()
        if notifications is not None:
            notifications.put((1.0, "BiblioSleuth AI update check complete"))
        return {
            "status": classify_update(manifest, installed_version, calibre_version),
            "manifest": {
                "version": manifest.version,
                "published": manifest.published,
                "minimum_calibre": manifest.minimum_calibre,
                "changelog": changelog_dict(manifest.changelog),
            },
        }
    except UpdateCheckError as exc:
        if log is not None:
            log("BiblioSleuth AI update check did not complete")
        return {"status": "error", "error": str(exc)}
