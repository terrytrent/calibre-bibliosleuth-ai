# Changelog

All notable changes to BiblioSleuth AI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.1] - 2026-09-05

### Fixed

- Preserved completed SearXNG search counts and timing when an Ollama or LM Studio
  request subsequently returns invalid structured output.
- Disabled the ineffective Reasoning effort control for Ollama and LM Studio,
  normalized local statistics to no configured reasoning, and clarified that LM
  Studio reasoning is determined by the loaded model.

## [1.1.0] - 2026-09-02

### Changed

- Audited the complete user, security, developer, and wiki documentation against
  the implemented provider workflow. Corrected Claude split-call and session-undo
  descriptions and documented the SearXNG limits, normalization limits, timeout
  defaults/ranges, preset values, and local-provider schema behavior.
- Added a maintainer-observed best-to-worst quality comparison for all six
  provider/search paths and a separate billable API-cost ranking, including the
  tested LM Studio and Ollama model results and appropriate benchmark caveats.

### Fixed

- Hardened local-model CI matrix dispatch against workflow template injection by
  passing the selected runtime through a quoted environment variable.
- Allowed unreleased Keep a Changelog comparison links in CI link validation;
  those links become live when the matching release tag is published.
- Fixed disposable SearXNG and Ollama tests reporting false failures after their
  assertions passed when root-owned container files prevented temporary cleanup.
- Fixed Claude full-record chunk merging by establishing the edition match once,
  then passing that selected identity into later field-only chunks instead of
  asking Claude to regenerate and exactly repeat the match summary.
- Expanded LM Studio setup and troubleshooting documentation with the validated
  `/v1` endpoint, full desktop Developer-server workflow, conservative 16 GB Mac
  settings, and the observed incompatibility of thinking models that return JSON
  only in `reasoning_content`.
- Fixed LM Studio requests freezing after prompt processing by using a compact
  decoder grammar while retaining the complete canonical validation locally.
- Expanded Ollama and LM Studio documentation to explain that strong local models
  are necessary for reliable exact-edition research, lightweight models are best
  treated as integration tests, and 16 GB Macs may not run models approaching
  hosted OpenAI or Claude quality. Added guidance to use longer 120–300 second
  timeouts for local models while recognizing persistent swapping and timeouts as
  signs that a model is too large for comfortable use.
- Fixed small local models causing an entire Ollama or LM Studio lookup to fail
  when they formatted SearXNG citations incorrectly. SearXNG-backed providers now
  retain only exact URLs supplied by the search service before schema validation.

### Added

- Added a required Linux CI contract test that provisions a digest-pinned,
  disposable SearXNG container, exercises the real JSON search API, and tears it
  down automatically. Developers can run the same check with `make test-searxng`.
- Added `make test-debug` and `make test-searxng-debug` for verbose test output;
  the live debug target shows container lifecycle, endpoint readiness, normalized
  results, and confirmed teardown.
- Added required disposable Ollama and generic OpenAI-compatible local-inference
  CI contracts using tiny models, pinned runtime-image digests, verified model
  artifacts, random loopback ports, and automatic teardown. Genuine native LM
  Studio CI remains explicitly deferred until a supported runner is available.
- Disabled Ollama's default thinking for bounded structured-output requests so
  small reasoning models cannot consume the output allowance without returning
  the required JSON content.
- Simplified provider-neutral statistics assembly so completed, failed, cached,
  and cancelled lookups share one tested record-building path.
- Hardened cancellation cost reporting by tracking whether a model request
  actually started instead of inferring it from usage fields that providers may omit.
- Added context-specific completion window titles when research is cancelled or
  finishes without reviewable results.
- Added dated cost estimates for all selectable priced OpenAI and Claude model
  families, including provider-specific cached tokens and hosted-search calls.
- Updated the Claude default to Sonnet 5, bundled the current compatible Claude
  choices, and retained compatible account-visible aliases and snapshots.
- Added optional Anthropic workspace-ID configuration and
  `ANTHROPIC_WORKSPACE_ID` support for identity-linked and multi-workspace API
  keys; the validated ID is sent on every Claude API request.
- Fixed a Calibre runtime crash when starting research after workspace-ID support
  was added by importing the environment module at the packaged action boundary.
- Separated Claude hosted-search output capacity from the smaller final-metadata
  cap. Anthropic server-search iterations now receive a 6,000-token safety ceiling
  and concise-summary instruction, preventing normal three-search research from
  failing at the Balanced preset's 2,000-token schema limit without a costly retry.
- Reduced Anthropic's strict generation grammar by removing duplicated constraint
  descriptions while retaining required keys, shapes, enums, and nullability.
  The full canonical limits remain enforced locally before results reach review.
- Documented the substantial default-provider cost difference, including the
  maintainer's observed full-book Balanced examples of roughly $0.07 for OpenAI
  GPT-5.6 Luna and nearly $0.13 for Claude Sonnet 5, with explicit variability
  and non-equivalence caveats.
- Added regression coverage for Claude split boundaries, partial failure,
  cancellation, merged validation, SearXNG reuse, prompt synthetic tests,
  workspace precedence/redaction, defaults, pricing tables, and documentation.
  The new coverage found and fixed the SearXNG Claude path still sending the
  complete eight-field grammar instead of using the shared split helper.
- Fixed first-run Ollama and LM Studio model refresh: discovery now uses an
  internal sanitized placeholder when no model has been selected yet, allowing
  the server's model list to populate the non-editable dropdown.

#### Multiple AI and search providers

- Added provider-neutral research for OpenAI, the direct Anthropic Claude API,
  Ollama, and LM Studio. Claude can perform prompt review/repair, capability
  checks, metadata research, and strict-schema generation just like OpenAI.
- Added provider-hosted search choices for OpenAI and Claude plus a shared,
  user-managed SearXNG option for every provider. Ollama and LM Studio use
  SearXNG for web evidence.
- Added separate provider credentials, model choices, local endpoints, search
  limits, model discovery, readiness tests, and provider/search-aware cache keys.
- Added bounded SearXNG JSON querying with loopback-safe HTTP defaults, response
  limits, URL filtering, untrusted-evidence delimiting, and redirect refusal.
- Expanded anonymized statistics with AI-provider and search-provider filters and
  separate hosted-search and SearXNG counters; local inference is clearly labeled
  as having no reported API cost.
- Added setup and security documentation for Ollama, LM Studio, Claude, and a
  separately operated SearXNG service.
- Consolidated provider integrations around typed settings, one bounded JSON
  transport, shared research/security handling, and a provider-keyed model cache.
  Claude schema generation now uses the current native structured-output API;
  hosted search remains a separate request because Anthropic web-search citations
  are incompatible with strict JSON output.
- Hardened provider credential isolation, including optional Ollama tokens and
  exact-secret redaction from provider errors. Cache identity now includes the
  local endpoint and remote-endpoint policy; usage, timings, and diagnostics
  retain provider/search provenance and separate hosted/SearXNG counters.
- Improved local-provider onboarding by routing first-run setup through model,
  endpoint, SearXNG, connection, and capability configuration before research.
- Preserved existing OpenAI model selections during upgrade, bound custom-prompt
  validation to the tested provider and model, and prevented failed searches
  from inheriting usage from an earlier book.
- Bounded Claude's hosted-search handoff to sanitized summaries and citation
  metadata, rejected credential-bearing result URLs, corrected failed-search
  timing attribution, and tightened provider-aware settings and diagnostics.
- Corrected OpenAI cost estimates so SearXNG calls never receive hosted-search
  pricing, retained token usage from incomplete or malformed billable responses,
  and made mixed-provider cost coverage explicit in Statistics.
- Filtered Claude model choices to structured-output-capable families, sent
  effort only to supporting models, and added direct setup guidance when Ollama
  or LM Studio exposes no loaded models.
- Completed provider/search provenance in diagnostic history, distinguished
  known-zero pre-provider failures and cancellations from unknown provider cost,
  retained partial SearXNG call counts on failure, and report Claude refusals
  directly while preserving their usage.
- Expanded Claude capability matching for documented Opus, Sonnet, Haiku,
  Fable, and Mythos aliases and snapshots; incompatible catalogs no longer make
  an empty model list appear fresh for seven days.
- Added an Anthropic-specific generation-schema transformation that removes
  unsupported decoding constraints while retaining the canonical schema for
  strict local validation.
- Treats a valid empty SearXNG result set as a successful readiness check,
  propagates Calibre cancellation between SearXNG queries and before/after model
  requests, and classifies SearXNG failures as search-stage diagnostics.
- Preserves usage, cost, search counts, and timing for the specific book whose
  completed provider response is discarded by a late cancellation; only books
  never started are recorded as zero-cost cancellations.
- Carries removed Anthropic schema constraints into bounded generation guidance
  while enforcing the originals locally, and groups SearXNG failures under a
  dedicated web-search diagnostic category.
- Cancellation-only jobs now show a retained non-modal completion notice instead
  of creating an invisible pending batch. Aggregate cost availability is tracked
  per operation so a SearXNG-only cancellation remains known-zero, and all
  SearXNG failures group consistently under web search.

#### Project assurance

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

## [1.0.0] - 2026-08-25

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

[Unreleased]: https://github.com/terrytrent/calibre-bibliosleuth-ai/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/terrytrent/calibre-bibliosleuth-ai/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/terrytrent/calibre-bibliosleuth-ai/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/terrytrent/calibre-bibliosleuth-ai/releases/tag/v1.0.0
