# Frequently asked questions

## Does BiblioSleuth AI upload the whole EPUB?

No. It sends selected OPF metadata and bounded evidence from a confidently identified title page and copyright page, never body chapters.

## Does it modify the EPUB?

No. Approved values are written to the calibre database only.

## Do I need an OpenAI API key?

Only when OpenAI is selected. Claude uses a separate Anthropic API key. Ollama
normally needs no token; LM Studio needs one only when server authentication is
enabled. Chat subscriptions and API billing remain separate products.

## Can I avoid hosted web-search charges?

Yes. Run SearXNG separately and select it as the web-research provider. SearXNG
has no per-query API fee, though it uses local resources, contacts configured
upstream search engines, and its evidence still consumes AI input tokens.

## Can I research only descriptions or authors?

Yes. Use the specific-field action in the toolbar dropdown. Series selection automatically includes series index.

## Can I correct a wrong proposal before applying it?

Yes. Select the field and choose **Edit proposed value**.

## Can I approve a batch without reviewing every book?

Yes. Choose **Accept all remaining books**, with the understanding that this blindly applies the recommended fields.

## Why did a repeated lookup return instantly?

The matching result may have come from the session cache. Choose **Research fresh** to bypass it.

## Is the displayed price exact?

No. It is an estimate based on known pricing and reported usage; actual billing may differ.

## Which hosted provider is less expensive?

OpenAI plus SearXNG was the least expensive billable-model path in maintainer
testing, followed by OpenAI hosted search, Claude plus SearXNG, and Claude hosted
search. With the bundled hosted-search defaults, testing observed about $0.07 per
book with GPT-5.6 Luna versus nearly $0.13 with Claude Sonnet 5. These are planning
observations rather than guarantees. Local inference has no model API fee but has
hardware, power, time, and maintenance costs.

## Which provider and search combination produced the best results?

Maintainer testing ranked OpenAI hosted search first, OpenAI with SearXNG a close
second, Claude hosted search third and on par with OpenAI, and Claude with SearXNG
fourth and on par with OpenAI plus SearXNG. LM Studio with SearXNG ranked fifth
and produced acceptable results with `qwen/qwen3-4b-2507`. Ollama with SearXNG
ranked sixth in the tested group; `gemma3:4b` and `qwen3:8b` were weaker than the
tested LM Studio Qwen 3 4B path. This is a small-sample observation and can change
with books, models, search results, configuration, and hardware.

## Will a local model match OpenAI or Claude?

Not necessarily. BiblioSleuth AI's exact-edition workflow requires strong source
comparison, instruction following, structured output, and resistance to invented
facts. Small models can prove that Ollama or LM Studio is configured correctly
without producing dependable metadata. Maintainer testing on an M2 Mac with 16 GB
of unified memory found that locally practical models produced substantially
weaker results than OpenAI or Claude. Test against known books and review all local
proposals carefully; larger models also require more memory and may be slow.

Local inference often needs a longer timeout than a hosted API. Start at 120
seconds and consider 180–300 seconds for a larger model, especially for its first
request after loading. Repeated timeouts with memory pressure usually indicate
that the model is too large for the machine, not that SearXNG is failing.

## Why does an LM Studio thinking model fail after generating JSON?

Some thinking variants place the result in `reasoning_content` and return an empty
standard `content` field. BiblioSleuth AI requires the normal OpenAI-compatible
structured-output field and rejects the empty response. Choose the corresponding
non-thinking instruct model. Maintainer testing succeeded with
`qwen/qwen3-4b-2507` and reproduced this failure with its `-thinking-2507`
variant; model behavior can change between releases.
