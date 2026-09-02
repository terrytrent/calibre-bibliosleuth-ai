# Statistics and diagnostics

BiblioSleuth AI can record compact local lookup statistics without charts. Available measurements include:

- Queue, extraction, API, validation, review, and apply durations
- Books attempted, completed, failed, skipped, and cache-served
- Average, median, minimum, maximum, and percentile lookup times
- Throughput per minute and estimated completion time
- Token totals, cached-token share, searches, estimated cost, and cost per book
- Preset, model family, requested fields, and failure categories

Statistics are bounded local data and can be viewed, exported, or cleared from the plugin. They do not include API keys, extracted book passages, or full prompts.

Filter or group by AI provider and search provider to compare OpenAI, Claude,
Ollama, and LM Studio. Hosted-search and SearXNG calls are counted separately.
Local inference is labeled as having no reported API cost; missing provider
measurements remain unavailable rather than being presented as zero.

## Collect logs

On an error, choose **Collect logs** to build a support bundle containing sanitized plugin diagnostics, relevant calibre/plugin versions, settings summaries, and failure details. Review the archive before sharing it. Book text, request headers, credentials, and full custom prompts are excluded from normal diagnostics.
