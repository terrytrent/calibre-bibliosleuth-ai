"""Small bounded JSON transport shared by external providers."""

import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .provider_base import ProviderError


MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_ERROR_BYTES = 16 * 1024


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_response(stream, limit=MAX_RESPONSE_BYTES, label="Provider"):
    data = stream.read(limit + 1)
    if len(data) > limit:
        raise ProviderError("%s response exceeded the safety size limit" % label)
    return data


def safe_api_error(exc, secrets=()):
    raw = exc.read(MAX_ERROR_BYTES + 1)[:MAX_ERROR_BYTES].decode("utf-8", "replace")
    message = "request rejected"
    error_type = ""
    try:
        error = json.loads(raw).get("error") or {}
        message = str(error.get("message") or message)
        error_type = str(error.get("code") or error.get("type") or "")
    except (ValueError, AttributeError):
        pass
    for secret in secrets:
        if secret:
            message = message.replace(str(secret), "[REDACTED]")
    message = re.sub(r"\b(?:sk-|sess-)[A-Za-z0-9_-]{8,}\b", "[REDACTED]", message)
    message = " ".join(message.split())[:500]
    return "%s%s" % ((error_type + ": ") if error_type else "", message)


class JSONTransport:
    def __init__(self, label, timeout=60, opener=None):
        self.label = label
        self.timeout = int(timeout)
        self.opener = opener or build_opener(NoRedirectHandler()).open

    def open(self, request):
        opener = getattr(self.opener, "open", self.opener)
        return opener(request, timeout=self.timeout)

    def request(self, url, method="GET", payload=None, headers=None, limit=MAX_RESPONSE_BYTES,
                secrets=()):
        data = None
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        request = Request(url, data=data, headers=headers or {}, method=method)
        try:
            with self.open(request) as response:
                result = json.loads(read_response(response, limit, self.label).decode("utf-8"))
        except HTTPError as exc:
            if 300 <= exc.code < 400:
                raise ProviderError("%s API redirect refused for security" % self.label)
            raise ProviderError("%s API error %s: %s" % (
                self.label, exc.code, safe_api_error(exc, secrets)
            ))
        except (URLError, socket.timeout, OSError, UnicodeDecodeError, ValueError) as exc:
            raise ProviderError("%s request failed: %s" % (self.label, exc))
        return result
