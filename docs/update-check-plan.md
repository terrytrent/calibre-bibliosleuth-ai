# Deferred update-check design

Status: deferred until the maintainer can fully transfer the custom domain.

This document records the agreed direction for adding a friendly version check to
BiblioSleuth AI. It is a design note, not an implemented feature. No plugin code,
release automation, Cloudflare credentials, DNS records, or production update
endpoint are currently configured by this branch.

## Decision summary

- Publish a small static JSON manifest through Cloudflare Pages.
- Serve it from a dedicated custom subdomain such as
  `updates.example.com/bibliosleuth/latest.json`; the final hostname is deferred.
- Deploy the manifest automatically only after a tagged GitHub Release has been
  published successfully.
- Have the plugin check in the background no more than once every seven days.
- Notify without interrupting the user, and never download or install an update
  automatically.
- Keep GitHub Releases as the authoritative location for release notes, the plugin
  ZIP, checksum, SBOM, and artifact attestations.

Cloudflare Pages static assets are suitable because they require no dynamic
function and are currently free for this use. A dedicated subdomain also keeps the
update trust boundary separate from the maintainer's primary website and permits a
future hosting change through DNS.

## Alternatives considered

### GitHub Releases REST API

The public endpoint is easy to consume but unauthenticated requests share a limit
of 60 requests per hour per originating IP address. A weekly persistent cache would
make that limit unlikely to matter for an individual installation, but a static
manifest avoids the API quota entirely and requires no GitHub credential.

### GitHub `releases/latest`

The supported latest-release redirect is a reasonable zero-configuration fallback
and can expose the current tag without using the REST API. It does not provide a
purpose-built, extensible manifest and remains tied directly to GitHub hosting.

### DNS TXT record

A TXT record can carry a version but was rejected as the primary design because
portable TXT resolution would require another bundled dependency or a DNS-over-HTTPS
service. Resolver caching, TXT quoting and splitting, multiple answers, and uneven
DNSSEC validation would add complexity without improving the user experience.

## Manifest contract

The first manifest should remain small, stable, and strictly validated:

```json
{
  "schema": 1,
  "product": "BiblioSleuth AI",
  "channel": "stable",
  "version": "1.1.1",
  "published": "2026-09-05T21:27:55Z",
  "minimum_calibre": "7.0.0"
}
```

The release workflow must generate `version` from the already validated semantic
tag and `published` from a UTC timestamp. `minimum_calibre` should come from plugin
metadata rather than duplicated workflow text.

The plugin should derive the release page from the validated version:

```text
https://github.com/terrytrent/calibre-bibliosleuth-ai/releases/tag/vMAJOR.MINOR.PATCH
```

The manifest should not be trusted to supply an arbitrary release or download URL.
A future schema may include the release ZIP SHA-256, but the initial version checker
does not need it because it will not download or install files.

## Cloudflare preparation

After the domain transfer is complete:

1. Create a Cloudflare Pages Direct Upload project, tentatively named
   `bibliosleuth-updates`.
2. Attach a dedicated update subdomain and confirm automatic HTTPS works.
3. Create a custom Cloudflare API token with only **Account / Cloudflare Pages /
   Edit**, restricted to the relevant account as narrowly as Cloudflare permits.
   Do not use the Global API Key.
4. Store the account identifier and token as GitHub Actions environment secrets:
   `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`.
5. Use a protected GitHub environment tentatively named `cloudflare-updates` so
   these credentials are available only to the production deployment job.
6. Never paste the token into issues, chat, source, workflow output, diagnostics,
   or Calibre preferences.

Cloudflare documents Direct Upload from continuous integration with Wrangler and
requires the account-scoped Cloudflare Pages Edit permission:

- <https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/>
- <https://developers.cloudflare.com/fundamentals/api/reference/permissions/>

## Automated release sequence

Extend the existing tagged release workflow in this order:

1. Validate that the tag is semantic, matches the embedded plugin version, and is
   reachable from `main`.
2. Complete the Windows, macOS, Linux, SearXNG, Ollama, OpenAI-compatible,
   packaging, dependency, quality, and security gates.
3. Build and verify the deterministic ZIP, checksum, and SBOM; create artifact
   attestations.
4. Publish the GitHub Release and its assets.
5. Generate `latest.json` into the runner's temporary directory.
6. Deploy that directory to the production Cloudflare Pages project.
7. Fetch the public custom-domain URL and validate that its manifest reports the
   tagged version before declaring the deployment successful.

Publishing GitHub first is intentional. If Cloudflare deployment fails, the new
release remains valid while clients continue to see the previous manifest. The
deployment job should be rerunnable without rebuilding or republishing the release.

The Cloudflare deployment job should:

- depend on the successful GitHub publisher job;
- run only for version tags, never for pull requests;
- receive only the permissions it needs, normally `contents: read`;
- use the protected `cloudflare-updates` environment;
- pin every third-party action to an immutable commit;
- pin the Wrangler version rather than installing an unbounded latest version;
- avoid printing secrets or verbose authenticated request headers; and
- upload only the directory containing the generated manifest.

## Plugin behavior

The check must be friendly and must not delay Calibre startup or research:

- Start it asynchronously after the first normal plugin use in a Calibre session.
- Persist the last-attempt and last-success timestamps across restarts.
- Check automatically at most once every seven days.
- Provide an explicit **Check for updates…** command in the toolbar menu and Help
  settings tab.
- Consider an **Automatically check weekly** preference. Decide its default during
  implementation and disclose the small GitHub-independent network request during
  onboarding or in settings.
- Show one non-modal notification for each newly discovered stable version.
- Add a clear **Update available: VERSION…** menu entry until the user visits or
  dismisses that release.
- Open the derived GitHub release page only after the user's confirmation.
- Do not automatically download, install, or replace a plugin ZIP.
- Ignore prereleases in schema version 1.

Only update-check state belongs in preferences, for example:

```json
{
  "last_update_attempt": "2026-09-05T21:27:55Z",
  "last_update_success": "2026-09-05T21:27:55Z",
  "latest_known_version": "1.1.1",
  "last_notified_version": "1.1.1"
}
```

Do not include library, book, provider, API-key, model, installation-identity, or
hardware information in the request.

## Transport and validation requirements

- Permit only HTTPS to the exact configured update hostname and fixed manifest
  path.
- Refuse cross-origin redirects and revalidate scheme and host at the boundary.
- Use a short connection/read timeout, approximately five seconds.
- Cap the response at 4 KiB before parsing.
- Require UTF-8 JSON, an exact supported schema number, the exact product name,
  the stable channel, a sanitized `MAJOR.MINOR.PATCH` version, a valid UTC timestamp,
  and a supported Calibre-version value.
- Compare numeric tuples, never lexicographic version strings.
- Ignore equal, older, malformed, incompatible, and unsupported-schema manifests.
- Make no automatic retry. On ordinary failure, record the attempt and remain
  silent. On a server or transport failure, wait at least one day before a manual
  background retry and retain the last valid manifest.
- Never place the manifest body, response headers, custom domain, or request details
  in normal diagnostic journals unless the established redaction rules explicitly
  permit a non-sensitive summary.

The update transport should be separate from AI-provider transports. It has no
credentials and must not loosen the provider origin, redirect, or bearer-token
protections.

## Test plan

Keep manifest parsing, version comparison, scheduling, and notification decisions
independent of Qt and Calibre where practical. Automated coverage should include:

- equal, newer, older, major, minor, and patch versions;
- rejection of leading/trailing junk, excessive lengths, malformed semantic
  versions, booleans, nulls, and unexpected value types;
- unsupported schemas, wrong product/channel, invalid timestamps, and incompatible
  Calibre versions;
- oversized, invalid UTF-8, invalid JSON, duplicate-key policy, and truncated
  responses;
- HTTPS/hostname/path enforcement and same-origin/cross-origin redirect behavior;
- timeouts, DNS failures, TLS failures, HTTP errors, and offline operation;
- seven-day persistence, clock skew, failed-attempt backoff, and manual refresh;
- suppression of repeated notifications for the same release;
- no update when the manifest is equal to or older than the installed version;
- confirmation and URL validation before opening the GitHub release page;
- proof that no library metadata, API credentials, model settings, or unique
  identifiers enter the request or persisted state;
- release-workflow manifest generation from the tag and embedded version;
- deployment ordering, least-privilege permissions, secret isolation, immutable
  action pins, and post-deployment verification; and
- packaged-plugin inclusion for every new runtime module or resource.

Tests must mock normal update requests and must not depend on Cloudflare. A separate
non-billable integration contract may serve a local HTTPS fixture if it adds useful
transport coverage.

## Documentation work when implementation resumes

Update the README, bundled HTML guide, wiki, About text where appropriate,
configuration help, privacy/security documentation, developer guide, changelog,
MobileRead update summary, and release notes to explain:

- what is requested and how often;
- that no library data or credentials are sent;
- how to disable automatic checks and run a manual check;
- how update notifications behave;
- that installation is always deliberate and manual; and
- troubleshooting for offline, blocked, or stale manifests.

## Decisions deferred with the domain transfer

- Final custom update hostname and manifest path.
- Cloudflare account and Pages project names.
- Whether weekly automatic checks default on or require first-run opt-in.
- Exact non-modal notification and toolbar badge treatment.
- Whether the first manifest includes the ZIP checksum.
- Whether a supported GitHub `releases/latest` check should be retained as a manual
  fallback when the custom endpoint is unavailable.

Resume only after the custom domain is under the maintainer's full control and the
Cloudflare Pages endpoint can be configured without a temporary hostname migration.
