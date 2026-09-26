"""Render subtitles as SRT and write them out in one step.

``render_srt`` turns a list of :class:`~subsync.models.Subtitle` into SRT
text (E9). ``write_output`` then writes that text to disk so that no
partial or half-written file can ever appear: the full content goes to a
temporary file in the target folder first, and only then is it published
under the final name, in a single filesystem operation (R17).
"""

import logging
import os
import tempfile
from datetime import timedelta
from pathlib import Path

from subsync.errors import OutputError, OutputExistsError
from subsync.models import Subtitle

logger = logging.getLogger(__name__)

_MILLISECOND = timedelta(milliseconds=1)
_EXISTS_HINT = "Re-run with --force to replace it, or choose another path with -o."

# Short and fixed-length on purpose: unlike a prefix built from the final
# name, this never pushes a legal final name (up to 255 bytes) over a
# filesystem's name-length limit.
_TEMP_PREFIX = ".subsync-"
_TEMP_SUFFIX = ".tmp"


def _format_timestamp(moment: timedelta) -> str:
    """Format a timestamp as ``HH:MM:SS,mmm`` (hours zero-padded to 2+ digits).

    Args:
        moment: A whole number of milliseconds since the start of the file.

    Returns:
        The SRT timestamp text.
    """
    total_ms = moment // _MILLISECOND
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def render_srt(subtitles: list[Subtitle]) -> str:
    """Render subtitles as SRT text.

    Cues are numbered 1..n by their position in ``subtitles``, regardless of
    each subtitle's own ``index``. The result is UTF-8-safe text (encoding
    happens in ``write_output``): cues separated by exactly one blank line,
    ending with a single trailing newline.

    Args:
        subtitles: Subtitles in the order they should appear.

    Returns:
        The rendered SRT text, or ``""`` for an empty list.
    """
    blocks = []
    for position, subtitle in enumerate(subtitles, start=1):
        timing = (
            f"{_format_timestamp(subtitle.start_time)} --> "
            f"{_format_timestamp(subtitle.end_time)}"
        )
        blocks.append("\n".join([str(position), timing, *subtitle.lines]))
    return "\n\n".join(blocks) + "\n" if blocks else ""


def _default_file_mode() -> int:
    """Return the permissions a normally created file would get right now.

    Reads the process umask by setting it and immediately restoring it;
    this is the standard way to read it without a dedicated getter, and is
    safe for a single-threaded CLI.
    """
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def write_output(content: str, path: Path, force: bool) -> None:
    """Write ``content`` to ``path`` in one step; never leaves a partial file.

    The content is encoded as UTF-8 without a BOM and written in full to a
    temporary file in ``path``'s folder. Publishing under the final name is
    then a single step: without ``force`` it fails if the name already
    exists (no check-then-replace race), and with ``force`` it replaces the
    existing file. The temporary file never survives the call, on any
    outcome, including ``KeyboardInterrupt``, which is left to propagate
    unchanged.

    Args:
        content: The full file content to write.
        path: The absolute final path.
        force: Whether to replace an existing file at ``path``.

    Raises:
        OutputExistsError: ``path`` already exists and ``force`` is false
            (F11, re-checked at write time).
        OutputError: The write failed for any other OS reason (F23).
    """
    path = Path(path)
    data = content.encode("utf-8")
    mode = _default_file_mode()

    # Recorded as a plain string, in the same statement mkstemp returns it
    # in, so cleanup never depends on a later statement (not even
    # ``Path(tmp_name)``) having run before an interrupt lands.
    tmp_name: str | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=_TEMP_PREFIX, suffix=_TEMP_SUFFIX
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)

        if force:
            os.replace(tmp_path, path)
        else:
            _publish_no_clobber(tmp_path, path, mode)
    except FileExistsError as exc:
        raise OutputExistsError(
            f"{path.name} already exists.", hint=_EXISTS_HINT
        ) from exc
    except OSError as exc:
        reason = exc.strerror or str(exc)
        logger.debug("write to %s failed: %s", path, exc)
        raise OutputError(f"Couldn't write {path.name}: {reason}.") from exc
    finally:
        # Covers every exit: success (nothing left to remove), a mapped
        # error, and a bare KeyboardInterrupt at any point above.
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass


def _publish_no_clobber(tmp_path: Path, path: Path, mode: int) -> None:
    """Publish ``tmp_path`` under ``path``, never replacing an existing file.

    A hard link is atomic and leaves no window between checking and
    creating the name, so it is tried first. Some filesystems (exFAT,
    FAT32 — common on external drives) don't support hard links, and a
    temp file and its target can end up on different devices; either
    raises an ``OSError`` other than ``FileExistsError``, which falls back
    to an exclusive-create reservation instead.

    Args:
        tmp_path: The finished temporary file to publish.
        path: The final path; must not already exist.
        mode: Permissions to give the reservation in the fallback path.

    Raises:
        FileExistsError: ``path`` already exists.
        OSError: The fallback publish failed for another reason.
    """
    try:
        os.link(tmp_path, path)
    except FileExistsError:
        raise
    except OSError as exc:
        logger.debug(
            "hard link publish to %s failed (%s); falling back to a reservation",
            path,
            exc,
        )
        _publish_via_reservation(tmp_path, path, mode)


def _publish_via_reservation(tmp_path: Path, path: Path, mode: int) -> None:
    """Reserve ``path`` exclusively, then replace it with the finished file.

    Used when a hard link is not available. The reservation is briefly
    visible as an empty file; it is removed again if anything goes wrong,
    including a ``KeyboardInterrupt``, before the replace completes.

    Args:
        tmp_path: The finished temporary file to publish.
        path: The final path; must not already exist.
        mode: Permissions for the reservation (discarded once replaced).

    Raises:
        FileExistsError: ``path`` already exists.
        OSError: The replace failed for another reason.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        os.close(fd)
        os.replace(tmp_path, path)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
