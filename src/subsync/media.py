"""Local media inspection and audio extraction via FFmpeg.

Reads container and stream info with ``ffprobe`` and extracts a
Whisper-ready mono WAV with ``ffmpeg``. Every subprocess call passes an
absolute-path argument list — never through a shell — closes the child's
stdin so it can never read the terminal, and captures stdout/stderr so
nothing from FFmpeg is printed; FFmpeg's own stderr is logged at debug
level only. If the call is interrupted, the whole child process group is
killed before the interrupt propagates, so no FFmpeg process is ever left
running.
"""

import json
import logging
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any

from subsync.errors import DependencyError, MediaError

logger = logging.getLogger(__name__)

_FFMPEG = "ffmpeg"
_FFPROBE = "ffprobe"


def check_ffmpeg() -> None:
    """Verify that ``ffmpeg`` and ``ffprobe`` are both on ``PATH``.

    A pure ``PATH`` lookup: starts no subprocess and returns instantly.

    Raises:
        DependencyError: Either tool is missing from ``PATH``.
    """
    if shutil.which(_FFMPEG) is None or shutil.which(_FFPROBE) is None:
        raise DependencyError(
            "FFmpeg is required but wasn't found.",
            hint="Install it with: brew install ffmpeg",
        )


def probe_media(path: Path) -> float:
    """Read a local media file's duration and confirm it has an audio track.

    The file's actual content decides this, never its extension.

    Args:
        path: Path to the local file to inspect.

    Returns:
        Duration in seconds, read from the container and falling back to
        the audio stream when the container has none.

    Raises:
        DependencyError: FFmpeg/ffprobe are not on ``PATH``.
        MediaError: The file has no audio stream, or ffprobe can't read it
            as audio or video at all.
    """
    check_ffmpeg()
    path = Path(path)
    resolved = path.resolve()
    name = path.name

    result = _run(
        [
            _FFPROBE,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(resolved),
        ]
    )
    _log_stderr(_FFPROBE, result.stderr)

    info: dict[str, Any] | None = None
    if result.returncode == 0:
        try:
            info = json.loads(result.stdout)
        except (json.JSONDecodeError, UnicodeDecodeError):
            info = None

    streams = info.get("streams") if info else None
    if result.returncode != 0 or not streams:
        raise MediaError(f"Can't read {name} as audio or video.")

    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio_streams:
        raise MediaError(f"No audio track found in {name}.")

    fmt = info.get("format", {}) if info else {}
    duration = _parse_duration(fmt.get("duration"))
    if duration is None:
        duration = _parse_duration(audio_streams[0].get("duration"))
    if duration is None:
        # Files written to a pipe or never finalized (e.g. browser WebM
        # recordings) carry no duration anywhere; the last audio packet does.
        duration = _last_audio_packet_end(resolved)
    if duration is None:
        raise MediaError(f"Can't read {name} as audio or video.")

    return duration


def extract_audio(path: Path, output_dir: Path) -> Path:
    """Extract FFmpeg's default audio stream as a 16 kHz mono 16-bit PCM WAV.

    Multi-track files use FFmpeg's own default stream selection; there is
    no track selection.

    Args:
        path: Local media file to read.
        output_dir: Existing folder to write the WAV file into.

    Returns:
        Path to the extracted WAV file, inside ``output_dir``.

    Raises:
        DependencyError: FFmpeg/ffprobe are not on ``PATH``.
        MediaError: FFmpeg could not extract audio from the file.
    """
    check_ffmpeg()
    path = Path(path)
    resolved = path.resolve()
    name = path.name
    output_path = Path(output_dir).resolve() / f"{resolved.stem}.wav"

    result = _run(
        [
            _FFMPEG,
            "-nostdin",
            "-y",
            "-i",
            str(resolved),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-acodec",
            "pcm_s16le",
            str(output_path),
        ]
    )
    _log_stderr(_FFMPEG, result.stderr)

    if result.returncode != 0 or not output_path.exists():
        reason = _last_line(result.stderr) or "FFmpeg failed"
        raise MediaError(f"Can't extract audio from {name}: {reason}.")

    return output_path


def _last_audio_packet_end(resolved: Path) -> float | None:
    """Read where the first audio stream's last packet ends (demux only).

    Returns:
        The end time in seconds, or ``None`` if no packet has a timestamp.
    """
    result = _run(
        [
            _FFPROBE,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "packet=pts_time,duration_time",
            "-of",
            "csv=p=0",
            str(resolved),
        ]
    )
    _log_stderr(_FFPROBE, result.stderr)
    if result.returncode != 0:
        return None
    lines = result.stdout.decode("utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        fields = [field for field in line.split(",") if field]
        pts = _parse_duration(fields[0]) if fields else None
        if pts is None:
            continue
        length = _parse_duration(fields[1]) if len(fields) > 1 else None
        return pts + (length or 0.0)
    return None


def _run(cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Run an FFmpeg/ffprobe command safely and return its result.

    stdin is closed so the child can never read the terminal; stdout and
    stderr are always captured, never printed. The child runs in its own
    process group, and on interrupt (or any other exception raised while
    waiting for it) that whole group is killed before the exception
    propagates unchanged, so no FFmpeg process is ever left running.
    """
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate()
    except BaseException:
        _kill_process_group(process)
        process.wait()
        raise
    return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    """Kill the process group the child was started in, ignoring races."""
    try:
        pgid = os.getpgid(process.pid)
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _log_stderr(tool: str, stderr: bytes) -> None:
    """Send captured FFmpeg/ffprobe stderr to debug logging only."""
    if stderr:
        logger.debug(
            "%s stderr:\n%s", tool, stderr.decode("utf-8", errors="replace").strip()
        )


def _last_line(data: bytes) -> str:
    """Return the last non-blank line of decoded output, or an empty string."""
    text = data.decode("utf-8", errors="replace").strip()
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _parse_duration(value: Any) -> float | None:
    """Parse an ffprobe duration field, or ``None`` if missing/unparsable."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
