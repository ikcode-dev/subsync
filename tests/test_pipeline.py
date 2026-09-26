"""Tests for the pipeline module."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from media_fixtures import make_tone_clip, make_video_only_clip, requires_ffmpeg
from srt_invariants import assert_valid_srt
from transcriber_stand_in import StandInTranscriber
from transcript_fixtures import EPISODE_WITH_URL, NO_SEGMENTS, URL, load_transcript

from subsync import pipeline, transcriber
from subsync.errors import (
    InputError,
    MediaError,
    NoSpeechError,
    OutputExistsError,
    SubSyncError,
    TranscriptionError,
    URLParseError,
    VideoUnavailableError,
)
from subsync.models import (
    MediaSource,
    ProcessingConfig,
    TranscriptionConfig,
    TranscriptionResult,
    TranscriptionSegment,
    VideoMetadata,
    Word,
)
from subsync.output import plan_output
from subsync.pipeline import pipeline_temp_dir, process_video
from subsync.sources import resolve_input


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


# =============================================================================
# generate() tests: real FFmpeg, processor and writer; stand-in transcriber
# =============================================================================


@pytest.fixture(scope="module")
def tone_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One 3 s tone clip per module, copied into each test's folder."""
    return make_tone_clip(tmp_path_factory.mktemp("media") / "tone.mp4")


def _run_generate(
    clip: Path,
    *,
    language: str | None = None,
    force: bool = False,
    events: list[pipeline.GenerateEvent] | None = None,
) -> pipeline.GenerateResult:
    """Resolve, plan and generate for ``clip`` as the CLI would."""
    source = resolve_input(str(clip))
    plan = plan_output(source, None, "srt", language, force)
    return pipeline.generate(
        source,
        TranscriptionConfig(model_name="tiny", language=language),
        ProcessingConfig(),
        plan,
        force,
        events.append if events is not None else None,
    )


@requires_ffmpeg
class TestGenerate:
    """generate() runs every stage in order and reports each as an event."""

    def test_writes_valid_srt_and_reports_stages_in_order(
        self,
        tmp_path: Path,
        tone_template: Path,
        run_tmpdir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        clip = Path(shutil.copy(tone_template, tmp_path / "tone.mp4"))
        stand_in = StandInTranscriber(load_transcript(EPISODE_WITH_URL)).install(
            monkeypatch
        )
        events: list[pipeline.GenerateEvent] = []

        result = _run_generate(clip, events=events)

        assert result.path == tmp_path / "tone.en.srt"
        assert_valid_srt(result.path.read_bytes())
        assert result.language == "en"
        assert result.language_detected is True
        assert (result.model_name, result.device) == ("tiny", "CPU")
        assert result.source.duration == pytest.approx(3.0, abs=0.1)
        assert [f.kind for f in result.report.flags] == ["long_word"]
        assert URL in result.subtitles[result.report.flags[0].subtitle_index - 1].text
        assert [type(e).__name__ for e in events] == [
            "SourceReady",
            "AudioExtracted",
            "ModelLoaded",
            "TranscriptionStarted",
            "Transcribed",
            "Formatted",
            "Written",
        ]
        assert stand_in.audio_existed == [True]
        assert list(run_tmpdir.iterdir()) == []
        captured = capfd.readouterr()
        assert (captured.out, captured.err) == ("", "")

    def test_download_notice_only_when_not_cached(
        self,
        tmp_path: Path,
        tone_template: Path,
        run_tmpdir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        clip = Path(shutil.copy(tone_template, tmp_path / "tone.mp4"))
        StandInTranscriber(load_transcript(EPISODE_WITH_URL), cached=False).install(
            monkeypatch
        )
        events: list[pipeline.GenerateEvent] = []

        _run_generate(clip, events=events)

        names = [type(e).__name__ for e in events]
        assert names.index("ModelDownloading") == names.index("ModelLoaded") - 1

    def test_language_set_with_l_names_the_file(
        self,
        tmp_path: Path,
        tone_template: Path,
        run_tmpdir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        clip = Path(shutil.copy(tone_template, tmp_path / "tone.mp4"))
        stand_in = StandInTranscriber(load_transcript(EPISODE_WITH_URL)).install(
            monkeypatch
        )

        result = _run_generate(clip, language="de")

        assert result.path.name == "tone.de.srt"
        assert result.language_detected is False
        assert stand_in.transcribe_calls[0][1].language == "de"

    def test_no_speech_writes_nothing(
        self,
        tmp_path: Path,
        tone_template: Path,
        run_tmpdir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        clip = Path(shutil.copy(tone_template, tmp_path / "tone.mp4"))
        StandInTranscriber(load_transcript(NO_SEGMENTS)).install(monkeypatch)

        with pytest.raises(NoSpeechError) as info:
            _run_generate(clip)

        assert str(info.value) == "No speech found in tone.mp4, so nothing was written."
        assert info.value.hint == "If the language was misdetected, set it with -l en."
        assert sorted(p.name for p in tmp_path.iterdir()) == ["run-tmp", "tone.mp4"]
        assert list(run_tmpdir.iterdir()) == []

    def test_no_audio_fails_before_the_model_loads(
        self,
        tmp_path: Path,
        run_tmpdir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        clip = make_video_only_clip(tmp_path / "silent.mp4")
        stand_in = StandInTranscriber(load_transcript(EPISODE_WITH_URL)).install(
            monkeypatch
        )

        with pytest.raises(MediaError, match="No audio track found in silent.mp4."):
            _run_generate(clip)

        assert stand_in.load_calls == []

    def test_interrupt_during_transcription_cleans_up(
        self,
        tmp_path: Path,
        tone_template: Path,
        run_tmpdir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        clip = Path(shutil.copy(tone_template, tmp_path / "tone.mp4"))
        StandInTranscriber(
            load_transcript(EPISODE_WITH_URL), transcribe_error=KeyboardInterrupt()
        ).install(monkeypatch)

        with pytest.raises(KeyboardInterrupt):
            _run_generate(clip)

        assert list(run_tmpdir.iterdir()) == []
        assert not (tmp_path / "tone.en.srt").exists()

    def test_write_time_recheck_refuses_a_file_created_meanwhile(
        self,
        tmp_path: Path,
        tone_template: Path,
        run_tmpdir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        clip = Path(shutil.copy(tone_template, tmp_path / "tone.mp4"))
        target = tmp_path / "tone.en.srt"
        stand_in = StandInTranscriber(load_transcript(EPISODE_WITH_URL))
        original = stand_in.transcribe_with_model

        def transcribe_then_race(
            model: transcriber.LoadedModel,
            audio_path: Path,
            config: TranscriptionConfig,
            progress_callback: object = None,
        ) -> TranscriptionResult:
            target.write_text("hand-corrected\n", encoding="utf-8")
            return original(model, audio_path, config)

        stand_in.install(monkeypatch)
        monkeypatch.setattr(
            pipeline.transcriber, "transcribe_with_model", transcribe_then_race
        )

        with pytest.raises(OutputExistsError, match="tone.en.srt already exists."):
            _run_generate(clip)

        assert target.read_text(encoding="utf-8") == "hand-corrected\n"

    def test_rejects_sources_and_formats_not_in_s1(self, tmp_path: Path) -> None:
        youtube = MediaSource(
            kind="youtube",
            display_name="x",
            output_stem="x",
            output_dir=tmp_path,
            video_id="dQw4w9WgXcQ",
        )
        plan = plan_output(youtube, None, "srt", "en", False)
        with pytest.raises(InputError):
            pipeline.generate(
                youtube, TranscriptionConfig(), ProcessingConfig(), plan, False
            )
