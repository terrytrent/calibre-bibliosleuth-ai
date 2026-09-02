import hashlib
import pathlib
import subprocess
import sys
import tempfile
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "bibliosleuth_ai"
DIST = ROOT / "dist"
DEPENDENCY_CACHE = ROOT / "build" / "vendor-cache"
RUNTIME_REQUIREMENTS = ROOT / "requirements-runtime.txt"
DEFUSEDXML_WHEEL = DEPENDENCY_CACHE / "defusedxml-0.7.1-py2.py3-none-any.whl"
DEFUSEDXML_SHA256 = "a352e7e428770286cc899e2542b6cdaedb2b4953ff269a210103ec58f6198a61"
RUNTIME_FILES = {
    "__init__.py", "action.py", "config.py", "constants.py", "credentials.py",
    "docs.py", "epub.py", "normalizer.py", "openai_provider.py", "prefs.py",
    "prompt_validation.py", "review.py", "schema.py", "usage.py", "lookup_cache.py",
    "diagnostics.py", "diagnostic_journal.py", "diagnostic_bundle_dialog.py", "metrics.py",
    "statistics_dialog.py", "onboarding.py", "model_catalog.py", "anthropic_provider.py",
    "local_provider.py", "provider_base.py", "provider_config.py", "providers.py", "searxng.py", "transport.py",
    "model_ids.py", "about.txt",
    "plugin-import-name-bibliosleuth_ai.txt",
}
PACKAGE_FILES = {
    **{name: SOURCE / name for name in RUNTIME_FILES},
    "README.md": ROOT / "README.md",
    "LICENSE": ROOT / "LICENSE",
    "CHANGELOG.md": ROOT / "CHANGELOG.md",
    "images/icon.png": ROOT / "assets" / "icon.png",
    "docs/user-guide.html": ROOT / "docs" / "user-guide.html",
}


def _archive_bytes(archive, relative_name, data):
    info = zipfile.ZipInfo(relative_name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def _verify_defusedxml_wheel(path):
    if not path.is_file():
        raise FileNotFoundError("Downloaded dependency is missing: %s" % path)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != DEFUSEDXML_SHA256:
        raise ValueError("Downloaded defusedxml wheel failed its SHA-256 integrity check")


def _ensure_defusedxml_wheel():
    if DEFUSEDXML_WHEEL.is_file():
        _verify_defusedxml_wheel(DEFUSEDXML_WHEEL)
        return DEFUSEDXML_WHEEL

    DEPENDENCY_CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="download-", dir=DEPENDENCY_CACHE) as temporary:
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "pip", "download", "--disable-pip-version-check",
                    "--only-binary=:all:", "--no-deps", "--require-hashes",
                    "--dest", temporary, "--requirement", str(RUNTIME_REQUIREMENTS),
                ],
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise RuntimeError("Unable to download pinned runtime dependencies") from error
        downloaded = pathlib.Path(temporary) / DEFUSEDXML_WHEEL.name
        _verify_defusedxml_wheel(downloaded)
        downloaded.replace(DEFUSEDXML_WHEEL)
    return DEFUSEDXML_WHEEL


def _bundled_defusedxml():
    wheel_path = _ensure_defusedxml_wheel()
    with zipfile.ZipFile(wheel_path) as wheel:
        for name in sorted(wheel.namelist()):
            path = pathlib.PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe path in downloaded defusedxml wheel: %s" % name)
            if name.startswith("defusedxml/") and not name.endswith("/"):
                yield name, wheel.read(name)
            elif name == "defusedxml-0.7.1.dist-info/LICENSE":
                yield "third-party-licenses/defusedxml-LICENSE.txt", wheel.read(name)


def main():
    DIST.mkdir(exist_ok=True)
    target = DIST / "BiblioSleuth-AI.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative_name, path in sorted(PACKAGE_FILES.items()):
            if not path.is_file():
                raise FileNotFoundError("Required plugin file is missing: %s" % path.relative_to(ROOT))
            _archive_bytes(archive, relative_name, path.read_bytes())
        for relative_name, data in _bundled_defusedxml():
            _archive_bytes(archive, relative_name, data)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    checksum = target.with_suffix(target.suffix + ".sha256")
    checksum.write_text("%s  %s\n" % (digest, target.name), encoding="ascii")
    print(target)
    print(checksum)


if __name__ == "__main__":
    main()
