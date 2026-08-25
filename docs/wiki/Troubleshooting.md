# Troubleshooting

## The toolbar action is missing

Restart calibre after installation. Then open **Preferences → Toolbars & menus**, choose the relevant toolbar, and add **BiblioSleuth AI**. The main icon runs research; its adjacent arrow opens configuration, About, documentation, and field-specific actions.

## An API key is required

Use the offered **Configure API key** action. A stored key is represented by a status message, not by revealing the secret. Type a value only to add or replace the key.

## Research completed but nothing changed

Completion produces proposals, not automatic writes. Open the persistent notification or click the BiblioSleuth AI icon, select the fields to apply, and approve the book. Bulk acceptance is also available.

## A lookup failed

Use the user-visible error details and **Troubleshooting** action. **Retry failed fresh** bypasses the session cache. For support, use **Collect logs**, inspect the sanitized bundle, and attach it to a [GitHub issue](https://github.com/terrytrent/calibre-bibliosleuth-ai/issues).

## The exact edition is uncertain

Check identifiers, format, publisher, and date. Edit known proposals directly, or choose **Research fresh** with the Thorough preset.
