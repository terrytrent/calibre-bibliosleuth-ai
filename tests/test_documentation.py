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
    assert "<b>Version:</b> " + version in guide


def test_changelog_uses_keep_a_changelog_release_format():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = ".".join(map(str, PLUGIN_VERSION))
    assert "keepachangelog.com/en/1.1.0/" in changelog
    assert "semver.org/spec/v2.0.0.html" in changelog
    assert "## [Unreleased]" in changelog
    assert re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.MULTILINE)
    for category in ("### Added", "### Changed", "### Fixed"):
        assert category in changelog
    assert f"[{version}]: https://github.com/terrytrent/calibre-bibliosleuth-ai/compare/" in changelog


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


def test_provider_documentation_matches_current_claude_contract_and_costs():
    documentation = "\n".join(
        path.read_text(encoding="utf-8") for path in (
            ROOT / "README.md", ROOT / "docs/user-guide.html",
            ROOT / "docs/wiki/Optimization-and-Cost.md",
            ROOT / "docs/wiki/Troubleshooting.md",
        )
    )
    assert "claude-sonnet-5" in documentation
    assert "ANTHROPIC_WORKSPACE_ID" in documentation
    assert "$0.07" in documentation and "$0.13" in documentation
    assert "two strict" in documentation
    assert "establishes the edition match" in documentation
    assert "returns only the remaining fields" in documentation
    for stale in (
        "Claude usage is reported without a guessed dollar amount",
        "Claude hosted research uses two requests",
        "one strict-schema request because Anthropic",
    ):
        assert stale not in documentation


def test_configuration_documentation_covers_current_limits_and_defaults():
    documentation = "\n".join(
        path.read_text(encoding="utf-8") for path in (
            ROOT / "docs/user-guide.html", ROOT / "docs/wiki/Configuration.md"
        )
    )
    for phrase in (
        "default 3", "default 6", "default 60", "default 20", "default 5,000",
        "1–10", "10–300", "1–100", "500–30,000",
    ):
        assert phrase in documentation
