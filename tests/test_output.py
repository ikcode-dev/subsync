"""Tests for output.py: format checks, naming and the pre-write checks."""

import os
from pathlib import Path

import pytest

from subsync.errors import InputError, OutputError, OutputExistsError
from subsync.models import MediaSource
from subsync.output import check_output_args, plan_output

_EXISTS_HINT = "Re-run with --force to replace it, or choose another path with -o."


def _source(output_dir: Path, stem: str = "ep42") -> MediaSource:
    """Build a minimal file MediaSource rooted at ``output_dir``."""
    return MediaSource(
        kind="file",
        display_name=f"{stem}.mov",
        output_stem=stem,
        output_dir=output_dir,
        path=output_dir / f"{stem}.mov",
    )


class TestCheckOutputArgs:
    """F4: ``-o``'s extension must agree with ``--format``."""

    def test_no_output_arg_is_always_fine(self) -> None:
        check_output_args(None, "srt")

    def test_matching_extension_is_fine(self) -> None:
        check_output_args("clip.srt", "srt")

    def test_non_subtitle_extension_is_ignored(self) -> None:
        check_output_args("clip.mov", "srt")

    def test_folder_looking_arg_is_ignored(self) -> None:
        check_output_args("out/", "srt")

    def test_mismatched_extension_raises_input_error(self) -> None:
        with pytest.raises(InputError) as exc_info:
            check_output_args("final.vtt", "srt")
        err = exc_info.value
        assert str(err) == "Output name ends in .vtt but --format is srt."
        assert err.hint


class TestPlanOutputNaming:
    """R14: default name, -o rules, absolute paths, multi-dot stems."""

    def test_default_name_is_absolute(self, tmp_path: Path) -> None:
        videos = tmp_path / "Videos"
        videos.mkdir()
        source = _source(videos)

        plan = plan_output(source, None, "srt", "en", force=False)
        path = plan.path_for("en")

        assert path == videos / "ep42.en.srt"
        assert path.is_absolute()

    def test_output_arg_existing_folder_with_slash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "out").mkdir()
        source = _source(tmp_path)

        plan = plan_output(source, "out/", "srt", "en", force=False)

        assert plan.path_for("en") == tmp_path / "out" / "ep42.en.srt"

    def test_output_arg_missing_folder_raises_and_is_not_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        source = _source(tmp_path)

        with pytest.raises(OutputError) as exc_info:
            plan_output(source, "out/", "srt", "en", force=False)

        assert not isinstance(exc_info.value, OutputExistsError)
        # S1.3-Q5: dropping the OS reason from the message must fail this.
        assert str(exc_info.value) == "Can't write to out/: No such file or directory."
        assert not (tmp_path / "out").exists()

    def test_output_arg_exact_file_path_ignores_language(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "subs").mkdir()
        source = _source(tmp_path)

        plan = plan_output(source, "subs/final.srt", "srt", None, force=False)

        assert plan.path_for("en") == tmp_path / "subs" / "final.srt"
        assert plan.path_for("de") == tmp_path / "subs" / "final.srt"

    def test_output_arg_exact_file_missing_parent_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        source = _source(tmp_path)

        with pytest.raises(OutputError) as exc_info:
            plan_output(source, "subs/final.srt", "srt", "en", force=False)

        assert not isinstance(exc_info.value, OutputExistsError)
        assert not (tmp_path / "subs").exists()

    def test_multi_dot_stem_is_kept(self, tmp_path: Path) -> None:
        source = _source(tmp_path, stem="my.talk.final")

        plan = plan_output(source, None, "srt", "en", force=False)

        assert plan.path_for("en") == tmp_path / "my.talk.final.en.srt"

    def test_relative_output_arg_resolves_against_current_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "subs").mkdir()
        source = _source(tmp_path)

        plan = plan_output(source, "subs/final.srt", "srt", "en", force=False)

        assert plan.path_for("en").is_absolute()
        assert plan.path_for("en") == tmp_path / "subs" / "final.srt"

    def test_path_with_spaces_and_unicode(self, tmp_path: Path) -> None:
        folder = tmp_path / "clips ñ"
        folder.mkdir()
        source = _source(folder, stem="épisode 42")

        plan = plan_output(source, None, "srt", "en", force=False)

        assert plan.path_for("en") == folder / "épisode 42.en.srt"


class TestPlanOutputPreCheck:
    """R15, U1: refuse a name a previous run already used, unless --force."""

    def test_exact_path_conflict_names_the_file(self, tmp_path: Path) -> None:
        (tmp_path / "ep42.en.srt").write_text("existing")
        source = _source(tmp_path)

        with pytest.raises(OutputExistsError) as exc_info:
            plan_output(source, None, "srt", "en", force=False)

        assert str(exc_info.value) == "ep42.en.srt already exists."
        assert exc_info.value.hint == _EXISTS_HINT

    def test_auto_language_conflict_names_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "ep42.de.srt").write_text("existing")
        source = _source(tmp_path)

        with pytest.raises(OutputExistsError) as exc_info:
            plan_output(source, None, "srt", None, force=False)

        assert str(exc_info.value) == "ep42.de.srt already exists."

    def test_exact_language_ignores_other_language_files(self, tmp_path: Path) -> None:
        (tmp_path / "ep42.de.srt").write_text("existing")
        source = _source(tmp_path)

        plan = plan_output(source, None, "srt", "en", force=False)

        assert plan.path_for("en") == tmp_path / "ep42.en.srt"

    def test_force_skips_the_exists_precheck(self, tmp_path: Path) -> None:
        (tmp_path / "ep42.de.srt").write_text("existing")
        source = _source(tmp_path)

        plan = plan_output(source, None, "srt", None, force=True)

        assert plan.directory == tmp_path

    def test_conflict_match_is_literal_not_a_pattern(self, tmp_path: Path) -> None:
        (tmp_path / "ep1.en.srt").write_text("existing")
        source = _source(tmp_path, stem="ep[1]")

        plan = plan_output(source, None, "srt", None, force=False)

        assert plan.stem == "ep[1]"

    def test_force_does_not_skip_the_folder_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        source = _source(tmp_path)

        with pytest.raises(OutputError) as exc_info:
            plan_output(source, "out/", "srt", "en", force=True)

        assert not isinstance(exc_info.value, OutputExistsError)


class TestPlanOutputWritability:
    """F12: a folder that can't be written to fails before any work starts."""

    def test_read_only_folder_raises_with_os_reason(self, tmp_path: Path) -> None:
        if hasattr(os, "getuid") and os.getuid() == 0:
            pytest.skip("running as root bypasses folder permissions")
        readonly = tmp_path / "readonly"
        readonly.mkdir()
        readonly.chmod(0o500)
        source = _source(tmp_path)

        try:
            with pytest.raises(OutputError) as exc_info:
                plan_output(source, str(readonly), "srt", "en", force=False)
            assert not isinstance(exc_info.value, OutputExistsError)
            # S1.3-Q5: dropping the OS reason from the message must fail this.
            message = str(exc_info.value)
            assert message == f"Can't write to {readonly}/: Permission denied."
        finally:
            readonly.chmod(0o700)
