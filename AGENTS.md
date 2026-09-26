# AGENTS.md

Guidance for coding agents working in this repository. Read this file first; open the linked files only when the task needs them.

## Project

SubSync is a Python CLI tool that turns a local video file or a YouTube video into a Netflix-compliant subtitle file, using local AI (OpenAI Whisper). Translation to other languages is the next increment after v1. Entry point: `subsync.cli:main`.

- **Stack**: Python 3.13+, uv and uv_build, pytest, ruff, Taskfile
- **Key dependencies**: `yt-dlp` (YouTube audio download), `openai-whisper` (transcription), `rich` (terminal output)
- **System dependency**: FFmpeg (`ffmpeg` and `ffprobe`) on PATH (`brew install ffmpeg`)

Pipeline: input (local file or YouTube URL) → audio (FFmpeg extraction or yt-dlp download) → transcriber → subtitle processor → writer. SRT is the primary output format; VTT is optional.

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

## Map

Before working in a directory, read its `AGENTS.md`. Those files hold the rules for that area and are not repeated here.

| Path | What it is | Read first |
|---|---|---|
| `src/subsync/` | Application code: module map, Python conventions, CLI and behavior rules | [src/subsync/AGENTS.md](src/subsync/AGENTS.md) |
| `tests/` | Test suite: conventions, stand-ins, test layers | [tests/AGENTS.md](tests/AGENTS.md) |
| `spec/` | Specifications: context, phase plans, task files, templates | [spec/AGENTS.md](spec/AGENTS.md), then the subdirectory's `AGENTS.md` |
| `docs/` | Product-design and product-engineering documents | [docs/AGENTS.md](docs/AGENTS.md) |
| `decisions/` | Decision records | [decisions/README.md](decisions/README.md) (index) |

## Source of truth

When documents disagree, the first in this list wins:

1. Accepted [decision records](decisions/README.md).
2. The agreed v1 product documents in [`docs/product-design/subsync-v1/`](docs/product-design/subsync-v1/index.md) (brief, UX flows, handoff).
3. The [implementation roadmap](docs/product-engineering/subsync-v1/implementation-roadmap.md): delivery order, current status, next dispatchable work.
4. `spec/` plans and task files.
5. [`docs/SUBTITLE_GENERATION_ALGORITHM.md`](docs/SUBTITLE_GENERATION_ALGORITHM.md), background only.

## Spec-driven development

`spec/` defines **what** to build and **why**, never **how**. Workflow: context → plan → tasks → implementation. When implementing a task, read its spec first; it holds the requirements, acceptance criteria and test scenarios. Mark its acceptance criteria as done once verified. Authoring rules: [spec/AGENTS.md](spec/AGENTS.md).

## Decisions

Decisions that shape this project are recorded in [decisions/README.md](decisions/README.md). Read the index before changing structure, conventions, or dependencies. Record new decisions as a new numbered file; never edit an accepted record, supersede it.

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- **Scope is required**. Common scopes: `cli`, `transcribe`, `subtitles`, `audio`, `deps`, `config`, `agents`, `decisions`; use `phase-N` or `slice-N` for spec work on a phase or slice
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
