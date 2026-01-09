# Task 1: Install Dependencies

## Overview

Install all required project dependencies and verify they work correctly. This is the foundational task that enables all subsequent development.

**Plan Reference**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 1. Dependencies Setup"

**Context Reference**: [dependencies.md](../../context/dependencies.md)

---

## Objective

Set up the development environment with all required dependencies for SubSync.

---

## Requirements

### Core Dependencies

Install the following production dependencies:

| Package | Purpose |
|---------|---------|
| `yt-dlp` | YouTube video metadata extraction and audio download |
| `openai-whisper` | Speech-to-text transcription |
| `rich` | CLI formatting and progress display |

### Development Dependencies

Install the following dev dependencies:

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-cov` | Test coverage reporting |

### System Requirements

Verify FFmpeg is available in PATH (required by yt-dlp for audio extraction).

---

## Implementation Steps

1. **Add core dependencies**:
   ```bash
   uv add yt-dlp openai-whisper rich
   ```

2. **Add dev dependencies**:
   ```bash
   uv add --group dev pytest pytest-cov
   ```

3. **Verify FFmpeg availability**:
   ```bash
   ffmpeg -version
   ```

4. **Verify Python imports work**:
   ```python
   import yt_dlp
   import whisper
   import rich
   ```

---

## Verification Checklist

- [x] `uv sync` completes without errors
- [x] `uv run python -c "import yt_dlp"` succeeds
- [x] `uv run python -c "import whisper"` succeeds
- [x] `uv run python -c "import rich"` succeeds
- [x] `uv run python -c "import pytest"` succeeds
- [x] `ffmpeg -version` returns version info (not "command not found")
- [x] `task lint` passes

---

## Definition of Done

- All dependencies are listed in `pyproject.toml`
- All dependencies install successfully via `uv sync`
- All imports work from Python
- FFmpeg is confirmed available
- No linting errors

---

## Notes

- Whisper will download model files on first use (~1.5GB for turbo model)
- If FFmpeg is not installed, instruct user to install via: `brew install ffmpeg` (macOS)
- GPU support is optional; Whisper will auto-detect and use CPU if CUDA unavailable

---

## Next Task

After verification, proceed to → [02-error-definitions.md](./02-error-definitions.md)

---

## User Verification Required

**STOP** after completing this task. Present the changes to the user and wait for verification before proceeding to the next task.
