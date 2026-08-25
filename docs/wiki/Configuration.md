# Configuration

Open the arrow beside the BiblioSleuth AI toolbar icon and choose **Configure BiblioSleuth AI**.

## General

- **Replace API key:** the field is intentionally blank when a key is already stored. Type a new key to replace it; leaving it blank preserves the existing key.
- **Remember securely:** stores the key in the operating-system credential vault. Disable this for session-only storage.
- **Delete Stored API Key:** deliberately removes the saved credential.
- **Model:** choose a compatible model from the validated dropdown.
- **Refresh model choices:** requests the current compatible model list. Successful results are cached for seven days.
- **Timeout:** maximum duration allowed for an API request.

`OPENAI_API_KEY`, when set in calibre's environment, takes priority over a stored key.

## Optimization

Choose Economy, Balanced, Thorough, or Custom. Balanced is the default. Custom exposes front-matter evidence limits, web-search context, reasoning effort, output cap, and maximum evidence URLs.

## System prompt

An empty override uses the bundled prompt. Use **View Default**, **Preview Effective Prompt**, **Validate Prompt**, **Copy Default**, and **Restore Default** to manage an override safely. Custom prompts cannot be saved until validation succeeds.

## Privacy and security

This tab controls optional local statistics, diagnostic behavior, and related privacy settings. See [Privacy and security](Privacy-and-Security.md) before enabling verbose diagnostics.
