"""Tests for local-file input resolution."""

from pathlib import Path

import pytest
from subsync.errors import InputError
from subsync.sources import resolve_input


class TestExistingFile:
    """An existing file resolves to a file `MediaSource`."""

    def test_resolves_fields(self, tmp_path: Path) -> None:
        video = tmp_path / "ep42.mov"
        video.write_bytes(b"fake video bytes")

        source = resolve_input(str(video))

        assert source.kind == "file"
        assert source.display_name == "ep42.mov"
        assert source.output_stem == "ep42"
        assert source.output_dir == video.resolve().parent
        assert source.path == video.resolve()

    def test_symlinked_input_is_named_after_the_link(self, tmp_path: Path) -> None:
        """R14: subtitles go next to the path given, named after it."""
        renders = tmp_path / "renders"
        renders.mkdir()
        target = renders / "final-v3.mov"
        target.write_bytes(b"fake")
        videos = tmp_path / "Videos"
        videos.mkdir()
        link = videos / "ep42.mov"
        link.symlink_to(target)

        source = resolve_input(str(link))

        assert source.display_name == "ep42.mov"
        assert source.output_stem == "ep42"
        assert source.output_dir == videos
        assert source.path == link

    def test_relative_path_resolves_to_absolute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"fake")
        monkeypatch.chdir(tmp_path)

        source = resolve_input("clip.mp4")

        assert source.path is not None
        assert source.path.is_absolute()
        assert source.output_dir.is_absolute()
        assert source.output_dir == tmp_path.resolve()

    def test_multi_dot_stem_keeps_last_suffix_only(self, tmp_path: Path) -> None:
        video = tmp_path / "ep42.final.mov"
        video.write_bytes(b"fake")

        source = resolve_input(str(video))

        assert source.output_stem == "ep42.final"

    def test_youtube_fields_are_none(self, tmp_path: Path) -> None:
        video = tmp_path / "ep42.mov"
        video.write_bytes(b"fake")

        source = resolve_input(str(video))

        assert source.video_id is None
        assert source.channel is None
        assert source.duration is None


class TestFolder:
    """A folder is rejected with F8, never treated as a media file."""

    def test_folder_raises_input_error(self, tmp_path: Path) -> None:
        clips = tmp_path / "clips"
        clips.mkdir()

        with pytest.raises(InputError, match="is a folder, not a media file"):
            resolve_input(str(clips))

    def test_folder_message_quotes_raw_input(self, tmp_path: Path) -> None:
        clips = tmp_path / "clips"
        clips.mkdir()
        raw = f"{clips}/"

        with pytest.raises(InputError) as exc_info:
            resolve_input(raw)

        assert str(exc_info.value) == f"'{raw}' is a folder, not a media file."


class TestYoutubeUrl:
    """A YouTube URL is detected but not yet supported (interim, until S4)."""

    def test_youtube_url_raises_interim_error(self) -> None:
        with pytest.raises(InputError) as exc_info:
            resolve_input("https://youtu.be/dQw4w9WgXcQ")

        assert str(exc_info.value) == "YouTube links aren't supported yet."
        assert exc_info.value.hint == (
            "Export or download the video and run: subsync generate <file>"
        )

    def test_watch_url_also_raises_interim_error(self) -> None:
        with pytest.raises(InputError, match="aren't supported yet"):
            resolve_input("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


class TestNeitherFileNorUrl:
    """Anything else is rejected with F7 and an example command."""

    def test_missing_file_raises_input_error(self) -> None:
        with pytest.raises(InputError) as exc_info:
            resolve_input("foo")

        assert str(exc_info.value) == "'foo' is not a file or a supported YouTube URL."
        assert exc_info.value.hint is not None
        assert "subsync generate" in exc_info.value.hint

    def test_non_youtube_url_raises_input_error(self) -> None:
        with pytest.raises(InputError, match="not a file or a supported YouTube URL"):
            resolve_input("https://vimeo.com/12345")

    def test_existing_file_wins_over_url_parsing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A path that *is* a valid YouTube URL, but also exists, is a file.

        Refs: S1.6-Q2
        """
        # A relative "https://youtu.be/dQw4w9WgXcQ" resolves (via pathlib's
        # slash collapsing) to the file tmp_path/https:/youtu.be/dQw4w9WgXcQ.
        video = tmp_path / "https:" / "youtu.be" / "dQw4w9WgXcQ"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"fake")
        monkeypatch.chdir(tmp_path)

        source = resolve_input("https://youtu.be/dQw4w9WgXcQ")

        assert source.kind == "file"
