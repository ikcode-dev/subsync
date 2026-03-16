"""Tests for the progress module."""

from unittest.mock import MagicMock

import pytest

from subsync.progress import ProgressMapper


class TestProgressMapper:
    """Tests for ProgressMapper."""

    def test_start_of_range(self) -> None:
        """update(0.0) calls callback with start value."""
        callback = MagicMock()
        mapper = ProgressMapper(callback, start=0.05, end=0.50, stage="Downloading")

        mapper.update(0.0)

        callback.assert_called_once_with(0.05, "Downloading")

    def test_end_of_range(self) -> None:
        """update(1.0) calls callback with end value."""
        callback = MagicMock()
        mapper = ProgressMapper(callback, start=0.05, end=0.50, stage="Downloading")

        mapper.update(1.0)

        callback.assert_called_once_with(0.50, "Downloading")

    def test_midpoint(self) -> None:
        """update(0.5) on full range calls callback with 0.5."""
        callback = MagicMock()
        mapper = ProgressMapper(callback, start=0.0, end=1.0, stage="Processing")

        mapper.update(0.5)

        callback.assert_called_once_with(0.5, "Processing")

    def test_midpoint_partial_range(self) -> None:
        """update(0.5) on range (0.1, 0.5) calls callback with 0.3."""
        callback = MagicMock()
        mapper = ProgressMapper(callback, start=0.1, end=0.5, stage="Loading")

        mapper.update(0.5)

        callback.assert_called_once_with(pytest.approx(0.3), "Loading")

    def test_none_callback_no_error(self) -> None:
        """None callback is a no-op — no errors."""
        mapper = ProgressMapper(None, start=0.0, end=1.0, stage="Test")

        mapper.update(0.0)
        mapper.update(0.5)
        mapper.update(1.0)
        mapper.complete()
        # No exception raised

    def test_complete_calls_with_end(self) -> None:
        """complete() calls callback with end value."""
        callback = MagicMock()
        mapper = ProgressMapper(callback, start=0.5, end=1.0, stage="Transcribing")

        mapper.complete()

        callback.assert_called_once_with(1.0, "Transcribing")

    def test_stage_name_passed_through(self) -> None:
        """Stage name is passed to callback on every call."""
        callback = MagicMock()
        mapper = ProgressMapper(callback, start=0.0, end=1.0, stage="MyStage")

        mapper.update(0.25)

        callback.assert_called_once_with(0.25, "MyStage")

    def test_quarter_progress(self) -> None:
        """update(0.25) on range (0.05, 0.50) maps correctly."""
        callback = MagicMock()
        mapper = ProgressMapper(callback, start=0.05, end=0.50, stage="Download")

        mapper.update(0.25)

        # 0.05 + (0.50 - 0.05) * 0.25 = 0.05 + 0.1125 = 0.1625
        callback.assert_called_once_with(pytest.approx(0.1625), "Download")
