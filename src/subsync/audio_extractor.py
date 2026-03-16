"""Audio extraction from YouTube videos using yt-dlp.

This module handles video metadata extraction and audio downloading,
converting to Whisper-optimal format (16kHz mono WAV).
"""

import logging
from collections.abc import Callable
from pathlib import Path

import yt_dlp

from subsync.errors import AgeRestrictedError, LiveStreamError, VideoUnavailableError
from subsync.models import VideoMetadata

logger = logging.getLogger(__name__)


def _classify_download_error(
    error_message: str,
) -> type[VideoUnavailableError | AgeRestrictedError]:
    """Classify a yt-dlp DownloadError into a SubSync exception type.

    Args:
        error_message: The error message from yt-dlp.

    Returns:
        The appropriate SubSync exception class.
    """
    msg_lower = error_message.lower()

    age_keywords = [
        "age-restricted",
        "age restricted",
        "sign in to confirm your age",
        "age verification",
    ]
    if any(keyword in msg_lower for keyword in age_keywords):
        return AgeRestrictedError

    return VideoUnavailableError


def get_video_metadata(video_id: str) -> VideoMetadata:
    """Extract video metadata from YouTube without downloading.

    Args:
        video_id: YouTube video ID (11 characters).

    Returns:
        VideoMetadata with title, duration, uploader, and upload date.

    Raises:
        VideoUnavailableError: If video is unavailable, private, or deleted.
        AgeRestrictedError: If video requires age verification.
        LiveStreamError: If video is an active live stream.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    logger.debug("Extracting metadata for video: %s", video_id)

    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        error_cls = _classify_download_error(str(exc))
        raise error_cls(str(exc)) from exc

    if info is None:
        raise VideoUnavailableError(f"No metadata returned for video: {video_id}")

    # Check for live streams
    if info.get("is_live"):
        raise LiveStreamError(
            f"Video {video_id} is a live stream. "
            "Live streams are not supported — wait for the stream to end."
        )

    # Map fields with fallbacks
    uploader = info.get("uploader") or info.get("channel") or "Unknown"
    upload_date = info.get("upload_date") or ""

    metadata = VideoMetadata(
        id=info.get("id", video_id),
        title=(info.get("title") or "").strip(),
        duration=float(info.get("duration") or 0.0),
        uploader=uploader,
        upload_date=upload_date,
    )

    logger.debug("Metadata extracted: %s (%s)", metadata.title, metadata.duration)
    return metadata


def download_audio(
    video_id: str,
    output_dir: Path,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    """Download and convert audio from a YouTube video to 16kHz mono WAV.

    Args:
        video_id: YouTube video ID (11 characters).
        output_dir: Directory to save the WAV file.
        progress_callback: Optional callback receiving progress as 0.0–1.0.

    Returns:
        Path to the downloaded WAV file.

    Raises:
        VideoUnavailableError: If download fails.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = str(output_dir / f"{video_id}.%(ext)s")
    logger.debug("Downloading audio for video: %s to %s", video_id, output_dir)

    def _progress_hook(d: dict) -> None:
        if progress_callback is None:
            return

        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                progress_callback(min(downloaded / total, 1.0))
        elif d.get("status") == "finished":
            progress_callback(1.0)

    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
        "postprocessor_args": ["-ar", "16000", "-ac", "1"],
        "progress_hooks": [_progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        raise VideoUnavailableError(str(exc)) from exc

    wav_path = output_dir / f"{video_id}.wav"

    if not wav_path.exists():
        raise VideoUnavailableError(
            f"Audio download completed but WAV file not found at {wav_path}"
        )

    logger.debug("Audio downloaded: %s", wav_path)
    return wav_path
