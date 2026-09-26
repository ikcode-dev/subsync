"""Tests for the `subsync` CLI shell: arguments, error boundary, exit codes.

Scenario numbers refer to the table in "Task S1.6" of
`spec/tasks/slice-1-local-file-srt.tasks.md`. Scenario 14 (catalog drift
against installed Whisper) lives in `tests/test_catalog.py`.

`run_generate` is the seam S1.7 fills in; scenarios 10-12 replace it with a
stand-in to test the error boundary in `main` independently of input
resolution.
"""

import logging
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from subsync import catalog, cli
from subsync.errors import (
    AgeRestrictedError,
    DependencyError,
    InputError,
    LiveStreamError,
    MediaError,
    ModelDownloadError,
    ModelMemoryError,
    NoSpeechError,
    OutputError,
    OutputExistsError,
    SourceUnavailableError,
    SubSyncError,
    TranscriptionError,
    URLParseError,
    VideoUnavailableError,
)


@pytest.fixture(autouse=True)
def _isolate_root_logging() -> Iterator[None]:
    """Undo `main`'s `logging.basicConfig(..., force=True)` after each test.

    `main` reconfigures the *root* logger on every call so that `-v` turns
    on DEBUG logging in the real CLI process. In-process tests share that
    same root logger across the whole pytest session, so without this
    reset a `-v` test would leave DEBUG (and a `StreamHandler` bound to
    that test's now-torn-down `capsys` stream) in place for every test
    that runs after it. See `TestVerboseLoggingIsolation` below for a
    regression test that fails without this fixture.

    Refs: S1.6-Q5
    """
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    try:
        yield
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)


# Scenario 1
class TestVersion:
    """`--version` prints the package version and exits 0."""

    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cli.main(["--version"])

        captured = capsys.readouterr()
        assert rc == 0
        assert captured.out.strip() == "subsync 0.1.0"


# Scenario 2
class TestUsage:
    """Bare `subsync`, and `generate` without INPUT, print usage and exit 2."""

    def test_bare_subsync(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cli.main([])

        captured = capsys.readouterr()
        assert rc == 2
        assert "usage:" in captured.err
        assert captured.out == ""

    def test_generate_without_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cli.main(["generate"])

        captured = capsys.readouterr()
        assert rc == 2
        assert "usage:" in captured.err
        assert captured.out == ""


# Scenario 3
class TestUnknownOption:
    """An unrecognized option is an argparse usage error (F1)."""

    def test_bogus_option(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cli.main(["generate", "x", "--bogus"])

        captured = capsys.readouterr()
        assert rc == 2
        assert "usage:" in captured.err
        assert "--bogus" in captured.err
        assert captured.out == ""


# Scenario 4
class TestUnknownLanguage:
    """`-l xx` is F2: message and hint, exit 2."""

    def test_unknown_language_code(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cli.main(["generate", "missing.mov", "-l", "xx"])

        captured = capsys.readouterr()
        assert rc == 2
        assert captured.out == ""
        assert "✗ Unknown language code 'xx'." in captured.err
        assert "Use a code such as en, pl, de." in captured.err


# Scenario 5
class TestUnknownModel:
    """`-m banana` is F3: message and a hint listing the valid names, exit 2."""

    def test_unknown_model_name(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cli.main(["generate", "missing.mov", "-m", "banana"])

        captured = capsys.readouterr()
        assert rc == 2
        assert captured.out == ""
        assert "✗ Unknown model 'banana'." in captured.err
        for name in catalog.MODEL_NAMES:
            assert name in captured.err


# Scenario 6
class TestFormatChoice:
    """`-f vtt` is rejected: VTT arrives in S5, only `srt` is valid in S1."""

    def test_vtt_is_not_a_valid_choice(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = cli.main(["generate", "missing.mov", "-f", "vtt"])

        captured = capsys.readouterr()
        assert rc == 2
        assert "invalid choice" in captured.err
        assert captured.out == ""


# Scenario 7
class TestInputNotFileOrUrl:
    """A missing path that isn't a URL either is F7, exit 2."""

    def test_missing_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cli.main(["generate", "foo"])

        captured = capsys.readouterr()
        assert rc == 2
        assert captured.out == ""
        assert "✗ 'foo' is not a file or a supported YouTube URL." in captured.err
        assert "subsync generate" in captured.err


# Scenario 8
class TestInputIsFolder:
    """A folder INPUT is F8, exit 2."""

    def test_folder_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clips = tmp_path / "clips"
        clips.mkdir()

        rc = cli.main(["generate", str(clips)])

        captured = capsys.readouterr()
        assert rc == 2
        assert captured.out == ""
        assert "is a folder, not a media file." in captured.err


# Scenario 9
class TestYoutubeUrlIsInterim:
    """A YouTube URL is recognized but not yet supported, exit 2."""

    def test_youtube_url(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = cli.main(["generate", "https://youtu.be/dQw4w9WgXcQ"])

        captured = capsys.readouterr()
        assert rc == 2
        assert captured.out == ""
        assert "✗ YouTube links aren't supported yet." in captured.err
        assert "subsync generate <file>" in captured.err


# Scenario 10
SEAM_ERRORS: list[tuple[SubSyncError, int]] = [
    (InputError("Bad input.", hint="Fix it."), 2),
    (URLParseError("Bad URL.", hint="Fix it."), 2),
    (MediaError("Bad media.", hint="Fix it."), 2),
    (DependencyError("No FFmpeg.", hint="brew install ffmpeg"), 1),
    (SourceUnavailableError("No source.", hint="Try later."), 3),
    (VideoUnavailableError("Private video.", hint="Export it."), 3),
    (AgeRestrictedError("Age-restricted.", hint="Export it."), 3),
    (LiveStreamError("Still live.", hint="Try later."), 3),
    (TranscriptionError("Transcription failed.", hint="Re-run with -v."), 4),
    (ModelDownloadError("Download failed.", hint="Check network."), 4),
    (ModelMemoryError("Out of memory.", hint="Try -m small."), 4),
    (NoSpeechError("No speech found.", hint="Try -l en."), 4),
    (OutputError("Can't write.", hint="Check permissions."), 5),
    (OutputExistsError("Already exists.", hint="Use --force."), 5),
]


class TestSeamErrorBoundary:
    """Every S1.1 error category maps to its exit code; stdout stays empty."""

    @pytest.mark.parametrize(
        ("err", "exit_code"),
        SEAM_ERRORS,
        ids=[type(err).__name__ for err, _ in SEAM_ERRORS],
    )
    def test_maps_to_exit_code_and_prints_hint(
        self,
        err: SubSyncError,
        exit_code: int,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def raise_it(args: object) -> int:
            raise err

        monkeypatch.setattr(cli, "run_generate", raise_it)

        rc = cli.main(["generate", "x"])

        captured = capsys.readouterr()
        assert rc == exit_code
        assert rc == err.exit_code
        assert captured.out == ""
        assert captured.err.splitlines()[0] == f"✗ {err}"
        assert err.hint is not None
        assert f"  {err.hint}" in captured.err


# Scenario 11
class TestSeamKeyboardInterrupt:
    """Ctrl+C during the seam exits 130 and writes nothing."""

    def test_keyboard_interrupt_exits_130(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def raise_it(args: object) -> int:
            raise KeyboardInterrupt

        monkeypatch.setattr(cli, "run_generate", raise_it)

        rc = cli.main(["generate", "x"])

        captured = capsys.readouterr()
        assert rc == 130
        assert captured.out == ""
        assert captured.err.strip() == "Cancelled. Nothing written."


# Scenario 12
class TestSeamUnexpectedException:
    """An unmapped exception is F25: exit 1, traceback only with -v."""

    def test_no_traceback_without_verbose(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def raise_it(args: object) -> int:
            raise ValueError("x")

        monkeypatch.setattr(cli, "run_generate", raise_it)

        rc = cli.main(["generate", "input"])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.out == ""
        assert "Traceback" not in captured.err
        assert "✗ Something went wrong: x." in captured.err
        assert "Re-run with -v and share the output." in captured.err

    def test_traceback_with_verbose(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def raise_it(args: object) -> int:
            raise ValueError("x")

        monkeypatch.setattr(cli, "run_generate", raise_it)

        rc = cli.main(["generate", "input", "-v"])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.out == ""
        assert "Traceback" in captured.err
        assert "✗ Something went wrong: x." in captured.err
        # The traceback comes before the ✗ block.
        assert captured.err.index("Traceback") < captured.err.index("✗ Something")


class TestSeamSubSyncErrorTraceback:
    """`-v` also prints a `SubSyncError`'s traceback, including its cause.

    R20, and F21's "Re-run with -v for details" hint, depend on `-v`
    surfacing the underlying failure for a chained `SubSyncError` (e.g.
    S1.5's `raise TranscriptionError(...) from exc`), not only for the
    catch-all F25 branch.

    Refs: S1.6-Q1
    """

    @staticmethod
    def _raise_chained(args: object) -> int:
        try:
            raise ValueError("underlying decode failure")
        except ValueError as exc:
            raise TranscriptionError(
                "Transcription failed: underlying decode failure.",
                hint="Re-run with -v for details.",
            ) from exc

    def test_no_traceback_without_verbose(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(cli, "run_generate", self._raise_chained)

        rc = cli.main(["generate", "input"])

        captured = capsys.readouterr()
        assert rc == 4
        assert captured.out == ""
        assert "Traceback" not in captured.err
        assert "✗ Transcription failed: underlying decode failure." in captured.err

    def test_traceback_and_cause_with_verbose(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(cli, "run_generate", self._raise_chained)

        rc = cli.main(["generate", "input", "-v"])

        captured = capsys.readouterr()
        assert rc == 4
        assert captured.out == ""
        assert "Traceback" in captured.err
        assert "underlying decode failure" in captured.err
        assert "✗ Transcription failed: underlying decode failure." in captured.err
        # The traceback (and its chained cause) come before the ✗ block.
        assert captured.err.index("Traceback") < captured.err.index("✗ Transcription")


class TestVerboseLoggingIsolation:
    """`-v` turns on DEBUG logging to stderr; without it, none appears.

    Refs: S1.6-Q3, S1.6-Q5
    """

    def test_verbose_shows_debug_records(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"fake")

        cli.main(["generate", str(video), "-v"])

        captured = capsys.readouterr()
        assert "DEBUG" in captured.err
        assert logging.getLogger().level == logging.DEBUG

    def test_root_level_is_restored_before_this_test(self) -> None:
        """Proves `_isolate_root_logging` undoes the previous test's `-v`.

        Depends on running after `test_verbose_shows_debug_records` above
        (default, in-file pytest order); fails without the autouse fixture,
        since `main` would otherwise leave the root logger at DEBUG.
        """
        assert logging.getLogger().level != logging.DEBUG

    def test_without_verbose_no_debug_records(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"fake")

        cli.main(["generate", str(video)])

        captured = capsys.readouterr()
        assert "DEBUG" not in captured.err


class TestSummarizeUnexpectedException:
    """The F25 one-line summary never doubles a period or ends up blank.

    Refs: S1.6-Q6
    """

    def test_trailing_period_is_not_doubled(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def raise_it(args: object) -> int:
            raise ValueError("bad value.")

        monkeypatch.setattr(cli, "run_generate", raise_it)

        cli.main(["generate", "x"])

        captured = capsys.readouterr()
        assert "✗ Something went wrong: bad value.." not in captured.err
        assert "✗ Something went wrong: bad value." in captured.err

    def test_leading_blank_line_is_skipped(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def raise_it(args: object) -> int:
            raise ValueError("\nfoo")

        monkeypatch.setattr(cli, "run_generate", raise_it)

        cli.main(["generate", "x"])

        captured = capsys.readouterr()
        assert "✗ Something went wrong: foo." in captured.err

    def test_blank_message_falls_back_to_class_name(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def raise_it(args: object) -> int:
            raise RuntimeError("   ")

        monkeypatch.setattr(cli, "run_generate", raise_it)

        cli.main(["generate", "x"])

        captured = capsys.readouterr()
        assert "✗ Something went wrong: RuntimeError." in captured.err


# Scenario 13
class TestFastStartup:
    """Running a stage 0/1 failure must not import the ML stack."""

    def test_no_ml_imports_in_subprocess(self) -> None:
        script = (
            "import sys\n"
            "from subsync.cli import main\n"
            "main(['generate', 'missing.mov'])\n"
            "print(any(name in sys.modules "
            "for name in ('torch', 'whisper', 'yt_dlp')))\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert result.stdout.strip().splitlines()[-1] == "False"
