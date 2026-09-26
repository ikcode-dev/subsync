"""Audio transcription using OpenAI Whisper.

This module loads a Whisper model and transcribes audio files,
returning word-level timestamps for subtitle generation.

Loading and transcribing are separate steps (``is_model_cached``,
``load_model``, ``transcribe_with_model``) so a caller can show a one-time
download notice and distinct stage lines. ``transcribe_audio`` remains as a
convenience wrapper composed of the two, used until ``process_video()`` is
retired.
"""

import contextlib
import logging
import os
import threading
import warnings
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import URLError

import whisper

from subsync.errors import (
    ModelDownloadError,
    ModelMemoryError,
    TranscriptionError,
    reason_text,
)
from subsync.models import (
    TranscriptionConfig,
    TranscriptionResult,
    TranscriptionSegment,
    Word,
)

logger = logging.getLogger(__name__)

# Exception types that indicate a failed (or interrupted) network fetch of
# model weights, regardless of what is_model_cached() reported. URLError
# (and its subclass HTTPError), ConnectionError and TimeoutError are all
# OSError subclasses, but deliberately named individually rather than as a
# blanket `OSError` check: a cached model can fail to load for an OSError
# reason that has nothing to do with the network (e.g. a permission error
# on the weight file), and that must stay a generic load failure, not a
# download error.
_DOWNLOAD_EXCEPTION_TYPES = (
    URLError,
    HTTPException,
    ConnectionError,
    TimeoutError,
)

# Whisper caches weights under the basename of each model's download URL
# (see ``whisper._MODELS`` in openai-whisper 20250625). This mapping is kept
# local rather than read off the ``whisper`` module so that ``is_model_cached``
# behaves correctly even when ``whisper`` is replaced with a stand-in, and so
# it never needs the network or a heavy import to answer a cache question.
_MODEL_CACHE_FILENAMES: dict[str, str] = {
    "tiny.en": "tiny.en.pt",
    "tiny": "tiny.pt",
    "base.en": "base.en.pt",
    "base": "base.pt",
    "small.en": "small.en.pt",
    "small": "small.pt",
    "medium.en": "medium.en.pt",
    "medium": "medium.pt",
    "large-v1": "large-v1.pt",
    "large-v2": "large-v2.pt",
    "large-v3": "large-v3.pt",
    "large": "large-v3.pt",
    "large-v3-turbo": "large-v3-turbo.pt",
    "turbo": "large-v3-turbo.pt",
}


@dataclass
class LoadedModel:
    """A Whisper model ready to transcribe.

    Attributes:
        name: The requested model name (e.g. "turbo").
        device: Uppercase device label for display ("CPU" or "CUDA").
        engine: The underlying Whisper model instance.
    """

    name: str
    device: str
    engine: Any


class _DebugLogStream:
    """Write-only stream that forwards writes to a logger at debug level.

    Used to redirect Whisper's tqdm download bar (which writes straight to
    ``sys.stderr``) into ``logging`` instead of the terminal.
    """

    def __init__(self, target_logger: logging.Logger) -> None:
        """Create the stream.

        Args:
            target_logger: Logger to forward non-blank writes to.
        """
        self._logger = target_logger
        self._local = threading.local()

    def write(self, text: str) -> int:
        """Log a non-blank write at debug level.

        Guarded against re-entrancy: a debug handler can resolve
        ``sys.stderr`` fresh at emit time (for example rich's
        ``RichHandler`` backed by ``Console(stderr=True)``), which, while
        this stream is in place, writes straight back into this same
        ``write()`` call. Logging that write would recurse through the
        logging machinery indefinitely, so a re-entrant write on the same
        thread is dropped instead of logged or recursed into again --
        writing it to the real terminal instead would leak exactly the
        noise this stream exists to suppress.

        Args:
            text: Text passed to the stream by the writer.

        Returns:
            The number of characters "written" (all of them).
        """
        if getattr(self._local, "active", False):
            return len(text)

        stripped = text.strip()
        if stripped:
            self._local.active = True
            try:
                self._logger.debug("whisper: %s", stripped)
            finally:
                self._local.active = False
        return len(text)

    def flush(self) -> None:
        """No-op; nothing is buffered."""
        return None

    def isatty(self) -> bool:
        """Report as a non-interactive stream."""
        return False


@contextlib.contextmanager
def _quiet_whisper_output() -> Iterator[None]:
    """Suppress Whisper's stderr progress bar and warnings for one call.

    Whisper's download bar is redirected to debug logging and its
    ``warnings.warn`` calls (e.g. "FP16 is not supported on CPU") are
    captured and logged at debug level instead of being printed. Both are
    restored to normal behavior as soon as the wrapped call returns, so the
    rest of the process is unaffected.
    """
    stream = _DebugLogStream(logger)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with contextlib.redirect_stderr(stream):
            try:
                yield
            finally:
                for warning in captured:
                    logger.debug("%s: %s", warning.category.__name__, warning.message)


def _is_out_of_memory(exc: Exception) -> bool:
    """Check whether an exception indicates the process ran out of memory.

    Args:
        exc: The exception raised by Whisper or torch.

    Returns:
        True for a ``MemoryError``, or a ``RuntimeError`` mentioning "out of
        memory" (this covers torch's CUDA OOM errors).
    """
    if isinstance(exc, MemoryError):
        return True
    return isinstance(exc, RuntimeError) and "out of memory" in str(exc).lower()


def _is_download_error(exc: Exception) -> bool:
    """Check whether an exception looks like a failed model download.

    This covers network/HTTP failures, which can happen even when
    ``is_model_cached`` reported the model as cached: Whisper streams
    straight into the target file, so an interrupted first download can
    leave a partial file behind that a later run finds and treats as
    cached, only to re-download after a checksum mismatch. It also covers
    Whisper's own SHA256 checksum-mismatch ``RuntimeError`` raised after
    such a re-download attempt.

    Args:
        exc: The exception raised while loading the model.

    Returns:
        True if the failure should be reported as a download failure
        regardless of the cache pre-check.
    """
    if isinstance(exc, _DOWNLOAD_EXCEPTION_TYPES):
        return True
    return isinstance(exc, RuntimeError) and "checksum" in str(exc).lower()


def _out_of_memory(model_name: str) -> ModelMemoryError:
    """The F20 error for running out of memory with ``model_name``."""
    return ModelMemoryError(
        f"Ran out of memory with model '{model_name}'.",
        hint="Try a smaller one: -m small",
    )


def _resolve_device(device: str) -> str:
    """Resolve the compute device for Whisper.

    Args:
        device: Device specification ("auto", "cuda", or "cpu").

    Returns:
        Resolved device string ("cuda" or "cpu").
    """
    if device == "auto":
        try:
            import torch

            if torch.cuda.is_available():
                logger.debug("CUDA available, using GPU")
                return "cuda"
        except ImportError:
            pass
        logger.debug("CUDA not available, falling back to CPU")
        return "cpu"

    return device


def _whisper_cache_dir() -> Path:
    """Return Whisper's weight cache directory.

    Mirrors Whisper's own default: ``$XDG_CACHE_HOME/whisper`` when set,
    else ``~/.cache/whisper``.

    Returns:
        Path to the directory Whisper downloads model weights into.
    """
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "whisper"


def is_model_cached(model_name: str) -> bool:
    """Check whether a Whisper model's weights are already on disk.

    Args:
        model_name: Whisper model name (e.g. "turbo", "small").

    Returns:
        True if the cached weight file exists. False if it does not, or if
        ``model_name`` is not one of the known catalog names (such as a
        local checkpoint path), since that is never cached under Whisper's
        cache directory.

    Note:
        This only checks that a file exists at the expected path. Whisper
        streams a download straight into that path, so ``load_model``
        removes the file again when a first download fails or is cancelled;
        a file left by other means is re-downloaded by Whisper after a
        checksum mismatch, which ``load_model`` reports as a download error.
    """
    path = _model_cache_path(model_name)
    return path is not None and path.is_file()


def _model_cache_path(model_name: str) -> Path | None:
    """Where Whisper keeps ``model_name``'s weights, or None if not a catalog name."""
    filename = _MODEL_CACHE_FILENAMES.get(model_name)
    return None if filename is None else _whisper_cache_dir() / filename


def load_model(config: TranscriptionConfig) -> LoadedModel:
    """Load a Whisper model, ready to transcribe.

    Args:
        config: Transcription configuration naming the model and device.

    Returns:
        The loaded model, its resolved device label, and the engine handle.

    Raises:
        ModelDownloadError: Downloading the model failed (network, HTTP,
            or checksum) -- either because it was not cached, or because a
            checksum mismatch triggered a re-download that then failed.
        ModelMemoryError: Loading the model ran out of memory.
        TranscriptionError: Any other load failure.
    """
    device = _resolve_device(config.device)
    cached = is_model_cached(config.model_name)
    logger.debug(
        "Loading Whisper model=%s, device=%s, cached=%s",
        config.model_name,
        device,
        cached,
    )

    with _quiet_whisper_output():
        try:
            try:
                engine = whisper.load_model(config.model_name, device=device)
            except BaseException:
                if not cached:
                    _discard_partial_download(config.model_name)
                raise
        except Exception as exc:
            if _is_out_of_memory(exc):
                raise _out_of_memory(config.model_name) from exc
            if not cached or _is_download_error(exc):
                raise ModelDownloadError(
                    f"Couldn't download model '{config.model_name}': "
                    f"{reason_text(exc)}.",
                    hint="An internet connection is needed once per model.",
                ) from exc
            raise TranscriptionError(
                f"Couldn't load model '{config.model_name}': {reason_text(exc)}.",
                hint="Re-run with -v for details.",
            ) from exc

    return LoadedModel(name=config.model_name, device=device.upper(), engine=engine)


def _discard_partial_download(model_name: str) -> None:
    """Remove the weight file a failed or cancelled first download left.

    Whisper writes the download straight to the cache path, so without this
    an interrupted first run would leave a partial file that the next run
    takes for a cached model, skipping the one-time download notice (R7).
    Only called when the file did not exist before this load.

    Whisper verifies a finished download before loading it, so a load can
    also fail (out of memory, Ctrl+C) after a complete, valid file is on
    disk. Checkpoints are zip archives, which end with a directory record
    that a truncated download lacks, so only a file that is not a complete
    archive is removed. The check reads only the end of the file, keeping
    Ctrl+C fast.
    """
    path = _model_cache_path(model_name)
    if path is None or not path.is_file():
        return
    try:
        if zipfile.is_zipfile(path):
            logger.debug("Kept complete model download %s", path)
            return
        path.unlink()
        logger.debug("Removed partial model download %s", path)
    except OSError as exc:
        # Never let cleanup replace the error (or Ctrl+C) being handled.
        logger.debug("Couldn't remove partial model download %s: %s", path, exc)


def _map_segments(raw_segments: list[dict]) -> list[TranscriptionSegment]:
    """Map Whisper segment dicts to TranscriptionSegment models.

    Args:
        raw_segments: List of segment dicts from Whisper output.

    Returns:
        List of TranscriptionSegment dataclasses.
    """
    segments: list[TranscriptionSegment] = []

    for seg in raw_segments:
        words: list[Word] = []
        for w in seg.get("words", []):
            words.append(
                Word(
                    word=w.get("word", ""),
                    start=float(w.get("start", 0.0)),
                    end=float(w.get("end", 0.0)),
                )
            )

        segments.append(
            TranscriptionSegment(
                id=int(seg.get("id", 0)),
                start=float(seg.get("start", 0.0)),
                end=float(seg.get("end", 0.0)),
                text=seg.get("text", ""),
                words=words,
            )
        )

    return segments


def transcribe_with_model(
    model: LoadedModel,
    audio_path: Path,
    config: TranscriptionConfig,
    progress_callback: Callable[[float], None] | None = None,
) -> TranscriptionResult:
    """Transcribe an audio file with an already-loaded Whisper model.

    Args:
        model: A model returned by ``load_model()``.
        audio_path: Path to the audio file (WAV preferred).
        config: Transcription configuration (language, word timestamps).
        progress_callback: Optional callback receiving progress as 0.0-1.0.

    Returns:
        TranscriptionResult with segments and word-level timestamps.

    Raises:
        ModelMemoryError: Transcription ran out of memory.
        TranscriptionError: Any other transcription failure.
    """
    logger.debug(
        "Transcribing %s with model=%s, device=%s, language=%s",
        audio_path,
        model.name,
        model.device,
        config.language,
    )

    if progress_callback is not None:
        progress_callback(0.0)

    with _quiet_whisper_output():
        try:
            result = model.engine.transcribe(
                str(audio_path),
                language=config.language,
                word_timestamps=config.word_timestamps,
            )
        except Exception as exc:
            if _is_out_of_memory(exc):
                raise _out_of_memory(model.name) from exc
            raise TranscriptionError(
                f"Transcription failed: {reason_text(exc)}.",
                hint="Re-run with -v for details.",
            ) from exc

    if progress_callback is not None:
        progress_callback(1.0)

    raw_segments = result.get("segments", [])
    segments = _map_segments(raw_segments)

    # Compute duration from last segment or default to 0
    duration = 0.0
    if segments:
        duration = segments[-1].end

    language = result.get("language", config.language or "unknown")

    transcription = TranscriptionResult(
        language=language,
        duration=duration,
        segments=segments,
    )

    logger.debug(
        "Transcription complete: language=%s, duration=%.1fs, segments=%d",
        transcription.language,
        transcription.duration,
        len(transcription.segments),
    )
    return transcription


def transcribe_audio(
    audio_path: Path,
    config: TranscriptionConfig | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> TranscriptionResult:
    """Transcribe an audio file using OpenAI Whisper.

    Convenience wrapper composed of ``load_model`` and
    ``transcribe_with_model``; kept for ``process_video()`` until it is
    retired.

    Args:
        audio_path: Path to the audio file (WAV preferred).
        config: Transcription configuration. Uses defaults if None.
        progress_callback: Optional callback receiving progress as 0.0-1.0.

    Returns:
        TranscriptionResult with segments and word-level timestamps.

    Raises:
        ModelDownloadError: The model is not cached and downloading it
            failed.
        ModelMemoryError: Loading or transcribing ran out of memory.
        TranscriptionError: Any other load or transcription failure.
    """
    if config is None:
        config = TranscriptionConfig()

    model = load_model(config)
    return transcribe_with_model(
        model, audio_path, config, progress_callback=progress_callback
    )
