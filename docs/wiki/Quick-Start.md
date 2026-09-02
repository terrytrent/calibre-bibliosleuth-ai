# Quick start

1. Select one or more calibre books that contain EPUB files.
2. Configure OpenAI, Claude, Ollama, or LM Studio and select hosted search where
   offered or enter a tested SearXNG server.
3. Click the main **BiblioSleuth AI** icon.
4. Confirm the provider-aware preflight summary.
5. Continue using calibre while research runs as a background job.
6. When the persistent completion notice appears, click **Review books**.
7. Review and edit proposals, choose fields, and approve the book.

The completion notice can be hidden without discarding results. Click the BiblioSleuth AI icon later to resume review.

For a cost-conscious hosted starting point, choose OpenAI with the default
GPT-5.6 Luna model. Maintainer testing observed roughly $0.07 per complete
Balanced lookup versus nearly $0.13 with the default Claude Sonnet 5 path; actual
usage varies and the models are not capability-equivalent.

Maintainer testing found the best overall results with OpenAI hosted search.
OpenAI plus SearXNG was nearly as good and had the lowest API cost of the four
hosted-model paths, followed in cost by OpenAI hosted search, Claude plus SearXNG,
and Claude hosted search. Claude quality was on par with the corresponding OpenAI
search path. Treat this as observed guidance rather than a guaranteed benchmark.

For local inference, choose the strongest schema-capable instruct model your
hardware can run comfortably. Lightweight models are suitable for setup testing,
but may produce results far below OpenAI or Claude quality even when every
connection and capability test passes. Validate local output against known books
and review it carefully. Set the local timeout to at least 120 seconds; larger
models may need 180–300 seconds, particularly on the first request after loading.
For LM Studio, use a non-thinking model and keep its Developer server running;
the plugin endpoint is `http://127.0.0.1:1234/v1`, not the server root without
`/v1`.
Among the local combinations tested on the maintainer's M2 Mac, LM Studio with
`qwen/qwen3-4b-2507` produced acceptable results and outperformed Ollama with
`gemma3:4b` or `qwen3:8b`. Local results remain highly model- and hardware-dependent.

For unattended review, use **Accept all remaining books**. This applies the currently recommended fields to every remaining result, so use it only when you are comfortable accepting the AI proposals without inspecting each book.

## Research selected fields only

Open the arrow beside the toolbar icon and choose the specific-field research action. Select only the fields you want returned. Selecting **Series** automatically includes **Series Index**.
