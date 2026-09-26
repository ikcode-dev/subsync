# 0005: Write a subtitle file for manual upload; no YouTube API upload

- Status: accepted
- Date: 2026-09-25

## Context

SubSync's output ends up in YouTube Studio. Uploading captions automatically would need the YouTube Data API, which brings Google Cloud project setup, OAuth consent and API quota. Igor publishes as a solo creator, one video at a time, and already opens Studio for each upload.

## Options

1. **Upload through the YouTube API.** One step less per video; requires Google Cloud, OAuth and quota management.
2. **Write a subtitle file and upload it by hand.** The CLI writes `.srt` (or `.vtt`); Igor uploads it in Studio.

## Decision

Option 2 (discovery decision D3, [discovery index](../docs/product-design/subsync-v1/index.md#decisions-and-assumptions)). SubSync writes a subtitle file (next to a local video, in the current folder for a URL, or where `-o` says) and ends its summary with a one-line hint for the Studio upload path. It never talks to the YouTube API; the only YouTube network access is downloading audio for URL input.

## Consequences

- No credentials, OAuth flow or quota to manage; the tool stays a local command.
- One manual step per video remains. Studio's acceptance of the file format is checked by hand once (A3).
- Revisit if manual upload becomes the bottleneck; an upload feature would supersede this record.
