# src/subsync — application code

Rules for editing the SubSync package. Project-wide rules (commands, `uv` only, commits, decisions) are in the [root AGENTS.md](../../AGENTS.md).

## Modules

Update this list when you add, rename or retire a module.

| Module | Responsibility |
|---|---|
| `cli.py` | Entry point `subsync.cli:main`: arguments, stage 0–1 fail-fast checks, stage lines (stderr), summary (stdout), error boundary and exit codes |
| `catalog.py` | Static Whisper model names and language codes, so `-m`/`-l` validate without importing Whisper (drift-tested) |
| `sources.py` | Resolves INPUT into a `MediaSource` (local file in S1; a YouTube URL gets the interim message until S4) |
| `output.py` | Output naming (`-o`), the fail-fast pre-check for existing output, `OutputPlan` |
| `media.py` | FFmpeg check, media probe (duration, no-audio, unreadable) and 16 kHz mono WAV extraction for local files |
| `events.py` | Stage events and `GenerateResult` from `generate()`; imports no ML code, so the CLI renders events without the heavy import |
| `pipeline.py` | `generate()`: one orchestrator from resolved source to written file, reporting stage events ([0007](../../decisions/0007-one-generate-orchestrator-with-mediasource.md)); `process_video()` is the Phase 2 URL pipeline, retired in S4 |
| `transcriber.py` | Checks the Whisper cache, loads a model and transcribes with word-level timestamps, keeping Whisper's output off the terminal |
| `processor.py` | Turns a `TranscriptionResult` into compliant `Subtitle`s (timing, splitting, line breaks, long words) and a `ComplianceReport` |
| `writer.py` | Renders SRT and writes the file in one step, never leaving a partial file |
| `url_handler.py` | Parses YouTube URLs and extracts the 11-character video ID |
| `audio_extractor.py` | Reads YouTube video metadata and downloads audio as a 16 kHz mono WAV via yt-dlp |
| `progress.py` | `ProgressMapper` maps sub-task progress onto overall pipeline progress |
| `models.py` | Dataclasses for sources, metadata, transcription, subtitles, configs and compliance reports |
| `errors.py` | Exception hierarchy rooted at `SubSyncError`; each category carries its hint and exit code |

Modules planned for each slice are listed in the [implementation roadmap](../../docs/product-engineering/subsync-v1/implementation-roadmap.md).

## Python conventions

- Pragmatic, readable code over clever abstractions. PEP 8, enforced by ruff.
- Type hints on every argument and return value; docstrings on modules, classes and functions.
- Raise the specific exceptions from `errors.py`, never a bare or generic `Exception`.
- Use `logging` for debug and info messages. `print` (or `rich`) is only for CLI user output.
- Dataclass list defaults use `field(default_factory=lambda: [])`, not `field(default_factory=list)`, so Pyright infers the element type:

  ```python
  words: list[Word] = field(default_factory=lambda: [])
  ```

## Behavior rules

- Netflix compliance defaults live in `ProcessingConfig` (42 chars per line, 2 lines, 833–7000 ms, 83 ms gap, 20 CPS). Do not hard-code them elsewhere.
- The processor never rewrites transcribed text; it fixes timing and warns ([0008](../../decisions/0008-never-rewrite-transcribed-text.md)).
- The exit code answers "was an uploadable file written"; compliance warnings never fail a run ([0009](../../decisions/0009-exit-code-reports-whether-a-file-was-written.md)). Exit codes are listed in the [phase 4 plan](../../spec/plan/phase-4-cli-output.md#exit-codes-r22).
- CLI: Unix conventions. Progress, warnings and errors go to stderr, the summary to stdout. No tracebacks unless `-v`. Leave room for future subcommands such as `translate`.
- Fast startup: the argument, preflight and input-resolution path must not import whisper, torch or yt-dlp ([phase 4 plan, Fast Startup](../../spec/plan/phase-4-cli-output.md#fast-startup)). `transcriber.py` still imports whisper at module level; import it lazily from the CLI path.
- Local media never leaves the machine; only URL input and the first model download use the network ([0004](../../decisions/0004-transcribe-locally.md)).
