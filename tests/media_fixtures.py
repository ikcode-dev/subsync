"""Test media generated at test time with FFmpeg's built-in sources.

Shared with S1.7 (integration and end-to-end tests). Every helper renders
directly to the given path with real FFmpeg or macOS ``say`` — nothing here
mocks either tool — and clips default to a few seconds so a whole test file
using them stays fast. Import it as ``media_fixtures`` (pytest adds ``tests``
to ``sys.path``).

Skip markers:
    requires_ffmpeg: Skip when ``ffmpeg``/``ffprobe`` are not on ``PATH``.
    requires_say: Skip when macOS ``say`` is not on ``PATH``.
"""

import logging
import random
import shutil
import subprocess
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

DEFAULT_DURATION = 3.0

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg is not installed",
)

requires_say = pytest.mark.skipif(
    shutil.which("say") is None,
    reason="macOS `say` is not installed",
)


def _run(cmd: list[str]) -> None:
    """Run a fixture-generation command, raising with its stderr on failure."""
    result = subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"fixture generation failed ({cmd[0]}): {result.stderr.strip()}"
        )


def _ffmpeg(args: list[str]) -> None:
    """Run FFmpeg with ``args``, overwriting any existing output silently."""
    _run(["ffmpeg", "-nostdin", "-y", *args])


def make_tone_clip(path: Path, duration: float = DEFAULT_DURATION) -> Path:
    """Render a sine-wave tone with a solid-color video track.

    The container/codec is picked from ``path``'s extension.

    Args:
        path: Destination file path, e.g. ``tone.mp4``.
        duration: Clip length in seconds.

    Returns:
        ``path``, once written.
    """
    _ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"color=c=blue:s=64x64:d={duration}",
            "-shortest",
            str(path),
        ]
    )
    return path


def make_audio_only_clip(
    path: Path, duration: float = DEFAULT_DURATION, container: str | None = None
) -> Path:
    """Render a sine-wave tone with no video track.

    Args:
        path: Destination file path, e.g. ``audio.wav`` or ``audio.mp3``.
        duration: Clip length in seconds.
        container: FFmpeg muxer to force (e.g. ``"wav"``), so the content can
            differ from what the file's extension suggests. By default the
            muxer follows the extension.

    Returns:
        ``path``, once written.
    """
    muxer = ["-f", container] if container else []
    _ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            *muxer,
            str(path),
        ]
    )
    return path


def make_piped_clip(
    path: Path, container: str = "webm", duration: float = DEFAULT_DURATION
) -> Path:
    """Render a tone through a pipe, so the file carries no duration metadata.

    Like a browser's MediaRecorder WebM or an unfinalized MKV: neither the
    container nor the stream reports a duration.

    Args:
        path: Destination file path, e.g. ``piped.webm``.
        container: ``"webm"`` (Opus audio) or ``"matroska"`` (AAC audio and
            an MPEG-4 video track).
        duration: Clip length in seconds.

    Returns:
        ``path``, once written.
    """
    if container == "webm":
        args = ["-f", "lavfi", "-i", f"sine=d={duration}", "-c:a", "libopus"]
    else:
        args = [
            "-f",
            "lavfi",
            "-i",
            f"sine=d={duration}",
            "-f",
            "lavfi",
            "-i",
            f"color=c=red:s=64x64:d={duration}",
            "-c:a",
            "aac",
            "-c:v",
            "mpeg4",
        ]
    with path.open("wb") as handle:
        result = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", *args, "-f", container, "-"],
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.PIPE,
            text=False,
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"fixture generation failed (ffmpeg): {result.stderr.decode().strip()}"
        )
    return path


def make_video_only_clip(path: Path, duration: float = DEFAULT_DURATION) -> Path:
    """Render a solid-color video clip with no audio track.

    Args:
        path: Destination file path, e.g. ``silent-video.mp4``.
        duration: Clip length in seconds.

    Returns:
        ``path``, once written.
    """
    _ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c=red:s=64x64:d={duration}",
            str(path),
        ]
    )
    return path


def make_multi_track_clip(
    path: Path, duration: float = DEFAULT_DURATION, track_count: int = 2
) -> Path:
    """Render several mono audio tracks, no video: a tone, then silence.

    The first track is a 440 Hz tone and every other track is silent, so a
    test can tell which track was extracted. All tracks are mono, so FFmpeg's
    default stream selection picks the first one.

    Args:
        path: Destination file path, e.g. ``multitrack.mkv``.
        duration: Clip length in seconds.
        track_count: Number of audio tracks to mux.

    Returns:
        ``path``, once written.
    """
    args: list[str] = ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
    for _ in range(track_count - 1):
        args += [
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=mono:sample_rate=44100:duration={duration}",
        ]
    for i in range(track_count):
        args += ["-map", f"{i}:a"]
    args.append(str(path))
    _ffmpeg(args)
    return path


def make_garbage_file(path: Path, size: int = 256) -> Path:
    """Write fixed pseudo-random, non-media bytes to ``path``.

    The bytes come from a seeded generator, so every run gets the same
    content: truly random bytes are occasionally detected by ffprobe as a
    text format (for example lyrics files starting with ``[``).

    Args:
        path: Destination file path, e.g. ``garbage.mov``.
        size: Number of bytes to write.

    Returns:
        ``path``, once written.
    """
    path.write_bytes(random.Random(0).randbytes(size))
    return path


def make_speech_clip(
    path: Path,
    sentences: list[str] | None = None,
    *,
    rate: int = 180,
    voice: str | None = None,
    video_size: str = "64x64",
) -> Path:
    """Render English speech with macOS ``say`` and mux it with a color video.

    Requires ``requires_say`` (speech) and ``requires_ffmpeg`` (muxing). The
    video track is unbounded and trimmed to the speech's length with
    ``-shortest``, so any spoken duration works without precomputing it.

    Args:
        path: Destination file path, e.g. ``talk.mp4``.
        sentences: Lines to speak, joined with a space and read once. For a
            longer clip (S1.7 needs ~60 s), pass a longer or repeated list.
        rate: Speech rate in words per minute, passed to ``say -r``.
        voice: Optional ``say`` voice name (``say -v``).
        video_size: Size of the color video track muxed alongside the speech.

    Returns:
        ``path``, once written.
    """
    if sentences is None:
        sentences = [
            "This is a test recording generated for SubSync.",
            "It exists only to exercise the transcription pipeline.",
        ]
    text = " ".join(sentences)

    aiff_path = path.with_suffix(".say.aiff")
    try:
        say_cmd = ["say", "-o", str(aiff_path), "-r", str(rate)]
        if voice:
            say_cmd += ["-v", voice]
        say_cmd.append(text)
        _run(say_cmd)

        _ffmpeg(
            [
                "-i",
                str(aiff_path),
                "-f",
                "lavfi",
                "-i",
                f"color=c=gray:s={video_size}",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(path),
            ]
        )
    finally:
        aiff_path.unlink(missing_ok=True)

    return path
