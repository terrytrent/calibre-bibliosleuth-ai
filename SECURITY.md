# Security policy

## Supported version

Security fixes are applied to the latest released version of BiblioSleuth AI.

## Reporting a vulnerability

Do not disclose an unpatched vulnerability, API key, private EPUB passage, or
library export in a public issue or forum post. Contact the maintainer privately
through the source repository or MobileRead account associated with Terry Trent.
Include the affected version, operating system, impact, reproduction steps, and
a minimal sanitized test file when possible.
Use the built-in **Copy Redacted Diagnostics** command when configuration context
is helpful, and review its clipboard output before sharing it.

The maintainer will acknowledge a report, investigate it, and coordinate a fix
and disclosure timeline appropriate to its severity. This is a volunteer
project, so no fixed response-time guarantee is made.

## Security boundaries

### AI providers and SearXNG

- OpenAI, Anthropic, Ollama, and LM Studio credentials use distinct
  credential-vault identities and are never reused for another provider. Ollama
  normally needs no token, but authenticated installations remain isolated too.
- Anthropic identity-linked and multi-workspace keys may require a `wrkspc_…`
  selector. It is validated before use, stored separately as non-secret
  configuration, sent only to Anthropic, and omitted from diagnostic exports.
- Plain HTTP model and SearXNG endpoints are accepted only on loopback by default;
  remote services require HTTPS. Redirects and credential-bearing endpoint URLs
  are rejected.
- SearXNG is operated separately by the user. Search titles, snippets, and URLs
  are bounded, sanitized, treated as untrusted evidence, and excluded from logs,
  statistics, and diagnostic bundles.
- Selecting SearXNG discloses queries to that instance and its configured upstream
  engines. Local model inference does not make web search offline.
- An applicable research job first sends a fixed, non-bibliographic readiness
  query to SearXNG. Ollama and LM Studio readiness checks request only the local
  server's model list; neither check includes EPUB or library metadata or
  generates model output.
- BiblioSleuth AI does not install, launch, administer, or expose SearXNG and does
  not run an MCP or other network server inside Calibre.

### Update service

- Automatic update checks are enabled by default, run only after normal plugin
  use, and contact the fixed public manifest no more than once every 24 hours.
- The request has no credentials, query parameters, book/library/provider data,
  hardware details, or installation identifier. Calibre preferences retain only
  check timestamps, the latest known version, and reminder/skip choices.
- The client requires the exact HTTPS host and path, refuses redirects, limits
  responses to 4 KiB, strictly validates the manifest and its bounded plain-text
  changelog, and derives rather than accepts the GitHub release URL. It never
  downloads or installs plugin code.
- Cloudflare Worker observability persists ordinary invocation records for the
  public update endpoint, including request/response metadata. The plugin uses a
  fixed path with no query string and does not add book data, credentials, provider
  settings, hardware details, or an installation identifier to these requests.

BiblioSleuth AI sends selected OPF fields and bounded text only from confidently
identified title and copyright pages to the selected AI provider. Unidentified
pages, other front matter, and body chapters are excluded. Web evidence comes
from OpenAI or Claude hosted search, or from the configured SearXNG instance.
Every provider response is validated locally, and explicit confirmation is
required before writing Calibre metadata. Users may choose field-level review or
a separately warned bulk-accept workflow. The plugin never modifies EPUB files.

Operating-system credential vaults are used for persistent API keys; Calibre JSON
preferences never contain them. Direct API redirects are refused so credentials
cannot follow a redirect away from the selected fixed hosted origin or configured
local endpoint. Hosted search remains server-side and is unaffected by this rule.
Session lookup cache and undo checkpoints remain process-local and disappear
when Calibre exits. Diagnostic exports omit secrets, EPUB passages, full prompts,
responses, evidence URLs, and library metadata.

Optional performance history is stored locally with restrictive file permissions
and bounded by configured record/day limits. Book identity is a salted truncated
HMAC of the EPUB fingerprint. Records exclude bibliographic metadata, paths,
library identifiers, book text, prompts, responses, URLs, secrets, and exact errors.
Model selection is constrained to a validated dropdown of provider defaults and
provider-visible choices. Model identifiers are sanitized again before entering
diagnostics or statistics.
EPUB XML is parsed with a pinned, hash-verified bundled copy of `defusedxml` in
addition to archive/member limits and explicit declaration checks.

The diagnostic journal is limited to 20 entries and seven days. Diagnostic bundles
are created only after an explicit save action, use restrictive permissions, and are
never uploaded automatically. Sanitization removes keys, authorization values, URLs,
home/temp paths, book titles/paths known to the job, and bounds detailed text. Bundle
previews enumerate included files and excluded data before saving.

## Automated release gates

Tagged releases run the full supported operating-system/Python test matrix,
Bandit static analysis, Trivy dependency/secret/configuration scanning, Qlty,
and GitHub CodeQL with the extended security query suite,
dependency-change review, repository-specific Semgrep invariants, actionlint and
zizmor workflow auditing, deterministic packaging, ZIP integrity validation, and
SHA-256 verification. Third-party and GitHub Actions are pinned to immutable commit
IDs. Published assets include a CycloneDX SBOM and GitHub artifact attestations.
Release publication is the only workflow job with repository write permission;
test, analysis, and build jobs use read-only contents access. This automation
supplements rather than replaces manual review of security-sensitive changes. An
isolated Cloudflare Worker static-asset deployment follows publication using a
narrowly scoped Workers Scripts token in a protected tag-only environment. It
validates the schema before upload and verifies the public version afterward. The
token is never bundled with or sent by the plugin.
