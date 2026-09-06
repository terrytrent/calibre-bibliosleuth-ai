# Installation and updates

## Requirements

- calibre 7 or newer
- One or more books containing an EPUB format
- OpenAI or Anthropic API access, or a running Ollama/LM Studio model server
- Hosted search where supported, or a separately running SearXNG service
- Internet access while researching metadata

BiblioSleuth AI does not install or start the external providers. Follow
[Provider and search setup](Provider-and-Search-Setup.md) before the first
lookup; applicable research jobs then perform short automatic availability
checks.

## Install

1. Download `BiblioSleuth-AI.zip` from the [latest release](https://github.com/terrytrent/calibre-bibliosleuth-ai/releases/latest).
2. In calibre, open **Preferences → Plugins → Load plugin from file**.
3. Select the ZIP and accept calibre's third-party plugin warning.
4. Restart calibre when prompted.
5. If the action is not visible, open **Preferences → Toolbars & menus** and add **BiblioSleuth AI** to the desired toolbar or context menu.

Do not extract the plugin ZIP before installing it.

## Update

BiblioSleuth AI checks a small public manifest in the background after its first
normal use in a Calibre session, no more than once every 24 hours. Disable this
under **Configure BiblioSleuth AI → Help**, or choose **Check for Updates…** from
the toolbar menu for an immediate manual check.

When a newer compatible stable version is available, a non-modal notice offers
**View release…**, **Remind me tomorrow**, and **Skip this version**.
The notice includes a concise summary and categorized highlights from that
release. Closing the notice also defers it until tomorrow. Skipping suppresses
notices only for that version; a later release can notify again. The update
remains available from the toolbar menu even when its notice is deferred.
Viewing a release opens its derived GitHub page only after confirmation.
BiblioSleuth AI never downloads or installs an update automatically.

Install the newer ZIP over the existing plugin and restart calibre. Your accepted
settings are retained unless a release note explicitly says otherwise.

The check sends no book, library, provider, credential, model, hardware, or
installation-identifying data. Ordinary automatic-check failures are silent and
wait until the next daily opportunity; a manual check reports a concise error.

## Uninstall

Open **Preferences → Plugins**, select BiblioSleuth AI, choose **Remove plugin**, and restart calibre. If desired, delete the stored API key first from BiblioSleuth AI's configuration page.
