# Third-Party Dependencies

## Overview

This document captures information about external dependencies required for SubSync, including their purpose, licensing, and integration considerations.

**Revised 2026-09-25 for SubSync v1**: FFmpeg is now used directly for local files, the yt-dlp update policy (P7), Whisper's model cache (P6), Apple Silicon as the main platform, the lazy-import requirement, and a possible engine change after the E1 spike. Sources: [product brief](../../docs/product-design/subsync-v1/product-brief.md), [handoff](../../docs/product-design/subsync-v1/handoff.md), [phase 4 plan](../plan/phase-4-cli-output.md).

---

## Required Dependencies

### yt-dlp

**Purpose**: YouTube video metadata extraction and audio download

| Property | Value |
|----------|-------|
| Package | `yt-dlp` |
| License | Unlicense (Public Domain) |
| PyPI | https://pypi.org/project/yt-dlp/ |
| GitHub | https://github.com/yt-dlp/yt-dlp |

**Key Features Used**:
- Video metadata extraction (title, duration, availability)
- Audio-only download
- Format selection for best audio quality
- Progress callbacks for user feedback
- Python embedding API

**Considerations**:
- Requires FFmpeg for audio extraction
- Regular updates needed (YouTube changes frequently)
- Can handle cookies for age-restricted content, but SubSync v1 does not use cookies
- Well-documented error handling with specific exception types

**Update policy (P7)**: no exact version pin. `pyproject.toml` keeps a minimum version and `uv.lock` records the tested one. YouTube changes break old yt-dlp versions within weeks, so when a download fails because yt-dlp is out of date, SubSync shows the exact upgrade command for how it is installed (F18; detection is E11, install method E12).

**Retries (P4)**: rely on yt-dlp's built-in retries and timeouts; a network failure exits 3 with "check your connection and re-run". Retry and timeout options are chosen in S4 planning (E6).

**Used only for URL input**: the local-file route makes no network calls (R4).

---

### OpenAI Whisper

**Purpose**: Speech-to-text transcription with timestamps

| Property | Value |
|----------|-------|
| Package | `openai-whisper` |
| License | MIT |
| PyPI | https://pypi.org/project/openai-whisper/ |
| GitHub | https://github.com/openai/whisper |

**Available Models**:

| Model | Parameters | VRAM | Relative Speed | Use Case |
|-------|------------|------|----------------|----------|
| tiny | 39M | ~1GB | ~10x | Testing only |
| base | 74M | ~1GB | ~7x | Quick drafts |
| small | 244M | ~2GB | ~4x | Acceptable quality |
| medium | 769M | ~5GB | ~2x | Good quality |
| large-v3 | 1550M | ~10GB | 1x | Best accuracy |
| **turbo** | 809M | ~6GB | ~8x | **Recommended default** |

**Key Features**:
- Word-level timestamps for precise subtitle timing
- 99+ language support with auto-detection
- GPU acceleration with CUDA
- CPU fallback when GPU unavailable

**Considerations**:
- First run downloads model (~1-6GB depending on size); SubSync shows a one-time download notice (R7)
- GPU (CUDA) significantly faster than CPU
- **Model cache (P6)**: Whisper's own download cache (`~/.cache/whisper`, or under `XDG_CACHE_HOME`) is enough; SubSync builds no cache of its own. Once a model is cached, transcription needs no network
- **No automatic model fallback (P5)**: on a memory or load failure SubSync exits 4 and suggests `-m small`
- **Apple Silicon**: the installed openai-whisper runs on the CPU on Igor's Mac (M1 Max); SubSync does not use the Apple GPU through openai-whisper
- **Import cost**: importing Whisper (and torch) takes about 1–2 s. SubSync imports it lazily, after argument validation, the FFmpeg check and the output pre-check, and keeps Whisper's model names and language codes as static lists with a test that detects drift
- **Engine may change (E1)**: a spike after slice S1 compares openai-whisper on CPU with mlx-whisper, faster-whisper and whisper.cpp against the speed target (N1). Any replacement sits behind `TranscriptionResult` and must keep word timestamps, the vocabulary prompt and the standard model names used by `-m` (P3)

**Output Structure** (conceptual):
- Full text transcription
- Detected language code
- Segments with start/end times and text
- Optional word-level timing within segments

---

### FFmpeg

**Purpose**: Audio format conversion and processing

| Property | Value |
|----------|-------|
| Type | System dependency (not Python package) |
| License | GPL/LGPL |
| Website | https://ffmpeg.org/ |

**Installation**:
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `apt install ffmpeg`
- Windows: `choco install ffmpeg`

**Why Required**:
1. yt-dlp uses it to extract audio from video containers
2. Whisper uses it to load and process audio files
3. Audio conversion to Whisper-optimal format (16kHz mono WAV)
4. **SubSync uses it directly for local files (E2)**: `ffprobe` reads the duration and checks that an audio stream exists and decodes; `ffmpeg` extracts the default audio stream to a 16 kHz mono WAV in the run's temporary folder

**Preflight**: both `ffmpeg` and `ffprobe` must be on PATH. SubSync checks this before any heavy work and fails in under 1 s with an install hint (`brew install ffmpeg`, F6, exit 1).

---

## Optional Dependencies

### For CLI Enhancement

| Package | Purpose | License |
|---------|---------|---------|
| `rich` | Progress bars, colored output | MIT |

### For Testing

| Package | Purpose | License |
|---------|---------|---------|
| `pytest` | Test framework | MIT |
| `pytest-cov` | Coverage reporting | MIT |

The opt-in end-to-end tests (`pytest -m e2e`) also need macOS `say` to generate a speech clip, plus FFmpeg; they are skipped where either is missing. There is no CI until slice S5.

---

## System Requirements

### Minimum

- Python 3.13+
- FFmpeg installed and in PATH
- 4GB RAM
- 10GB disk space (for models)

### Main Platform (v1)

- macOS on Apple Silicon (Igor's Mac: M1 Max, 32 GB)
- FFmpeg from Homebrew
- Linux should work but is not a v1 acceptance target

### GPU and CPU

Whisper uses CUDA when an NVIDIA GPU is available and otherwise runs on the CPU:
- CPU is significantly slower (5-20x)
- Still functional for all model sizes
- The speed target is a 15-minute episode in ≤ 15 minutes (aim ≤ 5) with the default model on Igor's Mac (N1). Whether openai-whisper on CPU meets it is measured after S1; see "Engine may change" above

---

## Security Considerations

1. **yt-dlp**: Only downloads from YouTube, no arbitrary code execution
2. **Whisper**: Local model, no data sent to external services
3. **FFmpeg**: Well-audited, industry standard
4. **User content**: Audio files should be temporary, deleted after processing; local files and their transcripts never leave the machine (R4)

---

## References

- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp#readme)
- [Whisper Documentation](https://github.com/openai/whisper#readme)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
