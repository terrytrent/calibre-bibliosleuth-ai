# Configuration

Open the arrow beside the BiblioSleuth AI toolbar icon and choose **Configure BiblioSleuth AI**.

## General

Choose **OpenAI**, **Claude**, **Ollama**, or **LM Studio**. OpenAI and Claude can
use hosted web search or a user-managed SearXNG server. Ollama and LM Studio
require SearXNG. Each provider keeps its own model, endpoint, and credential.
See [Provider and search setup](Provider-and-Search-Setup.md) for complete setup
and verification checklists.

Ollama defaults to `http://127.0.0.1:11434/v1`; LM Studio defaults to
`http://127.0.0.1:1234/v1`; SearXNG defaults to `http://127.0.0.1:8080`. Use
**Refresh Model Choices**, **Test Connection**, **Test Model Capabilities**, and
**Test SearXNG** before the first lookup.

For LM Studio, note that `http://127.0.0.1:1234` is the server root but the plugin
setting requires `http://127.0.0.1:1234/v1`. Use a non-thinking instruct model and
keep LM Studio's Developer server running during research. Thinking variants that
return JSON only as `reasoning_content` are incompatible with the required
OpenAI-compatible structured `content` response.

Run SearXNG separately using its official container documentation and enable
`json` under `search.formats` in `settings.yml`. Plain HTTP is restricted to the
same computer by default; use HTTPS for a remote instance.

- **Replace API key:** the field is intentionally blank when a key is already stored. Type a new key to replace it; leaving it blank preserves the existing key.
- **Remember securely:** stores the key in the operating-system credential vault. Disable this for session-only storage.
- **Delete Stored API Key:** deliberately removes the saved credential.
- **Model:** choose a compatible model from the validated dropdown.
- **Refresh model choices:** requests the current compatible model list. Successful results are cached for seven days.
- **Claude workspace ID:** required for identity-linked or multi-workspace Anthropic keys; copy the `wrkspc_…` value from Claude Console → Settings → Workspaces. Leave it blank for a key already scoped to one workspace.
- **Maximum searches per book:** limits the edition-oriented SearXNG queries made
  for each book (1–10, default 3). It does not affect provider-hosted search.
- **Results per search:** limits the sanitized SearXNG results supplied to the
  model for each query (1–10, default 6). Higher values can improve coverage but
  increase model input and may add noise.
- **Timeout:** maximum duration allowed for an API request. Local models commonly
  need at least 120 seconds; larger or memory-constrained models may need 180–300
  seconds, especially on their first request after loading. The default is 60
  seconds and the available range is 10–300 seconds.

`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID`, or
`LM_STUDIO_API_KEY`, when applicable, takes priority over the corresponding
stored setting.

## Optimization

Choose Economy, Balanced, Thorough, or Custom. Balanced is the default. Economy
uses 4,000 evidence characters, low search context, no reasoning, 1,600 output
tokens, and 2 evidence URLs per field. Balanced uses 6,000, low, low, 2,000, and
3 respectively; Thorough uses 12,000, medium, medium, 3,000, and 4. Custom
unlocks those five controls (1,000–50,000 evidence characters, low/medium/high
search context, none/low/medium/high reasoning, 800–10,000 output tokens, and
1–10 evidence URLs).

**Maximum tags** (1–100, default 20) and **Maximum description characters**
(500–30,000, default 5,000) are independent safety limits applied to values
written to Calibre; changing presets does not change them. A low output-token cap
can still prevent the model from completing a long structured response.

## System prompt

An empty override uses the bundled prompt. Use **View Default**, **Preview Effective Prompt**, **Validate Prompt**, **Copy Default**, and **Restore Default** to manage an override safely. Custom prompts cannot be saved until validation succeeds.

## Privacy and security

This tab controls optional local statistics, diagnostic behavior, and related privacy settings. See [Privacy and security](Privacy-and-Security.md) before enabling verbose diagnostics.
