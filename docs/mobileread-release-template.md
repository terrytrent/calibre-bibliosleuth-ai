# MobileRead release checklist and first-post template

Calibre's official documentation directs community plugin authors to share
plugins in the MobileRead Calibre Plugins forum. The Plugin Index instructions
require the release ZIP to be attached to the first post and warn against
attaching multiple ZIP files there. After creating the thread, contact an active
Calibre moderator with the thread link, plugin name, and description so it can
be added to the index.

## Before posting

- Run the full test suite and install the final ZIP in Calibre.
- Verify `BiblioSleuth-AI.zip.sha256` from inside the `dist` directory and include its
  hash in the post if desired; attach only the ZIP itself to the first post.
- Confirm `__init__.py` contains the correct name, description, author, version,
  minimum Calibre version, and supported platforms.
- Attach exactly one file named `BiblioSleuth-AI.zip` to the first post.
- Keep beta/test ZIPs out of the first post; reserve a second post if needed.
- Include the literal heading `Version History` so Plugin Updater can discover
  release history.
- Never attach an API key, preferences file, EPUB, library export, or debug log
  containing private data.

## Suggested first post

```text
[GUI Plugin] BiblioSleuth AI

BiblioSleuth AI researches the exact edition of selected EPUB books with OpenAI web
search, then presents evidence-backed title, author, series/index, tag,
identifier, publication-date, publisher, and formatted-description suggestions
for field-level review—or a separately warned bulk-accept workflow—before
anything is written to Calibre.

Author: Terry Trent
License: MIT
Platforms: Windows, macOS, Linux
Minimum Calibre version: 7.0.0
Current version: 1.0.0

Requirements
- A selected Calibre book containing EPUB
- An OpenAI Platform API key with billing/credits
- Internet access

Installation
1. Download the single attached BiblioSleuth-AI.zip file without extracting it.
2. In Calibre, choose Preferences → Plugins → Load plugin from file.
3. Restart Calibre and add BiblioSleuth AI under Preferences → Toolbars & menus.
4. Open the arrow beside the BiblioSleuth AI icon and choose Configure BiblioSleuth AI.

Privacy and cost
Only selected OPF metadata and bounded text from confidently identified title
and copyright pages are sent. Unidentified pages and chapters are excluded; the
full book is not uploaded and EPUB files are not rewritten. API and web-search calls are
billable; the plugin displays reported usage and approximate cost. Persistent
keys use the operating-system credential vault rather than Calibre preferences.

Support
Post the BiblioSleuth AI/Calibre versions, operating system, optimization preset, and
a redacted error. Never post API keys or copyrighted book text.

Version History
[SPOILER]
1.0.0 — Cross-platform CI and release reliability
- Fixed UTF-8 documentation tests on Windows
- Added concurrency cancellation and removed duplicate Dependabot branch/PR runs
- Added a pinned blocking Ruff correctness gate and retained broader Qlty reports
- Consolidated deterministic package/checksum verification after the test matrix

1.0.0 — Initial stable release
- Exact-edition web research and structured metadata review
- Background jobs, field-specific searches, editable proposals, series index, and sort-field updates
- Economy/Balanced/Thorough/Custom optimization, usage/cost reporting, and validated custom prompts
- Title/copyright-page-only disclosure, secure credentials, strict schemas, safe HTML, and hardened EPUB/XML handling
- Settings-aware session caching, cached model discovery, connection reuse, and explicit fresh research
- First-run setup, accessible settings/review, pending notifications, batch and bulk workflows, and session undo
- Privacy-safe performance statistics plus previewable, locally saved redacted diagnostic bundles
- Deterministic self-contained packaging with pinned dependencies and automated test/security/release gates
[/SPOILER]
```

## Suggested index request

```text
Please add BiblioSleuth AI to the Calibre Plugin Index.

Thread: <MobileRead thread URL>
Name: BiblioSleuth AI
Type: GUI / User interface action
Description: AI-assisted exact-edition EPUB metadata research with evidence and
explicit review or warned bulk confirmation before applying changes.
Author: Terry Trent
```
