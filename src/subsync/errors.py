"""Custom exceptions for SubSync."""


class SubSyncError(Exception):
    """Base exception for all SubSync errors.

    All SubSync-specific exceptions inherit from this class,
    enabling catch-all handling when needed.
    """

    pass


class URLParseError(SubSyncError):
    """Invalid or unsupported YouTube URL.

    Raised when:
    - URL is not from youtube.com or youtu.be domain
    - URL does not contain a valid video ID
    - Video ID format is invalid (not 11 characters, invalid chars)
    """

    pass


class VideoUnavailableError(SubSyncError):
    """Video is not accessible.

    Raised when:
    - Video is private
    - Video has been deleted
    - Video is region-locked
    - Video requires purchase
    """

    pass


class AgeRestrictedError(SubSyncError):
    """Video requires age verification.

    Raised when video is age-restricted and no cookies are provided
    for authentication.
    """

    pass


class LiveStreamError(SubSyncError):
    """Live streams are not supported.

    Raised when the URL points to an active live stream rather than
    a completed video.
    """

    pass


class TranscriptionError(SubSyncError):
    """Error during audio transcription.

    Raised when:
    - Whisper model fails to load
    - Audio file is corrupted or unreadable
    - Transcription process fails
    """

    pass
