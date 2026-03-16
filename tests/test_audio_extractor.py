"""Tests for the audio_extractor module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from subsync.audio_extractor import download_audio, get_video_metadata
from subsync.errors import AgeRestrictedError, LiveStreamError, VideoUnavailableError
from subsync.models import VideoMetadata


# =============================================================================
# get_video_metadata tests
# =============================================================================


class TestGetVideoMetadata:
    """Tests for get_video_metadata()."""

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_successful_extraction(self, mock_ydl_cls: MagicMock) -> None:
        """Successful metadata extraction returns populated VideoMetadata."""
        info = {
            "id": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "duration": 212.0,
            "uploader": "Rick Astley",
            "upload_date": "20091025",
            "is_live": False,
        }
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = info
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        result = get_video_metadata("dQw4w9WgXcQ")

        assert isinstance(result, VideoMetadata)
        assert result.id == "dQw4w9WgXcQ"
        assert result.title == "Rick Astley - Never Gonna Give You Up"
        assert result.duration == 212.0
        assert result.uploader == "Rick Astley"
        assert result.upload_date == "20091025"

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_missing_uploader_falls_back_to_channel(
        self, mock_ydl_cls: MagicMock
    ) -> None:
        """When uploader is None, falls back to channel field."""
        info = {
            "id": "dQw4w9WgXcQ",
            "title": "Test Video",
            "duration": 60.0,
            "uploader": None,
            "channel": "Test Channel",
            "upload_date": "20230101",
            "is_live": False,
        }
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = info
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        result = get_video_metadata("dQw4w9WgXcQ")
        assert result.uploader == "Test Channel"

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_missing_both_uploader_and_channel(self, mock_ydl_cls: MagicMock) -> None:
        """When both uploader and channel are None, falls back to 'Unknown'."""
        info = {
            "id": "dQw4w9WgXcQ",
            "title": "Test Video",
            "duration": 60.0,
            "uploader": None,
            "channel": None,
            "upload_date": "20230101",
            "is_live": False,
        }
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = info
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        result = get_video_metadata("dQw4w9WgXcQ")
        assert result.uploader == "Unknown"

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_title_whitespace_stripped(self, mock_ydl_cls: MagicMock) -> None:
        """Title leading/trailing whitespace is stripped."""
        info = {
            "id": "dQw4w9WgXcQ",
            "title": "  Padded Title  ",
            "duration": 60.0,
            "uploader": "Test",
            "upload_date": "20230101",
            "is_live": False,
        }
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = info
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        result = get_video_metadata("dQw4w9WgXcQ")
        assert result.title == "Padded Title"

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_video_unavailable_raises(self, mock_ydl_cls: MagicMock) -> None:
        """DownloadError with 'unavailable' raises VideoUnavailableError."""
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "Video unavailable"
        )
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(VideoUnavailableError):
            get_video_metadata("xxxxxxxxxxx")

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_private_video_raises(self, mock_ydl_cls: MagicMock) -> None:
        """DownloadError with 'private' raises VideoUnavailableError."""
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "This video is private"
        )
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(VideoUnavailableError):
            get_video_metadata("xxxxxxxxxxx")

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_age_restricted_raises(self, mock_ydl_cls: MagicMock) -> None:
        """DownloadError with 'age' raises AgeRestrictedError."""
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "Sign in to confirm your age"
        )
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(AgeRestrictedError):
            get_video_metadata("xxxxxxxxxxx")

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_live_stream_raises(self, mock_ydl_cls: MagicMock) -> None:
        """Info dict with is_live=True raises LiveStreamError."""
        info = {
            "id": "dQw4w9WgXcQ",
            "title": "Live Stream",
            "duration": 0.0,
            "uploader": "Streamer",
            "upload_date": "20230101",
            "is_live": True,
        }
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = info
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(LiveStreamError):
            get_video_metadata("dQw4w9WgXcQ")

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_network_error_raises_video_unavailable(
        self, mock_ydl_cls: MagicMock
    ) -> None:
        """Generic DownloadError raises VideoUnavailableError."""
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "Unable to download webpage"
        )
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(VideoUnavailableError):
            get_video_metadata("xxxxxxxxxxx")

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_none_info_raises_video_unavailable(self, mock_ydl_cls: MagicMock) -> None:
        """extract_info returning None raises VideoUnavailableError."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = None
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(VideoUnavailableError):
            get_video_metadata("xxxxxxxxxxx")


# =============================================================================
# download_audio tests
# =============================================================================


class TestDownloadAudio:
    """Tests for download_audio()."""

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_successful_download(self, mock_ydl_cls: MagicMock, tmp_path: Path) -> None:
        """Successful download returns path to WAV file."""
        # Create the expected output file to simulate yt-dlp writing it
        wav_file = tmp_path / "dQw4w9WgXcQ.wav"
        wav_file.touch()

        mock_ydl = MagicMock()
        mock_ydl.download.return_value = 0
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        result = download_audio("dQw4w9WgXcQ", tmp_path)

        assert result == wav_file
        assert result.suffix == ".wav"

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_progress_callback_called(
        self, mock_ydl_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Progress callback receives values from progress hooks."""
        wav_file = tmp_path / "dQw4w9WgXcQ.wav"
        wav_file.touch()

        progress_values: list[float] = []

        def capture_progress(value: float) -> None:
            progress_values.append(value)

        mock_ydl = MagicMock()

        def fake_download(urls: list[str]) -> int:
            # Simulate yt-dlp calling the progress hook
            opts = mock_ydl_cls.call_args[0][0]
            hooks = opts.get("progress_hooks", [])
            for hook in hooks:
                hook(
                    {
                        "status": "downloading",
                        "downloaded_bytes": 50,
                        "total_bytes": 100,
                    }
                )
                hook(
                    {
                        "status": "downloading",
                        "downloaded_bytes": 100,
                        "total_bytes": 100,
                    }
                )
                hook({"status": "finished"})
            return 0

        mock_ydl.download.side_effect = fake_download
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        download_audio("dQw4w9WgXcQ", tmp_path, progress_callback=capture_progress)

        assert len(progress_values) >= 2
        assert progress_values[-1] == 1.0

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_download_failure_raises(
        self, mock_ydl_cls: MagicMock, tmp_path: Path
    ) -> None:
        """DownloadError raises VideoUnavailableError."""
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.download.side_effect = yt_dlp.utils.DownloadError("Download failed")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(VideoUnavailableError):
            download_audio("xxxxxxxxxxx", tmp_path)

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_no_progress_callback(
        self, mock_ydl_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Download works without a progress callback."""
        wav_file = tmp_path / "dQw4w9WgXcQ.wav"
        wav_file.touch()

        mock_ydl = MagicMock()
        mock_ydl.download.return_value = 0
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        result = download_audio("dQw4w9WgXcQ", tmp_path, progress_callback=None)
        assert result == wav_file

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_output_in_correct_directory(
        self, mock_ydl_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Output file is in the specified output directory."""
        wav_file = tmp_path / "dQw4w9WgXcQ.wav"
        wav_file.touch()

        mock_ydl = MagicMock()
        mock_ydl.download.return_value = 0
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        result = download_audio("dQw4w9WgXcQ", tmp_path)
        assert result.parent == tmp_path

    @patch("subsync.audio_extractor.yt_dlp.YoutubeDL")
    def test_missing_wav_raises(self, mock_ydl_cls: MagicMock, tmp_path: Path) -> None:
        """If WAV file is missing after download, raises VideoUnavailableError."""
        mock_ydl = MagicMock()
        mock_ydl.download.return_value = 0
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(VideoUnavailableError, match="WAV file not found"):
            download_audio("dQw4w9WgXcQ", tmp_path)
