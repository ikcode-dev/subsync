"""Integration tests for the media module, run against real FFmpeg.

Nothing about FFmpeg is mocked here except in the cancellation scenario,
where a fake ``ffmpeg`` script stands in so the interrupt timing is
deterministic and bounded. Clips are generated at test time with
``media_fixtures`` and are a few seconds long, so the whole module runs in
a few seconds.
"""

import json
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path

import media_fixtures
import pytest

from subsync import media
from subsync.errors import DependencyError, MediaError


def _pid_alive(pid: int) -> bool:
    """Return whether a process with ``pid`` still exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _ffprobe_json(path: Path) -> dict:
    """Read a media file's ffprobe JSON report (test verification only)."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def media_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A small set of clips shared by every test in this module."""
    base = tmp_path_factory.mktemp("media")
    media_fixtures.make_tone_clip(base / "tone.mp4", duration=3.0)
    media_fixtures.make_video_only_clip(base / "silent-video.mp4", duration=1.0)
    media_fixtures.make_garbage_file(base / "garbage.mov")
    return base


class TestCheckFfmpeg:
    """Scenario 11: DependencyError when FFmpeg/ffprobe are missing."""

    def test_raises_when_path_has_neither_tool(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", str(tmp_path))

        with pytest.raises(DependencyError) as exc_info:
            media.check_ffmpeg()

        assert str(exc_info.value) == "FFmpeg is required but wasn't found."
        assert exc_info.value.hint == "Install it with: brew install ffmpeg"

    def test_raises_when_ffprobe_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_ffmpeg = tmp_path / "ffmpeg"
        fake_ffmpeg.write_text("#!/bin/sh\nexit 0\n")
        fake_ffmpeg.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path))

        with pytest.raises(DependencyError) as exc_info:
            media.check_ffmpeg()

        assert exc_info.value.hint == "Install it with: brew install ffmpeg"

    def test_starts_no_subprocess(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PATH lookup only: no child process is ever started."""
        calls: list[object] = []
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: calls.append((a, kw)))
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: calls.append((a, kw)))

        try:
            media.check_ffmpeg()
        except DependencyError:
            pass

        assert calls == []

    def test_probe_media_propagates_dependency_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", str(tmp_path))

        with pytest.raises(DependencyError):
            media.probe_media(tmp_path / "whatever.mp4")

    def test_extract_audio_propagates_dependency_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", str(tmp_path))

        with pytest.raises(DependencyError):
            media.extract_audio(tmp_path / "whatever.mp4", tmp_path)


@media_fixtures.requires_ffmpeg
class TestProbeMedia:
    """Scenarios 1-4: duration, multi-container, no-audio, unreadable."""

    def test_duration_of_av_clip(self, media_dir: Path) -> None:
        duration = media.probe_media(media_dir / "tone.mp4")

        assert duration == pytest.approx(3.0, abs=0.1)

    @pytest.mark.parametrize("ext", ["mov", "mkv", "webm", "m4a", "mp3", "wav"])
    def test_duration_and_extraction_across_containers(
        self, tmp_path: Path, ext: str
    ) -> None:
        target = tmp_path / f"clip.{ext}"
        try:
            if ext in {"m4a", "mp3", "wav"}:
                media_fixtures.make_audio_only_clip(target, duration=1.5)
            else:
                media_fixtures.make_tone_clip(target, duration=1.5)
        except RuntimeError as exc:
            pytest.skip(f"encoder for .{ext} is not available: {exc}")

        duration = media.probe_media(target)
        assert duration == pytest.approx(1.5, abs=0.15)

        output_dir = tmp_path / "out"
        output_dir.mkdir()
        wav_path = media.extract_audio(target, output_dir)
        assert wav_path.exists()

    def test_video_only_file_raises_no_audio_track(self, media_dir: Path) -> None:
        with pytest.raises(
            MediaError, match=r"^No audio track found in silent-video\.mp4\.$"
        ):
            media.probe_media(media_dir / "silent-video.mp4")

    def test_garbage_bytes_raise_unreadable(self, media_dir: Path) -> None:
        with pytest.raises(
            MediaError, match=r"^Can't read garbage\.mov as audio or video\.$"
        ):
            media.probe_media(media_dir / "garbage.mov")

    def test_ignores_the_file_extension(self, tmp_path: Path) -> None:
        """Content decides, not the extension: real audio behind a .mov name."""
        target = tmp_path / "actually-audio.mov"
        media_fixtures.make_audio_only_clip(target, duration=1.0)

        duration = media.probe_media(target)

        assert duration == pytest.approx(1.0, abs=0.1)


@media_fixtures.requires_ffmpeg
class TestExtractAudio:
    """Scenarios 5-8: WAV format, multi-track default, unusual filenames."""

    def test_extracts_16k_mono_pcm_wav(self, media_dir: Path, tmp_path: Path) -> None:
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        wav_path = media.extract_audio(media_dir / "tone.mp4", output_dir)

        assert wav_path.parent == output_dir.resolve()
        assert wav_path.suffix == ".wav"
        info = _ffprobe_json(wav_path)
        stream = info["streams"][0]
        assert stream["codec_name"] == "pcm_s16le"
        assert stream["sample_rate"] == "16000"
        assert stream["channels"] == 1
        assert float(info["format"]["duration"]) == pytest.approx(3.0, abs=0.15)

    def test_extracts_default_stream_from_multi_track_file(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "multitrack.mkv"
        media_fixtures.make_multi_track_clip(target, duration=1.0)
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        wav_path = media.extract_audio(target, output_dir)

        assert wav_path.exists()
        info = _ffprobe_json(wav_path)
        assert info["streams"][0]["codec_type"] == "audio"
        assert info["streams"][0]["channels"] == 1

    @pytest.mark.parametrize(
        "filename",
        [
            "name with spaces & $(echo x).mp4",
            "-leading.mp4",
            "unicode-ñamé-日本語.mp4",
            "'quoted' \"name\".mp4",
        ],
    )
    def test_handles_unusual_filenames(
        self, tmp_path: Path, filename: str, capfd: pytest.CaptureFixture[str]
    ) -> None:
        target = tmp_path / filename
        media_fixtures.make_tone_clip(target, duration=1.0)

        duration = media.probe_media(target)
        assert duration == pytest.approx(1.0, abs=0.1)

        output_dir = tmp_path / "out"
        output_dir.mkdir()
        wav_path = media.extract_audio(target, output_dir)
        assert wav_path.exists()

        captured = capfd.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_failure_raises_media_error_with_one_line_reason(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "garbage.mov"
        media_fixtures.make_garbage_file(target)
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        with pytest.raises(MediaError, match=r"Can't extract audio from garbage\.mov"):
            media.extract_audio(target, output_dir)


@media_fixtures.requires_ffmpeg
class TestTerminalHygiene:
    """Scenario 9: nothing from FFmpeg reaches stdout or stderr."""

    def test_no_output_across_success_and_failure_calls(
        self, media_dir: Path, tmp_path: Path, capfd: pytest.CaptureFixture[str]
    ) -> None:
        media.probe_media(media_dir / "tone.mp4")
        with pytest.raises(MediaError):
            media.probe_media(media_dir / "silent-video.mp4")
        with pytest.raises(MediaError):
            media.probe_media(media_dir / "garbage.mov")

        output_dir = tmp_path / "out"
        output_dir.mkdir()
        media.extract_audio(media_dir / "tone.mp4", output_dir)

        captured = capfd.readouterr()
        assert captured.out == ""
        assert captured.err == ""


@media_fixtures.requires_ffmpeg
class TestCancellation:
    """Scenario 10: an interrupt kills FFmpeg and propagates unchanged."""

    def test_interrupt_kills_ffmpeg_within_two_seconds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pid_file = tmp_path / "pid.txt"
        fake_bin = tmp_path / "fakebin"
        fake_bin.mkdir()
        fake_ffmpeg = fake_bin / "ffmpeg"
        fake_ffmpeg.write_text(
            f"#!/bin/bash\necho $$ > {shlex.quote(str(pid_file))}\nsleep 30\n"
        )
        fake_ffmpeg.chmod(0o755)
        monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

        def _raise_keyboard_interrupt(signum: int, frame: object) -> None:
            raise KeyboardInterrupt

        original_handler = signal.signal(signal.SIGALRM, _raise_keyboard_interrupt)
        signal.setitimer(signal.ITIMER_REAL, 0.5)
        start = time.monotonic()
        try:
            with pytest.raises(KeyboardInterrupt):
                media.extract_audio(tmp_path / "input.mp4", tmp_path)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, original_handler)

        assert pid_file.exists(), "fake ffmpeg never started"
        pid = int(pid_file.read_text().strip())

        deadline = start + 2.0
        while time.monotonic() < deadline and _pid_alive(pid):
            time.sleep(0.05)

        assert not _pid_alive(pid), "fake ffmpeg child was not killed within 2 s"
