"""Local-file input resolution for `subsync generate`.

Only the local-file branch is implemented in slice S1. A YouTube URL is
still *detected* here (with the existing `url_handler.parse_youtube_url`),
so INPUT gets its own explicit, interim message until slice S4 adds real
YouTube support. An existing file always wins over URL parsing.

Fast startup: this module must not import the ML stack (whisper, torch,
yt_dlp); see `spec/plan/phase-4-cli-output.md` -> "Fast Startup".
"""

import logging
from pathlib import Path

from subsync.errors import InputError, URLParseError
from subsync.models import MediaSource
from subsync.url_handler import parse_youtube_url

logger = logging.getLogger(__name__)


def resolve_input(raw: str) -> MediaSource:
    """Resolve the `generate` command's INPUT argument.

    Args:
        raw: INPUT exactly as given on the command line.

    Returns:
        A `MediaSource` for the local file `raw` names.

    Raises:
        InputError: `raw` is a folder (F8); `raw` parses as a YouTube URL,
            not supported until slice S4 (interim message); or `raw` is
            neither an existing file nor a supported URL (F7).
    """
    path = Path(raw)

    if path.is_file():
        resolved = path.resolve()
        logger.debug("resolved input %r to local file %s", raw, resolved)
        return MediaSource(
            kind="file",
            display_name=resolved.name,
            output_stem=resolved.stem,
            output_dir=resolved.parent,
            path=resolved,
        )

    if path.is_dir():
        raise InputError(f"'{raw}' is a folder, not a media file.")

    if _looks_like_youtube_url(raw):
        raise InputError(
            "YouTube links aren't supported yet.",
            hint="Export or download the video and run: subsync generate <file>",
        )

    raise InputError(
        f"'{raw}' is not a file or a supported YouTube URL.",
        hint="Example: subsync generate ~/Videos/ep42.mov",
    )


def _looks_like_youtube_url(raw: str) -> bool:
    """Whether `raw` parses as a supported YouTube URL."""
    try:
        parse_youtube_url(raw)
    except URLParseError:
        return False
    return True
