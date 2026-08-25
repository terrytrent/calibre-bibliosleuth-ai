# Privacy and security

BiblioSleuth AI sends only metadata useful for edition matching: selected OPF values and bounded evidence from one confidently identified title page and one copyright page. It does not send body chapters or the complete book.

Security controls include:

- HTTPS requests to the fixed OpenAI API origin with redirects refused
- A fixed tool allowlist and schema-constrained output
- Local schema validation and normalization
- Prompt-injection separation for EPUB and web content
- Safe ZIP-path and archive-size handling
- Hardened XML parsing with a pinned build-time copy of `defusedxml`
- Sanitized comments HTML
- Restricted diagnostic logging and secret redaction
- Evidence checks before metadata can be recommended

Refused HTTP redirects are transport failures; they do not consume one of the configured evidence-URL slots. Hosted web search remains performed by OpenAI.

## API-key storage

The friendliest option is the operating-system credential vault. The key is never displayed after storage. You may replace it by typing a new key, explicitly delete it, use `OPENAI_API_KEY`, or choose session-only storage.

## Reporting vulnerabilities

Do not disclose secrets or unpublished vulnerabilities in a public issue. Follow the repository's [security policy](https://github.com/terrytrent/calibre-bibliosleuth-ai/blob/main/SECURITY.md).
