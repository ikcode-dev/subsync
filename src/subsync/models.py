"""Data models for SubSync.

This module defines the core data structures used throughout the SubSync application,
ensuring consistent data flow between modules.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path


# =============================================================================
# Core Models
# =============================================================================


@dataclass
class VideoMetadata:
    """Extracted information about a YouTube video.

    Attributes:
        id: YouTube video ID (11 characters).
        title: Video title (sanitized for filename).
        duration: Duration in seconds.
        uploader: Channel name.
        upload_date: Upload date in YYYYMMDD format.
    """

    id: str
    title: str
    duration: float
    uploader: str
    upload_date: str


@dataclass
class Word:
    """Individual word with precise timing from Whisper.

    Attributes:
        word: The word text.
        start: Start time in seconds.
        end: End time in seconds.
    """

    word: str
    start: float
    end: float


@dataclass
class TranscriptionSegment:
    """A segment of transcribed speech.

    Attributes:
        id: Segment index (0-based from Whisper).
        start: Start time in seconds.
        end: End time in seconds.
        text: Transcribed text.
        words: Word-level timestamps (may be empty).
    """

    id: int
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=lambda: [])


@dataclass
class TranscriptionResult:
    """Complete output from the transcription process.

    Attributes:
        language: Detected/specified language code.
        duration: Total audio duration in seconds.
        segments: List of transcription segments.
    """

    language: str
    duration: float
    segments: list[TranscriptionSegment]


@dataclass
class Subtitle:
    """A single subtitle event ready for output.

    Attributes:
        index: Sequential number (1-based for SRT).
        start_time: Start timestamp.
        end_time: End timestamp.
        text: Original text (pre-formatting).
        lines: Formatted lines (1-2 max).
    """

    index: int
    start_time: timedelta
    end_time: timedelta
    text: str
    lines: list[str]

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
        """Characters per second.

        Returns:
            Characters per second, or 0 if duration is zero.
        """
        duration_secs = self.duration_ms / 1000
        return self.char_count / duration_secs if duration_secs > 0 else 0


@dataclass
class SubtitleFile:
    """Container for a complete subtitle file.

    Attributes:
        format: Output format ("srt" or "vtt").
        language: Language code.
        video_id: Source video ID.
        subtitles: Ordered subtitle events.
    """

    format: str
    language: str
    video_id: str
    subtitles: list[Subtitle]


# =============================================================================
# Validation Models
# =============================================================================


@dataclass
class TimingValidation:
    """Result of timing validation for a subtitle.

    Attributes:
        is_valid: Overall validation result.
        duration_ok: Whether duration is within 833ms-7000ms.
        gap_ok: Whether gap from previous is >= 83ms.
        issues: Description of any issues.
    """

    is_valid: bool
    duration_ok: bool
    gap_ok: bool
    issues: list[str] = field(default_factory=lambda: [])


@dataclass
class ComplianceReport:
    """Aggregate compliance status for a subtitle file.

    Attributes:
        total_subtitles: Total number of subtitles.
        timing_issues: Count of subtitles with timing issues.
        cps_warnings: Count of subtitles exceeding CPS limit.
        line_length_issues: Count of lines exceeding 42 chars.
        is_compliant: True if no blocking issues.
        warnings: Non-blocking issues.
        errors: Blocking issues.
    """

    total_subtitles: int
    timing_issues: int
    cps_warnings: int
    line_length_issues: int
    is_compliant: bool
    warnings: list[str] = field(default_factory=lambda: [])
    errors: list[str] = field(default_factory=lambda: [])


# =============================================================================
# Configuration Models
# =============================================================================


@dataclass
class TranscriptionConfig:
    """Configuration for the transcription process.

    Attributes:
        model_name: Whisper model to use.
        language: Language code (None for auto-detect).
        word_timestamps: Whether to include word-level timestamps.
        device: Device to use ("auto", "cuda", "cpu").
    """

    model_name: str = "turbo"
    language: str | None = None
    word_timestamps: bool = True
    device: str = "auto"


@dataclass
class ProcessingConfig:
    """Configuration for subtitle processing.

    Attributes:
        max_chars_per_line: Maximum characters per line.
        max_lines: Maximum number of lines per subtitle.
        min_duration_ms: Minimum subtitle duration in milliseconds.
        max_duration_ms: Maximum subtitle duration in milliseconds.
        min_gap_ms: Minimum gap between subtitles in milliseconds.
        max_cps_adult: Maximum characters per second for adult content.
        max_cps_children: Maximum characters per second for children's content.
        is_children_content: Whether content is for children.
    """

    max_chars_per_line: int = 42
    max_lines: int = 2
    min_duration_ms: int = 833
    max_duration_ms: int = 7000
    min_gap_ms: int = 83
    max_cps_adult: float = 20.0
    max_cps_children: float = 17.0
    is_children_content: bool = False


@dataclass
class OutputConfig:
    """Configuration for output generation.

    Attributes:
        format: Output format ("srt" or "vtt").
        output_path: Output file path (None for auto-generate).
        include_bom: Whether to include UTF-8 BOM.
    """

    format: str = "srt"
    output_path: Path | None = None
    include_bom: bool = False
