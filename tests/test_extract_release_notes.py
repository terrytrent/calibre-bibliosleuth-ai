import pathlib
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/extract_release_notes.py"


def _module():
    namespace = {}
    exec(SCRIPT.read_text(encoding="utf-8"), namespace)
    return namespace


def test_extracts_only_requested_version_body():
    notes = _module()["release_notes"](
        "# Changelog\n\n## [Unreleased]\n\n- Future\n\n## [1.2.0] - 2026-08-25\n\n### Added\n\n- Useful change\n\n## [1.1.0]\n\n- Old change\n",
        "1.2.0",
    )
    assert notes == "### Added\n\n- Useful change\n"


@pytest.mark.parametrize("version", ["1.2", "v1.2.3", "latest"])
def test_rejects_non_semantic_versions(version):
    with pytest.raises(ValueError, match="MAJOR.MINOR.PATCH"):
        _module()["release_notes"]("## 1.2.3\n\n- Change\n", version)


def test_fails_when_version_is_missing_or_empty():
    release_notes = _module()["release_notes"]
    with pytest.raises(ValueError, match="no section"):
        release_notes("## 1.2.3\n\n- Change\n", "2.0.0")
    with pytest.raises(ValueError, match="is empty"):
        release_notes("## 2.0.0\n\n## 1.2.3\n", "2.0.0")


def test_cli_writes_release_notes_file(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    output = tmp_path / "notes.md"
    changelog.write_text("# Changelog\n\n## 1.0.0 — today\n\n- Initial release\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(SCRIPT), "--version", "1.0.0", "--changelog", str(changelog), "--output", str(output)],
        check=True,
    )
    assert output.read_text(encoding="utf-8") == "- Initial release\n"
