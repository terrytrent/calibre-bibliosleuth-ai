import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_update_manifest.py"


def _module():
    spec = importlib.util.spec_from_file_location("generate_update_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _template(version="1.2.3"):
    return json.dumps({
        "schema": 1,
        "product": "BiblioSleuth AI",
        "channel": "stable",
        "version": version,
        "published": "2026-09-06T01:06:34Z",
        "minimum_calibre": "99.0.0",
        "changelog": {
            "summary": "A concise release summary.",
            "items": [{"category": "Added", "text": "A useful feature."}],
        },
    })


def test_generates_strict_manifest_and_derives_minimum_calibre():
    rendered = _module().generate_manifest(
        _template(), "1.2.3", "2026-09-07T12:34:56Z"
    )
    manifest = json.loads(rendered)
    assert manifest["version"] == "1.2.3"
    assert manifest["published"] == "2026-09-07T12:34:56Z"
    assert manifest["minimum_calibre"] == "7.0.0"
    assert manifest["changelog"]["items"][0]["category"] == "Added"


def test_rejects_template_for_a_different_release():
    with pytest.raises(ValueError, match="does not match release"):
        _module().generate_manifest(
            _template("1.2.2"), "1.2.3", "2026-09-07T12:34:56Z"
        )


def test_rejects_invalid_generated_publication_date():
    with pytest.raises(ValueError, match="publication date"):
        _module().generate_manifest(_template(), "1.2.3", "not-a-date")


def test_rejects_manifest_that_exceeds_the_client_byte_limit():
    oversized = json.loads(_template())
    oversized["changelog"] = {
        "summary": "🚀" * 300,
        "items": [
            {"category": "Added", "text": "🚀" * 240}
            for _index in range(8)
        ],
    }
    with pytest.raises(ValueError, match="response limit"):
        _module().generate_manifest(
            json.dumps(oversized), "1.2.3", "2026-09-07T12:34:56Z"
        )


def test_cli_writes_only_the_validated_manifest(tmp_path):
    template = tmp_path / "template.json"
    output = tmp_path / "site/latest.json"
    template.write_text(_template(), encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--version",
            "1.2.3",
            "--published",
            "2026-09-07T12:34:56Z",
            "--template",
            str(template),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
    )
    assert json.loads(output.read_text(encoding="utf-8"))["version"] == "1.2.3"
