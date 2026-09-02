# Troubleshooting

## The toolbar action is missing

Restart calibre after installation. Then open **Preferences → Toolbars & menus**, choose the relevant toolbar, and add **BiblioSleuth AI**. The main icon runs research; its adjacent arrow opens configuration, About, documentation, and field-specific actions.

## An API key is required

Use the offered configuration action for the selected hosted provider. OpenAI
uses `OPENAI_API_KEY`; Claude uses `ANTHROPIC_API_KEY`. Local providers normally
need no key. A stored key is represented by status, never by revealing it.

Identity-linked or multi-workspace Anthropic keys also require the non-secret
`wrkspc_…` value in **Claude workspace ID** or `ANTHROPIC_WORKSPACE_ID`. A key
already scoped to one workspace may leave it blank.

## SearXNG test fails

Confirm the service is running, JSON response format is enabled, and
`/search?q=test&format=json` returns an object with a `results` array. Plain HTTP
works only on loopback by default. Upstream engines can temporarily throttle or
challenge a self-hosted instance.

## A local model connects but research fails

Connection does not prove structured-output quality. Load a schema-capable instruct
model with enough context, run the capability test, and confirm SearXNG returns
results. Small models may obey the schema yet still confuse editions, invent
metadata, or synthesize weak descriptions. Use a stronger model for real research,
compare it against books whose metadata you already know, and treat lightweight
models primarily as integration tests. On memory-limited Macs, a model may time
out or trigger swapping even when it can technically be loaded. Increase the
local-provider timeout from 60 seconds to about 120 seconds for smaller models or
180–300 seconds for larger models, then retry fresh. The first request after a
model loads is often slowest. If long timeouts recur alongside sustained memory
pressure or swapping, use a smaller model rather than continuing to increase the
timeout.

## LM Studio stops at the end of prompt processing

Confirm that a current BiblioSleuth AI build is installed. LM Studio receives a
compact decoder grammar because its runtime can stall while compiling the full
canonical metadata schema; BiblioSleuth AI still applies the complete schema
locally afterward. Fully restart calibre after updating the plugin.

Use a non-thinking instruct model. A thinking model may finish generation but put
the JSON in `reasoning_content` and leave `content` empty, producing the correct
`lmstudio returned invalid structured output` failure. Maintainer testing observed
this with `qwen/qwen3-4b-thinking-2507` and completed successfully with
`qwen/qwen3-4b-2507`. In LM Studio, use one concurrent prediction on a
memory-limited Mac and keep the Developer server running. `Connection refused`
means that nothing is listening at the configured endpoint; restart the server
and verify `/v1/models` before retrying.

## Claude hosted research uses multiple requests

This is expected. Anthropic web-search citations are always enabled, and its
strict structured-output mode cannot share a response with citations. The first
request performs cited research. Full eight-field metadata then uses two strict
generation requests because Anthropic rejects the complete compiled grammar. The
first establishes the edition match; the second reuses it and returns only its
remaining fields. Requests for four or fewer fields use one. SearXNG removes the hosted
search request and fee, but full Claude generation still uses two strict calls.

## Anthropic reports that the compiled grammar is too large

Fully restart Calibre after updating BiblioSleuth AI. Current builds split full
Claude metadata into two bounded strict schemas and merge them before canonical
local validation. If the error persists, collect a new diagnostic bundle so its
timestamp reflects the installed build.

## Model refresh succeeds but a model fails capability testing

Provider model-list APIs report available model identities, not every supported
feature. Choose another current instruct model and rerun the capability test.
For local providers, also confirm the model is loaded and has enough context for
the EPUB evidence, SearXNG results, and output schema.

## Research completed but nothing changed

Completion produces proposals, not automatic writes. Open the persistent notification or click the BiblioSleuth AI icon, select the fields to apply, and approve the book. Bulk acceptance is also available.

## A lookup failed

Use the user-visible error details and **Troubleshooting** action. **Retry failed fresh** bypasses the session cache. For support, use **Collect logs**, inspect the sanitized bundle, and attach it to a [GitHub issue](https://github.com/terrytrent/calibre-bibliosleuth-ai/issues).

## The exact edition is uncertain

Check identifiers, format, publisher, and date. Edit known proposals directly, or choose **Research fresh** with the Thorough preset.
