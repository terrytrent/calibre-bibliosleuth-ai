# Researching metadata

BiblioSleuth AI extracts existing calibre metadata, selected OPF metadata, and
only high-confidence title-page and copyright-page evidence from the EPUB. It
then sends that bounded evidence to the selected AI provider. Web evidence comes
from OpenAI or Claude hosted search, or from the user-managed SearXNG instance.
Ollama and LM Studio always use SearXNG.

OpenAI hosted research completes search and strict output in one Responses API
request. Claude hosted research uses one cited search request followed by one or
two strict-schema requests because Anthropic does not permit web-search citations and
structured output in the same response. SearXNG modes perform bounded searches
first and pass their sanitized results to one model request for OpenAI and local
providers. Full Claude metadata uses two strict generation calls: the first
establishes the edition match and its assigned fields, and the second receives
that selected match and returns only the remaining fields. Requests for four or
fewer fields use one Claude generation call.

Exact-edition matching is prioritized in this order:

1. Exact ISBN or identifier agreement
2. Publisher, edition, format, and publication-date agreement
3. Title and author agreement
4. Series and description consistency

Every returned field includes a value, confidence, evidence URLs, and an inference marker. Missing information remains null rather than being invented. Results must pass a fixed local schema before review.

## Specific-field research

The selected-field runtime schema restricts the response to the requested metadata. It takes precedence even when a custom prompt asks for every field. The custom prompt itself is not changed. Series research always includes series index.

## Cached and fresh research

Repeated lookups may use the session cache when the EPUB fingerprint, model, effective prompt, and settings match. Choose **Research fresh** to bypass that cache and retrieve current results.
