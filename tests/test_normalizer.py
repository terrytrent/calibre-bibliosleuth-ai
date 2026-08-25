from bibliosleuth_ai.normalizer import normalize_identifiers, normalize_tags, sanitize_comments


def test_normalizes_identifiers_and_tags():
    assert normalize_identifiers([{"type": "ISBN", "value": "978-0-306-40615-7"}]) == {"isbn": "9780306406157"}
    assert normalize_tags(["Science Fiction", "science fiction", " Space Opera "], 10) == ["Science Fiction", "Space Opera"]


def test_sanitizes_comments():
    value = sanitize_comments('<p onclick="bad()">Good</p><script>alert(1)</script>')
    assert "onclick" not in value and "script" not in value and "Good" in value


def test_comments_use_strict_formatting_allowlist():
    hostile = '<img src="https://bad/pixel"><iframe>bad</iframe><p onclick=bad()>Safe <strong class=x>bold</strong></p><a href="javascript:bad()">link</a><svg>bad</svg>'
    value = sanitize_comments(hostile)
    assert value == "<p>Safe <strong>bold</strong></p>link"


def test_comments_remove_trailing_edition_identification_note():
    value = sanitize_comments(
        "<p>A practical introduction to Python for new programmers. "
        "The selected edition is identified in the supplied EPUB front matter as a "
        "2015 No Starch Press edition and carries ISBN-10 1593275730 and "
        "ISBN-13 9781593275730.</p>"
    )
    assert value == "<p>A practical introduction to Python for new programmers.</p>"
    assert "ISBN" not in value


def test_comments_keep_reader_relevant_edition_information():
    value = sanitize_comments(
        "<p>This revised edition adds three chapters on type hints and testing.</p>"
    )
    assert "adds three chapters" in value


def test_invalid_isbn_checksum_is_dropped():
    assert normalize_identifiers([{"type": "isbn", "value": "9780306406158"}]) == {}


def test_isbn_x_is_only_valid_as_final_check_digit():
    assert normalize_identifiers([{"type": "isbn", "value": "0X30640615"}]) == {}
    assert normalize_identifiers([{"type": "isbn", "value": "080442957X"}]) == {"isbn": "080442957X"}
