from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".html", ".json", ".md", ".py", ".svg", ".txt", ".yml", ".yaml"}
FORBIDDEN_BRAND = ("meta" + "datai").casefold()
FORBIDDEN_PACKAGE = "calibre" + "_ai_plugin"


def _project_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        if any(part in {".git", ".venv", "build", "dist", "__pycache__"} for part in path.parts):
            continue
        yield path


def test_legacy_brand_and_package_names_are_absent():
    offenders = []
    for path in _project_text_files():
        relative = path.relative_to(ROOT)
        searchable = (str(relative) + "\n" + path.read_text(encoding="utf-8")).casefold()
        if FORBIDDEN_BRAND in searchable or FORBIDDEN_PACKAGE in searchable:
            offenders.append(str(relative))
    assert offenders == []
