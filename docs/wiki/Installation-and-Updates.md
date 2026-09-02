# Installation and updates

## Requirements

- calibre 7 or newer
- One or more books containing an EPUB format
- OpenAI or Anthropic API access, or a running Ollama/LM Studio model server
- Hosted search where supported, or a separately running SearXNG service
- Internet access while researching metadata

## Install

1. Download `BiblioSleuth-AI.zip` from the [latest release](https://github.com/terrytrent/calibre-bibliosleuth-ai/releases/latest).
2. In calibre, open **Preferences → Plugins → Load plugin from file**.
3. Select the ZIP and accept calibre's third-party plugin warning.
4. Restart calibre when prompted.
5. If the action is not visible, open **Preferences → Toolbars & menus** and add **BiblioSleuth AI** to the desired toolbar or context menu.

Do not extract the plugin ZIP before installing it.

## Update

Install the newer ZIP over the existing plugin and restart calibre. Your accepted settings are retained unless a release note explicitly says otherwise.

## Uninstall

Open **Preferences → Plugins**, select BiblioSleuth AI, choose **Remove plugin**, and restart calibre. If desired, delete the stored API key first from BiblioSleuth AI's configuration page.
