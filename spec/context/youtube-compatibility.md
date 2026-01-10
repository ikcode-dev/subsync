# YouTube Subtitle Compatibility - Context

## Overview

This document captures YouTube's subtitle upload requirements and format specifications for SubSync output files.

**Source**: [YouTube Help - Add subtitles & captions](https://support.google.com/youtube/answer/2734796)

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
4. UTF-8 encoding required
5. No styling tags in basic SRT (YouTube strips them)

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

### Video ID Format

- 11 characters
- Alphanumeric plus `-` and `_`
- Case-sensitive

---

## Limitations & Restrictions

### Cannot Process

- Private videos (unless authenticated)
- Age-restricted content (requires cookies)
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
2. **Optional output**: VTT as secondary format
3. **Filename convention**: `{video_title}.{language}.srt`
4. **Encoding**: Always UTF-8 with BOM consideration
5. **URL parsing**: Extract video ID, ignore extra parameters
