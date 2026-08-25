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

BiblioSleuth AI sends selected OPF fields and bounded text only from confidently
identified title and copyright pages to the OpenAI Responses API over HTTPS.
Unidentified pages, front matter of other kinds, and body chapters are excluded,
uses only hosted web search, validates structured output locally, and requires
explicit user confirmation before writing Calibre metadata. Users may choose
field-level review or a separately warned bulk-accept workflow. It does not
modify EPUB files. Operating-system credential vaults are used for persistent API keys;
Calibre JSON preferences never contain the key.
Direct API redirects are refused so bearer credentials cannot follow a redirect
outside the fixed OpenAI API origin. Hosted web search remains server-side and
is unaffected by this restriction.
Session lookup cache and undo checkpoints remain process-local and disappear
when Calibre exits. Diagnostic exports omit secrets, EPUB passages, full prompts,
responses, evidence URLs, and library metadata.

Optional performance history is stored locally with restrictive file permissions
and bounded by configured record/day limits. Book identity is a salted truncated
HMAC of the EPUB fingerprint. Records exclude bibliographic metadata, paths,
library identifiers, book text, prompts, responses, URLs, secrets, and exact errors.
Model selection is constrained to a validated dropdown of bundled defaults and
relevant account-visible choices; model
identifiers are sanitized again before entering diagnostics or statistics.
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
deterministic packaging, ZIP integrity validation, and SHA-256 verification.
Release publication is the only workflow job with repository write permission;
test, analysis, and build jobs use read-only contents access. This automation
supplements rather than replaces manual review of security-sensitive changes.
