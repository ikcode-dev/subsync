# YouTube Subtitle Compatibility - Context

## Overview

This document captures YouTube's subtitle upload requirements and format specifications for SubSync output files.

**Source**: [YouTube Help - Add subtitles & captions](https://support.google.com/youtube/answer/2734796)

**Revised 2026-09-25 for SubSync v1**: adds `/shorts/` and `m.youtube.com` URL patterns and the unsupported link kinds, fixes the encoding to UTF-8 without BOM with LF line endings, records the file naming for both input routes, and the private-video route (export the file, use local-file input). Sources: [product brief](../../docs/product-design/subsync-v1/product-brief.md) R2, R14, R17, R21 and the [phase 4 plan](../plan/phase-4-cli-output.md).

---

## Supported Upload Formats

| Format | Extension | Recommended | Notes |
|--------|-----------|-------------|-------|
| **SubRip** | .srt | ✅ Primary | Universal compatibility |
| **WebVTT** | .vtt | ✅ Alternative | HTML5 native |
| SubViewer | .sbv, .sub | ❌ | Legacy format |
| MPsub | .mpsub | ❌ | Limited support |
| LRC | .lrc | ❌ | Audio lyrics format |
| SAMI | .sami | ❌ | Microsoft legacy |
| TTML | .ttml, .dfxp | ❌ | Advanced, complex |
| SCC | .scc | ❌ | Broadcast standard |

---

## SRT Format Specification

### Structure

```
[SEQUENCE_NUMBER]
[START_TIME] --> [END_TIME]
[SUBTITLE_TEXT]

[BLANK_LINE]
```

### Time Format

`HH:MM:SS,mmm` where:
- **HH**: Hours (00-99)
- **MM**: Minutes (00-59)
- **SS**: Seconds (00-59)
- **mmm**: Milliseconds (000-999)

**Important**: Uses comma (,) as decimal separator, not period.

### Example

```
1
00:00:00,000 --> 00:00:02,500
Hello everyone and welcome
to today's video.

2
00:00:02,600 --> 00:00:05,000
Today we're going to discuss
something very important.
```

### Rules

1. Sequence numbers start at 1, increment by 1
2. Blank line required between subtitle events
3. Maximum 2 lines per subtitle
4. UTF-8 encoding required; SubSync writes it **without a BOM** (A3: YouTube Studio accepts it)
5. No styling tags in basic SRT (YouTube strips them)
6. SubSync uses LF line endings and ends the file with a single newline (E9)

---

## VTT Format Specification

### Structure

```
WEBVTT

[START_TIME] --> [END_TIME]
[SUBTITLE_TEXT]

```

### Time Format

`HH:MM:SS.mmm` where:
- Uses period (.) as decimal separator
- Hours are optional for times under 1 hour

### Example

```
WEBVTT

00:00:00.000 --> 00:00:02.500
Hello everyone and welcome
to today's video.

00:00:02.600 --> 00:00:05.000
Today we're going to discuss
something very important.
```

### Features

- Optional cue identifiers
- Supports basic styling (limited on YouTube)
- Position/alignment metadata (often ignored by YouTube)

---

## YouTube Upload Process

1. Go to YouTube Studio
2. Select video → Subtitles
3. Click "Add Language" → Select language
4. Click "Add" under Subtitles
5. Choose "Upload file"
6. Select "With timing"
7. Upload .srt or .vtt file
8. Review in editor
9. Publish

SubSync's summary ends with this path as a one-line hint (`YouTube Studio → Subtitles → your video → Add → Upload file → With timing`). The wording follows the current Studio UI and is checked at the first manual upload (A3, U7). Upload through the YouTube API is out of scope (D3).

---

## YouTube URL Patterns

SubSync must recognize these URL formats:

| Pattern | Example |
|---------|---------|
| Standard watch | `https://www.youtube.com/watch?v=VIDEO_ID` |
| Short link | `https://youtu.be/VIDEO_ID` |
| Embed | `https://www.youtube.com/embed/VIDEO_ID` |
| Legacy | `https://www.youtube.com/v/VIDEO_ID` |
| With playlist | `https://www.youtube.com/watch?v=VIDEO_ID&list=...` |
| With timestamp | `https://www.youtube.com/watch?v=VIDEO_ID&t=123` |
| Shorts | `https://youtube.com/shorts/VIDEO_ID` |
| Mobile | `https://m.youtube.com/watch?v=VIDEO_ID` |

The Shorts and mobile patterns are new in v1 (R2) and are delivered in slice S4; until then only the first six are parsed.

**Not supported** (stop with "This link isn't a single YouTube video", exit 2, F10):

| Link kind | Example |
|---|---|
| Playlist only | `https://www.youtube.com/playlist?list=...` |
| Channel | `https://www.youtube.com/@handle`, `/channel/...`, `/c/...` |
| YouTube Music | `https://music.youtube.com/watch?v=...` |
| Live URL | `https://www.youtube.com/live/...` (useful later for streams that have ended) |

A URL input is only considered when the input is not an existing local file (R3).

### Video ID Format

- 11 characters
- Alphanumeric plus `-` and `_`
- Case-sensitive

---

## Limitations & Restrictions

### Cannot Process

- Private videos (unless authenticated). SubSync's route for a private draft is to export the rendered file and run it as local-file input; the private-video error says so (R21, F13)
- Age-restricted content (requires cookies, which v1 does not support)
- Live streams (real-time processing not supported)
- Deleted/removed videos
- Region-locked content (from blocked regions)

### YouTube API Considerations

- No API needed for public video metadata extraction
- yt-dlp handles extraction without API keys
- Rate limiting may apply for bulk operations

---

## Implementation Notes

For SubSync:
1. **Primary output**: SRT format for maximum compatibility
2. **Optional output**: VTT as secondary format (`-f vtt`, slice S5)
3. **Filename convention** (R14):
   - Local file input: `<input folder>/<stem>.<lang>.srt`
   - YouTube URL input: `./<sanitized title>.<lang>.srt`
   - `-o <folder>` puts the default name in that folder; `-o <file>` is used as the exact path
4. **Encoding**: UTF-8 without BOM, LF line endings
5. **URL parsing**: Extract video ID, ignore extra parameters
