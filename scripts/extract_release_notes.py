import argparse
import pathlib
import re


VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
HEADING = re.compile(r"^##\s+(.+?)\s*$")


def release_notes(changelog, version):
    if not VERSION.fullmatch(version):
        raise ValueError("release version must use MAJOR.MINOR.PATCH")

    lines = changelog.splitlines()
    start = None
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if match and re.match(rf"^\[?{re.escape(version)}\]?(?:\s|$)", match.group(1)):
            start = index + 1
            break
    if start is None:
        raise ValueError("CHANGELOG.md has no section for version %s" % version)

    end = len(lines)
    for index in range(start, len(lines)):
        if HEADING.match(lines[index]):
            end = index
            break
    notes = "\n".join(lines[start:end]).strip()
    if not notes:
        raise ValueError("changelog section for version %s is empty" % version)
    return notes + "\n"


def main():
    parser = argparse.ArgumentParser(description="Extract one version's GitHub Release notes from CHANGELOG.md")
    parser.add_argument("--version", required=True)
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = pathlib.Path(args.changelog)
    output = pathlib.Path(args.output)
    notes = release_notes(source.read_text(encoding="utf-8"), args.version)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(notes, encoding="utf-8")
    print("Extracted release notes for %s to %s" % (args.version, output))


if __name__ == "__main__":
    main()
