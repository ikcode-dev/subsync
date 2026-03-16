# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SubSync is a Python CLI tool that generates Netflix-compliant subtitles for YouTube videos using local AI (OpenAI Whisper). Entry point: `subsync.cli:main`.

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

Pipeline: URL Handler → Audio Extractor → Transcriber → Subtitle Processor → Writer

Source is in `src/subsync/`, tests in `tests/`. Currently Phase 1 (foundation) is complete; Phase 2 (core pipeline) is next.

Key modules:
- `url_handler.py` — Parses YouTube URLs, extracts 11-char video IDs
- `models.py` — Dataclasses for video metadata, transcription segments, subtitles, configs, and Netflix compliance validation
- `errors.py` — Exception hierarchy rooted at `SubSyncError` (URLParseError, VideoUnavailableError, AgeRestrictedError, LiveStreamError, TranscriptionError)
- `cli.py` — CLI entry point (placeholder, to be expanded)

## Spec-Driven Development

The `spec/` directory defines **what** to build and **why**, never **how**. Implementation decisions belong in code, not specs.

- `spec/context/` — Domain knowledge, constraints (Netflix compliance rules, YouTube URL formats, dependencies)
- `spec/plan/` — Phase-level architecture and strategy (phases 1–4)
- `spec/tasks/` — Atomic work units with acceptance criteria and test scenarios

When implementing a task, read its spec file first — it contains all requirements, acceptance criteria, and test scenarios.

## Coding Conventions

- Python 3.13+, type hints on all function signatures
- Use `logging` module, not `print` (except CLI user output)
- Use specific exceptions from `errors.py`, never bare `Exception`
- Dataclass mutable defaults: use `field(default_factory=lambda: [])` not `field(default_factory=list)` — avoids Pyright type inference issues
- Netflix compliance defaults are in `ProcessingConfig` (42 chars/line, 833–7000ms duration, 20 CPS max)
