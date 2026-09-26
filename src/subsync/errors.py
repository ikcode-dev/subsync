"""Custom exceptions for SubSync.

Every SubSync error carries a message (the headline of the failure) and an
optional hint (the "what to do next" line). Each category also names the exit
code the CLI maps it to; see the error categories in
``spec/context/data-models.md``.
"""


class SubSyncError(Exception):
    """Base exception for all SubSync errors.

    All SubSync-specific exceptions inherit from this class,
    enabling catch-all handling when needed. Raised directly only for
    unexpected pipeline failures.

    Attributes:
        hint: Optional next-step text shown under the headline.
        exit_code: Process exit code for this error category.
    """

    exit_code: int = 1

    def __init__(self, message: str, hint: str | None = None) -> None:
        """Create the error.

        Args:
            message: Headline saying what went wrong; also ``str(err)``.
            hint: Optional line saying what to do next.
        """
        super().__init__(message)
        self.hint = hint


class InputError(SubSyncError):
    """Bad input or usage (exit 2).

    Raised when:
    - A language code or model name is unknown
    - ``-o`` and ``-f`` name different formats
    - INPUT is neither a file nor a supported URL, or is a folder
    """

    exit_code = 2


class URLParseError(InputError):
    """Invalid or unsupported YouTube URL.

    Raised when:
    - URL is not from youtube.com or youtu.be domain
    - URL does not contain a valid video ID
    - Video ID format is invalid (not 11 characters, invalid chars)
    """


class MediaError(InputError):
    """A local file has no audio track or cannot be decoded."""


class DependencyError(SubSyncError):
    """A required system tool (FFmpeg, ffprobe) is not on PATH (exit 1)."""

    exit_code = 1


class SourceUnavailableError(SubSyncError):
    """The YouTube source cannot be fetched (exit 3)."""

    exit_code = 3


class VideoUnavailableError(SourceUnavailableError):
    """Video is not accessible.

    Raised when:
    - Video is private
    - Video has been deleted
    - Video is region-locked
    - Video requires purchase
    """


class AgeRestrictedError(SourceUnavailableError):
    """Video requires age verification.

    Raised when video is age-restricted and no cookies are provided
    for authentication.
    """


class LiveStreamError(SourceUnavailableError):
    """Live streams are not supported.

    Raised when the URL points to an active live stream rather than
    a completed video.
    """


class TranscriptionError(SubSyncError):
    """Error during audio transcription (exit 4).

    Raised when:
    - Whisper model fails to load
    - Audio file is corrupted or unreadable
    - Transcription process fails
    """

    exit_code = 4


class ModelDownloadError(TranscriptionError):
    """Model weights could not be downloaded."""


class ModelMemoryError(TranscriptionError):
    """Out of memory while loading a model or transcribing."""


class NoSpeechError(TranscriptionError):
    """Transcription produced zero subtitles; nothing is written."""


class OutputError(SubSyncError):
    """Output folder missing or not writable, or the write failed (exit 5)."""

    exit_code = 5


class OutputExistsError(OutputError):
    """Output file already exists and ``--force`` was not given."""

    @classmethod
    def for_file(cls, name: str) -> "OutputExistsError":
        """The F11 error for an existing output file.

        Args:
            name: The existing file's name, e.g. ``ep42.en.srt``.

        Returns:
            The error, with the ``--force`` / ``-o`` hint.
        """
        return cls(
            f"{name} already exists.",
            hint="Re-run with --force to replace it, or choose another path with -o.",
        )


def reason_text(exc: BaseException) -> str:
    """Render an exception as a one-line reason for an error headline.

    Takes the first non-blank line of ``str(exc)`` and drops one trailing
    period, so the caller can end its sentence with its own. Falls back to
    the exception's class name when the message is empty or only a period,
    so a headline never ends in a blank reason.

    Args:
        exc: The exception to describe.

    Returns:
        A non-empty, single-line reason without a trailing period.
    """
    for raw_line in str(exc).splitlines():
        line = raw_line.strip().removesuffix(".").strip()
        if line:
            return line
    return exc.__class__.__name__
