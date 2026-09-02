import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_is_deterministic_and_checksummed():
    subprocess.run([sys.executable, "scripts/build_plugin.py"], cwd=ROOT, check=True, capture_output=True)
    target = ROOT / "dist" / "BiblioSleuth-AI.zip"
    first = hashlib.sha256(target.read_bytes()).hexdigest()
    subprocess.run([sys.executable, "scripts/build_plugin.py"], cwd=ROOT, check=True, capture_output=True)
    second = hashlib.sha256(target.read_bytes()).hexdigest()
    assert first == second
    assert (target.with_suffix(".zip.sha256")).read_text(encoding="ascii") == "%s  BiblioSleuth-AI.zip\n" % first
    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        searchable = "\n".join(names).casefold()
        for name in names:
            if Path(name).suffix.casefold() in {".html", ".md", ".py", ".txt"}:
                searchable += "\n" + archive.read(name).decode("utf-8").casefold()
    assert {
        "__init__.py", "action.py", "images/icon.png", "docs/user-guide.html",
        "providers.py", "anthropic_provider.py", "local_provider.py", "searxng.py",
        "defusedxml/ElementTree.py", "third-party-licenses/defusedxml-LICENSE.txt",
    } <= names
    assert not any(name.startswith(("src/", "assets/", "scripts/", "tests/")) for name in names)
    assert ("meta" + "datai").casefold() not in searchable
    assert "calibre" + "_ai_plugin" not in searchable


def test_downloaded_dependency_is_pinned_hash_verified_and_not_committed():
    requirements = (ROOT / "requirements-runtime.txt").read_text(encoding="utf-8")
    builder = (ROOT / "scripts/build_plugin.py").read_text(encoding="utf-8")
    assert "defusedxml==0.7.1" in requirements
    assert "a352e7e428770286cc899e2542b6cdaedb2b4953ff269a210103ec58f6198a61" in requirements
    assert "DEFUSEDXML_SHA256" in builder
    assert "pip\", \"download" in builder
    assert not (ROOT / "vendor").exists()
    assert "build/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_epub_uses_calibre_plugin_local_bundled_dependency():
    source = (ROOT / "src/bibliosleuth_ai/epub.py").read_text(encoding="utf-8")
    assert "from .defusedxml import ElementTree as ET" in source
    assert "from .defusedxml.common import DefusedXmlException" in source


def test_repository_uses_separated_source_and_tooling_layout():
    assert (ROOT / "src/bibliosleuth_ai/action.py").is_file()
    assert (ROOT / "assets/icon.png").is_file()
    assert (ROOT / "scripts/build_plugin.py").is_file()
    assert not (ROOT / "action.py").exists()
    assert not (ROOT / "build_plugin.py").exists()
