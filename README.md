# BiblioSleuth AI for Calibre

<p align="center">
  <img src="assets/icon.png" alt="BiblioSleuth AI blue metadata-tag icon" width="140">
</p>

[![CI](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/tests.yml/badge.svg)](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/tests.yml)
[![Security](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/security.yml/badge.svg)](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/security.yml)
[![Code Quality](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/quality.yml/badge.svg)](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/quality.yml)
[![Assurance](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/assurance.yml/badge.svg)](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/assurance.yml)
[![Calibre Compatibility](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/calibre-compatibility.yml/badge.svg)](https://github.com/terrytrent/calibre-bibliosleuth-ai/actions/workflows/calibre-compatibility.yml)
[![Tagged Release](https://img.shields.io/github/v/release/terrytrent/calibre-bibliosleuth-ai?display_name=tag&label=tagged%20release)](https://github.com/terrytrent/calibre-bibliosleuth-ai/releases/latest)
[![Release Downloads](https://img.shields.io/github/downloads/terrytrent/calibre-bibliosleuth-ai/total?label=downloads)](https://github.com/terrytrent/calibre-bibliosleuth-ai/releases)
[![Last Commit](https://img.shields.io/github/last-commit/terrytrent/calibre-bibliosleuth-ai?label=last%20commit)](https://github.com/terrytrent/calibre-bibliosleuth-ai/commits/main)
[![History: CHANGELOG](https://img.shields.io/badge/History-CHANGELOG-007ec6.svg)](CHANGELOG.md)
[![Status: Stable](https://img.shields.io/badge/Status-Stable-44a833.svg)](#project-status)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Calibre 7+](https://img.shields.io/badge/calibre-7%2B-blue.svg)](https://calibre-ebook.com/)
[![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#install)

- **Author:** Terry Trent
- **Version:** 1.0.0
- **License:** MIT
- **Platforms:** Windows, macOS, and Linux
- **Minimum Calibre version:** 7.0.0
- **Bundled dependency:** `defusedxml` 0.7.1 (Python Software Foundation License)

BiblioSleuth AI is a Calibre interface-action plugin that extracts selected EPUB
metadata and confidently identified title/copyright pages, researches the exact edition with OpenAI web search,
and lets you approve individual metadata fields before updating the library.

Research runs as a native Calibre background job. Its progress and log appear in
the Jobs panel. Completion shows a persistent, non-modal results-ready notice;
review opens only when the user requests it.

High- and medium-confidence proposals are selected by default. Low-confidence
proposals remain visible but must be selected manually.

BiblioSleuth AI includes guided first-run setup, tabbed settings, batch preflight,
clearer diffs and confidence badges, rich description and tag editors, source
labels, keyboard shortcuts, navigable batch review, final confirmation, session
undo, cache provenance, model capability testing, redacted diagnostics, and
actionable failure recovery.

BiblioSleuth AI is an independent community plugin. It is not affiliated with or
endorsed by Calibre or OpenAI.

## Project status

**Stable.** BiblioSleuth AI is usable for normal single-book and small-batch metadata
research. Releases pass the automated test, packaging, security, and quality
checks shown above. Because metadata is generated from AI-assisted web research,
users should still review proposed values before applying them. See the
[changelog](CHANGELOG.md) for release history and known changes.

Pull requests and releases are additionally checked for dependency changes,
project-specific security invariants, workflow vulnerabilities, documentation
quality, link integrity, coverage regressions, and real plugin installation in
the oldest and current supported Calibre releases. Release downloads include a
CycloneDX SBOM, SHA-256 checksum, and GitHub artifact attestations.

To correct a proposed value before applying it, select the field and click
**Edit proposed value…** (or double-click its field/proposed-value cell). The
editor uses one item per line for authors, an add/remove tag list, `type:value`
lines for identifiers, separate series name/index controls, and a rendered/source
description editor with counts. Saved overrides are
automatically selected and applied in the same review pass.

Settings content wraps within the available window so no horizontal scrolling is
required. The System Prompt tab can display the bundled default independently of
the effective/custom-prompt preview. Review uses the active Calibre palette and
typographic changed/unchanged indicators for readable light and dark themes.

Use **View all details…** to open a single resizable, scrollable comparison of
every complete current and proposed value, including long tag lists, comments,
confidence labels, and evidence links.

## Install

1. Run `python3 scripts/build_plugin.py`.
2. In Calibre, open Preferences → Plugins → Load plugin from file and choose
   `dist/BiblioSleuth-AI.zip`.
3. Add **BiblioSleuth AI** to the desired toolbar/context menu.
4. Configure an OpenAI API key in the plugin settings (stored in the operating
   system credential vault when available) or set
   `OPENAI_API_KEY` before starting Calibre.

Restart Calibre after installing or updating the plugin. To uninstall it, open
Preferences → Plugins, select BiblioSleuth AI under User interface action plugins,
and choose Remove plugin. Removing the plugin does not modify EPUB files or
undo metadata already applied. Use **Delete Stored API Key** before uninstalling if
you also want to remove its operating-system credential-vault entry.
Use **Clear Statistics…** as well if you want to delete locally retained
performance history before removing the plugin.

The default model is the configurable `gpt-5.6-luna`, selected for its
low token price while retaining Responses API structured output, web search,
and reasoning support. Metadata research and custom-prompt
validation/repair make billable API calls. Only selected OPF metadata and the configured
amount of identified title/copyright-page text are sent; unidentified pages, chapters, and complete books are never uploaded.

Model selection uses a non-editable list containing bundled defaults plus relevant
models visible to the configured OpenAI account. A successful account list is cached for seven days; settings
refreshes an expired list when possible, and **Refresh Model Choices** performs an
explicit refresh. Listing models is not a generation or web-search request. Because
the Models API provides identity rather than tool-capability details, use **Test
Model Capabilities…** before adopting an unfamiliar model.

The default Balanced optimization preset uses up to 6,000 characters of identified
title/copyright-page evidence, low web-search context, low reasoning, a 2,000-token output cap, and
up to three evidence URLs per field.
Economy and Thorough presets are included, while Custom unlocks each control.
Jobs report input, cached-input, output, reasoning, total-token, and web-search
usage per lookup and per batch, together with a clearly dated approximate USD
cost for recognized models. Stable prompt-cache routing and configurable evidence limits reduce
repeated input and output overhead.

The plugin includes its own book-search icon for Calibre toolbars and menus.
Comprehensive documentation is bundled into the plugin and available from the
toolbar icon's drop-down menu, the configuration screen, or the first-run API-key prompt.
The main toolbar icon starts a lookup; its separate arrow opens configuration,
About, documentation, setup, fresh research, pending bulk acceptance, cache
clearing, session undo, statistics, redacted diagnostics, and diagnostic-log collection.

Choose **Research Specific Fields…** from that arrow menu when only part of a
book's metadata needs attention. A checklist offers Title, Authors, Series,
Tags, Identifiers, Published Date, Publisher, and Description. Only the checked
fields are requested from OpenAI and shown in review. **Series and series index**
is one coupled choice: selecting it always asks for both the series name and the
book's number in that series. The normal main-icon action continues to research
all supported fields.

Successful lookups are cached only in memory for the current Calibre session,
keyed by the EPUB SHA-256 fingerprint, model, effective prompt, requested-field
set, and research settings. Repeating an identical lookup avoids another billable request while
still opening the normal review screen. Use **Research Fresh (Ignore Cache)**
when current web research is required, or clear the cache from the same menu.

Field-specific research usually reduces structured-output tokens, especially for
long descriptions or tag lists. Exact-edition identification and web research are
still performed, so input tokens, search calls, elapsed time, and cost do not
necessarily fall in direct proportion to the number of selected fields.

Batch preflight shows eligible EPUBs, skipped selections, preset, cache behavior,
and a rough cost range. It never reads or fingerprints complete EPUB files on the
GUI thread; fingerprinting and exact cache detection occur in the cancellable
background job with progress reporting. Review uses explicit Previous, Skip This Book, and
Approve Selected Fields navigation labels; metadata is written only after final
confirmation. The toolbar menu can undo the
last batch during the same Calibre session. Cached reviews show their research
time and model and offer a fresh lookup. Review shortcuts are `Space` to toggle,
`Enter` to edit, `Ctrl+Shift+A` for recommendations, and `Ctrl+Return` to advance.

The final update and API-usage summary opens in a resizable, scrollable window.
Its complete text can be selected normally or copied with **Copy summary**.

When research completes, the results-ready notice remains until **Review books**,
**Hide notification**, or **Abort** is selected. Hiding preserves the completed
results: click the main BiblioSleuth AI icon later to review them. Abort discards all
waiting results without changing metadata. A numbered badge on the toolbar icon
shows how many books are waiting; while results are pending, clicking the main
icon reviews them instead of starting another lookup.

Users who do not want field-by-field review can choose **Accept all…** in the
results-ready notice or **Accept All Pending Results…** in the toolbar menu. A
confirmation reports the affected books and counts inferred and low-confidence
fields. Confirming applies every non-null proposal, verifies that each record and
EPUB is unchanged, and creates one session undo checkpoint. This mode is faster
but intentionally bypasses the principal accuracy safeguard; use it only when
the risk of incorrect AI metadata is acceptable.

During a multi-book review, **Accept all remaining books…** provides the same
confirmed bulk behavior for the current and all later books while preserving
edits already made. Navigation buttons use explicit outcomes: **Review previous
book**, **Skip this book and review next**, and **Approve selected fields and
review next** (with “finish” wording on the last book).
All review navigation and bulk-action buttons share one aligned horizontal row.

## Performance statistics

BiblioSleuth AI records privacy-safe performance statistics locally by default. Open
**Statistics…** from the toolbar menu or the Statistics settings tab to view:

- researched/successful/failed/cancelled/applied/skipped/discarded counts;
- live requests, cache hits, total time, average, median, fastest, slowest, P90,
  P95, and books per minute;
- average queue, fingerprint, cache, extraction, OpenAI, validation, review-wait,
  and metadata normalization/application time;
- token/search totals, cost totals and averages, cost/tokens per success, and
  estimated savings from repeated session-cache hits;
- comparison tables grouped by preset, model, live/cache, outcome, date, or
  single-book/batch operation.

Filters cover the current session, 7/30/90 days, or all retained history plus
model, preset, source, and outcome. Users can disable collection, choose retention
days and maximum records, clear history, or export the filtered records to CSV.
The defaults retain at most 1,000 records and 90 days, whichever is reached first.
No charts are included.

Statistics contain only timing/settings/usage/outcome values and a salted,
truncated EPUB fingerprint. They never store titles, authors, library IDs, paths,
book text, prompts, responses, evidence URLs, API keys, or exact error messages.

## Collecting diagnostic logs

Failure dialogs include **Collect diagnostic logs…**, and the toolbar menu offers
**Collect Recent Diagnostic Logs…** after a dialog has closed. BiblioSleuth AI retains a
bounded local journal of at most 20 job summaries for seven days. Successful jobs
keep only minimal stage/timing/usage counts; failures additionally keep sanitized
error categories, optional sanitized messages/stacks, anonymous book identifiers,
and content-free EPUB structural facts such as archive/member sizes, encryption
count, and container declaration flags.

Before saving, a preview lists every file and privacy exclusion. Users choose the
ZIP destination and whether exact sanitized errors/stacks are included. Bundles
contain README, manifest, redacted environment/configuration and aggregate
statistics, and recent journal JSON. Nothing is uploaded automatically.
The same preview can permanently clear retained diagnostic history.

Bundles never contain keys or authorization headers, titles, authors, library IDs
or paths, EPUB text or metadata values, prompts, model responses, evidence URLs,
credential-vault data, or unredacted URLs. Review a bundle before sharing it.

## Security and privacy

- The API key is never stored in Calibre's JSON preferences. BiblioSleuth AI uses
  macOS Keychain, Windows Credential Manager, or Linux Secret Service when
  available; otherwise the key is session-only. `OPENAI_API_KEY` takes priority.
- The settings screen displays **✓ API key is stored securely and active** when
  a credential exists, while never revealing its value. The field is labeled
  **Replace API key**: leaving it blank retains the existing credential,
  entering a new key replaces it, and you can use
  **Delete Stored API Key** to remove the vault and session copies.
- Requests use HTTPS and `store=false`. Only selected OPF metadata and bounded
  text from confidently identified title and copyright pages are sent. Unidentified
  pages, contents, prefaces, introductions, dedications, and body chapters are
  excluded rather than used as fallback evidence.
- API redirects are refused so authorization headers cannot leave the fixed
  OpenAI API origin. This does not limit hosted web search or consume an evidence-URL slot.
- EPUB archive reads, API responses, metadata values, URLs, and generated HTML
  are locally bounded and validated. Comments allow only paragraphs, line
  breaks, bold, italics, and lists.
- EPUB and web text are treated as untrusted evidence. Instruction-like EPUB
  text disables automatic field selection, and model-provided evidence links
  require confirmation before opening.
- Metadata is applied only after explicit user confirmation—either field-level
  review or the clearly warned bulk-accept workflow—and the EPUB file itself is
  never rewritten.
- Simple legacy external `DOCTYPE` declarations in EPUB package XML are removed
  without resolution; bundled `defusedxml` independently blocks DTDs, entity
  declarations, and external references.
- Redacted diagnostics exclude keys, EPUB passages, full prompts, responses,
  evidence URLs, and library metadata.
- Internal history and exported statistics are written with restrictive local
  permissions where supported; malformed retained data is discarded safely.

macOS Keychain integration is exercised on macOS. Windows Credential Manager
and Linux Secret Service adapters have automated mock coverage but still need
field testing on those operating systems.

## Custom prompts

Leave the override empty to use the bundled prompt. A custom prompt cannot be
saved until it passes an AI review and a schema-constrained synthetic test. If
repair is needed, the plugin shows a summary and requires explicit acceptance.
The canonical response schema, allowed web-search tool, disclosure limits, and
local validation cannot be changed by the prompt.

## Development

Run `make help` to see the common development commands. The usual workflow is:

```sh
make test
make build
make verify
make install
```

`make release` runs the tests followed by a deterministic build, ZIP integrity
check, and checksum verification. The Makefile is a convenience layer; the
cross-platform Python packager remains the authoritative implementation.

Without Make, run tests with `.venv/bin/pytest`. Build the distributable with
`python3 scripts/build_plugin.py`, then install/update the built ZIP with:

```sh
/Applications/calibre.app/Contents/MacOS/calibre-customize -a dist/BiblioSleuth-AI.zip
```

The repository is organized by purpose:

```text
assets/                     Plugin artwork
docs/                       User guide and release material
docs/wiki/                  Canonical, reviewable GitHub Wiki source
scripts/                    Build and packaging tools
Makefile                    Shortcuts for test/build/verify/install/release
src/calibre_ai_plugin/      Runtime plugin source and bundled metadata
tests/                      Calibre-independent automated tests
build/                      Generated dependency cache (ignored by Git)
dist/                       Generated ZIP and checksum (not committed)
```

Calibre plugins require their Python modules and resources at the root of the
installed ZIP. The build script deliberately maps the organized source tree into
that flat installation layout and extracts approved pure-Python modules from the
downloaded wheel; do not install `src/calibre_ai_plugin` directly. Runtime dependency
versions and hashes are recorded in `requirements-runtime.txt`. The first build (and
the first build after `make clean`) downloads the pinned wheel from PyPI into the
Git-ignored `build/vendor-cache` directory. The builder verifies its SHA-256 hash
again before packaging it. Later builds reuse that verified cache, and the finished
plugin ZIP remains self-contained.

Run the security and core test suite before packaging:

```sh
.venv/bin/pytest -q
make verify
```

The default `make install` command targets Calibre's standard macOS location.
On another platform or a nonstandard installation, override it—for example,
`make install CALIBRE_CUSTOMIZE=calibre-customize`. The Python commands remain
available on systems without Make, including typical Windows environments.

The ZIP is deterministic for identical committed inputs. GitHub Actions runs
the core suite and byte-compilation checks on current Ubuntu, macOS, and Windows
runners with Python 3.11 and 3.13, then performs one deterministic package and
checksum verification after the matrix passes. Native Calibre UI integration
still requires manual testing in Calibre, while a separate compatibility workflow
installs and registers the built ZIP in Calibre 7.0.0 and 9.13.0 on Linux. Obsolete branch/PR runs are cancelled,
and branch pushes run continuously only for `main` to avoid duplicate checks.

The badges at the top of this README link to the latest CI, security, and
code-quality runs plus the latest published GitHub Release. Security runs Trivy filesystem,
dependency, secret, and configuration scanning; a hash-enforcing Python
dependency audit; Bandit; and CodeQL. It also
runs every Monday so newly disclosed vulnerabilities can be detected without a
source change. Trivy and CodeQL findings are uploaded to GitHub code scanning.

The code-quality workflow blocks syntax, broken-control-flow, and undefined-name
regressions with a pinned, correctness-oriented Ruff ruleset. Qlty runs its
broader linters and analyzers and records code smells and maintainability metrics;
those reports remain informational while existing style debt is improved
incrementally. Complete reports are retained as workflow artifacts for 30 days.
The dedicated security workflow remains the strict vulnerability gate.

The assurance workflow reviews dependency changes, enforces five project-specific
Semgrep invariants, audits workflow syntax and security with actionlint and zizmor,
checks Markdown and links, and prevents total headless test coverage from dropping
below the current 35% baseline. All workflow actions—not only third-party scanners—
are pinned to immutable commit IDs. Canonical pages under `docs/wiki/` are validated
on pull requests and synchronized to the GitHub Wiki after merging to `main`.

### Tagged GitHub releases

After a release commit has been merged to `main`, confirm that every documented
and embedded version matches. Then push an annotated semantic version tag:

```sh
git switch main
git pull --ff-only
git tag -a v1.0.0 -m "BiblioSleuth AI 1.0.0"
git push origin v1.0.0
```

The workflow refuses non-`vMAJOR.MINOR.PATCH` tags, tags whose commit is not on
`main`, and tags that disagree with the plugin version. It then runs the complete
Windows/macOS/Linux test matrix, Bandit, CodeQL, and Trivy security scans, and a
Qlty analysis. It then builds the deterministic ZIP, verifies its contents and
checksum, generates a CycloneDX SBOM, creates GitHub artifact attestations, and
uploads the ZIP, checksum, and SBOM to a generated GitHub Release. Only the
publisher job receives `contents: write`; the package job receives only the
identity permissions required to create attestations, and all other jobs are read-only.
Every action is pinned to an immutable commit hash, and checkout
credentials are not retained. Failed gates do not create a release.
The release description is the matching version section from `CHANGELOG.md`;
the workflow refuses to publish when that section is missing or empty.

CodeQL must be available for the repository. Public repositories support it
directly; private repositories may require GitHub Code Security. Dependabot
checks first-party GitHub Action versions weekly.

See [CHANGELOG.md](CHANGELOG.md), [SECURITY.md](SECURITY.md), and
[CONTRIBUTING.md](CONTRIBUTING.md). A module-by-module map and common commands are
in [docs/development.md](docs/development.md). The MobileRead release-thread checklist and
first-post template are in [docs/mobileread-release-template.md](docs/mobileread-release-template.md).

## Support and limitations

An OpenAI Platform account with API billing is required. Searches, model calls,
and custom-prompt validation can incur charges. AI output and online catalogs
can be wrong; review every field, especially identifiers, dates, publisher, and
series index. BiblioSleuth AI supports EPUB inspection only and does not retrieve
covers or rewrite embedded metadata.

When reporting a problem, include the BiblioSleuth AI and Calibre versions, operating
system, optimization preset, and a redacted job error. Never include an API key,
complete custom prompt, copyrighted EPUB passage, or private library export.
