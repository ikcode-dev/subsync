"""SubSync command-line interface.

Argument parsing, static catalog validation, local-file input resolution
and the single error boundary that turns every outcome into the right
message and exit code. Fast startup: this module, and every stage 0-1
failure path, must never import the ML stack (whisper, torch, yt_dlp); see
`spec/plan/phase-4-cli-output.md` -> "Fast Startup". `subsync.pipeline`,
`subsync.transcriber` and `subsync.audio_extractor` import those modules at
their top level, so they are never imported here.
"""

import argparse
import logging
import sys
import traceback
from importlib import metadata

from subsync import catalog
from subsync.errors import InputError, SubSyncError
from subsync.sources import resolve_input

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the `subsync` argument parser.

    Returns:
        The top-level parser, with `generate` as its one subcommand. The
        subcommand layout leaves room for future subcommands (e.g.
        `translate`).
    """
    parser = argparse.ArgumentParser(
        prog="subsync",
        description=(
            "Turn a local video file or a YouTube video into a "
            "Netflix-compliant subtitle file."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"subsync {metadata.version('subsync')}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate",
        help="Generate a subtitle file from a local media file.",
    )
    generate.add_argument(
        "input",
        metavar="INPUT",
        help="Local video/audio file, or a YouTube video URL.",
    )
    generate.add_argument(
        "-l",
        "--language",
        metavar="CODE",
        default=None,
        help="Spoken language code; skips detection (default: auto-detect).",
    )
    generate.add_argument(
        "-m",
        "--model",
        metavar="NAME",
        default="turbo",
        help="Whisper model name (default: turbo).",
    )
    generate.add_argument(
        "-f",
        "--format",
        choices=["srt"],
        default="srt",
        help="Output subtitle format (default: srt).",
    )
    generate.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        default=None,
        help="Output folder or exact file path (default: next to INPUT).",
    )
    generate.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output file.",
    )
    generate.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logging, and a traceback if an error occurs.",
    )

    return parser


def _validate_language(code: str | None) -> None:
    """Raise if `-l` names an unknown Whisper language code (F2)."""
    if code is not None and code not in catalog.LANGUAGES:
        raise InputError(
            f"Unknown language code '{code}'.",
            hint="Use a code such as en, pl, de.",
        )


def _validate_model(name: str) -> None:
    """Raise if `-m` names an unknown Whisper model (F3)."""
    if name not in catalog.MODEL_NAMES:
        raise InputError(
            f"Unknown model '{name}'.",
            hint="Valid models: " + ", ".join(catalog.MODEL_NAMES),
        )


def run_generate(args: argparse.Namespace) -> int:
    """Run `subsync generate`.

    This is the seam task S1.7 fills in. As of slice S1.6 it covers stage 0
    (`-l`/`-m` validation) and stage 1 (input resolution), then stops.

    S1.7 will:
    - add the `-o`/`-f` consistency check (F4) and the FFmpeg check (F6) to
      stage 0, before input resolution;
    - use the resolved `MediaSource` to run the output pre-check, audio
      extraction, transcription, subtitle processing and the write, render
      the stage lines and summary, and return the final exit code.

    Args:
        args: Parsed arguments from the `generate` subcommand (`input`,
            `language`, `model`, `format`, `output`, `force`, `verbose`).

    Returns:
        The process exit code.

    Raises:
        SubSyncError: Any stage 0/1 validation failure (F2, F3, F7, F8, or
            the interim YouTube-URL message).
    """
    _validate_language(args.language)
    _validate_model(args.model)

    resolve_input(args.input)

    # --- S1.7 continues from here (see the docstring above). ---
    return 0


def _summarize(exc: BaseException) -> str:
    """One-line summary of an unexpected exception, for the F25 message."""
    text = str(exc) or exc.__class__.__name__
    return text.splitlines()[0]


def _print_error(err: SubSyncError) -> None:
    """Print the ``✗`` error block to stderr: headline, then each hint line."""
    print(f"✗ {err}", file=sys.stderr)
    if err.hint:
        for line in err.hint.splitlines():
            print(f"  {line}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the `subsync` console script.

    Args:
        argv: Arguments excluding the program name; `sys.argv[1:]` when
            `None`.

    Returns:
        The process exit code: 0 on success, 130 on Ctrl+C, or the failing
        error's category exit code. Never raises; every outcome, including
        argparse's own usage errors and `--version`/`--help`, is turned
        into a returned int.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    verbose = getattr(args, "verbose", False)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )

    try:
        return run_generate(args)
    except SubSyncError as err:
        if verbose:
            traceback.print_exc(file=sys.stderr)
        _print_error(err)
        return err.exit_code
    except KeyboardInterrupt:
        print("Cancelled. Nothing written.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - last-resort boundary (F25)
        if verbose:
            traceback.print_exc(file=sys.stderr)
        _print_error(
            SubSyncError(
                f"Something went wrong: {_summarize(exc)}.",
                hint="Re-run with -v and share the output.",
            )
        )
        return 1
