# Data Models

## Overview

This document defines the conceptual data structures used throughout SubSync. These models describe the domain entities and their relationships, providing a contract for data flow between modules.

**Reference**: [SUBTITLE_GENERATION_ALGORITHM.md](../../docs/SUBTITLE_GENERATION_ALGORITHM.md) Section 7

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
- **char_count**: Total characters across all lines
- **duration_ms**: Duration in milliseconds
- **cps**: Characters per second (char_count / duration)

#### SubtitleFile

Container for a complete subtitle file.

| Field | Type | Description |
|-------|------|-------------|
| format | string | "srt" or "vtt" |
| language | string | Language code |
| video_id | string | Source video ID |
| subtitles | list of Subtitle | Ordered subtitle events |

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
| is_compliant | boolean | No blocking issues |
| warnings | list of string | Non-blocking issues |
| errors | list of string | Blocking issues |

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

### OutputConfig

Settings for output generation.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| format | string | "srt" | Output format: "srt" or "vtt" |
| output_path | path or null | null | Output path (null = auto-generate) |
| include_bom | boolean | false | Include UTF-8 BOM |

---

## Error Categories

SubSync defines a hierarchy of errors for granular handling:

| Error Type | When Raised |
|------------|-------------|
| SubSyncError | Base for all SubSync errors |
| URLParseError | Invalid/unsupported YouTube URL |
| VideoUnavailableError | Video is private, deleted, or region-locked |
| AgeRestrictedError | Video requires age verification |
| LiveStreamError | Live streams not supported |
| TranscriptionError | Audio transcription failures |

---

## Data Flow

| Model | Created By | Consumed By |
|-------|------------|-------------|
| VideoMetadata | URL Handler | Audio Extractor, Writer |
| TranscriptionResult | Transcriber | Subtitle Processor |
| Subtitle | Subtitle Processor | Writer |
| SubtitleFile | Writer | File System |
| ComplianceReport | Subtitle Processor | CLI (display) |

---

## Constraints

1. Video IDs are exactly 11 characters
2. Subtitle indices start at 1 (SRT convention)
3. Timestamps use millisecond precision
4. Text encoding must be UTF-8
5. Lines array has maximum 2 elements
