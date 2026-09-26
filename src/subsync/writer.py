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

    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, _default_file_mode())

        if force:
            os.replace(tmp_path, path)
        else:
            # A hard link fails atomically if the name exists, with no
            # window between checking and creating it.
            os.link(tmp_path, path)
    except FileExistsError as exc:
        raise OutputExistsError(
            f"{path.name} already exists.", hint=_EXISTS_HINT
        ) from exc
    except OSError as exc:
        reason = exc.strerror or str(exc)
        logger.debug("write to %s failed: %s", path, exc)
        raise OutputError(f"Couldn't write {path.name}: {reason}.") from exc
    finally:
        # os.link leaves the temporary file behind on success; every other
        # path (including a bare KeyboardInterrupt) leaves it behind too.
        tmp_path.unlink(missing_ok=True)
