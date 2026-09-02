"""Bounded client for a user-managed SearXNG JSON search service."""

import ipaddress
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SearXNGError(RuntimeError):
    pass


MAX_SEARCH_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_QUERY_CHARS = 500
MAX_RESULTS = 10


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def normalize_service_url(value, allow_remote=False, label="SearXNG"):
    """Return a safe base URL; plain HTTP is restricted to loopback by default."""
    value = str(value or "").strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise SearXNGError("Enter a complete %s http:// or https:// server address" % label)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SearXNGError("The %s server address cannot contain credentials, a query, or a fragment" % label)
    host = parsed.hostname.casefold()
    loopback = host == "localhost"
    try:
        loopback = loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if parsed.scheme == "http" and not loopback and not allow_remote:
        raise SearXNGError("Plain HTTP %s connections are allowed only on this computer" % label)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


class SearXNGClient:
    def __init__(self, base_url, timeout=30, result_limit=6, opener=None, allow_remote=False):
        self.base_url = normalize_service_url(base_url, allow_remote=allow_remote)
        self.timeout = max(5, int(timeout))
        self.result_limit = max(1, min(MAX_RESULTS, int(result_limit)))
        self._opener = opener or build_opener(_NoRedirectHandler()).open
        self.last_search_calls = 0

    def _open(self, request):
        opener = getattr(self._opener, "open", self._opener)
        return opener(request, timeout=self.timeout)

    def search(self, query):
        query = " ".join(str(query or "").split())[:MAX_QUERY_CHARS]
        if not query:
            raise SearXNGError("SearXNG search query is empty")
        url = self.base_url + "/search?" + urlencode({"q": query, "format": "json", "safesearch": 1})
        request = Request(url, headers={"Accept": "application/json"}, method="GET")
        try:
            with self._open(request) as response:
                raw = response.read(MAX_SEARCH_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise SearXNGError("SearXNG returned HTTP %s" % exc.code)
        except (URLError, socket.timeout, OSError) as exc:
            raise SearXNGError("Could not reach SearXNG: %s" % exc)
        if len(raw) > MAX_SEARCH_RESPONSE_BYTES:
            raise SearXNGError("SearXNG response exceeded the safety size limit")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise SearXNGError("SearXNG did not return valid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise SearXNGError("SearXNG JSON search is unavailable; enable the json response format")
        self.last_search_calls += 1
        results = []
        for item in payload["results"]:
            if not isinstance(item, dict):
                continue
            title = " ".join(str(item.get("title") or "").split())[:300]
            content = " ".join(str(item.get("content") or "").split())[:1500]
            result_url = str(item.get("url") or "").strip()[:2048]
            parsed = urlsplit(result_url)
            if (parsed.scheme not in ("http", "https") or not parsed.hostname
                    or parsed.username or parsed.password):
                continue
            results.append({"title": title, "url": result_url, "snippet": content})
            if len(results) >= self.result_limit:
                break
        return results

    def test_connection(self):
        self.search("BiblioSleuth AI connection test")
        return True


def research_queries(local_book, maximum=3):
    """Build conservative edition-oriented searches from the bounded EPUB evidence."""
    opf = local_book.get("opf") if isinstance(local_book, dict) else {}
    opf = opf if isinstance(opf, dict) else {}
    identifiers = opf.get("identifiers") or local_book.get("identifiers") or []
    values = []
    if isinstance(identifiers, dict):
        values = list(identifiers.values())
    elif isinstance(identifiers, list):
        for item in identifiers:
            values.append(item.get("value") if isinstance(item, dict) else item)
    queries = []
    for value in values:
        compact = "".join(character for character in str(value or "") if character.isalnum())
        if 8 <= len(compact) <= 20:
            queries.append('"%s" publisher publication date edition' % compact)
    title = opf.get("title") or local_book.get("title")
    if not title and isinstance(opf.get("titles"), list) and opf["titles"]:
        title = opf["titles"][0]
    authors = opf.get("authors") or local_book.get("authors") or []
    if isinstance(authors, str):
        authors = [authors]
    if title:
        query = '"%s"' % " ".join(str(title).split())[:180]
        if authors:
            query += ' "%s"' % " ".join(str(authors[0]).split())[:100]
        queries.append(query + " publisher ISBN edition")
    unique = []
    for query in queries:
        if query not in unique:
            unique.append(query)
    return unique[:max(1, int(maximum))]


def collect_search_evidence(client, local_book, maximum=3, cancelled=None):
    evidence = []
    for query in research_queries(local_book, maximum):
        if cancelled is not None and cancelled():
            # Imported lazily to avoid a module cycle with provider_base.
            from .provider_base import ProviderCancelled
            raise ProviderCancelled("Research was cancelled")
        evidence.append({"query": query, "results": client.search(query)})
    if not evidence:
        raise SearXNGError("The EPUB did not contain enough bounded metadata to construct a safe search")
    return evidence


# Backward-compatible public name for callers and tests from earlier releases.
normalize_searxng_url = normalize_service_url
