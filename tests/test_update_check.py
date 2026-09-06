import json
import queue
import threading
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from bibliosleuth_ai.update_check import (
    RELEASE_TAG_BASE,
    UPDATE_CHECK_INTERVAL_SECONDS,
    UPDATE_MANIFEST_URL,
    UPDATE_REMINDER_SECONDS,
    UpdateCheckError,
    automatic_check_due,
    classify_update,
    fetch_update_manifest,
    known_update_available,
    notification_due,
    parse_changelog,
    parse_manifest,
    parse_version,
    release_url,
    update_check_job,
)
from bibliosleuth_ai.constants import PLUGIN_VERSION
from tests.http_helpers import Response


ROOT = Path(__file__).resolve().parents[1]


VALID = {
    "schema": 1,
    "product": "BiblioSleuth AI",
    "channel": "stable",
    "version": "1.2.0",
    "published": "2026-09-06T12:34:56Z",
    "minimum_calibre": "7.0.0",
    "changelog": {
        "summary": "Adds a friendly update check.",
        "items": [
            {"category": "Added", "text": "Daily update notifications."},
            {"category": "Fixed", "text": "Improved local service errors."},
        ],
    },
}


def encoded(**changes):
    value = dict(VALID)
    value.update(changes)
    return json.dumps(value).encode("utf-8")


class Opener:
    def __init__(self, payload=None, error=None, final_url=None):
        self.payload = encoded() if payload is None else payload
        self.error = error
        self.final_url = final_url
        self.request = None
        self.timeout = None

    def open(self, request, timeout=None):
        self.request = request
        self.timeout = timeout
        if self.error:
            raise self.error
        response = Response(self.payload)
        if self.final_url is not None:
            response.geturl = lambda: self.final_url
        return response


def test_fetch_uses_only_fixed_credential_free_endpoint_and_limits():
    opener = Opener()
    manifest = fetch_update_manifest(opener, timeout=3)
    assert manifest.version == "1.2.0"
    assert manifest.changelog.summary == "Adds a friendly update check."
    assert manifest.changelog.items[0].category == "Added"
    assert opener.request.full_url == UPDATE_MANIFEST_URL
    assert opener.request.get_method() == "GET"
    assert opener.request.get_header("Accept") == "application/json"
    assert opener.request.get_header("User-agent") == "BiblioSleuth-AI-Update-Check"
    assert opener.request.get_header("Authorization") is None
    assert set(name.lower() for name, _value in opener.request.header_items()) == {
        "accept", "user-agent",
    }
    assert "?" not in opener.request.full_url
    assert opener.timeout == 3


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://bibliosleuthai-updates.trentathome.xyz/latest.json",
        "https://bibliosleuthai-updates.trentathome.xyz/other.json",
        "https://bibliosleuthai-updates.trentathome.xyz:443/latest.json",
        "https://bibliosleuthai-updates.trentathome.xyz/latest.json?install=1",
        "https://user@bibliosleuthai-updates.trentathome.xyz/latest.json",
        "https://example.com/latest.json",
    ],
)
def test_fetch_refuses_any_modified_update_endpoint(monkeypatch, unsafe_url):
    monkeypatch.setattr("bibliosleuth_ai.update_check.UPDATE_MANIFEST_URL", unsafe_url)
    opener = Opener()
    with pytest.raises(UpdateCheckError, match="address is invalid"):
        fetch_update_manifest(opener)
    assert opener.request is None


@pytest.mark.parametrize(
    ("installed", "available", "expected"),
    [
        ("1.1.2", "1.1.2", "current"),
        ("1.1.2", "1.1.1", "current"),
        ("1.1.2", "1.1.3", "available"),
        ("1.9.9", "1.10.0", "available"),
        ("1.9.9", "2.0.0", "available"),
    ],
)
def test_versions_are_compared_numerically(installed, available, expected):
    manifest = parse_manifest(encoded(version=available))
    assert classify_update(manifest, installed, "9.13.0") == expected


def test_minimum_calibre_is_enforced_before_update_notice():
    manifest = parse_manifest(encoded(minimum_calibre="10.0.0"))
    assert classify_update(manifest, "1.1.2", "9.13.0") == "incompatible"


@pytest.mark.parametrize(
    "version",
    ["", "1.2", "1.2.3.4", "v1.2.3", "01.2.3", "1.02.3", "1.2.03", "1.2.-1", "1.2.3 ", None, True, 123, "1.2.1000000"],
)
def test_invalid_versions_are_rejected(version):
    with pytest.raises(UpdateCheckError):
        parse_version(version)


@pytest.mark.parametrize(
    "changes",
    [
        {"schema": 2}, {"schema": True}, {"product": "Other"}, {"channel": "beta"},
        {"version": "v1.2.0"}, {"minimum_calibre": "7"},
        {"published": "2026-09-06"}, {"published": "2026-02-30T12:34:56Z"},
    ],
)
def test_invalid_manifest_values_are_rejected(changes):
    with pytest.raises(UpdateCheckError):
        parse_manifest(encoded(**changes))


def test_manifest_requires_exact_keys_and_rejects_duplicate_keys():
    missing = dict(VALID)
    del missing["channel"]
    with pytest.raises(UpdateCheckError):
        parse_manifest(json.dumps(missing))
    with pytest.raises(UpdateCheckError):
        parse_manifest(json.dumps(dict(VALID, extra="no")))
    with pytest.raises(UpdateCheckError, match="duplicate"):
        parse_manifest('{"schema":1,"schema":1}')


@pytest.mark.parametrize(
    "changelog",
    [
        None,
        {},
        {"summary": "Summary", "items": []},
        {"summary": "", "items": [{"category": "Added", "text": "Text"}]},
        {"summary": " Summary", "items": [{"category": "Added", "text": "Text"}]},
        {"summary": "Summary", "items": [{"category": "Other", "text": "Text"}]},
        {"summary": "Summary", "items": [{"category": "Added", "text": ""}]},
        {"summary": "Summary", "items": [{"category": "Added", "text": "<b>HTML</b>"}]},
        {"summary": "Summary", "items": [{"category": "Added", "text": "See https://example.com"}]},
        {"summary": "Summary", "items": [{"category": "Added", "text": "Line\nbreak"}]},
        {"summary": "Summary", "items": [{"category": "Added", "text": "Text", "extra": True}]},
        {"summary": "Summary", "items": [{"category": "Added", "text": "Text"}] * 9},
        {"summary": "Summary", "items": [{"category": "Added", "text": "x" * 241}]},
        {"summary": "x" * 301, "items": [{"category": "Added", "text": "Text"}]},
    ],
)
def test_changelog_is_strictly_bounded_plain_text(changelog):
    with pytest.raises(UpdateCheckError):
        parse_manifest(encoded(changelog=changelog))


@pytest.mark.parametrize(
    "category", ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
)
def test_all_keep_a_changelog_categories_are_accepted(category):
    parsed = parse_changelog({
        "summary": "Release summary.",
        "items": [{"category": category, "text": "Release highlight."}],
    })
    assert parsed.items[0].category == category


@pytest.mark.parametrize("payload", [b"\xff", b"not json", b"[]", b"null"])
def test_invalid_response_bodies_are_rejected(payload):
    with pytest.raises(UpdateCheckError):
        parse_manifest(payload)


def test_fetch_rejects_oversize_and_redirected_responses():
    with pytest.raises(UpdateCheckError, match="too large"):
        fetch_update_manifest(Opener(b"x" * 4097))
    with pytest.raises(UpdateCheckError, match="redirected"):
        fetch_update_manifest(Opener(final_url="https://example.com/latest.json"))
    with pytest.raises(UpdateCheckError, match="redirected"):
        fetch_update_manifest(Opener(error=HTTPError(
            UPDATE_MANIFEST_URL, 302, "moved", {"Location": UPDATE_MANIFEST_URL}, None
        )))


@pytest.mark.parametrize(
    "error",
    [URLError("offline"), TimeoutError(), HTTPError(UPDATE_MANIFEST_URL, 503, "down", {}, None)],
)
def test_network_failures_are_sanitized(error):
    with pytest.raises(UpdateCheckError) as caught:
        fetch_update_manifest(Opener(error=error))
    assert "offline" not in str(caught.value)
    assert UPDATE_MANIFEST_URL not in str(caught.value)


def test_background_job_returns_only_sanitized_error(monkeypatch):
    def failed():
        raise UpdateCheckError("The update service could not be reached.")

    messages = []
    monkeypatch.setattr("bibliosleuth_ai.update_check.fetch_update_manifest", failed)
    result = update_check_job("1.1.2", "9.13.0", log=messages.append)
    assert result == {
        "status": "error", "error": "The update service could not be reached."
    }
    assert messages == ["BiblioSleuth AI update check did not complete"]


def test_background_job_accepts_calibre_injected_controls(monkeypatch):
    monkeypatch.setattr(
        "bibliosleuth_ai.update_check.fetch_update_manifest",
        lambda: parse_manifest(encoded()),
    )
    notifications = queue.Queue()
    result = update_check_job(
        "1.1.2", "9.13.0", abort=threading.Event(), notifications=notifications
    )
    assert result["status"] == "available"
    assert notifications.get_nowait()[0] == 0.1
    assert notifications.get_nowait()[0] == 1.0

    cancelled = threading.Event()
    cancelled.set()
    assert update_check_job("1.1.2", "9.13.0", abort=cancelled) == {
        "status": "cancelled"
    }


def test_release_url_is_derived_from_validated_version():
    assert release_url("1.2.3") == RELEASE_TAG_BASE + "1.2.3"
    with pytest.raises(UpdateCheckError):
        release_url("../../other")


def test_automatic_check_is_due_once_daily_and_handles_clock_skew():
    now = 2_000_000.0
    assert automatic_check_due({}, now)
    assert not automatic_check_due({"automatic_update_checks": False}, now)
    assert not automatic_check_due({"automatic_update_checks": True, "last_update_attempt": now - UPDATE_CHECK_INTERVAL_SECONDS + 1}, now)
    assert automatic_check_due({"automatic_update_checks": True, "last_update_attempt": now - UPDATE_CHECK_INTERVAL_SECONDS}, now)
    assert automatic_check_due({"automatic_update_checks": True, "last_update_attempt": now + 1}, now)
    assert automatic_check_due({"automatic_update_checks": True, "last_update_attempt": "invalid"}, now)
    assert automatic_check_due({"automatic_update_checks": True, "last_update_attempt": float("nan")}, now)
    assert automatic_check_due({"automatic_update_checks": True, "last_update_attempt": float("inf")}, now)


def test_notification_can_be_deferred_until_tomorrow_or_skipped_by_version():
    now = 2_000_000.0
    assert notification_due({}, "1.2.0", now)
    tomorrow = now + UPDATE_REMINDER_SECONDS
    deferred = {"update_remind_version": "1.2.0", "update_remind_after": tomorrow}
    assert not notification_due(deferred, "1.2.0", now)
    assert notification_due(deferred, "1.2.0", tomorrow)
    assert notification_due({"update_remind_version": "1.2.0", "update_remind_after": float("nan")}, "1.2.0", now)
    assert notification_due({"update_remind_version": "1.2.0", "update_remind_after": float("inf")}, "1.2.0", now)
    assert notification_due(deferred, "1.3.0", now)
    assert not notification_due({"skipped_update_version": "1.2.0"}, "1.2.0", now)
    assert notification_due({"skipped_update_version": "1.2.0"}, "1.3.0", now)


def test_retained_update_must_be_newer_and_calibre_compatible():
    retained = {
        "latest_known_version": "1.2.0",
        "latest_known_minimum_calibre": "7.0.0",
    }
    assert known_update_available(retained, "1.1.2", "9.13.0")
    assert not known_update_available(retained, "1.2.0", "9.13.0")
    assert not known_update_available(retained, "1.1.2", "invalid")
    assert not known_update_available(retained, "1.1.2", "6.99.0")
    assert not known_update_available(
        {**retained, "latest_known_minimum_calibre": "10.0.0"},
        "1.1.2",
        "9.13.0",
    )
    assert not known_update_available(
        {"latest_known_version": "1.2.0"}, "1.1.2", "9.13.0"
    )


def test_calibre_integration_runs_in_background_and_exposes_deferrals():
    action = (ROOT / "src/bibliosleuth_ai/action.py").read_text(encoding="utf-8")
    config = (ROOT / "src/bibliosleuth_ai/config.py").read_text(encoding="utf-8")
    onboarding = (ROOT / "src/bibliosleuth_ai/onboarding.py").read_text(encoding="utf-8")
    assert 'ThreadedJob(\n            "BiblioSleuth AI update check"' in action
    assert "QTimer.singleShot(0, self._maybe_check_for_updates)" in action
    assert "self._schedule_automatic_update_check()" in action
    assert 'prefs["latest_known_minimum_calibre"] = manifest.get(' in action
    assert 'QPushButton("Remind me tomorrow")' in action
    assert 'QPushButton("Skip this version")' in action
    assert "self.action.remind_update_tomorrow(self.version)" in action
    assert 'self.message.setAccessibleName("BiblioSleuth AI update highlights")' in action
    assert 'self.message.setPlainText("\\n".join(lines))' in action
    assert '"• %s: %s"' in action
    assert 'QCheckBox("Automatically check daily for updates")' in config
    assert 'prefs["automatic_update_checks"] = self.automatic_update_checks.isChecked()' in config
    assert "sends no library or provider data" in onboarding


def test_update_documentation_covers_frequency_privacy_and_user_control():
    documentation = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md", "SECURITY.md", "docs/user-guide.html",
            "docs/wiki/Installation-and-Updates.md", "docs/wiki/Configuration.md",
            "docs/wiki/Privacy-and-Security.md", "docs/wiki/Troubleshooting.md",
        )
    )
    for phrase in (
        "once every 24 hours", "Remind me tomorrow", "Skip this version",
        "never downloads or installs", "installation identifier",
        "bibliosleuthai-updates.trentathome.xyz/latest.json",
        "ordinary invocation logs",
    ):
        assert phrase in documentation


def test_upload_ready_manifest_matches_plugin_and_contract():
    path = ROOT / "docs/update-site/latest.json"
    payload = path.read_bytes()
    manifest = parse_manifest(payload)
    assert len(payload) <= 4096
    assert manifest.version == ".".join(map(str, PLUGIN_VERSION))
    assert manifest.changelog.summary
    assert manifest.changelog.items
