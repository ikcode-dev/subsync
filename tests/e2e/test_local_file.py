"""Opt-in end-to-end tests: real FFmpeg, real Whisper `tiny`, real CLI.

Run with `task test:e2e` (`uv run pytest -m e2e`). Skipped by default and
wherever macOS `say` or FFmpeg is missing. The first run downloads the
`tiny` model once (about 75 MB); after that the file route runs offline.
Scenario numbers (E1-E4) refer to "Task S1.7" in
`spec/tasks/slice-1-local-file-srt.tasks.md`.
"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from media_fixtures import make_speech_clip, requires_ffmpeg, requires_say
from srt_invariants import assert_valid_srt, parse_srt

from subsync import cli

pytestmark = [pytest.mark.e2e, requires_ffmpeg, requires_say]

SUBSYNC = Path(sys.executable).with_name("subsync")

SENTENCES = [
    "Hello and welcome back to the channel.",
    "Today we turn a local video file into subtitles.",
    "Everything runs on your own machine, so nothing is uploaded.",
    "At the end you get a file you can upload to YouTube Studio.",
]


@pytest.fixture(scope="module")
def talk_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A short English speech clip with a color video track, `talk.mp4`."""
    return make_speech_clip(tmp_path_factory.mktemp("speech") / "talk.mp4", SENTENCES)


@pytest.fixture(scope="module")
def long_talk_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A clip of roughly 90 s, long enough to interrupt mid-transcription."""
    return make_speech_clip(
        tmp_path_factory.mktemp("speech") / "long-talk.mp4", SENTENCES * 12
    )


@pytest.fixture
def talk(tmp_path: Path, talk_template: Path) -> Path:
    """A fresh copy of the speech clip in its own folder."""
    folder = tmp_path / "videos"
    folder.mkdir()
    return Path(shutil.copy(talk_template, folder / "talk.mp4"))


def subsync_env(tmp_dir: Path) -> dict[str, str]:
    """The environment for a `subsync` subprocess with its own temp folder."""
    env = dict(os.environ)
    env["TMPDIR"] = str(tmp_dir)
    return env


# E1
def test_generates_a_valid_srt_with_real_whisper(talk: Path, tmp_path: Path) -> None:
    run_tmp = tmp_path / "run-tmp"
    run_tmp.mkdir()

    result = subprocess.run(
        [str(SUBSYNC), "generate", str(talk), "-m", "tiny"],
        env=subsync_env(run_tmp),
        capture_output=True,
        text=True,
        timeout=600,
    )

    output = talk.with_name("talk.en.srt")
    assert result.returncode == 0, result.stderr
    data = output.read_bytes()
    assert_valid_srt(data)
    assert len(parse_srt(data)) >= 1
    assert "  Language:  English (auto-detected)" in result.stdout
    assert f"  File:      {output}" in result.stdout
    assert "FP16" not in result.stderr
    assert "%|" not in result.stderr and "\r" not in result.stderr
    assert "ffmpeg" not in result.stderr.lower()
    assert list(run_tmp.iterdir()) == []


# E2
def test_file_route_runs_with_every_connection_refused(
    talk: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from subsync import transcriber
    from subsync.models import TranscriptionConfig

    if not transcriber.is_model_cached("tiny"):
        transcriber.load_model(TranscriptionConfig(model_name="tiny"))

    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)

    rc = cli.main(["generate", str(talk), "-m", "tiny"])

    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert_valid_srt(talk.with_name("talk.en.srt").read_bytes())


# E3
def test_second_run_fails_fast(talk: Path, tmp_path: Path) -> None:
    run_tmp = tmp_path / "run-tmp"
    run_tmp.mkdir()
    env = subsync_env(run_tmp)
    command = [str(SUBSYNC), "generate", str(talk), "-m", "tiny"]
    first = subprocess.run(command, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    before = talk.with_name("talk.en.srt").read_bytes()

    started = time.monotonic()
    second = subprocess.run(command, env=env, capture_output=True, text=True)
    elapsed = time.monotonic() - started

    assert second.returncode == 5
    assert second.stdout == ""
    assert "✗ talk.en.srt already exists." in second.stderr
    assert talk.with_name("talk.en.srt").read_bytes() == before
    assert elapsed < 1.5


# E4
def test_ctrl_c_during_transcription(long_talk_template: Path, tmp_path: Path) -> None:
    folder = tmp_path / "videos"
    folder.mkdir()
    clip = Path(shutil.copy(long_talk_template, folder / "long-talk.mp4"))
    run_tmp = tmp_path / "run-tmp"
    run_tmp.mkdir()

    process = subprocess.Popen(
        [str(SUBSYNC), "generate", str(clip), "-m", "tiny"],
        env=subsync_env(run_tmp),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stderr is not None
    lines: list[str] = []
    for line in process.stderr:
        lines.append(line)
        if line.strip().startswith("Transcribing"):
            break
    else:
        process.wait(timeout=60)
        pytest.fail(f"never started transcribing: {''.join(lines)}")

    process.send_signal(signal.SIGINT)
    sent = time.monotonic()
    rc = process.wait(timeout=10)
    elapsed = time.monotonic() - sent
    lines.extend(process.stderr.read().splitlines(keepends=True))

    assert rc == 130, "".join(lines)
    assert elapsed <= 2.0
    assert lines[-1].strip() == "Cancelled. Nothing written."
    assert sorted(p.name for p in folder.iterdir()) == ["long-talk.mp4"]
    assert list(run_tmp.iterdir()) == []
