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
- **Version:** 1.1.0
- **License:** MIT
- **Platforms:** Windows, macOS, and Linux
- **Minimum Calibre version:** 7.0.0
- **Bundled dependency:** `defusedxml` 0.7.1 (Python Software Foundation License)

BiblioSleuth AI is a Calibre interface-action plugin that extracts selected EPUB
metadata and confidently identified title/copyright pages, researches the exact edition with a selected AI and web-search provider,
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
endorsed by Calibre, OpenAI, Anthropic, Ollama, LM Studio, or SearXNG.

## Demo

<p align="center">
  <img src="assets/demo.gif" alt="BiblioSleuth AI researching and reviewing EPUB metadata in Calibre" width="800">
</p>

### Workflow highlights

**Guided setup:** The first-run assistant explains what BiblioSleuth AI does and
walks new users through the required configuration.

<p align="center">
  <img src="assets/screenshot-guided-setup.png" alt="BiblioSleuth AI guided first-run setup in Calibre" width="800">
</p>

**Background research:** Metadata retrieval runs as a native, cancellable Calibre
job with visible status, progress, and elapsed time.

<p align="center">
  <img src="assets/screenshot-background-job.png" alt="BiblioSleuth AI metadata research running in Calibre's Jobs window" width="800">
</p>

**Field-level review:** Current and proposed metadata appear side by side with
confidence, evidence, usage, and cost information before anything is applied.

<p align="center">
  <img src="assets/screenshot-metadata-review.png" alt="BiblioSleuth AI field-level metadata review window" width="800">
</p>

**Complete comparison:** A scrollable detail view makes long values, identifiers,
confidence levels, and supporting evidence easier to inspect.

<p align="center">
  <img src="assets/screenshot-full-comparison.png" alt="BiblioSleuth AI complete current and proposed metadata comparison" width="800">
</p>

**Performance statistics:** Local, privacy-preserving statistics summarize lookup
speed, timing stages, outcomes, token usage, cache hits, and estimated cost.

<p align="center">
  <img src="assets/screenshot-statistics.png" alt="BiblioSleuth AI retrieval performance and usage statistics" width="800">
</p>

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
4. Choose OpenAI, Claude, Ollama, or LM Studio in plugin settings. Configure the
   selected hosted provider's API key, or start the selected local model server.

Restart Calibre after installing or updating the plugin. To uninstall it, open
Preferences → Plugins, select BiblioSleuth AI under User interface action plugins,
and choose Remove plugin. Removing the plugin does not modify EPUB files or
undo metadata already applied. Use **Delete Stored API Key** before uninstalling if
you also want to remove its operating-system credential-vault entry.
Use **Clear Statistics…** as well if you want to delete locally retained
performance history before removing the plugin.

The default provider remains OpenAI with configurable `gpt-5.6-luna`, selected for its
low token price while retaining Responses API structured output, web search,
and reasoning support. Metadata research and custom-prompt
validation/repair make billable API calls. Only selected OPF metadata and the configured
amount of identified title/copyright-page text are sent; unidentified pages, chapters, and complete books are never uploaded.

Model selection uses a non-editable list containing provider defaults plus models
visible to the configured account or local server. A successful provider list is cached for seven days; settings
refreshes an expired list when possible, and **Refresh Model Choices** performs an
explicit refresh. Listing models is not a generation or web-search request. Because
the Models API provides identity rather than tool-capability details, use **Test
Model Capabilities…** before adopting an unfamiliar model.

Claude choices are limited to model families supporting the strict structured
output required by BiblioSleuth AI, including compatible Opus, Sonnet, Haiku,
Fable, and Mythos families. Current supported Claude choices are bundled so a new
installation is not limited to the prior default; account-visible compatible
models are added by refresh. Claude defaults to `claude-sonnet-5`. The effort
control is sent only to Claude models that support it. Incompatible results do
not make an empty model cache appear fresh.
If Ollama or LM Studio returns no models, settings gives provider-specific
instructions for pulling or loading one.

## AI and web-search providers

BiblioSleuth AI supports four inference providers:

- **OpenAI:** Responses API with either OpenAI hosted web search or SearXNG.
- **Claude:** the direct Anthropic Messages API with either Claude hosted web
  search or SearXNG. Claude is also used for custom-prompt review, repair,
  synthetic validation, connection tests, and metadata generation when selected.
  Hosted research uses one cited search request followed by native strict JSON
  Schema generation, as Anthropic does not permit citations and structured output
  in the same request. Full-record generation is split into two bounded strict
  calls because Anthropic rejects the complete eight-field grammar. The first
  establishes the edition match; the second receives that selected match and
  returns only its remaining fields. Field-specific requests containing four or
  fewer fields remain one strict call.
  Anthropic receives compact generation grammars containing required keys,
  shapes, enums, and nullability; BiblioSleuth AI still applies every canonical
  length, count, pattern, range, and URL constraint locally before presenting a
  result.
- **Ollama:** its local OpenAI-compatible API with SearXNG research.
- **LM Studio:** its local OpenAI-compatible API with SearXNG research.

OpenAI and Claude keys are kept in separate operating-system vault entries and
can also be supplied as `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. A protected LM
Studio server may use `LM_STUDIO_API_KEY`. Ollama normally needs no token, but an
optional token entered for it receives its own vault identity. A credential is
never copied from one provider to another. Anthropic identity-linked or
multi-workspace keys also need the non-secret `wrkspc_…` workspace ID in settings
or `ANTHROPIC_WORKSPACE_ID`; workspace-scoped keys may leave it blank.

### Local model setup

For Ollama, install Ollama, pull an instruct model that reliably supports strict
JSON Schema output, and leave its API listening on the loopback default
`http://127.0.0.1:11434/v1`. For example, use Ollama's documented `ollama pull
<model>` workflow, then select **Ollama**, refresh models, and run both connection
and capability tests in BiblioSleuth AI.

For LM Studio, use the full desktop application's **Developer** page rather than
the Bionic chat surface alone. Download and load a schema-capable,
**non-thinking** instruct model, then start the local API server. The server root
is `http://127.0.0.1:1234`, while the BiblioSleuth AI endpoint must include the
OpenAI-compatible suffix: `http://127.0.0.1:1234/v1`. Keep the server running
throughout research. If server authentication is enabled, create an LM Studio
token and store it through BiblioSleuth AI. Avoid LAN exposure unless it is
deliberate and protected. On a memory-limited Mac, use a context length around
8192 and one concurrent prediction as a conservative starting point.

Thinking/reasoning variants are not recommended for LM Studio integration. Some
place the entire schema result in the nonstandard `reasoning_content` field while
returning an empty standard `content` field; BiblioSleuth AI rejects that as
invalid structured output. In maintainer testing, `qwen/qwen3-4b-2507` completed
the integration workflow, while `qwen/qwen3-4b-thinking-2507` exhibited this exact
failure. Model availability and behavior can change, so run both readiness tests.

Local model quality, context capacity, structured-output reliability, speed, and
hardware requirements vary considerably. A successful connection test proves
only reachability; the capability test checks the behavior BiblioSleuth AI needs.
Exact-edition research is a demanding task: the model must reconcile conflicting
sources, distinguish closely related editions, follow a large schema, and avoid
inventing facts or citations. Strong models are therefore necessary for good
results. Lightweight models are useful for confirming that Ollama or LM Studio is
configured correctly, but should not be assumed to match OpenAI or Claude.
Maintainer testing on an M2 Mac with 16 GB of unified memory found that locally
practical models produced results well below the quality of the supported hosted
providers. Review local-model proposals especially carefully; hardware able to
run a server does not guarantee enough capacity for a high-quality research model.
Local models also commonly need longer request timeouts, particularly on their
first request after loading. As model size approaches available memory, loading,
prompt processing, generation, and macOS swapping can push a lookup well beyond
60 seconds. Start with 120 seconds for smaller models and consider 180–300 seconds
for larger models, while treating sustained memory pressure or repeated timeouts
as evidence that the model is too large for comfortable use.
The first-run wizard sends local-provider users to the full settings screen so a
model, endpoint, SearXNG service, and both readiness tests are not accidentally
skipped.

Changing the AI provider or model requires a custom prompt to be validated again.
This reruns the disclosed synthetic structured-output test against the exact
runtime selected by the user.

### No-per-query-cost SearXNG research

[SearXNG](https://docs.searxng.org/) is a separate, user-managed metasearch
service. BiblioSleuth AI does not bundle, install, start, or update it. Install it
using the official Docker/Podman Compose guidance, keep it on a trusted loopback
or HTTPS endpoint, and enable JSON results in `settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

Verify it independently:

```sh
curl 'http://127.0.0.1:8080/search?q=ISBN+9780143127741&format=json'
```

Then choose **SearXNG** under Web research, enter the server address, and select
**Test SearXNG**. BiblioSleuth AI constructs bounded edition-oriented searches,
calls the SearXNG JSON API, removes unsafe result URLs, limits snippets and result
counts, marks all returned content as untrusted evidence, and supplies it to the
selected AI. No MCP package is required.

A successfully parsed SearXNG JSON response is considered ready even when that
particular test query returns no matches. Cancelling a job stops additional
SearXNG queries and prevents a model request from starting when possible; an
already-running network request may still take until its response or timeout.
If a provider response finishes just after cancellation, its usage and timing
remain in Statistics even though its metadata result is discarded. Books that
never started remain explicit zero-cost cancellations. A job with no reviewable
results shows its own non-modal completion notice and is not left invisibly in
the pending-results queue.

Claude hosted search uses a bounded intermediate handoff containing sanitized
research text and citation metadata. Opaque provider search state is not copied
into the strict structured-output request.

SearXNG has no per-query API fee, but it still sends queries to its configured
public search engines. Those engines can throttle traffic, present CAPTCHAs, or
change behavior. Running the service also uses the user's own compute, network,
and maintenance time.

### Choosing a search path

OpenAI and Claude users can choose their provider's hosted search for the simplest
setup or SearXNG for application-managed search without a hosted-search fee.
Ollama and LM Studio require SearXNG. Hosted provider search and model inference
may be billable; SearXNG results still contribute to model input-token usage.

Maintainer testing currently ranks the complete research paths as follows for
result quality (best to worst):

1. **OpenAI with OpenAI hosted search** — best overall results; second-lowest API
   cost among the four hosted-model paths tested.
2. **OpenAI with SearXNG** — lowest tested API cost and results nearly as good as
   OpenAI hosted search.
3. **Claude with Claude hosted search** — results on par with OpenAI in testing,
   but the highest API cost of the four hosted-model paths.
4. **Claude with SearXNG** — results on par with OpenAI plus SearXNG and the
   third-lowest tested API cost.
5. **LM Studio with SearXNG** — quality depends heavily on the local model;
   `qwen/qwen3-4b-2507` produced acceptable results on the maintainer's M2 Mac.
6. **Ollama with SearXNG** — also model-dependent; the tested LM Studio Qwen 3
   4B path outperformed Ollama with `gemma3:4b` and `qwen3:8b`.

This is a practical, small-sample observation rather than a permanent benchmark.
Books, model revisions, search results, prompts, and hardware can change the
ordering. The API-cost ranks compare only the four OpenAI/Claude paths: local
providers have no per-request model API fee but use local hardware, power, and
maintenance time.

The default Balanced optimization preset uses up to 6,000 characters of identified
title/copyright-page evidence, low web-search context, low reasoning, a 2,000-token output cap, and
up to three evidence URLs per field.
Economy and Thorough presets are included, while Custom unlocks each control.
Jobs report input, cached-input, output, reasoning, total-token, and web-search
usage per lookup and per batch, together with a clearly dated approximate USD
cost for recognized models. Stable prompt-cache routing and configurable evidence limits reduce
repeated input and output overhead.

For the bundled defaults, OpenAI is substantially less expensive than Claude.
Maintainer testing of full Balanced hosted-search lookups observed roughly
**$0.07 per book with GPT-5.6 Luna** versus **nearly $0.13 with Claude Sonnet 5**.
This is a planning comparison, not a guaranteed price: books, searches, output,
provider pricing, and account terms vary, and the two defaults do not provide
identical capability. Sonnet 5 also uses a separate search phase and two strict
generation calls for a full record, while OpenAI normally completes the workflow
in one Responses API request.

The plugin includes its own book-search icon for Calibre toolbars and menus.
Comprehensive documentation is bundled into the plugin and available from the
toolbar icon's drop-down menu, the configuration screen, or the first-run API-key prompt.
The main toolbar icon starts a lookup; its separate arrow opens configuration,
About, documentation, setup, fresh research, pending bulk acceptance, cache
clearing, session undo, statistics, redacted diagnostics, and diagnostic-log collection.

Choose **Research Specific Fields…** from that arrow menu when only part of a
book's metadata needs attention. A checklist offers Title, Authors, Series,
Tags, Identifiers, Published Date, Publisher, and Description. Only the checked
fields are requested from the selected AI and shown in review. **Series and series index**
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
- average queue, fingerprint, cache, extraction, AI-provider, search, validation, review-wait,
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

- Provider API keys are never stored in Calibre's JSON preferences. BiblioSleuth AI uses
  macOS Keychain, Windows Credential Manager, or Linux Secret Service when
  available; otherwise a key is session-only. `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, or `LM_STUDIO_API_KEY` takes priority for its provider.
  `ANTHROPIC_WORKSPACE_ID` supplies the non-secret workspace selector required
  by identity-linked or multi-workspace Anthropic keys.
- The settings screen displays **✓ API key is stored securely and active** when
  a credential exists, while never revealing its value. The field is labeled
  **Replace API key**: leaving it blank retains the existing credential,
  entering a new key replaces it, and you can use
  **Delete Stored API Key** to remove the vault and session copies.
- Hosted requests use fixed HTTPS origins; OpenAI requests also set `store=false`.
  Only selected OPF metadata and bounded
  text from confidently identified title and copyright pages are sent. Unidentified
  pages, contents, prefaces, introductions, dedications, and body chapters are
  excluded rather than used as fallback evidence.
- API redirects are refused so authorization headers cannot leave the selected
  hosted origin or configured endpoint. This does not limit hosted web search or
  consume an evidence-URL slot.
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
src/bibliosleuth_ai/      Runtime plugin source and bundled metadata
tests/                      Calibre-independent automated tests
build/                      Generated dependency cache (ignored by Git)
dist/                       Generated ZIP and checksum (not committed)
```

Calibre plugins require their Python modules and resources at the root of the
installed ZIP. The build script deliberately maps the organized source tree into
that flat installation layout and extracts approved pure-Python modules from the
downloaded wheel; do not install `src/bibliosleuth_ai` directly. Runtime dependency
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
git tag -a v1.1.0 -m "BiblioSleuth AI 1.1.0"
git push bibliosleuth v1.1.0
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
in [docs/development.md](docs/development.md).

## Support and limitations

A configured OpenAI or Claude account, or a running Ollama/LM Studio server with
SearXNG, is required. Hosted searches, model calls, and custom-prompt validation
can incur charges. AI output and online catalogs
can be wrong; review every field, especially identifiers, dates, publisher, and
series index. BiblioSleuth AI supports EPUB inspection only and does not retrieve
covers or rewrite embedded metadata.

When reporting a problem, include the BiblioSleuth AI and Calibre versions, operating
system, optimization preset, and a redacted job error. Never include an API key,
complete custom prompt, copyrighted EPUB passage, or private library export.

## Support BiblioSleuth AI

If BiblioSleuth AI saves you time organizing your library, you can support its
continued development, testing, documentation, and maintenance:

<p align="center">
  <a href="https://www.buymeacoffee.com/terry.trent" target="_blank"><img src="assets/buy_me_a_book.png" alt="Buy me a book!" height="60" width="217"></a>
</p>
