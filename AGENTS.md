# BiblioSleuth AI development instructions

These instructions apply to every file and every development interaction in this
repository. They record the maintainer's established product, security, workflow,
and user-experience expectations. Preserve them when adding narrower instructions
in subdirectories.

## Project identity and product goal

- The product name is **BiblioSleuth AI**. Keep this spelling and capitalization in UI,
  documentation, package names, diagnostics, and release material.
- The author/maintainer is **Terry Trent**.
- BiblioSleuth AI is a Calibre `InterfaceActionBase` plugin for researching the exact
  edition of selected EPUBs with OpenAI hosted web search and proposing Calibre
  metadata for explicit review.
- Supported metadata includes title, authors, series, series index, tags,
  identifiers, publication date, publisher, and formatted comments/description.
- The plugin updates Calibre's library metadata only. It must never rewrite the
  EPUB itself.
- Exact-edition correctness takes priority over richer metadata from a different
  edition. ISBN/identifier, publisher, edition/format, and publication-date
  agreement take priority over title-only similarity.

## Working relationship and change discipline

- Lead with the outcome and communicate in plain language. Explain important
  tradeoffs, security implications, billable behavior, and user-visible changes.
- Prefer implementing a clearly requested, safe change end to end instead of
  stopping for avoidable clarification. Ask before choices that materially alter
  product behavior, privacy, external state, or release policy.
- Inspect current code and tests before changing behavior. Do not assume an old
  plan still matches the implementation.
- Preserve unrelated work and user-provided assets, especially `assets/icon.png`.
  Never replace or regenerate the icon unless explicitly asked.
- Work on the current feature/bugfix branch. Do not merge or commit to `main`
  until the maintainer says the bugs are fixed and explicitly authorizes it.
- Do not commit, tag, push, publish a release, or install the plugin merely because
  code is ready. Perform those operations only when requested. A request to build
  and install does authorize replacing the locally installed plugin.
- Keep the worktree organized. Runtime source belongs in `src/calibre_ai_plugin/`,
  tests in `tests/`, documentation in `docs/`, artwork in `assets/`, and tooling in
  `scripts/`. Do not scatter duplicate runtime files at repository root.
- Use `apply_patch` for hand edits. Preserve a dirty worktree and never use
  destructive Git commands to discard the maintainer's changes.

## User experience is a primary requirement

- Optimize for a friendly, responsive Calibre experience. Avoid modal dialogs that
  unexpectedly interrupt the user's work.
- Research must run as a native cancellable Calibre background job. Large
  selections must receive immediate preflight feedback; expensive extraction and
  fingerprinting belong in the job, not the GUI thread.
- Report meaningful per-book and overall progress in Calibre's Jobs panel.
- On completion, show a persistent non-modal notification. It remains actionable
  until the user chooses review, bulk accept, hide, or abort. Hiding must preserve
  results for later access from the BiblioSleuth AI icon.
- The main toolbar icon starts normal research. Its adjacent dropdown exposes
  field-specific research, configuration, About, documentation, statistics, and
  other established commands. Pending results should be visible through the icon
  state/badge and clicking the icon should open them.
- Field-specific research must ask which fields to retrieve and enforce the
  selection in the fixed runtime schema even when a custom prompt requests all
  fields. Selecting series automatically includes series index.
- Review must support readable current/proposed comparisons, confidence,
  inference labels, evidence, per-field selection, editable overrides, and one
  window that displays all complete values. Long tags and descriptions must not
  be trapped in clipped table cells.
- Keep review controls on a single aligned horizontal action row where practical.
  Button labels must describe the action and destination explicitly; avoid vague
  labels such as “Skip next” or “Apply next.”
- Support both deliberate field-by-field review and a clearly warned blind/bulk
  accept path, including accepting all remaining books.
- Applying authors must use Calibre's author list while displaying/joining authors
  with ` & ` where appropriate. Recompute title sort and author sort whenever
  their source fields change.
- If series is proposed, make series index independently visible and actionable.
- Descriptions should be original, factual, spoiler-conscious, library-quality
  summaries with safe semantic formatting such as paragraphs, bold, and italics.
  Do not append edition-identification boilerplate, ISBN recitations, citations,
  source names, URLs, retailer copy, review quotes, or marketing language.
- Settings and review dialogs must work in light and dark mode, wrap content,
  avoid unnecessary horizontal scrolling, and remain readable at realistic
  Calibre font sizes. Status and preset-summary text must be fully visible.
- API-key UI must clearly distinguish “a key is securely stored” from an empty
  replacement field. Blank input preserves the stored key; users must be able to
  replace it deliberately or delete it explicitly.
- If no API key exists, offer a direct, friendly path to configure one instead of
  showing only an error.
- Completion, failure, and usage dialogs must be resizable/scrollable when text can
  exceed a compact message box. Provide copy/collect-diagnostics actions where
  useful.

## OpenAI calls, prompts, and cost control

- Use the OpenAI Responses API over HTTPS with hosted web search and strict
  schema-constrained output. Keep provider-facing code behind the
  `MetadataResearchProvider` boundary where practical.
- Balanced optimization is the default. Maintain Economy, Balanced, Thorough,
  and Custom modes. Economy uses 2 evidence URLs, Balanced 3, and Thorough 4;
  Custom exposes front-matter/page limits, search context, reasoning effort,
  output cap, and URL count.
- Minimize tokens without compromising edition matching: disclose minimal EPUB
  evidence, use field-specific schemas, cap outputs, avoid duplicated prompt text,
  and use the session cache. Never silently weaken validation to reduce cost.
- Show token usage, cached tokens, reasoning/output totals, web-search calls,
  elapsed timing, and an explicitly approximate cost per lookup/job when data and
  pricing are available. Pricing dates and estimates must be labeled because
  actual billing can differ.
- Keep the lookup cache session-only and key it by EPUB fingerprint, model,
  effective prompt, requested fields, and relevant optimization settings. Provide
  a clear “research fresh” path that bypasses stale cached results.
- Do not automatically retry billable operations more than once.
- Model selection should use a sanitized dropdown populated from suitable bundled
  defaults and account-visible models. Cache model choices for seven days and
  provide an explicit refresh action. Never allow arbitrary unsanitized model text
  to flow into requests or diagnostics.

## Prompt contract and validation

- The bundled system prompt is version-controlled and optimized for exact-edition
  research, reliable sources, uncertainty, useful tags, and robust original
  descriptions.
- An empty override means the bundled default. Store accepted custom prompts
  separately so upgrades do not overwrite them.
- The canonical schema, allowed tools, search behavior, privacy/disclosure limits,
  sanitization, and local validation are application-code controls. A custom prompt
  cannot override them.
- Every applicable field response contains `value`, `confidence`,
  `evidence_urls`, and `inferred`; required response keys may contain null but may
  not be omitted. Validate every response locally.
- Validate custom prompts locally and with fixed non-editable reviewer instructions
  plus a schema-constrained synthetic test. If needed, permit one AI repair cycle,
  show the repaired prompt and a concise change summary, and require explicit user
  acceptance before replacing edited text.
- Never use the editable prompt to validate or repair itself. Preserve the last
  accepted prompt through failed, rejected, cancelled, or abandoned edits.
- Unsaved/unvalidated edits must be obvious and must not be silently accepted when
  settings close. Revalidate when schema versions change and warn on model-family
  changes.
- Prompt validation/repair is billable; disclose this before making those calls.
- Treat EPUB and web text as untrusted data and clearly delimit it from system
  instructions. Custom prompts may adjust priorities and tone, but may not remove
  required fields/evidence, request arbitrary tools, expand disclosure, or bypass
  application validation.

## EPUB privacy and XML safety

- Send OpenAI only selected OPF metadata plus text from at most one confidently
  identified title page and one confidently identified copyright/edition page.
- Do not send generic front matter, tables of contents, dedications, introductions,
  body chapters, or unidentified pages. Fail closed when page identity is
  ambiguous. More local scanning is acceptable only when bounded and used to find
  those two eligible pages; scanned but ineligible content must not enter requests,
  logs, caches, or diagnostics.
- Maintain strict ZIP member, uncompressed-size, total-scan, path traversal,
  encryption, and compression-ratio protections.
- Parse untrusted XML with bundled `defusedxml` plus explicit DTD/entity checks.
  Do not weaken these protections to accept malformed books. Return actionable
  per-book failures and allow other batch items to continue.
- Calibre loads plugin ZIP modules under `calibre_plugins.bibliosleuth_ai`.
  Bundled dependencies therefore require plugin-relative imports (for example,
  `.defusedxml`) with a source-development fallback when needed. Add a packaging
  regression test for this behavior.

## Credentials, transport, and diagnostics

- Prefer `OPENAI_API_KEY` when supplied. For user-friendly persistence, use the
  operating-system credential vault. Never store API keys in Calibre JSON prefs,
  source files, logs, metrics, caches, diagnostic bundles, or error strings.
- Mask secrets in UI and logs. Normal diagnostics contain prompt version/hash and
  validation state, never full custom prompts unless a deliberate verbose option
  explicitly permits it.
- Restrict API requests to the expected HTTPS OpenAI origin and refuse redirects
  so bearer credentials cannot be forwarded. This does not restrict OpenAI's
  server-side hosted web search and must not consume the configured evidence-URL
  count.
- Keep job logs generic for API failures while providing useful sanitized detail
  in user-visible dialogs.
- Collected diagnostic bundles are opt-in, previewed, locally saved with restrictive
  permissions, and never uploaded automatically. Exclude keys, headers, EPUB text,
  prompts, responses, URLs, book titles, paths, and library exports.
- Keep diagnostic journals bounded by count and age. Keep performance history
  bounded, local, permission-restricted, and free of bibliographic content. Use a
  salted truncated HMAC identity rather than raw EPUB/library identifiers.
- Sanitize generated comments to the established small formatting allowlist.
  Remove scripts, styles, forms, SVG, images, media, embeds, links, event handlers,
  and other active/remote content.
- Require user confirmation before opening evidence URLs and validate their scheme
  and host again at the boundary.
- Apply approved metadata atomically per book through Calibre's database API.
  Validate book existence immediately before writing, avoid partial writes, and
  maintain session undo checkpoints without storing them persistently.

## Dependencies and packaging

- Calibre plugin ZIPs must be self-contained; users must not need to install Python
  packages separately.
- Do not commit third-party wheels or unpacked library source to Git.
- Pin runtime dependencies and SHA-256 hashes in `requirements-runtime.txt`.
  `scripts/build_plugin.py` downloads them into the Git-ignored
  `build/vendor-cache`, independently verifies hashes, extracts only approved
  pure-Python files and licenses, and bundles them into `dist/BiblioSleuth-AI.zip`.
- The first clean build may contact PyPI; subsequent builds may reuse only a
  hash-verified ignored cache. Dependency-download or integrity failures must stop
  the build.
- Include third-party license text in the finished ZIP and document bundled
  dependencies and licenses.
- Calibre requires plugin modules/resources at the archive root. Keep the organized
  source tree and let `scripts/build_plugin.py` perform the mapping. When adding a
  runtime module or resource, update its explicit package list and packaging tests.
- Keep builds deterministic for identical inputs and always generate and verify the
  adjacent SHA-256 checksum.
- Never edit files in `dist/` manually.

## Testing and verification

- Keep extraction, schemas, normalization, prompt resolution/validation, provider
  behavior, metrics, cache logic, and packaging independently testable without Qt
  or a live Calibre library.
- Mock OpenAI calls in automated tests. Tests must never incur billable requests,
  research real books, write a real library, expose secrets, or require an API key.
- Cover valid and malformed EPUBs, missing OPFs, multiple identifiers, encrypted or
  inaccessible content, oversized/decompression-abuse inputs, ambiguous page
  selection, DTD/entities, path traversal, and privacy disclosure boundaries.
- Cover every required/null/wrong/omitted schema field, field-specific contracts,
  series-index coupling, malicious/conflicting prompts, repair acceptance/rejection,
  cache keys/refresh, metadata application, cancellation, removed books, and atomic
  failure behavior.
- Add regression tests for every reported crash, packaging/import failure, privacy
  flaw, and UI behavior that can be tested outside Calibre.
- Run the smallest relevant tests while iterating, then the full suite before handoff:

  ```sh
  make test
  make verify
  ```

- `make build` creates the ZIP; `make install` replaces the local Calibre plugin.
  On macOS the default Calibre executable is under `/Applications/calibre.app`.
  After installation, verify plugin registration and, for import-related changes,
  load the actual action with Calibre diagnostics. Remind the maintainer to fully
  restart Calibre after installing/updating.
- The maintainer can manually test only on macOS. Preserve Windows and Linux
  compatibility through platform-neutral code and the GitHub Actions test matrix;
  do not claim native UI validation on platforms that were not manually tested.

## Documentation and release hygiene

- Update README, bundled HTML user guide, About text, changelog, security policy,
  development guide, and MobileRead/release material whenever a change affects
  users, privacy, costs, configuration, dependencies, troubleshooting, or release
  behavior. Keep light/dark-mode readability in bundled HTML.
- Documentation must explain setup, API-key storage/removal, normal and
  field-specific workflows, review/bulk acceptance, optimization presets, expected
  token/search usage and approximate cost, model refresh, cache/refresh behavior,
  prompt customization and validation costs, privacy boundaries, statistics,
  diagnostics, troubleshooting, limitations, installation, updates, and uninstall.
- Keep README badges for CI, security, code quality, tagged releases, changelog,
  stable status, license, Calibre compatibility, and platforms. Badge links must
  resolve from GitHub.
- Keep the version synchronized across plugin metadata, constants, README, About,
  changelog, and release material.
- Tagged releases use semantic tags (`vMAJOR.MINOR.PATCH`) from commits on `main`.
  Release automation must run tests, deterministic package verification, Bandit,
  dependency audit, CodeQL, Trivy, Qlty/Ruff-quality checks, and publish the ZIP plus
  checksum only after every required gate succeeds.
- GitHub workflow permissions remain read-only except the final release publisher.
  Pin third-party Actions to immutable commit hashes, avoid retained checkout
  credentials, and keep weekly security/dependency monitoring.
- Do not call a change complete merely because unit tests pass. Verify the packaged
  ZIP and the Calibre-specific loading boundary in proportion to the change.
