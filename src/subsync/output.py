"""Decide where the subtitle file goes, and refuse to overwrite it too late.

Two stages run before any extraction, download or transcription (R14, R15,
U1):

- ``check_output_args`` (stage 0) rejects a ``-o`` name whose extension
  disagrees with ``--format``.
- ``plan_output`` (stage 1) resolves the output folder and, when it is
  already fully known, the exact final path; it also fails fast if the
  folder cannot be written to, or if a previous run's file is still there.

The plan does not depend on the language, which may still be auto-detected
at this point; ``OutputPlan.path_for`` fills it in once transcription has
run.
"""

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from subsync.errors import InputError, OutputError, OutputExistsError
from subsync.models import MediaSource

logger = logging.getLogger(__name__)

_FORMAT_EXTENSIONS = (".srt", ".vtt")


def check_output_args(output_arg: str | None, fmt: str) -> None:
    """Reject a ``-o`` name whose extension disagrees with ``--format`` (F4).

    Args:
        output_arg: The raw ``-o`` value, or ``None``.
        fmt: The requested format (``"srt"`` in S1).

    Raises:
        InputError: If ``output_arg`` ends in ``.srt`` or ``.vtt`` and that
            differs from ``fmt``.
    """
    if output_arg is None:
        return
    suffix = Path(output_arg).suffix.lower()
    if suffix not in _FORMAT_EXTENSIONS:
        return
    named_fmt = suffix[1:]
    if named_fmt == fmt:
        return
    raise InputError(
        f"Output name ends in {suffix} but --format is {fmt}.",
        hint=f"Use --format {named_fmt}, or an output name ending in .{fmt}.",
    )


@dataclass
class OutputPlan:
    """Where the subtitle file will be written.

    Attributes:
        directory: The absolute folder the file will be written into.
        exact_path: The absolute final path, when it is already fully known
            (a language was given, or ``-o`` named a file directly). ``None``
            when the name still depends on an auto-detected language.
        stem: File stem used to build the default name, when ``exact_path``
            is ``None``.
        fmt: Output format extension (``"srt"`` in S1).
    """

    directory: Path
    exact_path: Path | None
    stem: str
    fmt: str

    def path_for(self, language: str) -> Path:
        """Return the absolute path to write, once the language is known.

        Args:
            language: The language code to use if the name still depends on
                one; ignored when ``exact_path`` was already fixed.

        Returns:
            An absolute path.
        """
        if self.exact_path is not None:
            return self.exact_path
        return self.directory / f"{self.stem}.{language}.{self.fmt}"


def plan_output(
    source: MediaSource,
    output_arg: str | None,
    fmt: str,
    language: str | None,
    force: bool,
) -> OutputPlan:
    """Resolve the output folder and fail fast if writing there is unsafe.

    Naming (R14): with no ``-o``, the default is
    ``<source.output_dir>/<source.output_stem>.<lang>.<fmt>``. A ``-o``
    naming an existing folder, or ending in ``/``, uses that default name
    inside it. Any other ``-o`` is used exactly as given; a relative ``-o``
    resolves against the current folder.

    Pre-check (R15, U1): unless ``force``,
    - an already-known exact path (a language was given, or ``-o`` named a
      file) must not already exist;
    - an auto-detected language must not collide with any
      ``<stem>.<something>.<fmt>`` file already in the output folder,
      matched literally (never as a glob).

    The output folder (or the parent of an exact path) must exist and be
    writable; this check is not skipped by ``force`` — it protects nothing
    that ``--force`` is meant to override. Folders are never created.

    Args:
        source: The resolved input, giving the default folder and stem.
        output_arg: The raw ``-o`` value, or ``None``.
        fmt: The requested format (``"srt"`` in S1).
        language: The language code, or ``None`` if not yet known.
        force: Whether ``--force`` was given.

    Returns:
        The resolved plan.

    Raises:
        OutputExistsError: A previous run's file is already there (F11).
        OutputError: The folder is missing or not writable (F12).
    """
    directory, stem, exact_path, folder_display = _resolve_naming(
        source, output_arg, fmt, language
    )

    _check_writable(directory, folder_display)

    if not force:
        if exact_path is not None:
            if exact_path.exists():
                raise OutputExistsError.for_file(exact_path.name)
        else:
            conflict = _auto_language_conflict(directory, stem, fmt, folder_display)
            if conflict is not None:
                raise OutputExistsError.for_file(conflict)

    return OutputPlan(directory=directory, exact_path=exact_path, stem=stem, fmt=fmt)


def _absolute(path: Path) -> Path:
    """Make ``path`` absolute against the current folder, without resolving it."""
    path = path.expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def _resolve_naming(
    source: MediaSource, output_arg: str | None, fmt: str, language: str | None
) -> tuple[Path, str, Path | None, str]:
    """Work out the directory, stem, exact path and folder display text."""
    if output_arg is None:
        directory = _absolute(source.output_dir)
        stem = source.output_stem
        exact_path = (
            None if language is None else directory / f"{stem}.{language}.{fmt}"
        )
        return directory, stem, exact_path, f"{directory}/"

    raw_path = Path(output_arg)
    absolute_path = _absolute(raw_path)
    is_folder = output_arg.endswith("/") or absolute_path.is_dir()

    if is_folder:
        directory = absolute_path
        stem = source.output_stem
        exact_path = (
            None if language is None else directory / f"{stem}.{language}.{fmt}"
        )
        display = output_arg if output_arg.endswith("/") else f"{output_arg}/"
        return directory, stem, exact_path, display

    exact_path = absolute_path
    directory = exact_path.parent
    parent_display = str(raw_path.parent)
    display = f"{parent_display}/" if parent_display != "." else "./"
    return directory, source.output_stem, exact_path, display


def _check_writable(directory: Path, display: str) -> None:
    """Verify that ``directory`` exists and is writable, without creating it.

    Tries to create and immediately remove a throwaway file, so the same
    check surfaces a missing folder and a read-only one with the operating
    system's own reason for either.

    Args:
        directory: The absolute folder to check.
        display: How to name the folder in the error message.

    Raises:
        OutputError: If the probe fails for any reason (F12).
    """
    try:
        with tempfile.TemporaryFile(dir=directory):
            pass
    except OSError as exc:
        reason = exc.strerror or str(exc)
        logger.debug("output folder %s is not writable: %s", directory, exc)
        raise OutputError(f"Can't write to {display}: {reason}.") from exc


def _auto_language_conflict(
    directory: Path, stem: str, fmt: str, display: str
) -> str | None:
    """Return the name of an existing ``<stem>.<something>.<fmt>`` file, if any.

    Matches literally: ``stem`` is compared as plain text, never as a glob
    or regex pattern, so characters such as ``[``, ``*`` or ``?`` in it never
    match unrelated files.

    Args:
        directory: The absolute folder to scan.
        stem: The literal stem to match at the start of the name.
        fmt: The extension to match at the end of the name.
        display: How to name the folder in the error message.

    Returns:
        The first conflicting file name found, or ``None``.

    Raises:
        OutputError: The folder can't be listed (F12).
    """
    prefix = f"{stem}."
    suffix = f".{fmt}"
    try:
        names = sorted(entry.name for entry in directory.iterdir() if entry.is_file())
    except OSError as exc:
        # Without a listing, U1 can't be honoured: say so before any work.
        reason = exc.strerror or str(exc)
        logger.debug("output folder %s can't be listed: %s", directory, exc)
        raise OutputError(f"Can't write to {display}: {reason}.") from exc
    for name in names:
        if not name.startswith(prefix) or not name.endswith(suffix):
            continue
        middle = name[len(prefix) : len(name) - len(suffix)]
        if middle:
            return name
    return None
