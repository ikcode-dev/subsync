# Data Models - Context

## Overview

This document defines the core data structures used throughout the SubSync application. These models ensure consistent data flow between modules.

**Reference**: [SUBTITLE_GENERATION_ALGORITHM.md](../../docs/SUBTITLE_GENERATION_ALGORITHM.md) Section 7

---

## Core Models

### VideoMetadata

Extracted information about the YouTube video.

```python
@dataclass
class VideoMetadata:
    id: str              # YouTube video ID (11 characters)
    title: str           # Video title (sanitized for filename)
    duration: float      # Duration in seconds
    uploader: str        # Channel name
    upload_date: str     # YYYYMMDD format
```

**Source**: yt-dlp `extract_info()` response

---

### Word

Individual word with precise timing from Whisper.

```python
@dataclass
class Word:
    word: str            # The word text
    start: float         # Start time in seconds
    end: float           # End time in seconds
```

---

### TranscriptionSegment

A segment of transcribed speech.

```python
@dataclass
class TranscriptionSegment:
    id: int              # Segment index (0-based from Whisper)
    start: float         # Start time in seconds
    end: float           # End time in seconds
    text: str            # Transcribed text
    words: list[Word]    # Word-level timestamps (may be empty)
```

---

### TranscriptionResult

Complete output from the transcription process.

```python
@dataclass
class TranscriptionResult:
    language: str                       # Detected/specified language code
    duration: float                     # Total audio duration in seconds
    segments: list[TranscriptionSegment]
```

---

### Subtitle

A single subtitle event ready for output.

```python
@dataclass
class Subtitle:
    index: int               # Sequential number (1-based for SRT)
    start_time: timedelta    # Start timestamp
    end_time: timedelta      # End timestamp
    text: str                # Original text (pre-formatting)
    lines: list[str]         # Formatted lines (1-2 max)

    @property
    def char_count(self) -> int:
        """Total characters across all lines."""
        return sum(len(line) for line in self.lines)

    @property
    def duration_ms(self) -> int:
        """Duration in milliseconds."""
        return int((self.end_time - self.start_time).total_seconds() * 1000)

    @property
    def cps(self) -> float:
        """Characters per second."""
        duration_secs = self.duration_ms / 1000
        return self.char_count / duration_secs if duration_secs > 0 else 0
```

---

### SubtitleFile

Container for a complete subtitle file.

```python
@dataclass
class SubtitleFile:
    format: str                  # "srt" or "vtt"
    language: str                # Language code
    video_id: str                # Source video ID
    subtitles: list[Subtitle]    # Ordered subtitle events
```

---

## Validation Models

### TimingValidation

Result of timing validation for a subtitle.

```python
@dataclass
class TimingValidation:
    is_valid: bool
    duration_ok: bool            # 833ms <= duration <= 7000ms
    gap_ok: bool                 # >= 83ms from previous
    issues: list[str]            # Description of any issues
```

---

### ComplianceReport

Aggregate compliance status for a subtitle file.

```python
@dataclass
class ComplianceReport:
    total_subtitles: int
    timing_issues: int
    cps_warnings: int            # Subtitles exceeding CPS limit
    line_length_issues: int      # Lines exceeding 42 chars
    is_compliant: bool           # No blocking issues
    warnings: list[str]          # Non-blocking issues
    errors: list[str]            # Blocking issues
```

---

## Configuration Models

### TranscriptionConfig

Configuration for the transcription process.

```python
@dataclass
class TranscriptionConfig:
    model_name: str = "turbo"        # Whisper model
    language: str | None = None       # None = auto-detect
    word_timestamps: bool = True
    device: str = "auto"              # "auto", "cuda", "cpu"
```

---

### ProcessingConfig

Configuration for subtitle processing.

```python
@dataclass
class ProcessingConfig:
    max_chars_per_line: int = 42
    max_lines: int = 2
    min_duration_ms: int = 833
    max_duration_ms: int = 7000
    min_gap_ms: int = 83
    max_cps_adult: float = 20.0
    max_cps_children: float = 17.0
    is_children_content: bool = False
```

---

### OutputConfig

Configuration for output generation.

```python
@dataclass
class OutputConfig:
    format: str = "srt"              # "srt" or "vtt"
    output_path: Path | None = None  # None = auto-generate
    include_bom: bool = False        # UTF-8 BOM
```

---

## Error Models

### SubSyncError (Base)

```python
class SubSyncError(Exception):
    """Base exception for SubSync errors."""
    pass
```

### Specific Errors

```python
class VideoUnavailableError(SubSyncError):
    """Video is private, deleted, or region-locked."""
    pass

class AgeRestrictedError(SubSyncError):
    """Video requires age verification."""
    pass

class LiveStreamError(SubSyncError):
    """Live streams are not supported."""
    pass

class TranscriptionError(SubSyncError):
    """Error during audio transcription."""
    pass

class URLParseError(SubSyncError):
    """Invalid or unsupported YouTube URL."""
    pass
```

---

## Module Boundaries

| Model | Created By | Consumed By |
|-------|------------|-------------|
| VideoMetadata | URL Handler | Audio Extractor, Writer |
| TranscriptionResult | Transcriber | Subtitle Processor |
| Subtitle | Subtitle Processor | Writer |
| SubtitleFile | Writer | File System |
| ComplianceReport | Subtitle Processor | CLI (display) |

---

## Implementation Notes

1. Use `@dataclass` for simple data containers
2. Use `typing` for all type hints
3. Consider `pydantic` if validation becomes complex
4. Keep models in a dedicated `models.py` module
5. Models should be immutable where practical
