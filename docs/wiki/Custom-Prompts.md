# Custom prompts

The bundled default prompt covers exact-edition matching, source quality, uncertainty, useful tags, and original formatted descriptions. An empty override always uses that versioned default.

## Validation and repair

When a custom prompt is validated or saved, BiblioSleuth AI:

1. Performs local checks for length and required concepts.
2. Uses a fixed, non-editable reviewer instruction and the canonical schema.
3. Runs a schema-constrained synthetic test.
4. If needed, performs one AI repair cycle and tests the repaired prompt.
5. Shows the repair and change summary for explicit acceptance.

The previous accepted prompt remains active until the replacement passes and is accepted. A schema-version change requires revalidation; a model-family change displays a warning.

## Boundaries

A custom prompt can change research priorities, source guidance, tone, and reconciliation rules. It cannot remove required fields, citations, confidence, or inference labels; enable arbitrary tools; expand EPUB disclosure; or bypass local validation. Specific-field research further restricts the runtime response without modifying the saved prompt.

Prompt review, synthetic testing, and repair are billable API operations.
OpenAI and local providers normally use one review call and one synthetic-test
call. Claude splits the full eight-field synthetic test into two strict calls, so
a successful Claude validation normally uses three model requests total. Repair
and failed-test paths can require additional calls; the confirmation warning is
therefore intentionally provider-neutral rather than quoting a fixed request count.
