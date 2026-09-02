# Optimization and cost

BiblioSleuth AI reports input, cached-input, output, reasoning, and total tokens;
hosted and SearXNG search calls; elapsed time; and approximate cost when a dated
price is available. OpenAI and first-party Claude estimates can differ from the
final invoice because account discounts, taxes, regions, and service tiers vary.
Local inference is labeled as having no reported API cost.

## OpenAI versus Claude defaults

OpenAI is substantially cheaper for the bundled default workflow. Maintainer
testing of complete Balanced hosted-search lookups observed approximately **$0.07
per book with GPT-5.6 Luna** and **nearly $0.13 with Claude Sonnet 5**. Use those
figures as planning examples, not guaranteed prices or an equal-capability
benchmark. Book evidence, search behavior, generated output, provider prices,
discounts, taxes, and regions all change the final charge.

The current standard token rates also favor Luna: GPT-5.6 Luna is $0.20 per
million input tokens and $1.20 per million output tokens, while Claude Sonnet 5
is $2 per million input tokens and $10 per million output tokens. Hosted search
is $0.01 per call at both providers. Claude full-record research additionally
uses a cited search phase and two strict generation calls, whereas OpenAI normally
uses one Responses API request. Check the [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
and [Anthropic API pricing](https://platform.claude.com/docs/en/about-claude/pricing)
before a large batch.

## Maintainer-observed quality and cost ranking

| Quality order | Research path | Observed quality | API-cost order among hosted-model paths |
| ---: | --- | --- | ---: |
| 1 | OpenAI + OpenAI hosted search | Best overall | 2 |
| 2 | OpenAI + SearXNG | Nearly as good as OpenAI hosted search | 1 (lowest) |
| 3 | Claude + Claude hosted search | On par with OpenAI | 4 (highest) |
| 4 | Claude + SearXNG | On par with OpenAI + SearXNG | 3 |
| 5 | LM Studio + SearXNG | Model-dependent; acceptable with `qwen/qwen3-4b-2507` in maintainer testing | No model API fee |
| 6 | Ollama + SearXNG | Model-dependent; tested `gemma3:4b` and `qwen3:8b` trailed LM Studio's tested Qwen 3 4B path | No model API fee |

This ordering summarizes limited maintainer testing, not a permanent benchmark.
Different books, model versions, SearXNG results, settings, prompts, and hardware
can change it. Cost ranks compare the four paths that still call a billable
OpenAI or Anthropic model. Local inference has no per-request model API fee but
does consume local compute, power, time, and maintenance effort.

| Research path | Calls per uncached book | Cost notes |
| --- | --- | --- |
| OpenAI hosted search | One Responses API request with search | Model and hosted-search charges may apply |
| Claude hosted search | One cited search request, then one or two strict-schema requests | All model calls and hosted search may be billable |
| OpenAI or Claude with SearXNG | SearXNG queries, then one model request; full Claude metadata uses two | No SearXNG API fee; model tokens may be billable |
| Ollama or LM Studio with SearXNG | SearXNG queries, then one local model request | Local hardware, power, and upstream-search costs remain |

## Presets

| Preset | Evidence URLs | Intended use |
| --- | ---: | --- |
| Economy | 2 | Lowest-cost routine matching |
| Balanced | 3 | Recommended default |
| Thorough | 4 | Difficult or ambiguous editions |
| Custom | Configurable | Manual control of every optimization setting |

The presets also vary front-matter evidence size, search context, reasoning effort, and output cap.

## Ways to reduce cost

- Prefer the default OpenAI GPT-5.6 Luna path when minimizing hosted-provider cost
  matters more than comparing Claude-specific output quality.
- Select SearXNG instead of hosted search to remove the provider's hosted-search
  fee. Model input/output tokens can still be billable.
- Use Ollama or LM Studio for local inference. BiblioSleuth AI reports available
  performance and token measurements but does not price local compute.
- Use Economy for books with strong identifiers.
- Research only the fields you need.
- Keep the session cache enabled and use **Research fresh** only when necessary.
- Avoid repeatedly validating custom prompts; validation and repair use billable model calls.
- Use batches deliberately and inspect the preflight estimate.

Automated tests mock every AI and search provider and do not incur API charges.
