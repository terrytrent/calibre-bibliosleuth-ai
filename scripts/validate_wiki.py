import pathlib
import re
import sys


LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "docs/wiki")
    pages = {path.stem for path in root.glob("*.md")}
    failures = []
    for path in sorted(root.glob("*.md")):
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#")):
                continue
            page = pathlib.PurePosixPath(target.split("#", 1)[0]).stem
            if page and page not in pages:
                failures.append("%s: missing wiki page %s" % (path.name, page))
    if failures:
        raise SystemExit("\n".join(failures))
    print("Validated %d wiki pages." % len(pages))


if __name__ == "__main__":
    main()
