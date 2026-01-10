# Third-Party Dependencies

## Overview

This document captures information about external dependencies required for SubSync, including their purpose, licensing, and integration considerations.

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
- Handles cookies for age-restricted content
- Well-documented error handling with specific exception types

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
- First run downloads model (~1-6GB depending on size)
- GPU (CUDA) significantly faster than CPU
- Model loading can be cached for repeated use

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

---

## System Requirements

### Minimum

- Python 3.13+
- FFmpeg installed and in PATH
- 4GB RAM
- 10GB disk space (for models)

### Recommended (for GPU acceleration)

- NVIDIA GPU with CUDA support
- 8GB+ VRAM for larger models
- CUDA toolkit installed

### CPU Fallback

Whisper automatically falls back to CPU if CUDA unavailable:
- Significantly slower (5-20x)
- Still functional for all model sizes
- Consider smaller models (base, small) for CPU-only usage

---

## Security Considerations

1. **yt-dlp**: Only downloads from YouTube, no arbitrary code execution
2. **Whisper**: Local model, no data sent to external services
3. **FFmpeg**: Well-audited, industry standard
4. **User content**: Audio files should be temporary, deleted after processing

---

## References

- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp#readme)
- [Whisper Documentation](https://github.com/openai/whisper#readme)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
