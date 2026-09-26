"""Tests for writer.py: SRT rendering and the one-step write."""

import errno
import os
import stat
import tempfile
from datetime import timedelta
from pathlib import Path

import pytest
from srt_invariants import assert_valid_srt

from subsync.errors import OutputError, OutputExistsError
from subsync.models import Subtitle
from subsync.writer import render_srt, write_output


def _subtitle(index: int, start_s: float, end_s: float, lines: list[str]) -> Subtitle:
    """Build a Subtitle from second offsets, for readable test data."""
    return Subtitle(
        index=index,
        start_time=timedelta(seconds=start_s),
        end_time=timedelta(seconds=end_s),
        text=" ".join(lines),
        lines=lines,
    )


class TestRenderSrt:
    """R16, E9: cue numbering, timestamp format, blank lines, trailing newline."""

    def test_golden_two_cues(self) -> None:
        subtitles = [
            _subtitle(1, 1.0, 4.0, ["Hello there."]),
            _subtitle(2, 3600.5, 3603.25, ["Second line one.", "Second line two."]),
        ]

        expected = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello there.\n"
            "\n"
            "2\n"
            "01:00:00,500 --> 01:00:03,250\n"
            "Second line one.\n"
            "Second line two.\n"
        )

        assert render_srt(subtitles) == expected

    def test_no_bom_and_no_carriage_returns(self) -> None:
        text = render_srt([_subtitle(1, 0.0, 1.0, ["Hi."])])

        assert not text.startswith("﻿")
        assert "\r" not in text

    def test_cue_numbers_follow_list_position_not_subtitle_index(self) -> None:
        subtitles = [_subtitle(99, 0.0, 1.0, ["A."]), _subtitle(1, 1.5, 2.5, ["B."])]

        text = render_srt(subtitles)

        assert text.startswith("1\n")
        assert "\n2\n" in text

    def test_hours_pad_to_at_least_two_digits(self) -> None:
        text = render_srt([_subtitle(1, 5.0, 6.0, ["Late."])])

        assert text.startswith("1\n00:00:05,000")

    def test_hours_over_99_are_not_truncated(self) -> None:
        huge = timedelta(hours=100)
        subtitle = Subtitle(
            index=1,
            start_time=huge,
            end_time=huge + timedelta(seconds=1),
            text="x",
            lines=["x"],
        )

        text = render_srt([subtitle])

        assert "100:00:00,000" in text

    def test_passes_the_invariant_checker(self) -> None:
        subtitles = [
            _subtitle(1, 0.0, 1.0, ["One."]),
            _subtitle(2, 1.5, 2.5, ["Two.", "Continued."]),
            _subtitle(3, 3.0, 5.0, ["Three."]),
        ]

        assert_valid_srt(render_srt(subtitles).encode("utf-8"))


class TestWriteOutput:
    """R17: one-step write, no-clobber without --force, no partial file ever."""

    def test_writes_new_file(self, tmp_path: Path) -> None:
        path = tmp_path / "ep42.en.srt"

        write_output("content\n", path, force=False)

        assert path.read_text(encoding="utf-8") == "content\n"
        assert [entry.name for entry in tmp_path.iterdir()] == ["ep42.en.srt"]

    def test_existing_file_without_force_raises_and_is_untouched(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "ep42.en.srt"
        path.write_bytes(b"original")

        with pytest.raises(OutputExistsError) as exc_info:
            write_output("new content", path, force=False)

        assert str(exc_info.value) == "ep42.en.srt already exists."
        assert exc_info.value.hint
        assert path.read_bytes() == b"original"
        assert [entry.name for entry in tmp_path.iterdir()] == ["ep42.en.srt"]

    def test_existing_file_with_force_is_replaced(self, tmp_path: Path) -> None:
        path = tmp_path / "ep42.en.srt"
        path.write_bytes(b"original")

        write_output("new content", path, force=True)

        assert path.read_text(encoding="utf-8") == "new content"
        assert [entry.name for entry in tmp_path.iterdir()] == ["ep42.en.srt"]

    def test_oserror_during_write_leaves_no_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*_args: object, **_kwargs: object) -> None:
            raise OSError(errno.ENOSPC, "No space left on device")

        monkeypatch.setattr(os, "fsync", boom)
        path = tmp_path / "ep42.en.srt"

        with pytest.raises(OutputError) as exc_info:
            write_output("content", path, force=False)

        assert not isinstance(exc_info.value, OutputExistsError)
        assert "ep42.en.srt" in str(exc_info.value)
        assert "No space left on device" in str(exc_info.value)
        assert list(tmp_path.iterdir()) == []

    def test_keyboard_interrupt_propagates_and_leaves_no_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*_args: object, **_kwargs: object) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(os, "fsync", boom)
        path = tmp_path / "ep42.en.srt"

        with pytest.raises(KeyboardInterrupt):
            write_output("content", path, force=False)

        assert list(tmp_path.iterdir()) == []

    def test_final_file_mode_matches_a_normally_created_file(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "ep42.en.srt"

        write_output("content", path, force=False)

        normal = tmp_path / "normal.txt"
        normal.write_text("x")

        assert stat.S_IMODE(path.stat().st_mode) == stat.S_IMODE(normal.stat().st_mode)
        assert stat.S_IMODE(path.stat().st_mode) != 0o600

    def test_target_folder_missing_raises_output_error(self, tmp_path: Path) -> None:
        # S1.3-Q2: mkstemp itself can fail (folder removed after planning,
        # ENOSPC, ENAMETOOLONG); that must become OutputError, not a raw
        # OSError, and must leave nothing behind.
        path = tmp_path / "gone" / "ep42.en.srt"

        with pytest.raises(OutputError) as exc_info:
            write_output("content", path, force=False)

        assert not isinstance(exc_info.value, OutputExistsError)
        assert "ep42.en.srt" in str(exc_info.value)
        assert list(tmp_path.iterdir()) == []

    def test_mkstemp_failure_raises_output_error_and_leaves_no_temp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*_args: object, **_kwargs: object) -> tuple[int, str]:
            raise OSError(errno.ENOSPC, "No space left on device")

        monkeypatch.setattr(tempfile, "mkstemp", boom)
        path = tmp_path / "ep42.en.srt"

        with pytest.raises(OutputError) as exc_info:
            write_output("content", path, force=False)

        assert not isinstance(exc_info.value, OutputExistsError)
        assert "No space left on device" in str(exc_info.value)
        assert list(tmp_path.iterdir()) == []
