# Changelog

All notable changes to BiblioSleuth AI are documented here.

## Unreleased

### Project assurance

- Added dependency review, project-specific Semgrep rules, actionlint/zizmor
  workflow auditing, documentation/link checks, and a coverage non-regression gate.
- Added automated installation checks against the oldest and current supported
  Calibre releases and reviewable source synchronization for the GitHub Wiki.
- Pinned every workflow action to an immutable commit and added release SBOMs and
  GitHub artifact attestations.
- Added privacy-conscious bug reports, feature requests, and pull-request templates.
- Changed tagged releases to publish the matching version section from this
  changelog instead of GitHub's generic generated “Full Changelog” notes.
- Completed the internal package rename and removed legacy branding remnants
  from source paths, automation, documentation, tests, and generated artifacts.

## 1.0.0 — 2026-08-25

Initial stable release of BiblioSleuth AI for Calibre.

### Metadata research and review

- Researches exact EPUB editions with the OpenAI Responses API and hosted web
  search, prioritizing identifiers, publisher, edition/format, publication date,
  title, authors, series, and description consistency.
- Proposes title, authors, series and series index, tags, identifiers, publication
  date, publisher, and formatted comments through a strict locally validated schema.
- Supports normal and field-specific research; field-specific schemas return only
  requested values, with series automatically coupled to its index.
- Runs cancellable batch research as native Calibre jobs with staged per-book
  progress and persistent non-modal result notifications.
- Provides confidence, inference labels, categorized evidence, readable diffs,
  complete-value review, editable overrides, fresh research, field selection,
  explicit batch navigation, confirmed bulk acceptance, and session undo.
- Applies approved metadata atomically without modifying EPUB files and refreshes
  title-sort and author-sort values when their source metadata changes.

### Prompting and OpenAI optimization

- Includes a versioned exact-edition prompt that produces original library-quality
  formatted descriptions while excluding retailer copy, citations, bibliographic
  matching notes, spoilers, and unsupported facts.
- Supports validated custom prompts with fixed reviewer instructions, synthetic
  schema tests, one-cycle AI repair, explicit acceptance, and preservation of the
  last accepted prompt after failed or abandoned edits.
- Provides Economy, Balanced, Thorough, and Custom optimization modes controlling
  disclosed page evidence, search context, reasoning, output caps, and evidence URL
  limits; Balanced is the default.
- Reduces repeated cost through field-specific schemas, bounded output, compact
  requests, connection reuse, batch coalescing, and a settings-aware session cache
  with an explicit fresh-research path.
- Displays token, cache, reasoning, web-search, timing, and approximate cost data.
- Offers a sanitized account-visible model dropdown, bundled fallbacks, a seven-day
  model-list cache, capability checks, and explicit model-choice refresh.

### Security and privacy

- Sends only selected OPF metadata and at most one confidently identified title
  page and copyright/edition page; unidentified front matter and body chapters are
  excluded and ambiguous selection fails closed.
- Treats EPUB and web content as untrusted evidence, separates it from instructions,
  enforces the response schema in application code, and warns on prompt-injection
  indicators.
- Defends EPUB processing with archive/path, encryption, decompression, size, and
  compression-ratio limits plus pinned, hash-verified `defusedxml` parsing and
  explicit DTD/entity protections.
- Restricts API traffic to the expected HTTPS OpenAI origin, refuses redirects,
  validates response limits and URLs, confirms evidence-link navigation, and
  sanitizes comments to a small non-active HTML allowlist.
- Stores persistent API keys in the operating-system credential vault with
  environment and session-only fallbacks; secrets never enter Calibre preferences,
  logs, statistics, caches, or diagnostic bundles.
- Verifies book identity and EPUB freshness before writes, keeps caches and undo
  state process-local, and bounds privacy-safe statistics and diagnostic history.
- Provides previewed, permission-restricted, redacted diagnostic bundles that are
  saved only at user request and never uploaded automatically.

### User experience, packaging, and quality

- Includes guided setup; accessible, light/dark-compatible settings and review
  dialogs; a split toolbar menu; pending-result icon state; documentation, About,
  statistics, troubleshooting, and API-key management commands.
- Packages a deterministic, self-contained Calibre ZIP and checksum. Runtime
  dependencies are pinned with hashes, downloaded only into an ignored build cache,
  independently verified, and bundled with their licenses rather than committed.
- Includes cross-platform tests, privacy and adversarial regression coverage,
  Bandit, dependency auditing, CodeQL, Trivy, Qlty/Ruff analysis, Dependabot, and
  least-privilege tagged GitHub release automation for Windows, macOS, and Linux.
