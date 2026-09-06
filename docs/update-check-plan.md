# Update-check design and deployment notes

Status: plugin implementation and automated production deployment configured.

This document records the security and deployment decisions behind BiblioSleuth
AI's version check. The production manifest is available at
`https://bibliosleuthai-updates.trentathome.xyz/latest.json`.

## Decision summary

- Publish a small static JSON manifest as Cloudflare Worker static assets.
- Serve it from the dedicated custom endpoint
  `https://bibliosleuthai-updates.trentathome.xyz/latest.json`.
- Deploy the manifest automatically only after a tagged GitHub Release has been
  published successfully.
- Have the plugin check in the background no more than once every 24 hours.
- Notify without interrupting the user, and never download or install an update
  automatically.
- Keep GitHub Releases as the authoritative location for release notes, the plugin
  ZIP, checksum, SBOM, and artifact attestations.

Cloudflare Worker static assets are suitable because they require no dynamic
application code for this use. A dedicated subdomain also keeps the update trust
boundary separate from the maintainer's primary website and permits a future
hosting change through DNS.

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
  "version": "1.2.0",
  "published": "2026-09-06T01:06:34Z",
  "minimum_calibre": "7.0.0",
  "changelog": {
    "summary": "Adds private, user-controlled update notifications and protected release publishing.",
    "items": [
      {
        "category": "Added",
        "text": "Checks daily in the background, supports manual checks, and shows concise release highlights when an update is available."
      },
      {
        "category": "Added",
        "text": "Provides next-day reminders and per-version notification suppression while keeping installation fully manual."
      },
      {
        "category": "Security",
        "text": "Uses a fixed credential-free endpoint, rejects redirects and malformed responses, and never downloads or installs plugin code."
      }
    ]
  }
}
```

Schema 1 includes changelog metadata from its first release; there is no earlier
published client contract to migrate. `summary` is required plain text of at most
300 characters. `items` contains 1–8 objects with an exact `category` and `text`;
categories follow Keep a Changelog (`Added`, `Changed`, `Deprecated`, `Removed`,
`Fixed`, or `Security`) and item text is limited to 240 characters. Control
characters, HTML-like text, and URLs are rejected. The UI renders every accepted
value explicitly as plain text.

The upload-ready repository copy lives at `docs/update-site/latest.json`. Keep it
aligned with the tagged version and curated high-level release notes before
uploading it to the fixed production endpoint.

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

## Cloudflare configuration

1. The asset-only Worker is named `bibliosleuthai-updates` and its custom domain
   is managed in the Cloudflare dashboard.
2. The deployment token has **Account / Workers Scripts / Edit**, restricted to
   the account containing that Worker. It does not need route permission while
   the existing custom domain remains dashboard-managed. Do not use the Global
   API Key.
3. The protected `cloudflare-updates` GitHub environment is restricted to `v*`
   tags. It stores `CLOUDFLARE_API_TOKEN` as a secret and
   `CLOUDFLARE_ACCOUNT_ID` plus `CLOUDFLARE_WORKER_NAME` as variables.
4. Never place the token in source, workflow output, diagnostics, Calibre
   preferences, issues, or other public records. Rotate it after suspected
   exposure and replace the GitHub environment secret.
5. Persist invocation logs for operational monitoring and disclose this ordinary
   request/response metadata retention in user-facing privacy documentation. The
   plugin's fixed request has no query string.

Cloudflare documents Worker deployment from GitHub Actions with Wrangler and
requires Workers Scripts write access:

- <https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/>
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
6. Deploy that directory as static assets to the production Cloudflare Worker.
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

`scripts/generate_update_manifest.py` requires the checked-in template version to
match the validated release tag, derives the minimum Calibre version from plugin
metadata, replaces the publication timestamp, and validates the final schema
before Wrangler sees it. It also enforces the client's 4 KiB byte limit after
UTF-8 encoding. A stale, oversized, or malformed template therefore fails
without changing production. The deployment uses pinned Wrangler directly
rather than a separate deployment action. `wrangler.jsonc` fixes the compatibility date,
disables per-version preview URLs, and preserves dashboard observability with
persisted invocation logs. The final step downloads and validates the public
manifest.

## Plugin behavior

The check must be friendly and must not delay Calibre startup or research:

- Start it asynchronously after the first normal plugin use in a Calibre session.
- Persist the last-attempt and last-success timestamps across restarts.
- Check automatically at most once every 24 hours.
- Provide an explicit **Check for Updates…** command in the toolbar menu.
- Enable **Automatically check daily for updates** by default in Help settings and
  disclose the small GitHub-independent network request during onboarding.
- Show a non-modal notification for each newly discovered stable version. Let the
  user choose **Remind me tomorrow** or **Skip this version**; a skipped version
  remains quiet while a later release may notify normally.
- Add a clear **Update available: VERSION…** menu entry until the user visits or
  dismisses that release.
- Open the derived GitHub release page only after the user's confirmation.
- Do not automatically download, install, or replace a plugin ZIP.
- Ignore prereleases in schema version 1.

Only update-check state belongs in preferences, for example:

```json
{
  "last_update_attempt": 1788643675.0,
  "last_update_success": 1788643675.0,
  "latest_known_version": "1.2.0",
  "latest_known_minimum_calibre": "7.0.0",
  "update_remind_version": "1.2.0",
  "update_remind_after": 1788730075.0,
  "skipped_update_version": ""
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
  a supported Calibre-version value, and the bounded schema-1 changelog object.
- Compare numeric tuples, never lexicographic version strings.
- Ignore equal, older, malformed, incompatible, and unsupported-schema manifests.
- Make no automatic retry. On ordinary failure, record the attempt, remain
  silent, and wait at least one day before another automatic attempt. Explicit
  manual checks may run at any time and the last valid version remains retained.
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
- missing, oversized, unsafe, malformed, or unknown changelog values and all
  supported Keep a Changelog categories;
- HTTPS/hostname/path enforcement and same-origin/cross-origin redirect behavior;
- timeouts, DNS failures, TLS failures, HTTP errors, and offline operation;
- daily persistence, clock skew, failed-attempt backoff, and manual refresh;
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

## Documentation coverage

Update the README, bundled HTML guide, wiki, About text where appropriate,
configuration help, privacy/security documentation, developer guide, changelog,
MobileRead update summary, and release notes to explain:

- what is requested and how often;
- that no library data or credentials are sent;
- how to disable automatic checks and run a manual check;
- how update notifications behave;
- that installation is always deliberate and manual; and
- troubleshooting for offline, blocked, or stale manifests.

## Possible future extensions

- Add the release ZIP checksum in a later manifest schema if the plugin ever gains
  an explicit download workflow.
- Consider a supported GitHub `releases/latest` manual fallback if the dedicated
  endpoint proves insufficient. Schema 1 deliberately has no fallback request.
