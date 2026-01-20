# Task 1: Install Dependencies

## Objective

Set up the development environment with all required dependencies for SubSync.

## Detail Level

EXPANDED

---

## Context

### References

- **Plan**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 1. Dependencies"
- **Context**: [dependencies.md](../../context/dependencies.md)

### Dependencies

- *(None — this is the first task)*

### Context Summary

SubSync requires three core Python packages and one system dependency:

| Package | Purpose | Why This Package |
|---------|---------|------------------|
| `yt-dlp` | YouTube metadata & audio download | Most maintained youtube-dl fork, handles YouTube changes, public domain license |
| `openai-whisper` | Speech-to-text transcription | State-of-the-art accuracy, word-level timestamps, MIT license |
| `rich` | CLI formatting & progress | Beautiful terminal output, widely adopted |
| `FFmpeg` (system) | Audio processing | Required by both yt-dlp and Whisper for audio extraction/conversion |

**Whisper Model Note**: Default model is "turbo" (~800MB). Models download on first use, not during installation.

**FFmpeg Rationale**:
- yt-dlp uses FFmpeg to extract audio from video containers
- Whisper uses FFmpeg to load/process audio files
- Cannot be installed via pip — must be system-installed

---

## Requirements

### Core Dependencies

| Package | Purpose |
|---------|---------|
| `yt-dlp` | YouTube video metadata extraction and audio download |
| `openai-whisper` | Speech-to-text transcription |
| `rich` | CLI formatting and progress display |

### Development Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-cov` | Test coverage reporting |

### System Requirements

FFmpeg must be available in PATH (required by yt-dlp and Whisper).

---

## Acceptance Criteria

- [x] All dependencies listed in `pyproject.toml`
- [x] `uv sync` completes without errors
- [x] `import yt_dlp` succeeds in Python
- [x] `import whisper` succeeds in Python
- [x] `import rich` succeeds in Python
- [x] `import pytest` succeeds in Python
- [x] `ffmpeg -version` returns version info
- [x] `task lint` passes

---

## Test Scenarios

| Scenario | Command | Expected Outcome |
|----------|---------|------------------|
| Sync dependencies | `uv sync` | Completes without errors |
| Import yt-dlp | `uv run python -c "import yt_dlp"` | No error |
| Import whisper | `uv run python -c "import whisper"` | No error |
| Import rich | `uv run python -c "import rich"` | No error |
| Import pytest | `uv run python -c "import pytest"` | No error |
| FFmpeg available | `ffmpeg -version` | Shows version, not "command not found" |

---

## Implementation Checklist

1. [x] Add core dependencies: `uv add yt-dlp openai-whisper rich`
2. [x] Add dev dependencies: `uv add --group dev pytest pytest-cov`
3. [x] Verify sync: `uv sync`
4. [x] Test all imports work
5. [x] Verify FFmpeg: `ffmpeg -version`
6. [x] Run: `task lint` — verify pass

---

## Definition of Done

- All dependencies in `pyproject.toml`
- All dependencies install via `uv sync`
- All Python imports work
- FFmpeg confirmed available
- Linting passes

---

## Notes

- If FFmpeg missing, install via: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)
- Whisper downloads model files on first use (~1.5GB for turbo model)
- GPU support is optional; Whisper auto-detects and falls back to CPU

---

## Next Task

→ [02-error-definitions.md](./02-error-definitions.md)
