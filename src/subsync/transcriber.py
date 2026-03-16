"""Audio transcription using OpenAI Whisper.

This module loads a Whisper model and transcribes audio files,
returning word-level timestamps for subtitle generation.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import whisper

from subsync.errors import TranscriptionError
from subsync.models import (
    TranscriptionConfig,
    TranscriptionResult,
    TranscriptionSegment,
    Word,
)

logger = logging.getLogger(__name__)


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


def transcribe_audio(
    audio_path: Path,
    config: TranscriptionConfig | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> TranscriptionResult:
    """Transcribe an audio file using OpenAI Whisper.

    Args:
        audio_path: Path to the audio file (WAV preferred).
        config: Transcription configuration. Uses defaults if None.
        progress_callback: Optional callback receiving progress as 0.0–1.0.

    Returns:
        TranscriptionResult with segments and word-level timestamps.

    Raises:
        TranscriptionError: If model loading or transcription fails.
    """
    if config is None:
        config = TranscriptionConfig()

    device = _resolve_device(config.device)
    logger.debug(
        "Transcribing %s with model=%s, device=%s, language=%s",
        audio_path,
        config.model_name,
        device,
        config.language,
    )

    # Load model
    try:
        model = whisper.load_model(config.model_name, device=device)
    except Exception as exc:
        raise TranscriptionError(
            f"Failed to load Whisper model '{config.model_name}': {exc}"
        ) from exc

    # Signal start of transcription
    if progress_callback is not None:
        progress_callback(0.0)

    # Transcribe
    try:
        result = model.transcribe(
            str(audio_path),
            language=config.language,
            word_timestamps=config.word_timestamps,
        )
    except RuntimeError as exc:
        error_msg = str(exc)
        if "out of memory" in error_msg.lower() or "CUDA" in error_msg:
            logger.warning(
                "GPU out of memory during transcription. "
                "Consider using a smaller model (e.g., 'base' or 'small') "
                "or setting device='cpu'."
            )
            raise TranscriptionError(
                f"GPU out of memory: {exc}. Try a smaller model or use device='cpu'."
            ) from exc
        raise TranscriptionError(f"Transcription failed: {exc}") from exc
    except Exception as exc:
        raise TranscriptionError(f"Transcription failed: {exc}") from exc

    # Signal completion
    if progress_callback is not None:
        progress_callback(1.0)

    # Map results
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
