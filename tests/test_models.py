"""Tests for data models."""

from datetime import timedelta
from pathlib import Path

from subsync.models import (
    ComplianceFlag,
    ComplianceReport,
    MediaSource,
    OutputConfig,
    ProcessingConfig,
    Subtitle,
    SubtitleFile,
    TimingValidation,
    TranscriptionConfig,
    TranscriptionResult,
    TranscriptionSegment,
    VideoMetadata,
    Word,
)


class TestVideoMetadata:
    """Tests for VideoMetadata model."""

    def test_create_video_metadata(self) -> None:
        """Test basic VideoMetadata creation."""
        meta = VideoMetadata(
            id="dQw4w9WgXcQ",
            title="Test Video",
            duration=180.0,
            uploader="Test Channel",
            upload_date="20240115",
        )
        assert meta.id == "dQw4w9WgXcQ"
        assert meta.title == "Test Video"
        assert meta.duration == 180.0
        assert meta.uploader == "Test Channel"
        assert meta.upload_date == "20240115"


class TestWord:
    """Tests for Word model."""

    def test_create_word(self) -> None:
        """Test basic Word creation."""
        word = Word(word="hello", start=0.0, end=0.5)
        assert word.word == "hello"
        assert word.start == 0.0
        assert word.end == 0.5


class TestTranscriptionSegment:
    """Tests for TranscriptionSegment model."""

    def test_create_segment_without_words(self) -> None:
        """Test segment creation without word-level timestamps."""
        segment = TranscriptionSegment(
            id=0,
            start=0.0,
            end=5.0,
            text="Hello world",
        )
        assert segment.id == 0
        assert segment.text == "Hello world"
        assert segment.words == []

    def test_create_segment_with_words(self) -> None:
        """Test segment creation with word-level timestamps."""
        words = [
            Word(word="Hello", start=0.0, end=0.3),
            Word(word="world", start=0.4, end=0.8),
        ]
        segment = TranscriptionSegment(
            id=0,
            start=0.0,
            end=1.0,
            text="Hello world",
            words=words,
        )
        assert len(segment.words) == 2
        assert segment.words[0].word == "Hello"


class TestTranscriptionResult:
    """Tests for TranscriptionResult model."""

    def test_create_transcription_result(self) -> None:
        """Test TranscriptionResult creation."""
        segment = TranscriptionSegment(
            id=0,
            start=0.0,
            end=5.0,
            text="Hello world",
        )
        result = TranscriptionResult(
            language="en",
            duration=120.0,
            segments=[segment],
        )
        assert result.language == "en"
        assert result.duration == 120.0
        assert len(result.segments) == 1


class TestSubtitle:
    """Tests for Subtitle model and computed properties."""

    def test_char_count_single_line(self) -> None:
        """Test character count with single line."""
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=2),
            text="Hello world",
            lines=["Hello world"],
        )
        assert subtitle.char_count == 11

    def test_char_count_multiple_lines(self) -> None:
        """Test character count with multiple lines."""
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=2),
            text="Hello world, how are you?",
            lines=["Hello world,", "how are you?"],
        )
        assert subtitle.char_count == 24  # 12 + 12

    def test_duration_ms(self) -> None:
        """Test duration calculation in milliseconds."""
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=1),
            end_time=timedelta(seconds=3, milliseconds=500),
            text="Test",
            lines=["Test"],
        )
        assert subtitle.duration_ms == 2500

    def test_duration_ms_is_exact_for_whole_milliseconds(self) -> None:
        """Whole-millisecond durations are never off by one (float truncation)."""
        start = timedelta(seconds=3)
        wrong = [
            ms
            for ms in range(0, 20_001)
            if Subtitle(
                index=1,
                start_time=start,
                end_time=start + timedelta(milliseconds=ms),
                text="x",
                lines=["x"],
            ).duration_ms
            != ms
        ]
        assert wrong == []

    def test_cps_calculation(self) -> None:
        """Test characters per second calculation."""
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=2),
            text="Hello world",
            lines=["Hello world"],  # 11 chars
        )
        # 11 chars / 2 seconds = 5.5 cps
        assert subtitle.cps == 5.5

    def test_cps_zero_duration(self) -> None:
        """Test CPS with zero duration (avoid division by zero)."""
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=1),
            end_time=timedelta(seconds=1),  # Same time = 0 duration
            text="Test",
            lines=["Test"],
        )
        assert subtitle.cps == 0  # Avoid division by zero


class TestSubtitleFile:
    """Tests for SubtitleFile model."""

    def test_create_subtitle_file(self) -> None:
        """Test SubtitleFile creation."""
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=2),
            text="Hello",
            lines=["Hello"],
        )
        file = SubtitleFile(
            format="srt",
            language="en",
            subtitles=[subtitle],
        )
        assert file.format == "srt"
        assert file.language == "en"
        assert len(file.subtitles) == 1

    def test_has_no_video_id(self) -> None:
        """SubtitleFile is source-agnostic and drops the YouTube video ID."""
        file = SubtitleFile(format="srt", language="en", subtitles=[])
        assert not hasattr(file, "video_id")


class TestMediaSource:
    """Tests for MediaSource model."""

    def test_local_file_source(self) -> None:
        """A local file source holds its fields; YouTube fields default to None."""
        path = Path("~/Videos/ep42.mov").expanduser()
        source = MediaSource(
            kind="file",
            display_name="ep42.mov",
            output_stem="ep42",
            output_dir=path.parent,
            path=path,
        )
        assert source.kind == "file"
        assert source.display_name == "ep42.mov"
        assert source.output_stem == "ep42"
        assert source.output_dir == path.parent
        assert source.path == path
        assert source.duration is None
        assert source.video_id is None
        assert source.channel is None

    def test_youtube_source(self) -> None:
        """A YouTube source carries its video ID and channel and no path."""
        source = MediaSource(
            kind="youtube",
            display_name="Episode 42",
            output_stem="Episode 42",
            output_dir=Path.cwd(),
            duration=892.0,
            video_id="dQw4w9WgXcQ",
            channel="ikcode",
        )
        assert source.path is None
        assert source.duration == 892.0
        assert source.video_id == "dQw4w9WgXcQ"
        assert source.channel == "ikcode"


class TestComplianceFlag:
    """Tests for ComplianceFlag model."""

    def test_create_flag(self) -> None:
        """A flag names its kind, subtitle, start time and optional detail."""
        flag = ComplianceFlag(
            kind="long_word",
            subtitle_index=3,
            start_time=timedelta(seconds=74.5),
        )
        assert flag.kind == "long_word"
        assert flag.subtitle_index == 3
        assert flag.start_time == timedelta(seconds=74.5)
        assert flag.detail == ""

    def test_flag_with_detail(self) -> None:
        """The detail carries extra information such as a CPS value."""
        flag = ComplianceFlag(
            kind="cps", subtitle_index=1, start_time=timedelta(0), detail="23.4 CPS"
        )
        assert flag.detail == "23.4 CPS"


class TestTimingValidation:
    """Tests for TimingValidation model."""

    def test_valid_timing(self) -> None:
        """Test valid timing validation."""
        validation = TimingValidation(
            is_valid=True,
            duration_ok=True,
            gap_ok=True,
        )
        assert validation.is_valid is True
        assert validation.issues == []

    def test_invalid_timing_with_issues(self) -> None:
        """Test invalid timing with issues."""
        validation = TimingValidation(
            is_valid=False,
            duration_ok=False,
            gap_ok=True,
            issues=["Duration too short: 500ms < 833ms"],
        )
        assert validation.is_valid is False
        assert len(validation.issues) == 1


class TestComplianceReport:
    """Tests for ComplianceReport model."""

    def test_compliant_report(self) -> None:
        """Test fully compliant report."""
        report = ComplianceReport(
            total_subtitles=10,
            timing_issues=0,
            cps_warnings=0,
            line_length_issues=0,
            is_compliant=True,
        )
        assert report.is_compliant is True
        assert report.warnings == []
        assert report.errors == []
        assert report.flags == []

    def test_non_compliant_report(self) -> None:
        """Test non-compliant report with issues."""
        report = ComplianceReport(
            total_subtitles=10,
            timing_issues=2,
            cps_warnings=1,
            line_length_issues=0,
            is_compliant=False,
            warnings=["CPS exceeds limit for subtitle 5"],
            errors=["Subtitle 3 duration too short", "Subtitle 7 duration too short"],
        )
        assert report.is_compliant is False
        assert len(report.warnings) == 1
        assert len(report.errors) == 2

    def test_flags_are_not_shared_between_reports(self) -> None:
        """Each report gets its own flags list."""
        first = ComplianceReport(
            total_subtitles=1,
            timing_issues=0,
            cps_warnings=0,
            line_length_issues=0,
            is_compliant=True,
        )
        second = ComplianceReport(
            total_subtitles=1,
            timing_issues=0,
            cps_warnings=0,
            line_length_issues=0,
            is_compliant=True,
        )
        first.flags.append(
            ComplianceFlag(kind="short", subtitle_index=1, start_time=timedelta(0))
        )
        assert len(first.flags) == 1
        assert second.flags == []


class TestConfigDefaults:
    """Tests for configuration model defaults."""

    def test_transcription_config_defaults(self) -> None:
        """Test TranscriptionConfig default values."""
        config = TranscriptionConfig()
        assert config.model_name == "turbo"
        assert config.language is None
        assert config.word_timestamps is True
        assert config.device == "auto"

    def test_transcription_config_custom(self) -> None:
        """Test TranscriptionConfig with custom values."""
        config = TranscriptionConfig(
            model_name="large-v3",
            language="es",
            word_timestamps=False,
            device="cuda",
        )
        assert config.model_name == "large-v3"
        assert config.language == "es"
        assert config.word_timestamps is False
        assert config.device == "cuda"

    def test_processing_config_defaults(self) -> None:
        """Test ProcessingConfig default values."""
        config = ProcessingConfig()
        assert config.max_chars_per_line == 42
        assert config.max_lines == 2
        assert config.min_duration_ms == 833
        assert config.max_duration_ms == 7000
        assert config.min_gap_ms == 83
        assert config.max_cps_adult == 20.0
        assert config.max_cps_children == 17.0
        assert config.is_children_content is False

    def test_output_config_defaults(self) -> None:
        """Test OutputConfig default values."""
        config = OutputConfig()
        assert config.format == "srt"
        assert config.output_path is None
        assert config.include_bom is False

    def test_output_config_with_path(self) -> None:
        """Test OutputConfig with custom output path."""
        config = OutputConfig(
            format="vtt",
            output_path=Path("/tmp/output.vtt"),
            include_bom=True,
        )
        assert config.format == "vtt"
        assert config.output_path == Path("/tmp/output.vtt")
        assert config.include_bom is True
