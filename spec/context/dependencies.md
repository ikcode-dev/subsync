# Third-Party Dependencies - Context

## Overview

This document captures information about external dependencies required for SubSync, including their purpose, licensing, and integration considerations.

---

## Required Dependencies

### yt-dlp

**Purpose**: YouTube video metadata extraction and audio download

| Property | Value |
|----------|-------|
| **Package** | `yt-dlp` |
| **License** | Unlicense (Public Domain) |
| **PyPI** | https://pypi.org/project/yt-dlp/ |
| **GitHub** | https://github.com/yt-dlp/yt-dlp |

#### Key Features Used

- Video metadata extraction (title, duration, availability)
- Audio-only download (`extract_audio=True`)
- Format selection (`bestaudio/best`)
- Progress callbacks
- Python embedding API

#### Integration Pattern

```python
import yt_dlp

ydl_opts = {
    'format': 'bestaudio/best',
    'extract_audio': True,
    'audio_format': 'wav',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
    }],
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=True)
```

#### Considerations

- Requires FFmpeg for audio extraction
- Regular updates needed (YouTube changes frequently)
- Handles cookies for age-restricted content

---

### OpenAI Whisper

**Purpose**: Speech-to-text transcription with timestamps

| Property | Value |
|----------|-------|
| **Package** | `openai-whisper` |
| **License** | MIT |
| **PyPI** | https://pypi.org/project/openai-whisper/ |
| **GitHub** | https://github.com/openai/whisper |

#### Available Models

| Model | Parameters | VRAM | Relative Speed | Use Case |
|-------|------------|------|----------------|----------|
| tiny | 39M | ~1GB | ~10x | Testing only |
| base | 74M | ~1GB | ~7x | Quick drafts |
| small | 244M | ~2GB | ~4x | Acceptable quality |
| medium | 769M | ~5GB | ~2x | Good quality |
| large-v3 | 1550M | ~10GB | 1x | Best accuracy |
| **turbo** | 809M | ~6GB | ~8x | **Recommended default** |

#### Integration Pattern

```python
import whisper

model = whisper.load_model("turbo")
result = model.transcribe(
    audio_path,
    language="en",
    word_timestamps=True,
    verbose=False
)
```

#### Output Structure

```python
{
    "text": "Full transcription text",
    "language": "en",
    "segments": [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.5,
            "text": "Segment text",
            "words": [
                {"word": "Segment", "start": 0.0, "end": 0.5},
                {"word": "text", "start": 0.6, "end": 1.0}
            ]
        }
    ]
}
```

#### Considerations

- First run downloads model (~1-6GB depending on size)
- GPU (CUDA) significantly faster than CPU
- Word timestamps enable precise subtitle timing
- Supports 99+ languages with auto-detection

---

### FFmpeg

**Purpose**: Audio format conversion and processing

| Property | Value |
|----------|-------|
| **Type** | System dependency |
| **License** | GPL/LGPL |
| **Website** | https://ffmpeg.org/ |

#### Installation

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
apt install ffmpeg

# Windows
choco install ffmpeg
```

#### Why Required

1. **yt-dlp**: Extracts audio from video containers
2. **Whisper**: Loads and processes audio files
3. **Audio conversion**: Normalize to Whisper-optimal format (16kHz WAV)

---

## Optional Dependencies

### For CLI Enhancement

| Package | Purpose | License |
|---------|---------|---------|
| `rich` | Progress bars, colored output | MIT |
| `click` | CLI framework (alternative to argparse) | BSD |
| `typer` | Modern CLI with type hints | MIT |

### For Subtitle Handling

| Package | Purpose | License |
|---------|---------|---------|
| `pysrt` | SRT file manipulation | GPL |
| `webvtt-py` | WebVTT parsing/generation | MIT |

### For Testing

| Package | Purpose | License |
|---------|---------|---------|
| `pytest` | Test framework | MIT |
| `pytest-cov` | Coverage reporting | MIT |
| `responses` | HTTP mocking | Apache 2.0 |

---

## Dependency Management

### Installation Commands

```bash
# Core dependencies
uv add yt-dlp openai-whisper

# CLI enhancement
uv add rich

# Development dependencies
uv add --group dev pytest pytest-cov ruff
```

### Version Pinning Strategy

- Pin major versions for stability
- Allow minor/patch updates for security fixes
- Lock file (`uv.lock`) for reproducibility

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
- Consider smaller models for CPU-only

---

## Security Considerations

1. **yt-dlp**: Only downloads from YouTube, no arbitrary code execution
2. **Whisper**: Local model, no data sent to external services
3. **FFmpeg**: Well-audited, industry standard
4. **User content**: Audio files are temporary, deleted after processing
