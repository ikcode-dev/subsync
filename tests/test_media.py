"""Integration tests for the media module, run against real FFmpeg.

Nothing about FFmpeg is mocked here except in the cancellation scenario,
where a fake ``ffmpeg`` script stands in so the interrupt timing is
deterministic and bounded. Clips are generated at test time with
``media_fixtures`` and are a few seconds long, so the whole module runs in
a few seconds.
"""

import json
import os
import re
import shlex
import signal
import subprocess
import sys
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


def _mean_volume_db(path: Path) -> float:
    """Measure a file's mean audio level in dB (test verification only)."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"mean_volume: (-?[\d.]+|-inf) dB", result.stderr)
    assert match, result.stderr
    return float(match.group(1))


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

    @pytest.mark.parametrize(
        ("filename", "container"),
        [("wav-inside.mp4", "wav"), ("no-extension", "mp3"), ("UPPER.MOV", "mov")],
    )
    def test_content_decides_not_the_extension(
        self, tmp_path: Path, filename: str, container: str
    ) -> None:
        """A WAV named .mp4, an MP3 with no extension, an upper-case .MOV."""
        target = tmp_path / filename
        media_fixtures.make_audio_only_clip(target, duration=1.0, container=container)

        assert media.probe_media(target) == pytest.approx(1.0, abs=0.1)
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        assert media.extract_audio(target, output_dir).exists()

    @pytest.mark.parametrize(
        ("filename", "container"),
        [("piped.webm", "webm"), ("piped.mkv", "matroska")],
    )
    def test_file_without_duration_metadata(
        self, tmp_path: Path, filename: str, container: str
    ) -> None:
        """A recording written to a pipe has no duration; its packets do."""
        target = media_fixtures.make_piped_clip(tmp_path / filename, container)
        assert "duration" not in _ffprobe_json(target)["format"]

        assert media.probe_media(target) == pytest.approx(3.0, abs=0.1)


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
        # The default stream is the first, audible track, not the silent one.
        assert _mean_volume_db(wav_path) > -60.0

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

    def test_relative_leading_dash_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A relative `-name` is never parsed as an FFmpeg option."""
        media_fixtures.make_tone_clip(tmp_path / "-leading.mp4", duration=1.0)
        monkeypatch.chdir(tmp_path)
        output_dir = Path("out")
        output_dir.mkdir()

        assert media.probe_media(Path("-leading.mp4")) == pytest.approx(1.0, abs=0.1)
        assert media.extract_audio(Path("-leading.mp4"), output_dir).exists()

    def test_failure_raises_media_error_with_one_line_reason(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "garbage.mov"
        media_fixtures.make_garbage_file(target)
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        with pytest.raises(
            MediaError, match=r"Can't extract audio from garbage\.mov"
        ) as exc_info:
            media.extract_audio(target, output_dir)

        assert "\n" not in str(exc_info.value)


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

    def test_nothing_reaches_the_terminal_in_a_plain_process(
        self, media_dir: Path, tmp_path: Path
    ) -> None:
        """Without pytest's log capture, FFmpeg's output still stays hidden.

        Python's last-resort handler prints any WARNING or above to stderr, so
        this fails if FFmpeg's output is logged above DEBUG.
        """
        code = (
            "import sys\n"
            "from pathlib import Path\n"
            "from subsync import media\n"
            "from subsync.errors import MediaError\n"
            "base, out = Path(sys.argv[1]), Path(sys.argv[2])\n"
            "media.probe_media(base / 'tone.mp4')\n"
            "for name in ('silent-video.mp4', 'garbage.mov'):\n"
            "    try:\n"
            "        media.probe_media(base / name)\n"
            "    except MediaError:\n"
            "        pass\n"
            "media.extract_audio(base / 'tone.mp4', out)\n"
            "try:\n"
            "    media.extract_audio(base / 'garbage.mov', out)\n"
            "except MediaError:\n"
            "    pass\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code, str(media_dir), str(tmp_path)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert (result.stdout, result.stderr) == ("", "")

    def test_ffmpeg_never_reads_the_terminal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Keystrokes waiting on SubSync's stdin never reach FFmpeg."""
        marker = tmp_path / "stdin-seen.txt"
        fake_bin = tmp_path / "fakebin"
        fake_bin.mkdir()
        fake_ffmpeg = fake_bin / "ffmpeg"
        fake_ffmpeg.write_text(f"#!/bin/bash\ncat > {shlex.quote(str(marker))}\n")
        fake_ffmpeg.chmod(0o755)
        monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

        read_end, write_end = os.pipe()
        os.write(write_end, b"q\n")
        os.close(write_end)
        saved_stdin = os.dup(0)
        os.dup2(read_end, 0)
        try:
            with pytest.raises(MediaError):
                media.extract_audio(tmp_path / "input.mp4", tmp_path)
        finally:
            os.dup2(saved_stdin, 0)
            os.close(saved_stdin)
            os.close(read_end)

        assert marker.read_bytes() == b""


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


@media_fixtures.requires_ffmpeg
@media_fixtures.requires_say
def test_speech_clip_helper_makes_a_readable_clip(tmp_path: Path) -> None:
    """`make_speech_clip` (used by the e2e suite) produces a probeable clip."""
    clip = media_fixtures.make_speech_clip(tmp_path / "talk.mp4", ["Hello there."])

    assert media.probe_media(clip) > 0.3
    assert sorted(p.name for p in tmp_path.iterdir()) == ["talk.mp4"]
