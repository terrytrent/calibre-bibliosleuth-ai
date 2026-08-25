import re
import zipfile
import posixpath
from html import unescape
from urllib.parse import unquote

try:
    # Calibre exposes files in a plugin ZIP beneath the plugin's private
    # namespace, so bundled dependencies must be imported relatively.
    from .defusedxml import ElementTree as ET
    from .defusedxml.common import DefusedXmlException
except ImportError:  # Source-tree tests and development environments.
    from defusedxml import ElementTree as ET
    from defusedxml.common import DefusedXmlException


class EpubExtractionError(ValueError):
    pass


MAX_ARCHIVE_MEMBERS = 10_000
MAX_CONTAINER_BYTES = 256 * 1024
MAX_OPF_BYTES = 2 * 1024 * 1024
MAX_TOTAL_SCAN_BYTES = 4 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
MIN_RATIO_CHECK_BYTES = 128 * 1024


def _safe_member_name(name):
    normalized = posixpath.normpath((name or "").replace("\\", "/"))
    if not normalized or normalized == "." or normalized.startswith("../") or normalized.startswith("/"):
        raise EpubExtractionError("EPUB contains an unsafe package path")
    return normalized


def _read_bounded(book, name, limit):
    name = _safe_member_name(name)
    try:
        info = book.getinfo(name)
    except KeyError:
        raise
    if info.flag_bits & 0x1:
        raise EpubExtractionError("EPUB contains an encrypted metadata member")
    if info.file_size > limit:
        raise EpubExtractionError("EPUB member is too large: %s" % name)
    ratio = info.file_size / max(1, info.compress_size)
    if info.file_size >= MIN_RATIO_CHECK_BYTES and ratio > MAX_COMPRESSION_RATIO:
        raise EpubExtractionError("EPUB member has a suspicious compression ratio: %s" % name)
    with book.open(info) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise EpubExtractionError("EPUB member exceeds its read limit: %s" % name)
    return data


def _parse_xml(raw, label):
    upper = raw.upper()
    if b"<!ENTITY" in upper:
        raise EpubExtractionError("Entity declarations are not allowed in %s" % label)
    if b"<!DOCTYPE" in upper:
        # Older EPUB generators sometimes include a simple external DOCTYPE.
        # ElementTree never needs it, so strip it without resolving anything.
        # Internal subsets remain forbidden because they can define entities or
        # other complex declarations with no metadata value to this plugin.
        if re.search(br"<!DOCTYPE[^>]*\[", raw, re.I | re.S):
            raise EpubExtractionError("Internal DTD subsets are not allowed in %s" % label)
        raw, count = re.subn(br"<!DOCTYPE\s+[^>\[]+>", b"", raw, count=1, flags=re.I | re.S)
        if count != 1 or b"<!DOCTYPE" in raw.upper():
            raise EpubExtractionError("Unsupported DTD declaration in %s" % label)
    # Declarations/entities are rejected above, external DOCTYPEs are removed
    # without resolution, and callers enforce strict byte limits.
    return ET.fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)


_STRONG_INSTRUCTION_PATTERNS = (
    re.compile(r"ignore\s+(?:all\s+|any\s+)?(?:previous|prior|system|developer)\s+instructions", re.I),
    re.compile(r"(?:override|disregard|replace)\s+(?:the\s+)?(?:system|developer|previous)\s+(?:prompt|instructions)", re.I),
    re.compile(r"</?epub_evidence>", re.I),
)
_WEAK_INSTRUCTION_PATTERNS = (
    re.compile(r"\bsystem\s+prompt\b", re.I),
    re.compile(r"\b(?:assistant|developer|system)\s*:", re.I),
    re.compile(r"\b(?:return|output|respond with)\s+(?:only\s+)?(?:json|metadata|the following)", re.I),
    re.compile(r"\bdo not follow\b|\bnew instructions\b", re.I),
)


def instruction_risk_score(text):
    if any(pattern.search(text or "") for pattern in _STRONG_INSTRUCTION_PATTERNS):
        return 3
    return sum(1 for pattern in _WEAK_INSTRUCTION_PATTERNS if pattern.search(text or ""))


def _local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _plain_text(raw):
    text = raw.decode("utf-8", "replace")
    text = re.sub(r"<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(unescape(text).split())


def epub_structural_diagnostics(path):
    """Return bounded, content-free EPUB facts suitable for support logs."""
    result = {
        "readable_zip": False, "member_count": 0, "total_compressed_bytes": 0,
        "total_uncompressed_bytes": 0, "encrypted_members": 0,
        "container_present": False, "container_bytes": None,
        "container_has_doctype": False, "container_has_internal_subset": False,
        "container_has_entity": False,
    }
    try:
        with zipfile.ZipFile(path) as book:
            result["readable_zip"] = True
            members = book.infolist()[:MAX_ARCHIVE_MEMBERS + 1]
            result["member_count"] = len(members)
            result["total_compressed_bytes"] = sum(max(0, item.compress_size) for item in members)
            result["total_uncompressed_bytes"] = sum(max(0, item.file_size) for item in members)
            result["encrypted_members"] = sum(bool(item.flag_bits & 0x1) for item in members)
            try:
                raw = _read_bounded(book, "META-INF/container.xml", MAX_CONTAINER_BYTES)
                upper = raw.upper(); result["container_present"] = True; result["container_bytes"] = len(raw)
                result["container_has_doctype"] = b"<!DOCTYPE" in upper
                result["container_has_internal_subset"] = bool(re.search(br"<!DOCTYPE[^>]*\[", raw, re.I | re.S))
                result["container_has_entity"] = b"<!ENTITY" in upper
            except (KeyError, EpubExtractionError):
                pass
    except (OSError, TypeError, zipfile.BadZipFile):
        pass
    return result


_TITLE_PATH = re.compile(r"(?:^|[/_. -])(?:title[-_ ]?page|titlepage|covertitle|title)(?:[/_. -]|$)", re.I)
_COPYRIGHT_PATH = re.compile(r"(?:^|[/_. -])(?:copyright|copyright[-_ ]?page)(?:[/_. -]|$)", re.I)
_EXCLUDED_PATH = re.compile(
    r"(?:^|[/_. -])(?:toc|contents?|nav|chapter|preface|introduction|dedication|acknowledg(?:e)?ments?|excerpt|sample)(?:[/_. -]|$)",
    re.I,
)
_TITLE_SEMANTIC = re.compile(
    rb"\bepub:type\s*=\s*[\"'][^\"']*\b(?:titlepage|title-page|covertitle)\b[^\"']*[\"']",
    re.I,
)
_COPYRIGHT_SEMANTIC = re.compile(
    rb"\bepub:type\s*=\s*[\"'][^\"']*\bcopyright-page\b[^\"']*[\"']",
    re.I,
)
_COPYRIGHT_MARKER = re.compile(r"\bcopyright\b|©|&#169;", re.I)
_COPYRIGHT_SUPPORT = re.compile(
    r"\bISBN(?:-1[03])?\b|\ball rights reserved\b|\bpublished by\b|\b(?:first|revised|updated) edition\b|\bimprint\b",
    re.I,
)


def _normalized_href(base, href):
    href = unquote((href or "").split("#", 1)[0])
    return _safe_member_name((base + "/" + href) if base else href)


def _page_kinds(name, raw, text, position, guide_kinds, titles, authors):
    """Classify only confidently identified title/copyright pages."""
    kinds = set()
    lowered = name.lower()
    normalized = text.casefold()
    has_title = any(title.casefold() in normalized for title in titles if len(title) >= 3)
    has_author = any(author.casefold() in normalized for author in authors if len(author) >= 3)
    has_copyright = bool(_COPYRIGHT_MARKER.search(text))
    has_copyright_support = bool(_COPYRIGHT_SUPPORT.search(text))
    structurally_title = "title" in guide_kinds or bool(_TITLE_SEMANTIC.search(raw))
    structurally_copyright = "copyright" in guide_kinds or bool(_COPYRIGHT_SEMANTIC.search(raw))
    if structurally_title and len(text) <= 10000 and has_title:
        kinds.add("title")
    if structurally_copyright and (has_copyright or has_copyright_support):
        kinds.add("copyright")
    # Filenames are useful but not authoritative by themselves. Combine them
    # with early position, bounded page length, and bibliographic page text.
    if _TITLE_PATH.search(lowered) and position < 8 and len(text) <= 5000 and has_title:
        kinds.add("title")
    if _COPYRIGHT_PATH.search(lowered) and (has_copyright or has_copyright_support):
        kinds.add("copyright")
    if not _EXCLUDED_PATH.search(lowered):
        # Copyright text is distinctive only when accompanied by another
        # bibliographic marker, avoiding ordinary chapters that mention it.
        if has_copyright and has_copyright_support:
            kinds.add("copyright")
        # Filename/semantic markup is preferred for title pages. This fallback
        # requires a short, early page containing both the OPF title and author.
        if position < 8 and len(text) <= 3000 and has_title and has_author:
            kinds.add("title")
    return kinds & {"title", "copyright"}


def _bounded_page_evidence(pages, limit):
    if not pages or limit <= 0:
        return ""
    chunks = []
    per_page = max(1, limit // len(pages))
    for kinds, text in pages:
        label = "[%s page]\n" % (" and ".join(sorted(kinds)) if len(kinds) > 1 else next(iter(kinds)))
        chunks.append((label + text)[:per_page])
    return "\n\n".join(chunks)[:limit]


def extract_epub(path, max_page_evidence_chars=12000):
    try:
        book = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise EpubExtractionError("Invalid or unreadable EPUB: %s" % exc)
    with book:
        if len(book.infolist()) > MAX_ARCHIVE_MEMBERS:
            raise EpubExtractionError("EPUB contains too many archive members")
        try:
            container = _parse_xml(_read_bounded(book, "META-INF/container.xml", MAX_CONTAINER_BYTES), "container.xml")
            rootfile = next(x for x in container.iter() if _local(x.tag) == "rootfile")
            opf_path = _safe_member_name(rootfile.attrib["full-path"])
            opf = _parse_xml(_read_bounded(book, opf_path, MAX_OPF_BYTES), "OPF")
        except (KeyError, StopIteration, ET.ParseError, DefusedXmlException) as exc:
            raise EpubExtractionError("EPUB package metadata is missing or invalid: %s" % exc)

        metadata = {"titles": [], "authors": [], "identifiers": [], "publisher": None, "date": None, "language": None}
        for node in opf.iter():
            name = _local(node.tag)
            value = " ".join((node.text or "").split())
            if not value:
                continue
            if name == "title":
                metadata["titles"].append(value)
            elif name in ("creator", "contributor"):
                metadata["authors"].append(value)
            elif name == "identifier":
                metadata["identifiers"].append(value)
            elif name in ("publisher", "date", "language") and not metadata.get(name):
                metadata[name] = value

        base = opf_path.rpartition("/")[0]
        manifest, spine, guide = {}, [], {}
        for node in opf.iter():
            name = _local(node.tag)
            if name == "item" and node.attrib.get("id") and node.attrib.get("href"):
                manifest[node.attrib["id"]] = {
                    "href": node.attrib["href"],
                    "media_type": node.attrib.get("media-type", ""),
                    "properties": node.attrib.get("properties", ""),
                }
            elif name == "itemref" and node.attrib.get("idref"):
                spine.append(node.attrib["idref"])
            elif name == "reference" and node.attrib.get("href"):
                reference_type = node.attrib.get("type", "").lower()
                kinds = set()
                if reference_type in ("title-page", "titlepage", "covertitle"):
                    kinds.add("title")
                if reference_type in ("copyright-page", "copyright"):
                    kinds.add("copyright")
                if kinds:
                    guide[_normalized_href(base, node.attrib["href"])] = kinds

        candidate_names = []
        positions = {}
        for name in guide:
            candidate_names.append(name)
            positions[name] = -1
        for position, item_id in enumerate(spine[:24]):
            item = manifest.get(item_id)
            if not item or item["media_type"] not in ("application/xhtml+xml", "text/html", ""):
                continue
            name = _normalized_href(base, item["href"])
            if name not in positions:
                candidate_names.append(name)
                positions[name] = position

        candidates = []
        scan_limit = max(20000, int(max_page_evidence_chars) * 2)
        member_limit = max(256 * 1024, scan_limit * 4)
        total_read = 0
        for name in candidate_names:
            try:
                raw = _read_bounded(book, name, member_limit)
            except KeyError:
                continue
            total_read += len(raw)
            if total_read > MAX_TOTAL_SCAN_BYTES:
                raise EpubExtractionError("EPUB candidate-page scan exceeds the total limit")
            text = _plain_text(raw)
            if text:
                text = text[:scan_limit]
                kinds = _page_kinds(
                    name, raw, text, positions[name], guide.get(name, set()),
                    metadata["titles"], metadata["authors"],
                )
                if kinds:
                    candidates.append((positions[name], name, kinds, text))

        # Send at most one confidently identified page for each purpose. A
        # combined title/copyright page satisfies both and is included once.
        candidates.sort(key=lambda item: item[0])
        selected, covered = [], set()
        for _position, _name, kinds, text in candidates:
            useful = kinds - covered
            if useful:
                selected.append((kinds, text))
                covered.update(kinds)
            if covered == {"title", "copyright"}:
                break
        page_evidence = _bounded_page_evidence(selected, max(0, int(max_page_evidence_chars)))
        return {
            "opf": metadata,
            "page_evidence": page_evidence,
            "suspicious_instructions": instruction_risk_score(page_evidence) >= 2,
        }
