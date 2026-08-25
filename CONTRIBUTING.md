# Contributing

Contributions should preserve BiblioSleuth AI's core boundaries: bounded EPUB
disclosure, fixed tool availability, local schema validation, safe comments
HTML, explicit metadata review, and no EPUB rewriting.

Before submitting a change:

1. Add or update tests, including adversarial cases for security-sensitive code.
2. Run `.venv/bin/pytest -q`.
3. Run `python3 scripts/build_plugin.py` and `unzip -t dist/BiblioSleuth-AI.zip`.
4. Test installation and the affected workflow in a supported Calibre version.
5. Do not commit API keys, Calibre preferences, EPUBs, library exports, logs, or
   copyrighted source passages.

For UI changes, exercise first-run setup, light and dark themes, keyboard-only
review, explicit batch navigation labels, bulk-accept warnings, final
confirmation, undo, cache-hit refresh, and failure recovery buttons.

Timing changes must use a monotonic clock. Statistics changes must preserve bounded
storage, atomic writes, anonymized book identifiers, CSV redaction, retention/filter
tests, and the prohibition on titles, paths, content, prompts, responses, and secrets.

Diagnostic changes must preserve seven-day/20-entry limits, atomic restrictive-file
writes, explicit local-only export, previewed contents, optional detailed errors,
bounded text, secret/URL/path redaction, anonymous book IDs, and adversarial tests.

Windows Credential Manager and Linux Secret Service changes should be tested on
their actual platforms before being described as field-tested.

If Make is available, `make release` performs steps 2 and 3 together, while
`make install` builds and installs the resulting ZIP. The underlying Python
commands remain supported for Windows and other environments without Make.

Publishing is intentionally separate from local packaging. A `vMAJOR.MINOR.PATCH`
tag pushed for a commit on `main` starts `.github/workflows/release.yml`. The tag
must match the embedded plugin version. GitHub publishes only after cross-platform
tests, Bandit, CodeQL, deterministic packaging, ZIP validation, and checksum
verification pass. Do not replace a failed release tag; fix the cause, increment
the version, merge it, and create a new tag.

Runtime code belongs in `src/calibre_ai_plugin`, artwork in `assets`, user and
release documentation in `docs`, packaging utilities in `scripts`, and tests in
`tests`. When adding a runtime file or bundled resource, add its source-to-ZIP
mapping in `scripts/build_plugin.py`; the generated Calibre ZIP intentionally has
a flatter layout than this repository.
