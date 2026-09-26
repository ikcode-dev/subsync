"""A stand-in for the Whisper transcriber, for integration tests.

Replaces ``subsync.transcriber``'s ``is_model_cached``, ``load_model`` and
``transcribe_with_model`` at the module boundary, so tests run the real
FFmpeg, processor, output planner and writer without loading a model. It
returns a canned ``TranscriptionResult`` and records its calls.
"""

import copy
from pathlib import Path

import pytest

from subsync import transcriber
from subsync.models import TranscriptionConfig, TranscriptionResult


class StandInTranscriber:
    """Canned transcription with call recording and injectable failures.

    Attributes:
        load_calls: The config of every ``load_model`` call.
        transcribe_calls: ``(audio path, config)`` of every transcription.
        audio_existed: Whether each transcription's audio file existed.
    """

    def __init__(
        self,
        result: TranscriptionResult,
        *,
        cached: bool = True,
        device: str = "CPU",
        load_error: BaseException | None = None,
        transcribe_error: BaseException | None = None,
    ) -> None:
        """Create the stand-in.

        Args:
            result: What every transcription returns. Its language is
                replaced by the configured language when one is set.
            cached: What ``is_model_cached`` answers.
            device: The loaded model's device label.
            load_error: Raised by ``load_model`` when set.
            transcribe_error: Raised by ``transcribe_with_model`` when set.
        """
        self.result = result
        self.cached = cached
        self.device = device
        self.load_error = load_error
        self.transcribe_error = transcribe_error
        self.load_calls: list[TranscriptionConfig] = []
        self.transcribe_calls: list[tuple[Path, TranscriptionConfig]] = []
        self.audio_existed: list[bool] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> "StandInTranscriber":
        """Replace the transcriber's functions for the rest of the test."""
        monkeypatch.setattr(transcriber, "is_model_cached", self.is_model_cached)
        monkeypatch.setattr(transcriber, "load_model", self.load_model)
        monkeypatch.setattr(
            transcriber, "transcribe_with_model", self.transcribe_with_model
        )
        return self

    def is_model_cached(self, model_name: str) -> bool:
        """Answer the configured cache state."""
        return self.cached

    def load_model(self, config: TranscriptionConfig) -> transcriber.LoadedModel:
        """Record the call; raise the configured error or return a model."""
        self.load_calls.append(config)
        if self.load_error is not None:
            raise self.load_error
        return transcriber.LoadedModel(
            name=config.model_name, device=self.device, engine=None
        )

    def transcribe_with_model(
        self,
        model: transcriber.LoadedModel,
        audio_path: Path,
        config: TranscriptionConfig,
        progress_callback: object = None,
    ) -> TranscriptionResult:
        """Record the call; raise the configured error or return the result."""
        self.transcribe_calls.append((audio_path, config))
        self.audio_existed.append(Path(audio_path).is_file())
        if self.transcribe_error is not None:
            raise self.transcribe_error
        result = copy.deepcopy(self.result)
        if config.language is not None:
            result.language = config.language
        return result
