# src/subsync — application code

Rules for editing the SubSync package. Project-wide rules (commands, `uv` only, commits, decisions) are in the [root AGENTS.md](../../AGENTS.md).

## Modules

Update this list when you add, rename or retire a module.

| Module | Responsibility |
|---|---|
| `cli.py` | Entry point `subsync.cli:main` (placeholder until slice S1) |
| `url_handler.py` | Parses YouTube URLs and extracts the 11-character video ID |
| `audio_extractor.py` | Reads YouTube video metadata and downloads audio as a 16 kHz mono WAV via yt-dlp |
| `transcriber.py` | Loads a Whisper model and transcribes audio with word-level timestamps |
| `pipeline.py` | Orchestrates URL → metadata → audio → transcription and cleans up temp files (`process_video()`, retired in S4 by `generate()`, [0007](../../decisions/0007-one-generate-orchestrator-with-mediasource.md)) |
| `progress.py` | `ProgressMapper` maps sub-task progress onto overall pipeline progress |
| `models.py` | Dataclasses for metadata, transcription, subtitles, configs and compliance reports |
| `errors.py` | Exception hierarchy rooted at `SubSyncError` |

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
