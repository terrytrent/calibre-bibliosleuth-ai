# Provider and search setup

Choose the inference provider and search path separately. OpenAI and Claude can
use hosted search or SearXNG. Ollama and LM Studio require SearXNG.

| AI provider | Credential | Search choices | Default endpoint/model |
| --- | --- | --- | --- |
| OpenAI | OpenAI API key | OpenAI hosted or SearXNG | `gpt-5.6-luna` |
| Claude | Anthropic API key | Claude hosted or SearXNG | `claude-sonnet-5` |

Identity-linked or multi-workspace Anthropic keys also require a workspace ID. Copy the `wrkspc_…` value from Claude Console → Settings → Workspaces into **Claude workspace ID**, or set `ANTHROPIC_WORKSPACE_ID`. Keys scoped to one workspace do not require it.
| Ollama | Normally none | SearXNG | `http://127.0.0.1:11434/v1` |
| LM Studio | Optional local token | SearXNG | `http://127.0.0.1:1234/v1` |

Credentials are stored under separate provider identities. An optional local
token can never fall back to, overwrite, or be substituted for a hosted-provider
key.

## OpenAI

1. Create an [OpenAI project API key](https://platform.openai.com/api-keys).
2. Select **OpenAI**, enter the key, and leave secure storage enabled unless the
   key should remain session-only.
3. Choose hosted search for the simplest setup, or enter a tested SearXNG URL.
4. Refresh model choices, run **Test Connection**, then approve the disclosed
   **Test Model Capabilities** request.

## Claude

1. In Claude Console, open **Settings → API keys** following the
   [Anthropic authentication guide](https://platform.claude.com/docs/en/manage-claude/authentication), create a key, and note its
   expiration. The key is separate from an ordinary Claude chat subscription.
2. Select **Claude**, enter the key, and choose Claude hosted search or SearXNG.
3. Refresh models and run both tests. The hosted capability test performs a real
   search and may be billable.
4. Claude hosted research uses a cited search request followed by native strict
   JSON generation. Full metadata uses two strict calls: the first establishes
   the edition match and its assigned fields; the second receives that match and
   returns only the remaining fields. Requests for four or fewer fields use one.
   This is expected: Anthropic does not permit
   citations and structured output in one response and rejects the complete
   eight-field grammar. The handoff contains only bounded,
   sanitized research text and citation metadata, not opaque search state.

## Ollama

1. Install and start Ollama using its [official documentation](https://docs.ollama.com/).
2. Download an instruct model with `ollama pull <model>`.
3. Confirm the OpenAI-compatible API is available at
   `http://127.0.0.1:11434/v1`.
4. Select **Ollama**, configure SearXNG, refresh models, and run both tests.

A connection test proves reachability, not reliable schema generation. Very small
or short-context models may connect successfully but fail research.

## LM Studio

1. Install the full [LM Studio](https://lmstudio.ai/) desktop application. The
   Bionic chat surface alone does not expose the server configuration needed by
   BiblioSleuth AI.
2. Download and load a schema-capable, **non-thinking** instruct model. On a
   memory-limited Mac, an 8192-token context and one concurrent prediction are
   conservative starting settings.
3. Open **Developer**, start the
   [local server](https://lmstudio.ai/docs/developer/core/server). The `lms`
   alternative is `lms server start`. Keep it running during research.
4. Keep the default loopback binding. `http://127.0.0.1:1234` is the server root;
   enter `http://127.0.0.1:1234/v1` in BiblioSleuth AI. If authentication is
   enabled, create a local token.
5. Select **LM Studio**, configure SearXNG, refresh models, and run the connection,
   model-capability, and SearXNG tests.

Avoid thinking/reasoning variants. LM Studio may place their entire generated
JSON in `reasoning_content` while returning an empty standard `content` value,
which BiblioSleuth AI correctly rejects as invalid structured output. Maintainer
testing completed successfully with `qwen/qwen3-4b-2507`, while
`qwen/qwen3-4b-thinking-2507` failed in this manner. This is an integration
example, not a claim that the 4B model matches hosted-provider research quality.

Do not enable network serving unless it is deliberate and protected. BiblioSleuth
AI rejects plain remote HTTP by default; use HTTPS for a remote model server.

## Choosing a local model

Exact-edition research requires more than valid JSON. The model must reconcile
conflicting search results, separate similar editions, preserve uncertainty, and
avoid invented metadata and citations. Use a strong, current instruct model for
real research. Small models are valuable for connection and compatibility tests,
but successful tests do not establish research quality.

Maintainer testing on an M2 Mac with 16 GB of unified memory found that models
practical on that system did not produce results close to OpenAI or Claude.
Larger models may improve quality but need more unified memory, run more slowly,
and can time out or cause macOS memory pressure. Validate any local model against
known books, use **Research fresh** for comparisons, and review every proposal.

Set a longer timeout for local providers than for hosted APIs. Start at 120
seconds for smaller models and try 180–300 seconds for larger ones. The first
request after loading is commonly the slowest. A longer timeout permits slow
inference; it cannot resolve sustained memory pressure, heavy swapping, or a model
that does not fit comfortably, so repeated long timeouts are a reason to select a
smaller model.

In maintainer testing, LM Studio with `qwen/qwen3-4b-2507` produced acceptable
results and ranked above the tested Ollama `gemma3:4b` and `qwen3:8b` paths.
This comparison reflects those specific runtimes, models, books, and hardware; it
does not imply that LM Studio is inherently more capable than Ollama.

## SearXNG

SearXNG runs separately from BiblioSleuth AI. Install it using the
[official container guide](https://docs.searxng.org/admin/installation-docker.html),
keep it on loopback or HTTPS, and enable JSON output:

```yaml
search:
  formats:
    - html
    - json
```

Verify the service before configuring the plugin:

```sh
curl 'http://127.0.0.1:8080/search?q=ISBN+9780143127741&format=json'
```

Then enter `http://127.0.0.1:8080` in BiblioSleuth AI and select **Test
SearXNG**. A 403 or non-JSON response usually means the `json` format is not
enabled or a reverse proxy is blocking the request.

SearXNG has no per-query API fee, but queries are disclosed to the configured
instance and its upstream engines. It is not an MCP server, and BiblioSleuth AI
does not need an MCP package for this workflow.

## Final readiness checklist

When a local provider is chosen in the first-run wizard, BiblioSleuth AI opens
the full configuration screen before research so these steps can be completed.

- The selected model appears after **Refresh Model Choices**.
- After changing provider or model, revalidate any custom system prompt against
  the newly selected runtime.
- **Test Connection** succeeds.
- **Test Model Capabilities** confirms structured output and the selected search.
- **Test SearXNG** succeeds when SearXNG is selected.
- The preflight dialog shows the intended AI provider, search path, model, and
  cost guidance before starting a batch.
