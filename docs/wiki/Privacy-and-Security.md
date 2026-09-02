# Privacy and security

BiblioSleuth AI sends only metadata useful for edition matching: selected OPF values and bounded evidence from one confidently identified title page and one copyright page. It does not send body chapters or the complete book.

Security controls include:

- Fixed hosted-provider HTTPS origins, loopback-safe local endpoints, and redirects refused
- A fixed tool allowlist and schema-constrained output
- Local schema validation and normalization
- Prompt-injection separation for EPUB and web content
- Safe ZIP-path and archive-size handling
- Hardened XML parsing with a pinned build-time copy of `defusedxml`
- Sanitized comments HTML
- Restricted diagnostic logging and secret redaction
- Evidence checks before metadata can be recommended

Refused HTTP redirects are transport failures; they do not consume one of the
configured evidence-URL slots. Hosted search remains inside OpenAI or Anthropic;
SearXNG requests remain limited to the configured endpoint.

## API-key storage

The friendliest option is the operating-system credential vault. OpenAI,
Anthropic, and optional LM Studio credentials use separate entries and are never
copied between providers. Keys are never displayed after storage. Environment
variables and session-only storage are also supported.

When SearXNG is selected, bounded bibliographic queries go to that service and
its configured upstream engines. Results are untrusted evidence and are not
retained in metrics or diagnostics.

## Reporting vulnerabilities

Do not disclose secrets or unpublished vulnerabilities in a public issue. Follow the repository's [security policy](https://github.com/terrytrent/calibre-bibliosleuth-ai/blob/main/SECURITY.md).
