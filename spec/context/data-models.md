# Data Models

## Overview

This document defines the conceptual data structures used throughout SubSync. These models describe the domain entities and their relationships, providing a contract for data flow between modules.

**Reference**: [SUBTITLE_GENERATION_ALGORITHM.md](../../docs/SUBTITLE_GENERATION_ALGORITHM.md) Section 7

**Revised 2026-09-25 for SubSync v1**: adds `MediaSource` (one model for local files and YouTube URLs, decision E4), `ComplianceFlag`, the P2 meaning of the compliance report, and the full error hierarchy with exit codes. `SubtitleFile` drops its YouTube-only `video_id`. Sources: [product brief](../../docs/product-design/subsync-v1/product-brief.md), [phase 3](../plan/phase-3-netflix-compliance.md) and [phase 4](../plan/phase-4-cli-output.md) plans.

---

## Core Domain Entities

### VideoMetadata

Information extracted from a YouTube video.

| Field | Type | Description |
|-------|------|-------------|
| id | string | YouTube video ID (11 characters) |
| title | string | Video title (sanitized for filename use) |
| duration | float | Duration in seconds |
| uploader | string | Channel name |
| upload_date | string | Format: YYYYMMDD |

**Source**: yt-dlp `extract_info()` response

VideoMetadata stays the raw result of the YouTube metadata fetch. From slice S4 it is mapped into a `MediaSource`; nothing after input resolution depends on it directly.

---

### MediaSource

What is being processed, for both input routes (E4). Created at input resolution (local file) or after the metadata fetch (YouTube URL), before any heavy work.

| Field | Type | Description |
|-------|------|-------------|
| kind | string | `"file"` or `"youtube"` |
| display_name | string | File name (`ep42.mov`) or video title; shown in the source line and summary |
| output_stem | string | File stem (`ep42`) or sanitized title; the first part of the default output name |
| output_dir | path | Default output folder: the input's folder (file) or the current folder (URL) |
| path | path or null | Local file path; null for YouTube |
| duration | float or null | Seconds; null until the file is probed or the video info is fetched |
| video_id | string or null | YouTube video ID (11 characters); null for files |
| channel | string or null | YouTube channel name; null for files |

**Why one model**: local files have no video ID, uploader or upload date. A single source model keeps naming, the pre-check and the summary identical for both routes without fake YouTube fields.

---

### Transcription Entities

#### Word

Individual word with precise timing from Whisper.

| Field | Type | Description |
|-------|------|-------------|
| word | string | The word text |
| start | float | Start time in seconds |
| end | float | End time in seconds |

#### TranscriptionSegment

A segment of transcribed speech.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Segment index (0-based from Whisper) |
| start | float | Start time in seconds |
| end | float | End time in seconds |
| text | string | Transcribed text |
| words | list of Word | Word-level timestamps (may be empty) |

#### TranscriptionResult

Complete output from the transcription process.

| Field | Type | Description |
|-------|------|-------------|
| language | string | Detected/specified language code |
| duration | float | Total audio duration in seconds |
| segments | list of TranscriptionSegment | Ordered segments |

---

### Subtitle Entities

#### Subtitle

A single subtitle event ready for output.

| Field | Type | Description |
|-------|------|-------------|
| index | integer | Sequential number (1-based for SRT) |
| start_time | timedelta | Start timestamp |
| end_time | timedelta | End timestamp |
| text | string | Original text (pre-formatting) |
| lines | list of string | Formatted lines (1-2 max) |

**Computed Properties**:
- **char_count**: Total characters across all lines, including spaces and punctuation, excluding line breaks (E9)
- **duration_ms**: Duration in milliseconds
- **cps**: Characters per second (char_count / duration)

Start and end times are whole milliseconds, so the timing invariants still hold after serialization as `HH:MM:SS,mmm`.

#### SubtitleFile

Container for a complete subtitle file.

| Field | Type | Description |
|-------|------|-------------|
| format | string | "srt" or "vtt" |
| language | string | Language code |
| subtitles | list of Subtitle | Ordered subtitle events |

The former `video_id` field is removed: it only applied to YouTube input, and nothing in the file needs it.

---

## Validation Entities

### TimingValidation

Result of timing validation for a single subtitle.

| Field | Type | Description |
|-------|------|-------------|
| is_valid | boolean | Overall validation result |
| duration_ok | boolean | 833ms ≤ duration ≤ 7000ms |
| gap_ok | boolean | ≥ 83ms from previous subtitle |
| issues | list of string | Description of any issues |

### ComplianceReport

Aggregate compliance status for a subtitle file.

| Field | Type | Description |
|-------|------|-------------|
| total_subtitles | integer | Total subtitle count |
| timing_issues | integer | Count of timing violations |
| cps_warnings | integer | Subtitles exceeding CPS limit |
| line_length_issues | integer | Lines exceeding 42 characters |
| is_compliant | boolean | True exactly when `errors` is empty |
| warnings | list of string | Non-blocking issues |
| errors | list of string | Structural breakage only (P2) |
| flags | list of ComplianceFlag | Subtitles to review, with timestamps |

**Errors vs warnings (P2)**: `errors` covers only structural breakage — an overlap, an out-of-order subtitle, an end at or before its start, or more than 2 lines. The processor must make these impossible, so an error means a bug. Everything else is a warning. A written file always exits 0; errors only change the summary headline. Zero subtitles is not a report error: the caller treats it as "no speech found" (NoSpeechError, exit 4, nothing written).

The counts the full compliance block needs (adjusted automatically, left short, eased by extending) are added in slice S2.

### ComplianceFlag

One subtitle that needs a look in the Studio editor.

| Field | Type | Description |
|-------|------|-------------|
| kind | string | `"short"` (under 833 ms, could not be fixed), `"long_word"` (a word over 42 characters kept whole, R12), `"cps"` (still above 20 CPS after easing, R11, from S2) |
| subtitle_index | integer | The flagged subtitle's number (1-based) |
| start_time | timedelta | Start of the flagged subtitle; shown as `HH:MM:SS` in the summary |
| detail | string | Extra information such as the CPS value; may be empty |

---

## Configuration Entities

### TranscriptionConfig

Settings for the transcription process.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| model_name | string | "turbo" | Whisper model to use |
| language | string or null | null | Language code (null = auto-detect) |
| word_timestamps | boolean | true | Request word-level timing |
| device | string | "auto" | Compute device: "auto", "cuda", "cpu" |

### ProcessingConfig

Settings for subtitle processing (Netflix compliance).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| max_chars_per_line | integer | 42 | Maximum characters per line |
| max_lines | integer | 2 | Maximum lines per subtitle |
| min_duration_ms | integer | 833 | Minimum subtitle duration |
| max_duration_ms | integer | 7000 | Maximum subtitle duration |
| min_gap_ms | integer | 83 | Minimum gap between subtitles |
| max_cps_adult | float | 20.0 | Max CPS for adult content |
| max_cps_children | float | 17.0 | Max CPS for children's content |
| is_children_content | boolean | false | Apply stricter CPS limit |

The children's fields stay in the model but are unused in v1: the children's profile (`--children`, 17 CPS) is out of scope.

### OutputConfig

Settings for output generation.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| format | string | "srt" | Output format: "srt" or "vtt" |
| output_path | path or null | null | Output path (null = auto-generate) |
| include_bom | boolean | false | Include UTF-8 BOM |

---

## Error Categories

SubSync defines a hierarchy of errors for granular handling. Every SubSync error carries a **message** (the headline of the failure, what went wrong) and an optional **hint** (the "what to do next" line). The CLI maps the category to the exit code and renders the ✗ block; wording per failure is in the [UX failure table](../../docs/product-design/subsync-v1/ux-flows.md#states-failures-and-recovery).

| Error Type | Parent | Exit | When Raised | Failure rows |
|------------|--------|------|-------------|---|
| SubSyncError | — | 1 | Base for all SubSync errors; raised directly only for unexpected pipeline failures | F25 |
| InputError | SubSyncError | 2 | Bad input or usage: unknown language or model, `-o`/`-f` mismatch, input is neither a file nor a supported URL, input is a folder | F2–F4, F7, F8 |
| URLParseError | InputError | 2 | Invalid or unsupported YouTube URL, or a link that isn't a single video | F7, F10 |
| MediaError | InputError | 2 | Local file has no audio track or cannot be decoded | F9 |
| DependencyError | SubSyncError | 1 | A required system tool (FFmpeg, ffprobe) is not on PATH | F6 |
| SourceUnavailableError | SubSyncError | 3 | The YouTube source cannot be fetched | F13–F18 |
| VideoUnavailableError | SourceUnavailableError | 3 | Video is private, deleted, or region-locked | F13, F14 |
| AgeRestrictedError | SourceUnavailableError | 3 | Video requires age verification | F15 |
| LiveStreamError | SourceUnavailableError | 3 | Live stream or premiere not finished | F16 |
| TranscriptionError | SubSyncError | 4 | Audio transcription failures | F21 |
| ModelDownloadError | TranscriptionError | 4 | Model weights could not be downloaded | F19 |
| ModelMemoryError | TranscriptionError | 4 | Out of memory while loading or transcribing | F20 |
| NoSpeechError | TranscriptionError | 4 | Transcription produced zero subtitles; nothing is written | F22 |
| OutputError | SubSyncError | 5 | Output folder missing or not writable, or the write failed | F12, F23 |
| OutputExistsError | OutputError | 5 | Output file already exists and `--force` was not given | F11 |

Outside the hierarchy: a keyboard interrupt (Ctrl+C) exits 130 with `Cancelled. Nothing written.` (F24). Any other exception is unexpected and exits 1 (F25). Network and outdated-yt-dlp failures (F17, F18) are classified under SourceUnavailableError in slice S4.

---

## Data Flow

| Model | Created By | Consumed By |
|-------|------------|-------------|
| VideoMetadata | Audio Extractor (metadata fetch) | Mapped into MediaSource (S4) |
| MediaSource | Input resolver (local file) or metadata fetch (YouTube URL) | Output planner, orchestrator (`generate`), summary |
| TranscriptionResult | Transcriber | Subtitle Processor |
| Subtitle | Subtitle Processor | Writer, summary |
| SubtitleFile | Orchestrator | Writer |
| ComplianceReport (with ComplianceFlags) | Subtitle Processor | Orchestrator, CLI summary |

---

## Constraints

1. Video IDs are exactly 11 characters
2. Subtitle indices start at 1 (SRT convention)
3. Timestamps use whole-millisecond precision
4. Text encoding must be UTF-8 without BOM
5. Lines array has maximum 2 elements
6. Subtitle text is never shortened or rewritten; a single word over 42 characters stays whole on its own line (R12)
