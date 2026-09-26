"""Stage events and the result of ``pipeline.generate()``.

Kept apart from ``pipeline`` (which imports Whisper and yt-dlp) so the CLI
can render events, and later slices can emit them before the heavy import,
without paying for it.
"""

from dataclasses import dataclass, field
from pathlib import Path

from subsync.models import ComplianceReport, MediaSource, Subtitle


@dataclass(frozen=True)
class SourceReady:
    """The source was read; its duration is known (stage 1F.2)."""

    source: MediaSource


@dataclass(frozen=True)
class AudioExtracted:
    """Audio was extracted to a temporary WAV (stage 1F.3)."""

    seconds: float


@dataclass(frozen=True)
class ModelDownloading:
    """The model is not cached, so loading it downloads it first (R7)."""

    model_name: str


@dataclass(frozen=True)
class ModelLoaded:
    """The model is loaded and ready (stage 2)."""

    model_name: str
    device: str
    seconds: float


@dataclass(frozen=True)
class TranscriptionStarted:
    """Transcription has started (stage 3)."""

    audio_duration: float


@dataclass(frozen=True)
class Transcribed:
    """Transcription finished and the language is known (stage 3)."""

    seconds: float
    language: str
    language_detected: bool


@dataclass(frozen=True)
class Formatted:
    """Segments were turned into compliant subtitles (stage 4)."""

    segment_count: int
    subtitle_count: int
    seconds: float


@dataclass(frozen=True)
class Written:
    """The subtitle file was written in one step (stage 5)."""

    path: Path
    seconds: float


type GenerateEvent = (
    SourceReady
    | AudioExtracted
    | ModelDownloading
    | ModelLoaded
    | TranscriptionStarted
    | Transcribed
    | Formatted
    | Written
)
"""A stage event reported by ``generate()`` for the CLI to render."""


@dataclass
class GenerateResult:
    """What ``generate()`` produced.

    Attributes:
        path: Absolute path of the written subtitle file.
        source: The source, with its duration filled in.
        language: Language code used in the file name.
        language_detected: True when the language was auto-detected.
        model_name: Whisper model used.
        device: Device label, e.g. "CPU".
        subtitles: The written subtitles, in order.
        report: The compliance report for those subtitles.
        timings: Seconds spent per stage ("extract", "load", "transcribe",
            "format", "write").
    """

    path: Path
    source: MediaSource
    language: str
    language_detected: bool
    model_name: str
    device: str
    subtitles: list[Subtitle]
    report: ComplianceReport
    timings: dict[str, float] = field(default_factory=lambda: {})
