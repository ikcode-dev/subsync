"""SubSync command-line interface.

Argument parsing, static catalog validation, the fail-fast stage 0-1 checks,
stage lines and the summary, and the single error boundary that turns every
outcome into the right message and exit code. Progress and errors go to
stderr, the summary to stdout (U6).

Fast startup: this module, and every stage 0-1 failure path, must never
import the ML stack (whisper, torch, yt_dlp); see
`spec/plan/phase-4-cli-output.md` -> "Fast Startup". `subsync.pipeline`,
`subsync.transcriber` and `subsync.audio_extractor` import those modules at
their top level, so `subsync.pipeline` is imported only once the output
pre-check has passed.
"""

import argparse
import logging
import shutil
import sys
import time
import traceback
import unicodedata
from datetime import timedelta
from importlib import metadata
from typing import TextIO

from subsync import catalog, events
from subsync.errors import InputError, SubSyncError, reason_text
from subsync.media import check_ffmpeg
from subsync.models import ProcessingConfig, TranscriptionConfig
from subsync.output import check_output_args, plan_output
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
    generate.set_defaults(handler=run_generate)
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
    """Run `subsync generate` from validated arguments to the summary.

    Stages 0-1 run here and fail fast, before any heavy import: argument
    values (F2, F3), `-o`/`-f` consistency (F4), FFmpeg on PATH (F6), input
    resolution (F7, F8) and the output pre-check (F11, F12). The rest runs in
    `pipeline.generate`, whose stage events become stderr lines. The summary
    goes to stdout.

    Args:
        args: Parsed arguments from the `generate` subcommand (`input`,
            `language`, `model`, `format`, `output`, `force`, `verbose`).

    Returns:
        0 once the subtitle file is written (decision 0009).

    Raises:
        SubSyncError: Any failure, mapped to its exit code by `main`.
    """
    started = time.monotonic()

    _validate_language(args.language)
    _validate_model(args.model)
    check_output_args(args.output, args.format)
    check_ffmpeg()

    source = resolve_input(args.input)
    plan = plan_output(source, args.output, args.format, args.language, args.force)

    from subsync import pipeline  # Imports Whisper and yt-dlp (1-2 s).

    result = pipeline.generate(
        source,
        TranscriptionConfig(model_name=args.model, language=args.language),
        ProcessingConfig(),
        plan,
        args.force,
        _print_stage,
    )

    width = shutil.get_terminal_size().columns
    for line in _summary_lines(result, time.monotonic() - started, args.verbose, width):
        print(_safe(line), file=sys.stdout)
    return 0


# =============================================================================
# Stage lines (stderr) and the summary (stdout)
# =============================================================================

_STAGE_WIDTH = 59
"""Stage lines right-align their time to this column, as in the UX transcript."""

_FLAG_LIMIT = 5
_PREVIEW_WIDTH = 42
_FLAG_LABELS = {"short": "short", "long_word": "long word", "cps": "CPS"}
_UPLOAD_HINT = (
    "Next: YouTube Studio → Subtitles → your video → Add → Upload file → With timing"
)


def _duration(seconds: float) -> str:
    """Format a media duration as `M:SS`, or `H:MM:SS` from one hour."""
    hours, rest = divmod(round(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _elapsed(seconds: float) -> str:
    """Format a stage time as `4s`, `6m 02s` or `1h 02m`."""
    total = round(seconds)
    if total < 60:
        return f"{total}s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def _timestamp(moment: timedelta) -> str:
    """Format a subtitle start as `HH:MM:SS`, as the Studio editor shows it."""
    hours, rest = divmod(int(moment.total_seconds()), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _done(label: str, seconds: float | None = None) -> str:
    """A finished stage line: `✓ <label>`, with its time right-aligned."""
    line = f"✓ {label}"
    if seconds is None:
        return line
    time_text = _elapsed(seconds)
    padding = max(2, _STAGE_WIDTH - len(line) - len(time_text))
    return f"{line}{' ' * padding}{time_text}"


def _language_label(code: str, detected: bool) -> str:
    """`English (auto-detected)` or `English (set with -l)`."""
    name = catalog.LANGUAGES.get(code, code)
    return f"{name} (auto-detected)" if detected else f"{name} (set with -l)"


def _stage_lines(event: events.GenerateEvent) -> list[str]:
    """The stderr lines for one `pipeline.generate` stage event."""
    match event:
        case events.SourceReady(source=source):
            return [
                f"{source.display_name} · {_duration(source.duration or 0)} · local file"
            ]
        case events.AudioExtracted(seconds=seconds):
            return [_done("Extracted audio", seconds)]
        case events.ModelDownloading(model_name=name):
            return [f"  Downloading model '{name}' (one-time)…"]
        case events.ModelLoaded(model_name=name, device=device, seconds=seconds):
            return [_done(f"Loaded model {name} on {device}", seconds)]
        case events.TranscriptionStarted(audio_duration=duration):
            return [f"  Transcribing {_duration(duration)} of audio…"]
        case events.Transcribed(
            seconds=seconds, language=language, language_detected=detected
        ):
            return [
                _done("Transcribed", seconds),
                f"  Language: {_language_label(language, detected)}",
            ]
        case events.Formatted(segment_count=segments, subtitle_count=subtitles):
            return [_done(f"Formatted {segments} segments → {subtitles} subtitles")]
        case events.Written():
            return [_done("Wrote subtitles"), ""]
    return []


def _print_stage(event: events.GenerateEvent, stream: TextIO | None = None) -> None:
    """Print one stage event's lines to stderr as soon as it happens."""
    stream = stream or sys.stderr
    for line in _stage_lines(event):
        print(_safe(line), file=stream, flush=True)


def _preview(text: str, width: int) -> str:
    """Cut `text` to `width` with `…` for display only, padded to `width`."""
    if len(text) > width:
        text = text[: width - 1] + "…"
    return text.ljust(width)


def _summary_lines(
    result: events.GenerateResult, total_seconds: float, verbose: bool, width: int
) -> list[str]:
    """The success summary (R19, P2): file first, then what to review.

    Args:
        result: What `pipeline.generate` produced.
        total_seconds: Wall time of the whole run.
        verbose: List every flagged subtitle instead of the first five.
        width: Terminal width; only the previews are shortened to fit it.

    Returns:
        The summary lines, without trailing newlines.
    """
    report = result.report
    flags = report.flags
    if report.errors:
        headline = "✗ Written but not compliant, please report with -v output"
    elif flags:
        headline = f"✓ Subtitles written, {len(flags)} to review"
    else:
        headline = "✓ Subtitles written"

    duration = _duration(result.source.duration or 0)
    language = _language_label(result.language, result.language_detected)
    lines = [
        headline,
        f"  File:      {result.path}",
        f"  Source:    {result.source.display_name} · {duration}",
        f"  Language:  {language}",
        f"  Model:     {result.model_name} on {result.device}"
        f" · {_elapsed(total_seconds)} total",
        f"  Subtitles: {len(result.subtitles)}",
    ]

    if flags:
        shown = flags if verbose else flags[:_FLAG_LIMIT]
        texts = {subtitle.index: subtitle.text for subtitle in result.subtitles}
        labels = [
            flag.detail
            if flag.kind == "cps" and flag.detail
            else _FLAG_LABELS[flag.kind]
            for flag in shown
        ]
        preview_width = max(
            10, min(_PREVIEW_WIDTH, width - 16 - max(len(label) for label in labels))
        )
        lines += ["", "  To review:"]
        for flag, label in zip(shown, labels, strict=True):
            preview = _preview(texts.get(flag.subtitle_index, ""), preview_width)
            lines.append(f"    {_timestamp(flag.start_time)}  {preview}  {label}")
        hidden = len(flags) - len(shown)
        if hidden:
            lines.append(f"    … {hidden} more (run with -v to list all)")

    lines += ["", f"  {_UPLOAD_HINT}"]
    return lines


_ESCAPED = frozenset(
    "\u2028\u2029\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
)


def _safe(text: str) -> str:
    """Escape control characters before text reaches the terminal.

    File names and transcribed text are untrusted: an escape sequence in a
    file name could otherwise retitle the window, hide lines or write the
    clipboard. Control characters (C0, DEL, C1) and bidirectional overrides
    and line or paragraph separators are shown as ``\\x1b``-style escapes; everything else, emoji included,
    is printed as is. The subtitle file itself is never altered (0008).
    """
    return "".join(
        ch.encode("unicode_escape").decode("ascii")
        if unicodedata.category(ch) == "Cc" or ch in _ESCAPED
        else ch
        for ch in text
    )


class _SafeFormatter(logging.Formatter):
    """A log formatter that escapes control characters, line by line."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the record, then make each of its lines safe to print."""
        return "\n".join(_safe(line) for line in super().format(record).split("\n"))


def _print_traceback() -> None:
    """Print the current exception's traceback to stderr (``-v`` only)."""
    for line in traceback.format_exc().rstrip("\n").split("\n"):
        print(_safe(line), file=sys.stderr)


def _print_error(err: SubSyncError) -> None:
    """Print the ``✗`` error block to stderr: headline, then each hint line."""
    print(_safe(f"✗ {err}"), file=sys.stderr)
    if err.hint:
        for line in err.hint.splitlines():
            print(_safe(f"  {line}"), file=sys.stderr)


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
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_SafeFormatter("%(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.WARNING, handlers=[handler], force=True)
    # -v shows SubSync's own debug records, including the Whisper and FFmpeg
    # output it captures, but not the thousands from its libraries (numba).
    logging.getLogger("subsync").setLevel(logging.DEBUG if verbose else logging.NOTSET)

    try:
        return args.handler(args)
    except SubSyncError as err:
        if verbose:
            _print_traceback()
        _print_error(err)
        return err.exit_code
    except KeyboardInterrupt:
        print("Cancelled. Nothing written.", file=sys.stderr)
        return 130
    except Exception as exc:  # Last-resort boundary (F25).
        if verbose:
            _print_traceback()
        _print_error(
            SubSyncError(
                f"Something went wrong: {reason_text(exc)}.",
                hint="Re-run with -v and share the output.",
            )
        )
        return 1
