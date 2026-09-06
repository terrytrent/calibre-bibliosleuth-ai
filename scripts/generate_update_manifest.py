"""Build the strict public update manifest used by the release workflow."""

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bibliosleuth_ai import BiblioSleuthAIPlugin  # noqa: E402
from bibliosleuth_ai.update_check import (  # noqa: E402
    UPDATE_RESPONSE_LIMIT,
    UpdateCheckError,
    changelog_dict,
    parse_manifest,
    parse_version,
)


def minimum_calibre_version():
    return ".".join(str(part) for part in BiblioSleuthAIPlugin.minimum_calibre_version)


def generate_manifest(template_text, version, published):
    try:
        parse_version(version)
        template = parse_manifest(template_text)
    except UpdateCheckError as exc:
        raise ValueError(str(exc)) from exc
    if template.version != version:
        raise ValueError(
            "update manifest template version %s does not match release %s"
            % (template.version, version)
        )

    manifest = {
        "schema": 1,
        "product": "BiblioSleuth AI",
        "channel": "stable",
        "version": version,
        "published": published,
        "minimum_calibre": minimum_calibre_version(),
        "changelog": changelog_dict(template.changelog),
    }
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    try:
        parse_manifest(rendered)
    except UpdateCheckError as exc:
        raise ValueError(str(exc)) from exc
    if len(rendered.encode("utf-8")) > UPDATE_RESPONSE_LIMIT:
        raise ValueError("generated update manifest exceeds the client response limit")
    return rendered


def main():
    parser = argparse.ArgumentParser(
        description="Generate BiblioSleuth AI's validated release manifest"
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--published", required=True)
    parser.add_argument("--template", default="docs/update-site/latest.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = pathlib.Path(args.template)
    output = pathlib.Path(args.output)
    rendered = generate_manifest(
        source.read_text(encoding="utf-8"), args.version, args.published
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print("Generated update manifest for %s" % args.version)


if __name__ == "__main__":
    main()
