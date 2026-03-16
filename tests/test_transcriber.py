"""Tests for the transcriber module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from subsync.errors import TranscriptionError
from subsync.models import TranscriptionConfig, TranscriptionResult
from subsync.transcriber import _resolve_device, transcribe_audio

# A mock whisper result dict used across multiple tests
MOCK_WHISPER_RESULT = {
    "language": "en",
    "segments": [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.5,
            "text": " Hello world",
            "words": [
                {"word": " Hello", "start": 0.0, "end": 1.2},
                {"word": " world", "start": 1.3, "end": 2.5},
            ],
        },
        {
            "id": 1,
            "start": 3.0,
            "end": 5.0,
            "text": " This is a test",
            "words": [
                {"word": " This", "start": 3.0, "end": 3.3},
                {"word": " is", "start": 3.4, "end": 3.5},
                {"word": " a", "start": 3.6, "end": 3.7},
                {"word": " test", "start": 3.8, "end": 5.0},
            ],
        },
    ],
}


# =============================================================================
# _resolve_device tests
# =============================================================================


class TestResolveDevice:
    """Tests for _resolve_device()."""

    @patch("subsync.transcriber.torch", create=True)
    def test_auto_with_cuda_available(self, mock_torch: MagicMock) -> None:
        """auto + CUDA available → 'cuda'."""
        mock_torch.cuda.is_available.return_value = True

        with patch.dict("sys.modules", {"torch": mock_torch}):
            assert _resolve_device("auto") == "cuda"

    @patch("subsync.transcriber.torch", create=True)
    def test_auto_without_cuda(self, mock_torch: MagicMock) -> None:
        """auto + CUDA not available → 'cpu'."""
        mock_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"torch": mock_torch}):
            assert _resolve_device("auto") == "cpu"

    def test_explicit_cpu(self) -> None:
        """Explicit 'cpu' returns 'cpu'."""
        assert _resolve_device("cpu") == "cpu"

    def test_explicit_cuda(self) -> None:
        """Explicit 'cuda' returns 'cuda'."""
        assert _resolve_device("cuda") == "cuda"


# =============================================================================
# transcribe_audio tests
# =============================================================================


class TestTranscribeAudio:
    """Tests for transcribe_audio()."""

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_successful_transcription(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """Successful transcription returns TranscriptionResult with segments and words."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = MOCK_WHISPER_RESULT
        mock_whisper.load_model.return_value = mock_model

        result = transcribe_audio(Path("/fake/audio.wav"))

        assert isinstance(result, TranscriptionResult)
        assert result.language == "en"
        assert result.duration == 5.0
        assert len(result.segments) == 2
        assert len(result.segments[0].words) == 2
        assert result.segments[0].words[0].word == " Hello"

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_auto_detect_language(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """Language auto-detection populates language from whisper result."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {**MOCK_WHISPER_RESULT, "language": "fr"}
        mock_whisper.load_model.return_value = mock_model

        config = TranscriptionConfig(language=None)
        result = transcribe_audio(Path("/fake/audio.wav"), config=config)

        assert result.language == "fr"
        mock_model.transcribe.assert_called_once()
        call_kwargs = mock_model.transcribe.call_args[1]
        assert call_kwargs["language"] is None

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_explicit_language(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """Explicit language is passed to whisper and returned in result."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {**MOCK_WHISPER_RESULT, "language": "en"}
        mock_whisper.load_model.return_value = mock_model

        config = TranscriptionConfig(language="en")
        result = transcribe_audio(Path("/fake/audio.wav"), config=config)

        assert result.language == "en"
        call_kwargs = mock_model.transcribe.call_args[1]
        assert call_kwargs["language"] == "en"

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_no_word_timestamps(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """Segments without words key have empty words list."""
        result_no_words = {
            "language": "en",
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 2.5,
                    "text": " Hello world",
                    # No "words" key
                }
            ],
        }
        mock_model = MagicMock()
        mock_model.transcribe.return_value = result_no_words
        mock_whisper.load_model.return_value = mock_model

        result = transcribe_audio(Path("/fake/audio.wav"))

        assert len(result.segments) == 1
        assert result.segments[0].words == []

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_model_load_failure(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """Whisper model load failure raises TranscriptionError."""
        mock_whisper.load_model.side_effect = RuntimeError("Model not found")

        with pytest.raises(TranscriptionError, match="Failed to load Whisper model"):
            transcribe_audio(Path("/fake/audio.wav"))

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_transcribe_failure(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """Whisper transcription failure raises TranscriptionError."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("Transcription failed")
        mock_whisper.load_model.return_value = mock_model

        with pytest.raises(TranscriptionError, match="Transcription failed"):
            transcribe_audio(Path("/fake/audio.wav"))

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_default_config_used(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """When config=None, default TranscriptionConfig is used."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = MOCK_WHISPER_RESULT
        mock_whisper.load_model.return_value = mock_model

        transcribe_audio(Path("/fake/audio.wav"), config=None)

        mock_whisper.load_model.assert_called_once_with("turbo", device="cpu")
        call_kwargs = mock_model.transcribe.call_args[1]
        assert call_kwargs["word_timestamps"] is True
        assert call_kwargs["language"] is None

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cuda")
    def test_gpu_out_of_memory(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """CUDA OOM raises TranscriptionError with actionable message."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError(
            "CUDA out of memory. Tried to allocate 2.00 GiB"
        )
        mock_whisper.load_model.return_value = mock_model

        with pytest.raises(TranscriptionError, match="GPU out of memory"):
            transcribe_audio(Path("/fake/audio.wav"))

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_progress_callback_called(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """Progress callback receives 0.0 and 1.0."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = MOCK_WHISPER_RESULT
        mock_whisper.load_model.return_value = mock_model

        progress_values: list[float] = []
        transcribe_audio(
            Path("/fake/audio.wav"),
            progress_callback=lambda v: progress_values.append(v),
        )

        assert 0.0 in progress_values
        assert 1.0 in progress_values
