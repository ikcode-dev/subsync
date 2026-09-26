"""Tests for the transcriber module."""

import logging
import sys
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from subsync.errors import ModelDownloadError, ModelMemoryError, TranscriptionError
from subsync.models import TranscriptionConfig, TranscriptionResult
from subsync.transcriber import (
    LoadedModel,
    _MODEL_CACHE_FILENAMES,
    _resolve_device,
    is_model_cached,
    load_model,
    transcribe_audio,
    transcribe_with_model,
)

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
# is_model_cached tests (Scenario 1)
# =============================================================================


class TestIsModelCached:
    """Tests for is_model_cached()."""

    def test_cached_when_weight_file_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XDG_CACHE_HOME set, weight file present → True."""
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        cache_dir = tmp_path / "whisper"
        cache_dir.mkdir()
        (cache_dir / "large-v3-turbo.pt").touch()

        assert is_model_cached("turbo") is True

    def test_not_cached_when_weight_file_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XDG_CACHE_HOME set, weight file absent → False."""
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

        assert is_model_cached("turbo") is False

    def test_falls_back_to_home_cache_without_xdg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without XDG_CACHE_HOME, ~/.cache/whisper is used."""
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        cache_dir = tmp_path / ".cache" / "whisper"
        cache_dir.mkdir(parents=True)
        (cache_dir / "large-v3-turbo.pt").touch()

        assert is_model_cached("turbo") is True

    def test_unknown_model_name_is_never_cached(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A name outside the known catalog (e.g. a checkpoint path) → False."""
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

        assert is_model_cached("/some/local/checkpoint.pt") is False

    @patch("subsync.transcriber.whisper")
    def test_unaffected_by_a_mocked_whisper_module(
        self,
        mock_whisper: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """is_model_cached does not rely on the (possibly mocked) whisper module."""
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        cache_dir = tmp_path / "whisper"
        cache_dir.mkdir()
        (cache_dir / "small.pt").touch()

        assert is_model_cached("small") is True
        mock_whisper.assert_not_called()


def test_model_cache_filenames_matches_real_whisper_urls() -> None:
    """Drift guard (S1.5-Q7): _MODEL_CACHE_FILENAMES tracks whisper._MODELS.

    Imports the real ``whisper`` package (not a stand-in) so a future
    openai-whisper upgrade that changes a download URL's basename is
    caught here instead of silently breaking is_model_cached().
    """
    import os as real_os

    import whisper as real_whisper

    expected = {
        name: real_os.path.basename(url) for name, url in real_whisper._MODELS.items()
    }

    assert _MODEL_CACHE_FILENAMES == expected


# =============================================================================
# load_model tests (Scenarios 2, 3, 4, 8)
# =============================================================================


class TestLoadModel:
    """Tests for load_model()."""

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber.is_model_cached", return_value=False)
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_not_cached_download_failure_raises_model_download_error(
        self,
        mock_device: MagicMock,
        mock_cached: MagicMock,
        mock_whisper: MagicMock,
    ) -> None:
        """Scenario 2: not cached, loader raises URLError → ModelDownloadError."""
        mock_whisper.load_model.side_effect = URLError("no network")
        config = TranscriptionConfig(model_name="turbo")

        with pytest.raises(ModelDownloadError) as exc_info:
            load_model(config)

        assert "Couldn't download model 'turbo'" in str(exc_info.value)
        assert exc_info.value.hint == "An internet connection is needed once per model."

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber.is_model_cached", return_value=False)
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_reason_ending_in_a_period_is_not_doubled(
        self,
        mock_device: MagicMock,
        mock_cached: MagicMock,
        mock_whisper: MagicMock,
    ) -> None:
        """S1.5-Q5: a reason that already ends in '.' must not get '..'."""
        mock_whisper.load_model.side_effect = RuntimeError(
            "Model has been downloaded but the SHA256 checksum does not "
            "match. Please retry loading the model."
        )
        config = TranscriptionConfig(model_name="turbo")

        with pytest.raises(ModelDownloadError) as exc_info:
            load_model(config)

        assert ".." not in str(exc_info.value)
        assert str(exc_info.value).endswith("Please retry loading the model.")

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber.is_model_cached", return_value=True)
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_cached_generic_failure_is_not_a_download_error(
        self,
        mock_device: MagicMock,
        mock_cached: MagicMock,
        mock_whisper: MagicMock,
    ) -> None:
        """Scenario 3: cached, loader raises RuntimeError('boom') → TranscriptionError."""
        mock_whisper.load_model.side_effect = RuntimeError("boom")
        config = TranscriptionConfig(model_name="turbo")

        with pytest.raises(TranscriptionError) as exc_info:
            load_model(config)

        assert not isinstance(exc_info.value, ModelDownloadError)
        assert not isinstance(exc_info.value, ModelMemoryError)

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber.is_model_cached", return_value=True)
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_runtime_out_of_memory_raises_model_memory_error(
        self,
        mock_device: MagicMock,
        mock_cached: MagicMock,
        mock_whisper: MagicMock,
    ) -> None:
        """Scenario 4: 'CUDA out of memory' RuntimeError → ModelMemoryError."""
        mock_whisper.load_model.side_effect = RuntimeError(
            "CUDA out of memory. Tried to allocate 2.00 GiB"
        )
        config = TranscriptionConfig(model_name="large-v3")

        with pytest.raises(ModelMemoryError) as exc_info:
            load_model(config)

        assert "large-v3" in str(exc_info.value)
        assert exc_info.value.hint == "Try a smaller one: -m small"

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber.is_model_cached", return_value=False)
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_memory_error_raises_model_memory_error_even_when_not_cached(
        self,
        mock_device: MagicMock,
        mock_cached: MagicMock,
        mock_whisper: MagicMock,
    ) -> None:
        """Scenario 4: bare MemoryError → ModelMemoryError, not a download error."""
        mock_whisper.load_model.side_effect = MemoryError()
        config = TranscriptionConfig(model_name="large-v3")

        with pytest.raises(ModelMemoryError) as exc_info:
            load_model(config)

        assert "large-v3" in str(exc_info.value)

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber.is_model_cached", return_value=True)
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_loaded_model_cpu_device_label(
        self,
        mock_device: MagicMock,
        mock_cached: MagicMock,
        mock_whisper: MagicMock,
    ) -> None:
        """Scenario 8: LoadedModel for CPU has the uppercase device label."""
        mock_engine = MagicMock()
        mock_whisper.load_model.return_value = mock_engine
        config = TranscriptionConfig(model_name="turbo")

        loaded = load_model(config)

        assert isinstance(loaded, LoadedModel)
        assert loaded.device == "CPU"
        assert loaded.name == "turbo"
        assert loaded.engine is mock_engine


# =============================================================================
# transcribe_with_model tests (Scenarios 5, 6, 7)
# =============================================================================


class TestTranscribeWithModel:
    """Tests for transcribe_with_model()."""

    def _loaded_model(self, engine: MagicMock) -> LoadedModel:
        return LoadedModel(name="turbo", device="CPU", engine=engine)

    def test_out_of_memory_raises_model_memory_error(self) -> None:
        """Scenario 5: transcribe raises an 'out of memory' error → ModelMemoryError."""
        engine = MagicMock()
        engine.transcribe.side_effect = RuntimeError(
            "CUDA out of memory. Tried to allocate 1.00 GiB"
        )
        model = self._loaded_model(engine)

        with pytest.raises(ModelMemoryError) as exc_info:
            transcribe_with_model(model, Path("/fake/audio.wav"), TranscriptionConfig())

        assert "turbo" in str(exc_info.value)
        assert exc_info.value.hint == "Try a smaller one: -m small"

    def test_other_failure_raises_transcription_error(self) -> None:
        """A non-memory transcribe failure raises TranscriptionError with the hint."""
        engine = MagicMock()
        engine.transcribe.side_effect = RuntimeError("boom")
        model = self._loaded_model(engine)

        with pytest.raises(TranscriptionError) as exc_info:
            transcribe_with_model(model, Path("/fake/audio.wav"), TranscriptionConfig())

        assert not isinstance(exc_info.value, ModelMemoryError)
        assert exc_info.value.hint == "Re-run with -v for details."

    def test_keyboard_interrupt_propagates(self) -> None:
        """Scenario 6: KeyboardInterrupt during transcribe is never caught."""
        engine = MagicMock()
        engine.transcribe.side_effect = KeyboardInterrupt()
        model = self._loaded_model(engine)

        with pytest.raises(KeyboardInterrupt):
            transcribe_with_model(model, Path("/fake/audio.wav"), TranscriptionConfig())

    def test_download_bar_and_warnings_are_quiet(
        self, capfd: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Scenario 7: Whisper's stderr bar and warnings go to debug logging."""

        def fake_transcribe(*args: object, **kwargs: object) -> dict:
            sys.stderr.write("50%|#####     | 5/10 [00:01<00:01]\r")
            warnings.warn("FP16 is not supported on CPU; using FP32 instead")
            return MOCK_WHISPER_RESULT

        engine = MagicMock()
        engine.transcribe.side_effect = fake_transcribe
        model = self._loaded_model(engine)

        with caplog.at_level(logging.DEBUG, logger="subsync.transcriber"):
            transcribe_with_model(model, Path("/fake/audio.wav"), TranscriptionConfig())

        captured = capfd.readouterr()
        assert captured.out == ""
        assert captured.err == ""
        assert any(record.levelno == logging.DEBUG for record in caplog.records)

    def test_warnings_behave_normally_outside_the_scope(self) -> None:
        """Suppression is scoped: a warning issued outside still surfaces normally."""
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            warnings.warn("unrelated warning", UserWarning)

        assert len(recorded) == 1
        assert "unrelated warning" in str(recorded[0].message)


# =============================================================================
# transcribe_audio tests (Scenario 9 — unchanged behavior, now composed)
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
    @patch("subsync.transcriber.is_model_cached", return_value=True)
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_model_load_failure_propagates_as_transcription_error(
        self,
        mock_device: MagicMock,
        mock_cached: MagicMock,
        mock_whisper: MagicMock,
    ) -> None:
        """A cached model's load failure surfaces as TranscriptionError."""
        mock_whisper.load_model.side_effect = RuntimeError("Model not found")

        with pytest.raises(TranscriptionError) as exc_info:
            transcribe_audio(Path("/fake/audio.wav"))

        assert not isinstance(exc_info.value, ModelDownloadError)

    @patch("subsync.transcriber.whisper")
    @patch("subsync.transcriber._resolve_device", return_value="cpu")
    def test_transcribe_failure_propagates_as_transcription_error(
        self, mock_device: MagicMock, mock_whisper: MagicMock
    ) -> None:
        """A transcription failure surfaces as TranscriptionError."""
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
        """CUDA OOM during transcription raises ModelMemoryError."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError(
            "CUDA out of memory. Tried to allocate 2.00 GiB"
        )
        mock_whisper.load_model.return_value = mock_model

        with pytest.raises(ModelMemoryError):
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
