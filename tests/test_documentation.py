import re
from html.parser import HTMLParser
from pathlib import Path

from bibliosleuth_ai.constants import PLUGIN_VERSION


ROOT = Path(__file__).resolve().parents[1]


class _HTMLStructure(HTMLParser):
    void = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(); self.stack = []; self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.void: self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in self.stack:
            self.errors.append("unexpected closing tag: " + tag); return
        while self.stack:
            if self.stack.pop() == tag: break


def test_documented_versions_match_plugin():
    version = ".".join(map(str, PLUGIN_VERSION))
    assert "**Version:** " + version in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Version: " + version in (ROOT / "src/bibliosleuth_ai/about.txt").read_text(encoding="utf-8")
    guide = (ROOT / "docs/user-guide.html").read_text(encoding="utf-8")
    release = (ROOT / "docs/mobileread-release-template.md").read_text(encoding="utf-8")
    assert "<b>Version:</b> " + version in guide
    assert "Current version: " + version in release


def test_user_guide_html_is_balanced_and_theme_aware():
    guide = (ROOT / "docs/user-guide.html").read_text(encoding="utf-8")
    parser = _HTMLStructure(); parser.feed(guide)
    assert parser.errors == [] and parser.stack == []
    for placeholder in ("{{BASE_COLOR}}", "{{TEXT_COLOR}}", "{{LINK_COLOR}}", "{{BORDER_COLOR}}"):
        assert placeholder in guide


def test_documentation_has_no_retired_model_or_navigation_wording():
    documentation = "\n".join(
        path.read_text(encoding="utf-8") for path in (
            ROOT / "README.md", ROOT / "SECURITY.md", ROOT / "docs/user-guide.html"
        )
    )
    for retired in ("Apply & Next", "Skip & Next", "unknown custom model", "A custom model must"):
        assert retired not in documentation
    assert "https://developers.openai.com/api/docs/quickstart" in documentation
    assert not re.search(r"platform\.openai\.com/docs/quickstart", documentation)
