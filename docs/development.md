# Developer guide

## Repository map

| Path | Purpose |
| --- | --- |
| `src/bibliosleuth_ai/` | Python code and small metadata files loaded by Calibre |
| `assets/` | Artwork copied into the plugin ZIP |
| `docs/` | User, developer, release, and canonical GitHub Wiki documentation |
| `scripts/` | Deterministic packaging tools |
| `Makefile` | Memorable shortcuts around tests, packaging, verification, and installation |
| `tests/` | Calibre-independent unit and packaging tests |
| `dist/` | Generated release ZIP and checksum; never edit these by hand |

Calibre expects plugin modules at the root of the installed ZIP. Source files do
not need to live at the repository root: `scripts/build_plugin.py` maps this
organized tree to Calibre's required archive layout.

## Runtime module map

### Calibre and Qt integration

- `action.py` — toolbar/menu actions, background jobs, pending results, application, and undo
- `config.py` — settings tabs and configuration validation
- `review.py` — field-level review, overrides, evidence, and batch navigation
- `onboarding.py` — first-run setup
- `statistics_dialog.py` and `diagnostic_bundle_dialog.py` — focused support dialogs
- `docs.py` — bundled documentation viewer

### Research pipeline

Provider-neutral construction lives in `providers.py`. `openai_provider.py` uses
the Responses API, `anthropic_provider.py` uses the Messages API, and
`local_provider.py` handles Ollama/LM Studio OpenAI-compatible chat completions.
`searxng.py` is a bounded client for a separately operated JSON Search API. Cache
identity includes AI provider, model, search provider, and SearXNG limits.

Anthropic hosted research has a separate 6,000-token server-tool ceiling because
intermediate search turns count against `max_tokens`; the configured preset cap
continues to bound final metadata generation. Anthropic and LM Studio receive a
compact decoder schema with constraints unsupported by their structured-output
engines removed; the unchanged canonical schema remains the final local authority.
Ollama receives the canonical schema directly. Anthropic metadata schemas containing
more than four fields are split into strict calls. The first establishes the match;
later calls omit that duplicate property, receive the selected match as bounded
context, and return only their field subset. Results are merged and then checked
against the unchanged canonical local schema. Keep this split in prompt synthetic
tests as well as normal research when changing the provider boundary.

Shared request preparation, SearXNG evidence handling, validation, security
warnings, usage shapes, and timings live in `provider_base.py`. The bounded,
redirect-refusing JSON transport lives in `transport.py`; provider modules keep
only API-specific payload and response translation. Provider facts and typed
runtime settings are centralized in `providers.py`, and `provider_config.py`
isolates the settings UI's per-provider switching state.

Do not add provider logic directly to the Calibre action. New providers implement
research, structured calls, model discovery, readiness tests, usage, timings, and
credential clearing behind the research boundary.

- `epub.py` — bounded, defensive extraction of selected OPF fields and confidently identified title/copyright pages
- `openai_provider.py` — HTTPS Responses API provider and model listing
- `schema.py` — canonical and field-specific response contracts plus local validation
- `prompt_validation.py` — custom-prompt review, repair, and synthetic testing
- `normalizer.py` — identifiers, tags, dates, and safe description HTML
- `lookup_cache.py` — session-only lookup cache and EPUB fingerprints

### Settings, security, and observability

- `constants.py` — versions, defaults, presets, and fixed prompts
- `prefs.py` and `credentials.py` — preferences and operating-system credential vaults
- `model_catalog.py` — validated, seven-day model-list cache
- `metrics.py` and `usage.py` — bounded statistics and cost estimates
- `diagnostics.py` and `diagnostic_journal.py` — redacted configuration and failure history

## Common commands

`make test` runs the mocked, cross-platform suite. `make test-searxng` additionally
verifies the client against a real SearXNG JSON endpoint. The integration target
requires Docker, starts an official SearXNG image pinned by digest on a random
loopback port, waits for readiness, runs the contract test, and removes both the
container and temporary configuration even if the test fails. Linux CI runs this
as a separate required job.

For visible diagnostic output, use `make test-debug` for the normal suite or
`make test-searxng-debug` for the live integration check. The latter prints the
temporary container name, loopback endpoint, readiness state, normalized search
results, and teardown confirmation. Debug mode still removes the container and
temporary configuration automatically.

Local inference has two additional live contract tests. `make test-ollama`
starts a digest-pinned Ollama container, downloads Qwen3 0.6B into temporary
storage, and verifies model discovery plus schema-constrained output.
`make test-openai-compatible` runs the LM Studio-shaped provider path against a
separate digest-pinned llama.cpp server and a revision- and SHA-256-pinned Qwen
2.5 0.5B GGUF. Append `-debug` to either target to see the container endpoint,
advertised models, structured response, usage, and teardown. Both are required
Linux CI and release checks. They validate local-provider interoperability, not
the bibliographic quality of these deliberately tiny models.

Genuine LM Studio automation is intentionally deferred because LM Studio does
not currently publish an official CI container. A future self-hosted macOS
workflow can test the native application through `lms`; the generic container
test must not be described as a genuine LM Studio runtime test.

```sh
make test
make build
make verify
make install
make release
```

The Makefile delegates packaging to `scripts/build_plugin.py`; it does not contain
a second file list or alternate ZIP implementation. Override `PYTHON` or
`CALIBRE_CUSTOMIZE` on the command line when local paths differ. Developers
without Make can invoke the corresponding Python, `unzip`, checksum, and Calibre
commands directly as documented in the README.

When adding a runtime module or resource, update `PACKAGE_FILES` in
`scripts/build_plugin.py` and add or adjust a packaging test. Keep domain logic
independent of Calibre and Qt where practical so it remains directly testable.

## Publishing

Merge the completed release commit to `main`, then push an annotated semantic tag
such as `v1.1.1`. The version must match the plugin and documentation. The tagged
release workflow verifies main ancestry, runs the complete test matrix, Bandit,
CodeQL, Trivy, dependency auditing, and the blocking Ruff correctness gate, builds
and re-verifies the package, and creates the GitHub Release with
`BiblioSleuth-AI.zip`, its SHA-256 checksum, and a CycloneDX SBOM. The build job
also creates GitHub artifact attestations for those assets. Continuous workflows
run on `main` and pull requests with concurrency cancellation to avoid duplicate
obsolete jobs. They include dependency review, repository-owned Semgrep rules,
actionlint and zizmor workflow checks, Markdown/link validation, a 35% total
headless-coverage non-regression floor, and installation checks against Calibre
7.0.0 and the current documented Calibre release. The baseline includes UI modules
that require Calibre/Qt and therefore cannot be imported by the headless unit suite;
raise it as integration coverage is added.

The publisher extracts the matching `## MAJOR.MINOR.PATCH` section from
`CHANGELOG.md` and uses that content as the GitHub Release description. A missing
or empty version section fails the release instead of publishing generic generated
notes. Update the changelog before creating the tag.

Files in `docs/wiki/` are the canonical wiki source. Merges to `main` synchronize
them to the repository wiki so changes remain reviewable and version controlled.
See the README for exact commands.
