"""Integration tests: `subsync generate` from argv to the written file.

Real FFmpeg on clips generated at test time, the real processor, output
planner and writer, and the real CLI through `main(argv)`. Only the Whisper
transcriber is replaced, at its module boundary, by a stand-in returning a
stored transcript. Scenario numbers (I1-I18) refer to "Task S1.7" in
`spec/tasks/slice-1-local-file-srt.tasks.md`.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from media_fixtures import make_tone_clip, make_video_only_clip, requires_ffmpeg
from srt_invariants import assert_valid_srt
from transcriber_stand_in import StandInTranscriber
from transcript_fixtures import EPISODE_WITH_URL, NO_SEGMENTS, URL, load_transcript

from subsync import cli, media, pipeline
from subsync.errors import ModelDownloadError, ModelMemoryError, TranscriptionError
from subsync.models import (
    ComplianceReport,
    Subtitle,
    TranscriptionResult,
    TranscriptionSegment,
    Word,
)

pytestmark = requires_ffmpeg

ML_MODULES = ("torch", "whisper", "yt_dlp")


@pytest.fixture(scope="module")
def tone_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One 3 s tone clip (color video and sine audio) for the whole module."""
    return make_tone_clip(tmp_path_factory.mktemp("media") / "tone.mp4")


@pytest.fixture
def videos(tmp_path: Path) -> Path:
    """The folder holding the input clip, where outputs land by default."""
    folder = tmp_path / "videos"
    folder.mkdir()
    return folder


@pytest.fixture
def tone(videos: Path, tone_template: Path) -> Path:
    """A fresh copy of the tone clip, `videos/tone.mp4`."""
    return Path(shutil.copy(tone_template, videos / "tone.mp4"))


@pytest.fixture
def stand_in(monkeypatch: pytest.MonkeyPatch) -> StandInTranscriber:
    """The stand-in transcriber, returning the episode with a 49-char URL."""
    return StandInTranscriber(load_transcript(EPISODE_WITH_URL)).install(monkeypatch)


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    """Run the CLI in-process; return the exit code, stdout and stderr."""
    rc = cli.main(argv)
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def leftovers(run_tmpdir: Path) -> list[str]:
    """Names of `subsync_*` temp folders left in the run's temp folder."""
    return sorted(p.name for p in run_tmpdir.iterdir() if p.name.startswith("subsync_"))


def long_word_transcript(count: int) -> TranscriptionResult:
    """A transcript with `count` subtitles, each flagged for a long word."""
    segments = []
    for n in range(count):
        start = n * 3.0
        word = f"example.com/{n}/" + "x" * 40
        segments.append(
            TranscriptionSegment(
                id=n,
                start=start,
                end=start + 2.0,
                text=f" See {word}",
                words=[
                    Word(word=" See", start=start, end=start + 0.5),
                    Word(word=f" {word}", start=start + 0.5, end=start + 2.0),
                ],
            )
        )
    return TranscriptionResult(language="en", duration=count * 3.0, segments=segments)


# I1, I16
def test_success_writes_a_valid_file_next_to_the_input(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out, err = run(["generate", str(tone)], capsys)

    output = videos / "tone.en.srt"
    assert rc == 0
    assert_valid_srt(output.read_bytes())
    assert out.splitlines()[0] == "✓ Subtitles written, 1 to review"
    assert f"  File:      {output}" in out
    assert "  Source:    tone.mp4 · 0:03" in out
    assert "  Language:  English (auto-detected)" in out
    assert "  Model:     turbo on CPU · " in out
    assert "  Subtitles: 11" in out
    assert "    00:00:21  " in out and "  long word" in out
    assert (
        "  Next: YouTube Studio → Subtitles → your video → Add → Upload file"
        " → With timing"
    ) in out
    stages = [
        "tone.mp4 · 0:03 · local file",
        "✓ Extracted audio",
        "✓ Loaded model turbo on CPU",
        "  Transcribing 0:03 of audio…",
        "✓ Transcribed",
        "  Language: English (auto-detected)",
        "✓ Formatted 8 segments → 11 subtitles",
        "✓ Wrote subtitles",
    ]
    positions = [err.index(stage) for stage in stages]
    assert positions == sorted(positions)
    assert "Downloading model" not in err
    assert "File:" not in err and "✓ Subtitles written" not in err
    assert "Extracted audio" not in out and "✗" not in err
    assert leftovers(run_tmpdir) == []


def test_file_route_opens_no_network_connections(
    tone: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """R4: with the model cached, nothing on the file route uses the network."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)

    rc, _, err = run(["generate", str(tone)], capsys)

    assert rc == 0, err


# I2
def test_language_set_with_l(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out, err = run(["generate", str(tone), "-l", "en"], capsys)

    assert rc == 0
    assert "  Language: English (set with -l)" in err
    assert "  Language:  English (set with -l)" in out
    assert [call[1].language for call in stand_in.transcribe_calls] == ["en"]
    assert (videos / "tone.en.srt").exists()


# I3
def test_second_run_fails_fast_without_extracting_or_loading(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["generate", str(tone)], capsys)[0] == 0
    output = videos / "tone.en.srt"
    before = output.read_bytes()
    stand_in.load_calls.clear()
    stand_in.transcribe_calls.clear()
    extract = Mock(wraps=media.extract_audio)
    monkeypatch.setattr(media, "extract_audio", extract)

    started = time.monotonic()
    rc, out, err = run(["generate", str(tone)], capsys)
    elapsed = time.monotonic() - started

    assert rc == 5
    assert out == ""
    assert err.splitlines() == [
        "✗ tone.en.srt already exists.",
        "  Re-run with --force to replace it, or choose another path with -o.",
    ]
    assert stand_in.load_calls == [] and stand_in.transcribe_calls == []
    assert extract.call_count == 0
    assert output.read_bytes() == before
    assert elapsed < 1.0


# I4
def test_auto_language_refuses_when_another_language_file_exists(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (videos / "tone.de.srt").write_text("1\n", encoding="utf-8")

    rc, out, err = run(["generate", str(tone)], capsys)

    assert rc == 5
    assert "✗ tone.de.srt already exists." in err
    assert stand_in.load_calls == []


# I5
def test_force_replaces_the_existing_file(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = videos / "tone.en.srt"
    output.write_text("hand-corrected\n", encoding="utf-8")

    rc, _, err = run(["generate", str(tone), "--force"], capsys)

    assert rc == 0, err
    assert_valid_srt(output.read_bytes())
    assert URL in output.read_text(encoding="utf-8")


# I6
def test_output_folder(
    tone: Path,
    tmp_path: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    rc, out, _ = run(["generate", str(tone), "-o", f"{out_dir}/"], capsys)

    assert rc == 0
    assert f"  File:      {out_dir / 'tone.en.srt'}" in out
    assert_valid_srt((out_dir / "tone.en.srt").read_bytes())


def test_missing_output_folder_fails_before_any_work(
    tone: Path,
    tmp_path: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing"

    rc, out, err = run(["generate", str(tone), "-o", f"{missing}/"], capsys)

    assert rc == 5
    assert out == ""
    assert f"✗ Can't write to {missing}/: No such file or directory." in err
    assert not missing.exists()
    assert stand_in.load_calls == []


def test_output_extension_that_contradicts_the_format(
    tone: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out, err = run(["generate", str(tone), "-o", "x.vtt"], capsys)

    assert rc == 2
    assert out == ""
    assert "✗ Output name ends in .vtt but --format is srt." in err
    assert stand_in.load_calls == []


# I7
def test_video_without_audio(
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    capsys: pytest.CaptureFixture[str],
) -> None:
    clip = make_video_only_clip(videos / "silent.mp4")

    rc, out, err = run(["generate", str(clip)], capsys)

    assert rc == 2
    assert out == ""
    assert err.splitlines() == ["✗ No audio track found in silent.mp4."]
    assert stand_in.load_calls == []
    assert leftovers(run_tmpdir) == []


# I8
def test_no_speech_writes_nothing(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StandInTranscriber(load_transcript(NO_SEGMENTS)).install(monkeypatch)

    rc, out, err = run(["generate", str(tone)], capsys)

    assert rc == 4
    assert out == ""
    assert "✗ No speech found in tone.mp4, so nothing was written." in err
    assert "  If the language was misdetected, set it with -l en." in err
    assert sorted(p.name for p in videos.iterdir()) == ["tone.mp4"]
    assert leftovers(run_tmpdir) == []


# I9
@pytest.mark.parametrize(
    ("where", "error", "expected"),
    [
        (
            "load",
            ModelDownloadError(
                "Couldn't download model 'turbo': no route to host.",
                hint="An internet connection is needed once per model.",
            ),
            [
                "✗ Couldn't download model 'turbo': no route to host.",
                "  An internet connection is needed once per model.",
            ],
        ),
        (
            "load",
            ModelMemoryError(
                "Ran out of memory with model 'turbo'.",
                hint="Try a smaller one: -m small",
            ),
            [
                "✗ Ran out of memory with model 'turbo'.",
                "  Try a smaller one: -m small",
            ],
        ),
        (
            "transcribe",
            TranscriptionError(
                "Transcription failed: decoder crashed.",
                hint="Re-run with -v for details.",
            ),
            [
                "✗ Transcription failed: decoder crashed.",
                "  Re-run with -v for details.",
            ],
        ),
    ],
    ids=["F19", "F20", "F21"],
)
def test_transcription_failures(
    where: str,
    error: Exception,
    expected: list[str],
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StandInTranscriber(
        load_transcript(EPISODE_WITH_URL),
        load_error=error if where == "load" else None,
        transcribe_error=error if where == "transcribe" else None,
    ).install(monkeypatch)

    rc, out, err = run(["generate", str(tone)], capsys)

    assert rc == 4
    assert out == ""
    assert err.splitlines()[-2:] == expected
    assert not (videos / "tone.en.srt").exists()
    assert leftovers(run_tmpdir) == []


# I10
def test_download_notice_when_the_model_is_not_cached(
    tone: Path,
    run_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StandInTranscriber(load_transcript(EPISODE_WITH_URL), cached=False).install(
        monkeypatch
    )

    rc, _, err = run(["generate", str(tone), "-m", "small"], capsys)

    assert rc == 0
    notice = err.index("  Downloading model 'small' (one-time)…")
    assert notice < err.index("✓ Loaded model small on CPU")


# I11
def test_ctrl_c_during_transcription(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StandInTranscriber(
        load_transcript(EPISODE_WITH_URL), transcribe_error=KeyboardInterrupt()
    ).install(monkeypatch)

    rc, out, err = run(["generate", str(tone)], capsys)

    assert rc == 130
    assert out == ""
    assert err.splitlines()[-1] == "Cancelled. Nothing written."
    assert sorted(p.name for p in videos.iterdir()) == ["tone.mp4"]
    assert leftovers(run_tmpdir) == []


# I12
def test_ctrl_c_during_the_write(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def interrupt(fd: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "fsync", interrupt)

    rc, out, err = run(["generate", str(tone)], capsys)

    assert rc == 130
    assert out == ""
    assert err.splitlines()[-1] == "Cancelled. Nothing written."
    assert sorted(p.name for p in videos.iterdir()) == ["tone.mp4"]
    assert leftovers(run_tmpdir) == []


# I13
def test_missing_ffmpeg_fails_before_anything_else(
    tone: Path,
    tmp_path: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()
    monkeypatch.setenv("PATH", str(empty_bin))
    resolve = Mock(wraps=cli.resolve_input)
    monkeypatch.setattr(cli, "resolve_input", resolve)

    started = time.monotonic()
    rc, out, err = run(["generate", str(tone)], capsys)
    elapsed = time.monotonic() - started

    assert rc == 1
    assert out == ""
    assert err.splitlines() == [
        "✗ FFmpeg is required but wasn't found.",
        "  Install it with: brew install ffmpeg",
    ]
    assert resolve.call_count == 0
    assert stand_in.load_calls == []
    assert elapsed < 1.0


# I14
def test_structural_errors_change_only_the_headline(
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    real = pipeline.process_transcription

    def broken(
        result: TranscriptionResult, config: object = None
    ) -> tuple[list[Subtitle], ComplianceReport]:
        subtitles, report = real(result, config)  # type: ignore[arg-type]
        report.errors.append("Subtitle 2 overlaps subtitle 1")
        report.is_compliant = False
        return subtitles, report

    monkeypatch.setattr(pipeline, "process_transcription", broken)

    rc, out, _ = run(["generate", str(tone)], capsys)

    assert rc == 0
    assert out.splitlines()[0] == (
        "✗ Written but not compliant, please report with -v output"
    )
    assert (videos / "tone.en.srt").exists()


# I15
@pytest.mark.parametrize("verbose", [False, True], ids=["plain", "-v"])
def test_unexpected_error(
    verbose: bool,
    tone: Path,
    videos: Path,
    run_tmpdir: Path,
    stand_in: StandInTranscriber,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def explode(result: TranscriptionResult, config: object = None) -> None:
        raise ValueError("segment table is corrupt")

    monkeypatch.setattr(pipeline, "process_transcription", explode)
    argv = ["generate", str(tone)] + (["-v"] if verbose else [])

    rc, out, err = run(argv, capsys)

    assert rc == 1
    assert out == ""
    assert "✗ Something went wrong: segment table is corrupt." in err
    assert "  Re-run with -v and share the output." in err
    assert ("Traceback" in err) is verbose
    assert not (videos / "tone.en.srt").exists()
    assert leftovers(run_tmpdir) == []


# I17
@pytest.mark.parametrize("verbose", [False, True], ids=["plain", "-v"])
def test_flag_list_is_capped_at_five_unless_verbose(
    verbose: bool,
    tone: Path,
    run_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StandInTranscriber(long_word_transcript(8)).install(monkeypatch)
    argv = ["generate", str(tone)] + (["-v"] if verbose else [])

    rc, out, _ = run(argv, capsys)

    rows = [line for line in out.splitlines() if line.startswith("    00:")]
    assert rc == 0
    assert out.splitlines()[0] == "✓ Subtitles written, 8 to review"
    if verbose:
        assert len(rows) == 8
        assert "more (run with -v to list all)" not in out
    else:
        assert len(rows) == 5
        assert "    … 3 more (run with -v to list all)" in out
    times = [row.split()[0] for row in rows]
    assert times == sorted(times)
    assert all(row.endswith("  long word") for row in rows)
    assert all(len(row) <= 80 for row in rows)


def test_flag_previews_fit_a_narrow_terminal_but_paths_do_not_shrink(
    tone: Path,
    run_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    StandInTranscriber(long_word_transcript(2)).install(monkeypatch)
    monkeypatch.setenv("COLUMNS", "40")

    rc, out, _ = run(["generate", str(tone)], capsys)

    rows = [line for line in out.splitlines() if line.startswith("    00:")]
    assert rc == 0
    assert all(len(row) <= 40 for row in rows)
    assert all("…" in row for row in rows)
    assert str(tone.parent / "tone.en.srt") in out


# I18
@pytest.mark.parametrize("case", ["F11", "F6"])
def test_fast_paths_never_import_the_ml_stack(
    case: str, tone: Path, videos: Path, tmp_path: Path
) -> None:
    env = dict(os.environ)
    if case == "F11":
        (videos / "tone.en.srt").write_text("1\n", encoding="utf-8")
        argv = ["generate", str(tone), "-l", "en"]
        expected_rc = 5
    else:
        empty_bin = tmp_path / "bin"
        empty_bin.mkdir()
        env["PATH"] = str(empty_bin)
        argv = ["generate", str(tone)]
        expected_rc = 1
    code = (
        "import sys\n"
        "from subsync.cli import main\n"
        f"rc = main({argv!r})\n"
        f"print(rc, [m for m in {ML_MODULES!r} if m in sys.modules])\n"
    )

    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    elapsed = time.monotonic() - started

    assert result.stdout.strip() == f"{expected_rc} []", result.stderr
    assert elapsed < 1.0
