"""Tests for the SubSync error hierarchy."""

import pytest

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

# (class, direct parent, exit code)
HIERARCHY: list[tuple[type[SubSyncError], type[Exception], int]] = [
    (SubSyncError, Exception, 1),
    (InputError, SubSyncError, 2),
    (URLParseError, InputError, 2),
    (MediaError, InputError, 2),
    (DependencyError, SubSyncError, 1),
    (SourceUnavailableError, SubSyncError, 3),
    (VideoUnavailableError, SourceUnavailableError, 3),
    (AgeRestrictedError, SourceUnavailableError, 3),
    (LiveStreamError, SourceUnavailableError, 3),
    (TranscriptionError, SubSyncError, 4),
    (ModelDownloadError, TranscriptionError, 4),
    (ModelMemoryError, TranscriptionError, 4),
    (NoSpeechError, TranscriptionError, 4),
    (OutputError, SubSyncError, 5),
    (OutputExistsError, OutputError, 5),
]


class TestHierarchy:
    """Each error sits under its parent and under SubSyncError."""

    @pytest.mark.parametrize(
        ("cls", "parent", "exit_code"),
        HIERARCHY,
        ids=[cls.__name__ for cls, _, _ in HIERARCHY],
    )
    def test_is_instance_of_parent_and_base(
        self, cls: type[SubSyncError], parent: type[Exception], exit_code: int
    ) -> None:
        """An instance is an instance of its parent and of SubSyncError."""
        err = cls("boom")
        assert isinstance(err, parent)
        assert isinstance(err, SubSyncError)

    @pytest.mark.parametrize(
        ("cls", "parent", "exit_code"),
        HIERARCHY,
        ids=[cls.__name__ for cls, _, _ in HIERARCHY],
    )
    def test_exit_code(
        self, cls: type[SubSyncError], parent: type[Exception], exit_code: int
    ) -> None:
        """Each category carries the exit code the CLI maps it to."""
        assert cls("boom").exit_code == exit_code

    @pytest.mark.parametrize(
        "cls", [cls for cls, _, _ in HIERARCHY], ids=lambda c: c.__name__
    )
    def test_caught_by_base(self, cls: type[SubSyncError]) -> None:
        """`except SubSyncError` catches every SubSync error."""
        with pytest.raises(SubSyncError):
            raise cls("boom")


class TestHint:
    """The optional next-step hint."""

    def test_hint_defaults_to_none(self) -> None:
        """Without a hint, `hint` is None."""
        assert SubSyncError("x").hint is None

    def test_explicit_hint(self) -> None:
        """A given hint is kept."""
        assert SubSyncError("x", hint="y").hint == "y"

    def test_str_is_the_message(self) -> None:
        """`str()` is the message, with or without a hint."""
        assert str(SubSyncError("x")) == "x"
        assert str(SubSyncError("x", hint="y")) == "x"

    def test_subclass_accepts_hint(self) -> None:
        """Subclasses take the hint keyword too."""
        err = OutputExistsError("ep42.en.srt already exists.", hint="Use --force.")
        assert str(err) == "ep42.en.srt already exists."
        assert err.hint == "Use --force."

    def test_message_only_call_sites_still_work(self) -> None:
        """Existing call sites that pass only a message keep working."""
        err = URLParseError("not a YouTube URL")
        assert str(err) == "not a YouTube URL"
        assert err.hint is None
        assert err.args == ("not a YouTube URL",)
