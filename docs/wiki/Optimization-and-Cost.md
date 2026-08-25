# Optimization and cost

BiblioSleuth AI reports input, cached-input, output, reasoning, and total tokens; web-search calls; elapsed time; and approximate cost for each lookup and job. Estimates can differ from the final OpenAI invoice.

## Presets

| Preset | Evidence URLs | Intended use |
| --- | ---: | --- |
| Economy | 2 | Lowest-cost routine matching |
| Balanced | 3 | Recommended default |
| Thorough | 4 | Difficult or ambiguous editions |
| Custom | Configurable | Manual control of every optimization setting |

The presets also vary front-matter evidence size, search context, reasoning effort, and output cap.

## Ways to reduce cost

- Use Economy for books with strong identifiers.
- Research only the fields you need.
- Keep the session cache enabled and use **Research fresh** only when necessary.
- Avoid repeatedly validating custom prompts; validation and repair use billable model calls.
- Use batches deliberately and inspect the preflight estimate.

Automated tests mock OpenAI calls and do not incur API charges.
