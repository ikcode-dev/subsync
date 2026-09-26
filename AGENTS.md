# AGENTS.md

Guidance for coding agents working in this repository.

## Project

SubSync is a Python CLI tool that turns a local video file or a YouTube video into a Netflix-compliant subtitle file, using local AI (OpenAI Whisper). Translation to other languages is the next increment after v1. Entry point: `subsync.cli:main`.

- **Language**: Python 3.13+
- **Package manager / build**: uv, uv_build
- **Testing**: pytest
- **Linting / formatting**: ruff
- **Task runner**: Taskfile
- **Key dependencies**: `yt-dlp` (YouTube audio download), `openai-whisper` (transcription), `rich` (terminal output)
- **System dependency**: FFmpeg (`ffmpeg` and `ffprobe`) must be on PATH (`brew install ffmpeg`)

## Commands

| Task | Command |
|------|---------|
| Install deps | `task install` or `uv sync` |
| Run app | `task run` or `uv run subsync` |
| Run all tests | `task test` or `uv run pytest` |
| Run single test | `uv run pytest tests/test_file.py::test_name` |
| Lint | `task lint` or `uv run ruff check .` |
| Format | `task format` or `uv run ruff format .` |
| Add dependency | `uv add <package>` |
| Add dev dependency | `uv add --group dev <package>` |

**Never use `pip`** — always use `uv` for package management and execution.

## Architecture

Pipeline: Input (local file or YouTube URL) → audio (FFmpeg extraction or yt-dlp download) → Transcriber → Subtitle Processor → Writer

Subtitle output follows the Netflix Timed Text Style Guide. SRT is the primary format; VTT is optional (planned for slice S5).

Source is in `src/subsync/`, tests in `tests/`. Phases 1 (foundation) and 2 (core pipeline) are merged. v1 is delivered in vertical slices S1–S5 that cut across Phase 3 (Netflix compliance) and Phase 4 (CLI and output); see the [implementation roadmap](docs/product-engineering/subsync-v1/implementation-roadmap.md). The product/design source of truth (brief, UX flows, handoff) is [`docs/product-design/subsync-v1/`](docs/product-design/subsync-v1/index.md).

Key modules:
- `url_handler.py` — Parses YouTube URLs, extracts 11-char video IDs
- `audio_extractor.py` — Extracts video metadata and downloads audio as 16kHz mono WAV via yt-dlp
- `transcriber.py` — Loads a Whisper model and transcribes audio with word-level timestamps
- `pipeline.py` — Orchestrates URL → metadata → audio → transcription, including temp-file cleanup
- `progress.py` — `ProgressMapper` maps sub-task progress onto overall pipeline progress
- `models.py` — Dataclasses for video metadata, transcription segments, subtitles, configs, and Netflix compliance validation
- `errors.py` — Exception hierarchy rooted at `SubSyncError` (URLParseError, VideoUnavailableError, AgeRestrictedError, LiveStreamError, TranscriptionError)
- `cli.py` — CLI entry point (placeholder, to be expanded)

## Spec-Driven Development

The `spec/` directory defines **what** to build and **why**, never **how**. Implementation decisions belong in code, not specs.

- `spec/context/` — Domain knowledge, constraints (Netflix compliance rules, YouTube URL formats, dependencies)
- `spec/plan/` — Phase-level architecture and strategy (phases 1–4)
- `spec/tasks/` — Atomic work units with acceptance criteria and test scenarios (per phase for phases 1–2, per slice for v1)

Workflow: context → plan → tasks → implementation. When implementing a task, read its spec file first — it contains all requirements, acceptance criteria, and test scenarios. Mark its acceptance criteria as done once they are verified.

Each `spec/` subdirectory has its own `AGENTS.md` with authoring rules for that kind of document.

## Coding Conventions

- Favor pragmatic, readable code over clever abstractions — simplicity wins
- Follow PEP 8 (enforced by ruff)
- Type hints on all function arguments and return values
- Docstrings for modules, classes, and functions
- Use specific exceptions from `errors.py`, never bare or generic `Exception`
- Use the `logging` module for debug/info messages, not `print` (except CLI user output)
- Netflix compliance defaults live in `ProcessingConfig` (42 chars/line, 2 lines, 833–7000ms duration, 20 CPS max for adult content)

### Dataclass mutable defaults

Use `field(default_factory=lambda: [])` instead of `field(default_factory=list)` so Pyright/Pylance infers the element type from the annotation:

```python
# ❌ Causes "Type is partially unknown" warning
words: list[Word] = field(default_factory=list)

# ✅ Type checker infers list[Word] correctly
words: list[Word] = field(default_factory=lambda: [])
```

### CLI design

- Follow Unix CLI conventions: clear exit codes, errors to stderr
- Design for future commands (`transcribe`, `translate`)

## Testing

- Tests live in `tests/` and follow pytest conventions
- Write tests when adding logic, especially to cover edge cases
- Prefer unit tests for pure functions
- Keep tests deterministic — no network calls unless explicitly requested and properly isolated

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- **Scope is required**. Common scopes: `cli`, `transcribe`, `subtitles`, `audio`, `deps`, `config`; use `phase-N` for spec work on a phase
- Imperative mood ("add", not "added" or "adds"), lowercase first letter, no trailing period
- Subject line ≤ 50 characters when possible, 72 max
- Body explains what and why, not how; wrap at 72 characters
- Breaking changes: add `!` after the type/scope and a `BREAKING CHANGE:` footer

Examples:

```
feat(cli): add --output flag for custom output path
fix(subtitles): prevent overlapping subtitle timestamps
docs(phase-2): mark all tasks as complete
feat(cli)!: change default output format to VTT

BREAKING CHANGE: Default subtitle format changed from SRT to VTT.
Use --format srt for previous behavior.
```
