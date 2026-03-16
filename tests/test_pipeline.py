"""Tests for the pipeline module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from subsync.errors import (
    SubSyncError,
    TranscriptionError,
    URLParseError,
    VideoUnavailableError,
)
from subsync.models import (
    TranscriptionResult,
    TranscriptionSegment,
    VideoMetadata,
    Word,
)
from subsync.pipeline import pipeline_temp_dir, process_video


# =============================================================================
# pipeline_temp_dir tests
# =============================================================================


class TestPipelineTempDir:
    """Tests for pipeline_temp_dir() context manager."""

    def test_normal_exit_cleans_up(self) -> None:
        """Directory is removed after normal exit."""
        with pipeline_temp_dir() as tmp_dir:
            assert tmp_dir.exists()
            assert tmp_dir.is_dir()
            captured = tmp_dir

        assert not captured.exists()

    def test_exception_exit_cleans_up(self) -> None:
        """Directory is removed after exception exit."""
        captured: Path | None = None
        with pytest.raises(ValueError, match="test"):
            with pipeline_temp_dir() as tmp_dir:
                captured = tmp_dir
                assert tmp_dir.exists()
                raise ValueError("test")

        assert captured is not None
        assert not captured.exists()

    def test_files_inside_cleaned_up(self) -> None:
        """Files inside temp directory are removed."""
        with pipeline_temp_dir() as tmp_dir:
            test_file = tmp_dir / "test.wav"
            test_file.write_text("fake audio data")
            assert test_file.exists()
            captured = tmp_dir

        assert not captured.exists()

    def test_directory_name_prefix(self) -> None:
        """Temp directory name starts with 'subsync_'."""
        with pipeline_temp_dir() as tmp_dir:
            assert tmp_dir.name.startswith("subsync_")


# =============================================================================
# process_video tests
# =============================================================================


# Shared test fixtures
_MOCK_METADATA = VideoMetadata(
    id="dQw4w9WgXcQ",
    title="Test Video",
    duration=120.0,
    uploader="Test Channel",
    upload_date="20230101",
)

_MOCK_TRANSCRIPTION = TranscriptionResult(
    language="en",
    duration=120.0,
    segments=[
        TranscriptionSegment(
            id=0,
            start=0.0,
            end=2.5,
            text="Hello world",
            words=[
                Word(word="Hello", start=0.0, end=1.2),
                Word(word="world", start=1.3, end=2.5),
            ],
        )
    ],
)


class TestProcessVideo:
    """Tests for process_video()."""

    @patch("subsync.pipeline.transcribe_audio")
    @patch("subsync.pipeline.download_audio")
    @patch("subsync.pipeline.get_video_metadata")
    @patch("subsync.pipeline.parse_youtube_url")
    def test_full_pipeline_success(
        self,
        mock_parse: MagicMock,
        mock_metadata: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
    ) -> None:
        """Full pipeline returns (VideoMetadata, TranscriptionResult)."""
        mock_parse.return_value = "dQw4w9WgXcQ"
        mock_metadata.return_value = _MOCK_METADATA
        mock_download.return_value = Path("/tmp/fake/dQw4w9WgXcQ.wav")
        mock_transcribe.return_value = _MOCK_TRANSCRIPTION

        metadata, result = process_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert metadata == _MOCK_METADATA
        assert result == _MOCK_TRANSCRIPTION
        mock_parse.assert_called_once()
        mock_metadata.assert_called_once_with("dQw4w9WgXcQ")
        mock_download.assert_called_once()
        mock_transcribe.assert_called_once()

    @patch("subsync.pipeline.parse_youtube_url")
    def test_invalid_url_propagates(self, mock_parse: MagicMock) -> None:
        """URLParseError propagates unchanged."""
        mock_parse.side_effect = URLParseError("not a YouTube URL")

        with pytest.raises(URLParseError, match="not a YouTube URL"):
            process_video("https://vimeo.com/12345")

    @patch("subsync.pipeline.get_video_metadata")
    @patch("subsync.pipeline.parse_youtube_url")
    def test_video_unavailable_propagates(
        self, mock_parse: MagicMock, mock_metadata: MagicMock
    ) -> None:
        """VideoUnavailableError propagates unchanged."""
        mock_parse.return_value = "xxxxxxxxxxx"
        mock_metadata.side_effect = VideoUnavailableError("Video unavailable")

        with pytest.raises(VideoUnavailableError):
            process_video("https://www.youtube.com/watch?v=xxxxxxxxxxx")

    @patch("subsync.pipeline.transcribe_audio")
    @patch("subsync.pipeline.download_audio")
    @patch("subsync.pipeline.get_video_metadata")
    @patch("subsync.pipeline.parse_youtube_url")
    def test_transcription_failure_propagates(
        self,
        mock_parse: MagicMock,
        mock_metadata: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
    ) -> None:
        """TranscriptionError propagates unchanged."""
        mock_parse.return_value = "dQw4w9WgXcQ"
        mock_metadata.return_value = _MOCK_METADATA
        mock_download.return_value = Path("/tmp/fake/dQw4w9WgXcQ.wav")
        mock_transcribe.side_effect = TranscriptionError("Transcription failed")

        with pytest.raises(TranscriptionError):
            process_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    @patch("subsync.pipeline.transcribe_audio")
    @patch("subsync.pipeline.download_audio")
    @patch("subsync.pipeline.get_video_metadata")
    @patch("subsync.pipeline.parse_youtube_url")
    def test_progress_reporting(
        self,
        mock_parse: MagicMock,
        mock_metadata: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
    ) -> None:
        """Progress callback receives increasing values and stage names."""
        mock_parse.return_value = "dQw4w9WgXcQ"
        mock_metadata.return_value = _MOCK_METADATA
        mock_download.return_value = Path("/tmp/fake/dQw4w9WgXcQ.wav")
        mock_transcribe.return_value = _MOCK_TRANSCRIPTION

        progress_calls: list[tuple[float, str]] = []

        def capture(progress: float, stage: str) -> None:
            progress_calls.append((progress, stage))

        process_video(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            progress_callback=capture,
        )

        # Verify we got progress calls
        assert len(progress_calls) > 0

        # Verify stage names are present
        stages = {stage for _, stage in progress_calls}
        assert "Parsing URL" in stages
        assert "Getting metadata" in stages

        # Verify first progress is 0.0
        assert progress_calls[0] == (0.0, "Parsing URL")

    @patch("subsync.pipeline.transcribe_audio")
    @patch("subsync.pipeline.download_audio")
    @patch("subsync.pipeline.get_video_metadata")
    @patch("subsync.pipeline.parse_youtube_url")
    def test_no_progress_callback(
        self,
        mock_parse: MagicMock,
        mock_metadata: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
    ) -> None:
        """Pipeline works without progress callback."""
        mock_parse.return_value = "dQw4w9WgXcQ"
        mock_metadata.return_value = _MOCK_METADATA
        mock_download.return_value = Path("/tmp/fake/dQw4w9WgXcQ.wav")
        mock_transcribe.return_value = _MOCK_TRANSCRIPTION

        metadata, result = process_video(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            progress_callback=None,
        )

        assert metadata == _MOCK_METADATA
        assert result == _MOCK_TRANSCRIPTION

    @patch("subsync.pipeline.transcribe_audio")
    @patch("subsync.pipeline.download_audio")
    @patch("subsync.pipeline.get_video_metadata")
    @patch("subsync.pipeline.parse_youtube_url")
    def test_default_transcription_config(
        self,
        mock_parse: MagicMock,
        mock_metadata: MagicMock,
        mock_download: MagicMock,
        mock_transcribe: MagicMock,
    ) -> None:
        """Default TranscriptionConfig is used when config=None."""
        mock_parse.return_value = "dQw4w9WgXcQ"
        mock_metadata.return_value = _MOCK_METADATA
        mock_download.return_value = Path("/tmp/fake/dQw4w9WgXcQ.wav")
        mock_transcribe.return_value = _MOCK_TRANSCRIPTION

        process_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # transcribe_audio should be called with config=None (pipeline passes it through)
        call_kwargs = mock_transcribe.call_args[1]
        assert call_kwargs["config"] is None

    @patch("subsync.pipeline.parse_youtube_url")
    def test_unexpected_error_wrapped(self, mock_parse: MagicMock) -> None:
        """Unexpected exceptions are wrapped in SubSyncError."""
        mock_parse.side_effect = RuntimeError("Something unexpected")

        with pytest.raises(SubSyncError, match="Unexpected pipeline error"):
            process_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
