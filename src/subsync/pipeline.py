"""Pipeline orchestration for the SubSync processing flow.

This module coordinates the full URL → transcription pipeline:
parse URL, get metadata, download audio, transcribe, and clean up.
"""

import logging
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from subsync.audio_extractor import download_audio, get_video_metadata
from subsync.errors import SubSyncError
from subsync.models import TranscriptionConfig, TranscriptionResult, VideoMetadata
from subsync.progress import ProgressMapper
from subsync.transcriber import transcribe_audio
from subsync.url_handler import parse_youtube_url

logger = logging.getLogger(__name__)


@contextmanager
def pipeline_temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for pipeline intermediary files.

    Yields a Path to a temporary directory prefixed with ``subsync_``.
    The directory and all its contents are removed on exit, whether
    the context exits normally or via an exception.

    Yields:
        Path to the temporary directory.
    """
    with tempfile.TemporaryDirectory(prefix="subsync_") as tmpdir:
        path = Path(tmpdir)
        logger.debug("Created temp directory: %s", path)
        try:
            yield path
        finally:
            logger.debug("Cleaning up temp directory: %s", path)


def process_video(
    url: str,
    transcription_config: TranscriptionConfig | None = None,
    progress_callback: Callable[[float, str], None] | None = None,
) -> tuple[VideoMetadata, TranscriptionResult]:
    """Run the full URL-to-transcription pipeline.

    Pipeline stages:
        1. Parse URL → extract video ID (0%)
        2. Get metadata → validate video availability (5%)
        3. Download audio → convert to 16kHz mono WAV (5–50%)
        4. Transcribe → speech-to-text with timestamps (50–100%)
        5. Cleanup → automatic via context manager

    Args:
        url: YouTube video URL.
        transcription_config: Whisper configuration. Uses defaults if None.
        progress_callback: Optional callback ``(progress, stage) -> None``
            where progress is 0.0–1.0 and stage is a human-readable name.

    Returns:
        Tuple of (VideoMetadata, TranscriptionResult).

    Raises:
        URLParseError: If the URL is invalid.
        VideoUnavailableError: If the video cannot be accessed.
        AgeRestrictedError: If the video is age-restricted.
        LiveStreamError: If the video is a live stream.
        TranscriptionError: If transcription fails.
        SubSyncError: For unexpected errors.
    """
    try:
        # Stage 1: Parse URL
        if progress_callback is not None:
            progress_callback(0.0, "Parsing URL")

        video_id = parse_youtube_url(url)
        logger.debug("Parsed video ID: %s", video_id)

        # Stage 2: Get metadata
        if progress_callback is not None:
            progress_callback(0.05, "Getting metadata")

        metadata = get_video_metadata(video_id)
        logger.debug("Got metadata: %s", metadata.title)

        # Stages 3-4: Download and transcribe inside temp directory
        with pipeline_temp_dir() as tmp_dir:
            # Stage 3: Download audio (5–50%)
            dl_mapper = ProgressMapper(
                progress_callback, start=0.05, end=0.50, stage="Downloading audio"
            )
            dl_mapper.update(0.0)

            def _dl_progress(fraction: float) -> None:
                dl_mapper.update(fraction)

            audio_path = download_audio(
                video_id, tmp_dir, progress_callback=_dl_progress
            )
            dl_mapper.complete()

            # Stage 4: Transcribe (50–100%)
            tr_mapper = ProgressMapper(
                progress_callback, start=0.50, end=1.0, stage="Transcribing"
            )
            tr_mapper.update(0.0)

            def _tr_progress(fraction: float) -> None:
                tr_mapper.update(fraction)

            result = transcribe_audio(
                audio_path,
                config=transcription_config,
                progress_callback=_tr_progress,
            )
            tr_mapper.complete()

        return metadata, result

    except SubSyncError:
        # Let SubSync exceptions propagate unchanged
        raise
    except Exception as exc:
        raise SubSyncError(f"Unexpected pipeline error: {exc}") from exc
