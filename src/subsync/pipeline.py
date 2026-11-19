"""Pipeline orchestration for the SubSync processing flow.

``generate()`` is the single orchestrator (E4): it takes a resolved source
through reading, audio extraction, model loading, transcription, formatting
and the one-step write, reporting each stage as an event for the CLI to
render. S1 builds the local-file branch. ``process_video()`` is the Phase 2
URL → transcription pipeline, kept until S4 folds the URL steps into
``generate()``.

Importing this module imports Whisper and yt-dlp (1–2 s), so the CLI imports
it only after the fast stage 0–1 checks.
"""

import logging
import tempfile
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from subsync import media, transcriber
from subsync.audio_extractor import download_audio, get_video_metadata
from subsync.errors import InputError, NoSpeechError, SubSyncError
from subsync.events import (
    AudioExtracted,
    Formatted,
    GenerateEvent,
    GenerateResult,
    ModelDownloading,
    ModelLoaded,
    SourceReady,
    Transcribed,
    TranscriptionStarted,
    Written,
)
from subsync.models import (
    MediaSource,
    ProcessingConfig,
    TranscriptionConfig,
    TranscriptionResult,
    VideoMetadata,
)
from subsync.output import OutputPlan
from subsync.processor import process_transcription
from subsync.progress import ProgressMapper
from subsync.transcriber import transcribe_audio
from subsync.url_handler import parse_youtube_url
from subsync.writer import RENDERERS, write_output

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


# =============================================================================
# generate(): one orchestrator for every source kind (E4)
# =============================================================================


def generate(
    source: MediaSource,
    transcription_config: TranscriptionConfig,
    processing_config: ProcessingConfig,
    plan: OutputPlan,
    force: bool,
    on_event: Callable[[GenerateEvent], None] | None = None,
) -> GenerateResult:
    """Turn a resolved source into a written subtitle file.

    Runs stages 1F.2 to 5 in fail-fast order: read the media, extract audio
    into a temporary folder, load the model, transcribe, format, then write
    in one step. The caller has already validated the arguments, checked
    FFmpeg, resolved the input and run the output pre-check (stages 0-1).
    Prints nothing; each stage is reported to ``on_event``. The temporary
    folder is removed on every exit path, including ``KeyboardInterrupt``.

    Args:
        source: The resolved input. S1 supports local files only.
        transcription_config: Model, language (None to detect) and device.
        processing_config: Compliance limits for the subtitle processor.
        plan: The output plan from the pre-check.
        force: Whether an existing output file may be replaced.
        on_event: Receives one event per stage.

    Returns:
        The written path, language, model, subtitles, report and timings.

    Raises:
        InputError: The source kind or format is not supported yet.
        MediaError: The file has no audio or cannot be read (F9).
        ModelDownloadError, ModelMemoryError, TranscriptionError: The model
            could not be loaded or transcription failed (F19-F21).
        NoSpeechError: Transcription produced no subtitles (F22).
        OutputError, OutputExistsError: The write failed (F11, F23).
    """
    if source.kind != "file" or source.path is None:
        raise InputError("YouTube links aren't supported yet.")
    render = RENDERERS.get(plan.fmt)
    if render is None:
        raise InputError(f"Unsupported format '{plan.fmt}'.")

    def emit(event: GenerateEvent) -> None:
        """Report one stage event to the caller, if it asked for events."""
        if on_event is not None:
            on_event(event)

    timings: dict[str, float] = {}

    duration = media.probe_media(source.path)
    source = replace(source, duration=duration)
    emit(SourceReady(source))

    with pipeline_temp_dir() as tmp_dir:
        started = time.monotonic()
        audio_path = media.extract_audio(source.path, tmp_dir)
        timings["extract"] = time.monotonic() - started
        emit(AudioExtracted(timings["extract"]))

        if not transcriber.is_model_cached(transcription_config.model_name):
            emit(ModelDownloading(transcription_config.model_name))
        started = time.monotonic()
        model = transcriber.load_model(transcription_config)
        timings["load"] = time.monotonic() - started
        emit(ModelLoaded(model.name, model.device, timings["load"]))

        emit(TranscriptionStarted(duration))
        started = time.monotonic()
        transcription = transcriber.transcribe_with_model(
            model, audio_path, transcription_config
        )
        timings["transcribe"] = time.monotonic() - started
        language = transcription_config.language or transcription.language
        language_detected = transcription_config.language is None
        emit(Transcribed(timings["transcribe"], language, language_detected))

    started = time.monotonic()
    subtitles, report = process_transcription(transcription, processing_config)
    timings["format"] = time.monotonic() - started
    if not subtitles:
        raise NoSpeechError(
            f"No speech found in {source.display_name}, so nothing was written.",
            hint="If the language was misdetected, set it with -l en.",
        )
    emit(Formatted(len(transcription.segments), len(subtitles), timings["format"]))

    started = time.monotonic()
    path = plan.path_for(language)
    write_output(render(subtitles), path, force)
    timings["write"] = time.monotonic() - started
    emit(Written(path, timings["write"]))

    return GenerateResult(
        path=path,
        source=source,
        language=language,
        language_detected=language_detected,
        model_name=model.name,
        device=model.device,
        subtitles=subtitles,
        report=report,
        timings=timings,
    )
