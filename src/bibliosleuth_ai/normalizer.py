import html
import re
from html.parser import HTMLParser


def normalize_isbn(value):
    raw = re.sub(r"[^0-9Xx]", "", value or "").upper()
    return raw if len(raw) in (10, 13) else ""


def _valid_isbn(value):
    if len(value) == 10:
        if "X" in value[:-1] or not all(ch.isdigit() for ch in value[:-1]):
            return False
        total = sum((10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(value))
        return total % 11 == 0
    if len(value) == 13 and value.isdigit():
        total = sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(value[:12]))
        return (10 - total % 10) % 10 == int(value[-1])
    return False


def normalize_identifiers(items):
    result = {}
    for item in items or []:
        kind = str(item.get("type", "")).strip().lower()
        value = str(item.get("value", "")).strip()
        if kind == "isbn":
            value = normalize_isbn(value)
            if value and not _valid_isbn(value):
                value = ""
        if kind and value:
            result[kind] = value
    return result


def normalize_tags(tags, limit=20):
    result, seen = [], set()
    for tag in tags or []:
        tag = " ".join(str(tag).split()).strip()
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            result.append(tag)
        if len(result) >= limit:
            break
    return result


class _CommentsSanitizer(HTMLParser):
    allowed = {"p", "br", "strong", "em", "ul", "ol", "li"}
    suppressed = {"script", "style", "iframe", "object", "embed", "svg", "math", "form"}

    def __init__(self, text_limit):
        super().__init__(convert_charrefs=True)
        self.remaining = max(0, int(text_limit))
        self.output = []
        self.stack = []
        self.suppress_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.suppressed:
            self.suppress_depth += 1
        elif not self.suppress_depth and tag in self.allowed:
            self.output.append("<br>" if tag == "br" else "<%s>" % tag)
            if tag != "br":
                self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if not self.suppress_depth and tag.lower() == "br":
            self.output.append("<br>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.suppressed:
            self.suppress_depth = max(0, self.suppress_depth - 1)
            return
        if self.suppress_depth or tag not in self.allowed or tag == "br" or tag not in self.stack:
            return
        while self.stack:
            opened = self.stack.pop()
            self.output.append("</%s>" % opened)
            if opened == tag:
                break

    def handle_data(self, data):
        if self.suppress_depth or self.remaining <= 0:
            return
        data = data[:self.remaining]
        self.remaining -= len(data)
        self.output.append(html.escape(data))

    def result(self):
        while self.stack:
            self.output.append("</%s>" % self.stack.pop())
        return "".join(self.output).strip()


_TRAILING_CATALOG_NOTE = re.compile(
    r"(?is)(?:\s|<br>)*"
    r"(?:"
    r"(?:the\s+)?selected\s+edition\s+is\s+(?:identified|confirmed|verified|matched)\b"
    r"|(?:the\s+)?(?:supplied|provided)\s+EPUB(?:\s+(?:front\s+matter|metadata))?\s+"
    r"(?:identifies|confirms|verifies|shows)\b"
    r")"
    r".*?(?=</p>\s*$|$)"
)


def _remove_trailing_catalog_note(value):
    """Remove narrow model boilerplate about how an edition was identified."""
    cleaned = _TRAILING_CATALOG_NOTE.sub("", value).strip()
    return re.sub(r"(?is)<p>\s*</p>\s*$", "", cleaned).strip()


def sanitize_comments(value, max_chars=5000):
    if not value:
        return ""
    raw = str(value)
    if "<" not in raw:
        raw = raw[:max_chars]
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", raw) if part.strip()]
        result = "".join("<p>%s</p>" % html.escape(part).replace("\n", "<br>") for part in paragraphs)
        return _remove_trailing_catalog_note(result)
    parser = _CommentsSanitizer(max_chars)
    parser.feed(raw[:max(4096, int(max_chars) * 8)])
    parser.close()
    return _remove_trailing_catalog_note(parser.result())


def display_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            return ", ".join("%s:%s" % (x.get("type", ""), x.get("value", "")) for x in value)
        return ", ".join(map(str, value))
    if isinstance(value, dict):
        index = value.get("index")
        return value.get("name", "") + ((" #%s" % index) if index is not None else "")
    return str(value)
