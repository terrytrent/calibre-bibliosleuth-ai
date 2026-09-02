# Reviewing results

The review window compares current and proposed metadata and shows confidence, rationale, evidence, token usage, search calls, timing, and estimated cost.

Available actions include:

- **Select recommended** or **Select none**
- **Restore AI proposal** after editing
- **Edit proposed value** to correct a known value immediately
- **View all details** for long tags, descriptions, and complete evidence
- **Research fresh** to bypass the session cache
- **Accept all remaining books** for blind bulk approval

Authors are stored as separate calibre authors and displayed with `&` between names. Series and series index are independently visible. Descriptions may contain safe formatting such as paragraphs, bold text, and italics, but edition-verification notes are excluded from the description.

When approved, changes are written atomically per book through calibre's database
API. Title sort and author sort are refreshed automatically. The EPUB is never
rewritten. BiblioSleuth AI keeps up to ten in-memory session undo checkpoints;
choose **Undo Last BiblioSleuth AI Apply** from the toolbar menu to restore the
latest checkpoint. Undo data disappears when calibre exits.
