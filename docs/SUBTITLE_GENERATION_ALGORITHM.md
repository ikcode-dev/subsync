# YouTube Video Subtitle Generation Algorithm

> **Background document (revised 2026-09-25 for SubSync v1).** v1 behavior is defined by the product/design documents in [`docs/product-design/subsync-v1/`](product-design/subsync-v1/index.md) and by the specs in [`spec/`](../spec/); where they differ, they win. In short: input is a **local media file or a YouTube URL**; the model is chosen with **`-m/--model`** (default `turbo`), not `-q/--quality`; there is **no `--children`** option; translation is the next increment after v1.

This algorithm has been created using Claude Opus 4.5.

## Executive Summary

This document outlines the algorithm and architecture for the **subsync** CLI application's core feature: generating Netflix-compliant subtitles from YouTube videos. The system extracts audio from YouTube videos, transcribes the speech using AI, processes the transcription to meet professional subtitle standards, and outputs YouTube-compatible subtitle files.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Detailed Algorithm](#3-detailed-algorithm)
4. [Netflix Compliance Rules](#4-netflix-compliance-rules)
5. [YouTube Format Compatibility](#5-youtube-format-compatibility)
6. [Third-Party Tools & Services](#6-third-party-tools--services)
7. [Data Structures](#7-data-structures)
8. [Error Handling](#8-error-handling)
9. [Future Extensibility: Translation](#9-future-extensibility-translation)
10. [Visual Diagrams](#10-visual-diagrams)

---

## 1. System Overview

### Purpose
Transform YouTube video audio into professional-quality subtitles that:
- Are accurately transcribed in the video's spoken language
- Meet Netflix's Timed Text Style Guide requirements
- Are formatted for direct upload to YouTube
- Support future translation capabilities

### Input
- A local video or audio file (mp4, mov, mkv, webm, m4a, mp3, wav), or a YouTube video URL (public or unlisted)
- Optional: spoken language code (auto-detected by default)
- Optional: output path, format, Whisper model name (`-m`), vocabulary hint

### Output
- SRT subtitle file (primary format - universal compatibility)
- Optional: VTT file (WebVTT format)

---

## 2. Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SUBSYNC CLI                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐│
│  │   URL        │    │   Audio      │    │              │    │  Subtitle  ││
│  │   Handler    │───▶│   Extractor  │───▶│  Transcriber │───▶│  Processor ││
│  │              │    │   (yt-dlp)   │    │  (Whisper)   │    │  (Netflix) ││
│  └──────────────┘    └──────────────┘    └──────────────┘    └─────┬──────┘│
│                                                                      │       │
│                                                                      ▼       │
│                      ┌──────────────────────────────────────────────────────┤
│                      │                                                       │
│                      │  ┌────────────┐    ┌────────────┐    ┌────────────┐ │
│                      │  │  Subtitle  │    │    SRT     │    │    VTT     │ │
│                      └─▶│   Writer   │───▶│   Output   │    │   Output   │ │
│                         │            │    │            │    │ (optional) │ │
│                         └────────────┘    └────────────┘    └────────────┘ │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────┤
│  │                    FUTURE: Translation Module                             │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────┐                     │
│  │  │  Google    │    │   DeepL    │    │   OpenAI   │                     │
│  │  │ Translate  │    │    API     │    │    API     │                     │
│  │  └────────────┘    └────────────┘    └────────────┘                     │
│  └──────────────────────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| **URL Handler** | Validate YouTube URLs, extract video ID |
| **Audio Extractor** | Download audio stream using yt-dlp |
| **Transcriber** | Convert speech to text with timestamps |
| **Subtitle Processor** | Apply Netflix timing/formatting rules |
| **Subtitle Writer** | Generate output files (SRT, VTT) |
| **Translation Module** | (Future) Translate subtitles to other languages |

---

## 3. Detailed Algorithm

### Step 1: Input Validation

```
INPUT: input (file path or YouTube URL), [language_code], [output_path], [format], [model]

PROCESS:
  1. Resolve the input (v1)
     - An existing file → local-file route (FFmpeg extracts the audio, offline)
     - Otherwise a supported YouTube URL → URL route; supported formats:
       • https://www.youtube.com/watch?v=VIDEO_ID
       • https://youtu.be/VIDEO_ID
       • https://www.youtube.com/embed/VIDEO_ID
       • https://www.youtube.com/v/VIDEO_ID
       • https://youtube.com/shorts/VIDEO_ID  (v1)
       • https://m.youtube.com/watch?v=VIDEO_ID  (v1)
     - Anything else → error with both accepted forms (exit 2)

  2. Validate language code against Whisper supported languages
     - List of 99+ supported languages
     - Auto-detection available if not specified

  3. Validate the model name, the format and the output path
     - The output folder must exist (it is never created)
     - An existing output file is refused without --force, before any heavy work
     - FFmpeg must be on PATH

OUTPUT: Validated parameters object
```

### Step 2: Video Metadata Extraction

```
INPUT: video_id

PROCESS (using yt-dlp):
  1. Extract video information without downloading
     - Title (for output filename)
     - Duration (for progress estimation)
     - Availability status
     - Video ID confirmation

  2. Check for restrictions:
     - Age restriction
     - Region locking
     - Private/unlisted status
     - Live stream (not supported)

OUTPUT: VideoMetadata {
  id: str,
  title: str,
  duration: float,
  uploader: str,
  upload_date: str
}

ERRORS:
  - VideoUnavailable: Video is private or deleted
  - AgeRestricted: Video requires age verification
  - LiveStream: Live streams not supported
```

### Step 3: Audio Extraction

```
INPUT: VideoMetadata, temp_directory

PROCESS (using yt-dlp):
  1. Configure extraction options:
     - format: "bestaudio/best"
     - extract_audio: True
     - audio_format: "wav"  # Best for Whisper
     - audio_quality: 0     # Highest quality
     - postprocessors: FFmpegExtractAudio

  2. Download and extract audio
     - Show progress callback
     - Handle interruptions gracefully

  3. Verify audio file integrity
     - Check file exists
     - Validate duration matches metadata

OUTPUT: audio_file_path (WAV format, 16kHz mono optimal)

CLEANUP: Register for deletion on completion/error
```

### Step 4: Speech Transcription

```
INPUT: audio_file_path, language_code

PROCESS (using OpenAI Whisper):
  1. Use the model named with -m/--model (standard Whisper names; default "turbo"):
     - "turbo": Fast, good accuracy (default)
     - "large-v3": Best accuracy, slower
     - "medium": Balanced
     - "small"/"base"/"tiny": Faster, less accurate

  2. Load model (cache for reuse)

  3. Transcribe with options:
     - language: specified or auto-detect
     - task: "transcribe" (not translate)
     - word_timestamps: True (granular timing)
     - no console output from Whisper (SubSync shows its own progress)

  4. Extract segments with timing:
     - Each segment has start, end, text
     - Word-level timestamps for precise alignment

OUTPUT: TranscriptionResult {
  language: str,
  segments: [
    {
      id: int,
      start: float,      # seconds
      end: float,        # seconds
      text: str,
      words: [{word, start, end}, ...]
    },
    ...
  ]
}
```

### Step 5: Netflix Compliance Processing

```
INPUT: TranscriptionResult

PROCESS:
  FOR each segment in transcription:

    1. TIMING VALIDATION:
       ┌─────────────────────────────────────────────┐
       │ Check duration = end - start                 │
       │                                              │
       │ IF duration < 833ms (5/6 second):           │
       │   - Extend end time if no conflict          │
       │   - Minimum: 833ms                          │
       │                                              │
       │ IF duration > 7000ms (7 seconds):           │
       │   - Split into multiple segments            │
       │   - Find natural break points               │
       │                                              │
       │ ENSURE gap from previous >= 83ms (2 frames) │
       └─────────────────────────────────────────────┘

    2. TEXT SEGMENTATION:
       ┌─────────────────────────────────────────────┐
       │ Count characters in text                     │
       │                                              │
       │ IF chars <= 42:                             │
       │   - Single line, no split needed            │
       │                                              │
       │ IF 42 < chars <= 84:                        │
       │   - Split into 2 lines                      │
       │   - Apply line break rules (see below)      │
       │                                              │
       │ IF chars > 84:                              │
       │   - Split into multiple subtitle events     │
       │   - Use word timestamps for timing          │
       └─────────────────────────────────────────────┘

    3. LINE BREAK RULES (in priority order):
       ┌─────────────────────────────────────────────┐
       │ PREFER breaking:                            │
       │   ✓ After punctuation marks (. , ! ? :)    │
       │   ✓ Before conjunctions (and, but, or)     │
       │   ✓ Before prepositions (in, on, at, to)   │
       │                                              │
       │ AVOID breaking:                             │
       │   ✗ Between article and noun               │
       │   ✗ Between adjective and noun             │
       │   ✗ Between first and last name            │
       │   ✗ Between verb and subject pronoun       │
       │   ✗ Between verb and auxiliary             │
       └─────────────────────────────────────────────┘

    4. READING SPEED VALIDATION:
       ┌─────────────────────────────────────────────┐
       │ Calculate CPS = total_chars / duration_secs │
       │                                              │
       │ IF CPS > 20 (adult content):               │
       │   Option A: Extend duration (if space)      │
       │   Option B: Flag for manual review          │
       │                                              │
       │ IF CPS > 17 (children's content):          │
       │   Apply stricter limits                     │
       └─────────────────────────────────────────────┘

    5. CREATE SUBTITLE EVENT:
       - Assign sequential index (1, 2, 3...)
       - Format times as HH:MM:SS,mmm
       - Store processed text with line breaks

OUTPUT: List[Subtitle] ready for output
```

### Step 6: Output Generation

```
INPUT: List[Subtitle], output_path, format

PROCESS:

  FOR SRT FORMAT:
    ┌────────────────────────────────────────┐
    │ 1                                       │
    │ 00:00:00,000 --> 00:00:02,500          │
    │ Hello everyone and welcome              │
    │ to today's video.                       │
    │                                         │
    │ 2                                       │
    │ 00:00:02,600 --> 00:00:05,000          │
    │ Today we're going to discuss           │
    │ something very important.               │
    └────────────────────────────────────────┘

    - Index number
    - Timestamp line: START --> END
    - Text (1-2 lines)
    - Blank line separator

  FOR VTT FORMAT (optional):
    ┌────────────────────────────────────────┐
    │ WEBVTT                                  │
    │                                         │
    │ 00:00:00.000 --> 00:00:02.500          │
    │ Hello everyone and welcome              │
    │ to today's video.                       │
    │                                         │
    │ 00:00:02.600 --> 00:00:05.000          │
    │ Today we're going to discuss           │
    │ something very important.               │
    └────────────────────────────────────────┘

    - Header: "WEBVTT"
    - Timestamp uses . instead of ,
    - No index numbers (optional)

OUTPUT: Subtitle file(s) written to disk
```

---

## 4. Netflix Compliance Rules

### Timing Requirements

| Rule | Value | Notes |
|------|-------|-------|
| **Minimum Duration** | 833ms (5/6 sec) | 20 frames at 24fps |
| **Maximum Duration** | 7000ms (7 sec) | Per subtitle event |
| **Minimum Gap** | 83ms (2 frames) | Between consecutive subtitles |
| **Frame Rate Reference** | 24fps | Adjust for other frame rates |

### Character & Line Limits

| Rule | Value |
|------|-------|
| **Max Characters/Line** | 42 |
| **Max Lines/Subtitle** | 2 |
| **Max Total Characters** | 84 (42 × 2) |

### Reading Speed

| Content Type | Max CPS |
|--------------|---------|
| **Adult Programs** | 20 characters/second |
| **Children's Programs** | 17 characters/second |

### Positioning

- Center justified
- Bottom of screen (default)
- Top positioning when avoiding on-screen text

### Typography

| Element | Specification |
|---------|---------------|
| **Font** | Arial (proportionalSansSerif) |
| **Color** | White |
| **Encoding** | UTF-8 |

---

## 5. YouTube Format Compatibility

### Supported Upload Formats

| Format | Extension | Recommended |
|--------|-----------|-------------|
| **SubRip** | .srt | ✅ Primary |
| **WebVTT** | .vtt | ✅ Alternative |
| **SubViewer** | .sbv, .sub | Supported |
| **MPsub** | .mpsub | Supported |
| **LRC** | .lrc | Supported |
| **SAMI** | .sami | Advanced |
| **TTML** | .ttml, .dfxp | Advanced |
| **SCC** | .scc | Broadcast |

### SRT Format Specification

```
[SEQUENCE_NUMBER]
[START_TIME] --> [END_TIME]
[SUBTITLE_TEXT]

[BLANK_LINE]
```

**Time Format:** `HH:MM:SS,mmm`
- Hours: 00-99
- Minutes: 00-59
- Seconds: 00-59
- Milliseconds: 000-999

### Upload Process

1. Go to YouTube Studio
2. Select video → Subtitles
3. Add Language → Upload file
4. Choose "With timing" option
5. Select .srt file
6. Review and publish

---

## 6. Third-Party Tools & Services

### Required Dependencies

#### yt-dlp
- **Purpose:** YouTube audio extraction
- **License:** Unlicense
- **Installation:** `pip install yt-dlp` or `uv add yt-dlp`
- **Key Features:**
  - Audio-only download (`-x` / `extract_audio`)
  - Format selection (`-f bestaudio`)
  - Python API for embedding
  - Handles age-restricted content (with cookies)

#### OpenAI Whisper
- **Purpose:** Speech-to-text transcription
- **License:** MIT
- **Installation:** `pip install openai-whisper` or `uv add openai-whisper`
- **Models:**

| Model | Parameters | VRAM | Speed | Accuracy |
|-------|------------|------|-------|----------|
| tiny | 39M | ~1GB | ~10x | Basic |
| base | 74M | ~1GB | ~7x | Good |
| small | 244M | ~2GB | ~4x | Better |
| medium | 769M | ~5GB | ~2x | Very Good |
| large-v3 | 1550M | ~10GB | 1x | Best |
| turbo | 809M | ~6GB | ~8x | Very Good |

#### FFmpeg
- **Purpose:** Audio processing (required by both yt-dlp and Whisper)
- **License:** GPL/LGPL
- **Installation:**
  - macOS: `brew install ffmpeg`
  - Ubuntu: `apt install ffmpeg`
  - Windows: `choco install ffmpeg`

### Optional Dependencies

| Package | Purpose |
|---------|---------|
| `pysrt` | SRT file manipulation |
| `webvtt-py` | WebVTT handling |
| `rich` | CLI progress display |

---

## 7. Data Structures

### Core Data Models

```
VideoMetadata:
  ├── id: str                    # YouTube video ID
  ├── title: str                 # Video title
  ├── duration: float            # Duration in seconds
  ├── uploader: str              # Channel name
  └── upload_date: str           # YYYYMMDD format

TranscriptionSegment:
  ├── id: int                    # Segment index
  ├── start: float               # Start time (seconds)
  ├── end: float                 # End time (seconds)
  ├── text: str                  # Transcribed text
  └── words: List[Word]          # Word-level timestamps
      └── Word:
          ├── word: str
          ├── start: float
          └── end: float

TranscriptionResult:
  ├── language: str              # Detected/specified language
  ├── duration: float            # Total audio duration
  └── segments: List[Segment]

Subtitle:
  ├── index: int                 # Sequential number (1-based)
  ├── start_time: timedelta      # Start timestamp
  ├── end_time: timedelta        # End timestamp
  ├── text: str                  # Original text
  ├── lines: List[str]           # Formatted lines (1-2)
  ├── char_count: int            # Total characters
  ├── duration_ms: int           # Duration in milliseconds
  └── cps: float                 # Characters per second

SubtitleFile:
  ├── format: str                # "srt" or "vtt"
  ├── language: str              # Language code
  ├── video_id: str              # Source video ID
  └── subtitles: List[Subtitle]
```

---

## 8. Error Handling

### Error Categories

| Category | Examples | Handling |
|----------|----------|----------|
| **Network** | Connection timeout, DNS failure | Retry with backoff |
| **YouTube** | Video unavailable, private, age-restricted | User-friendly message |
| **Transcription** | Model load failure, CUDA error | Fallback to CPU/smaller model |
| **Processing** | Invalid timestamps, encoding errors | Log and skip segment |
| **File System** | Permission denied, disk full | Clear error message |

### Retry Strategy

```
Network Operations:
  - Max retries: 3
  - Backoff: Exponential (1s, 2s, 4s)
  - Timeout: 30 seconds

Model Loading:
  - Fallback chain: GPU → CPU
  - Model fallback: large → turbo → medium
```

### Graceful Degradation

1. If word timestamps fail → use segment timestamps
2. If language detection fails → prompt user
3. If CPS exceeds limit → flag for review (don't block)

---

## 9. Future Extensibility: Translation

### Translation Module Interface

```
Protocol: ITranslator
  ├── translate(text: str, source: str, target: str) -> str
  ├── translate_batch(texts: List[str], source: str, target: str) -> List[str]
  ├── supports_language(lang: str) -> bool
  └── get_supported_languages() -> List[str]
```

### Planned Translation Providers

| Provider | API | Cost Model |
|----------|-----|------------|
| **Google Translate** | Cloud Translation API | Per character |
| **DeepL** | DeepL API | Per character |
| **OpenAI** | GPT-4 API | Per token |
| **Local** | NLLB, MarianMT | Free (compute) |

### Translation Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Source    │    │ Translation │    │  Translated │
│  Subtitles  │───▶│   Service   │───▶│  Subtitles  │
│   (SRT)     │    │             │    │   (SRT)     │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   Timing    │
                   │ Preservation│
                   │  (no sync   │
                   │   changes)  │
                   └─────────────┘
```

### Translation Considerations

1. **Preserve Timing:** Translation must maintain original timestamps
2. **Character Limits:** Translated text must fit within 42 chars/line
3. **Reading Speed:** May need adjustment for target language
4. **Cultural Adaptation:** Numbers, dates, cultural references
5. **Language-Specific Rules:** Different Netflix style guides per language

---

## 10. Visual Diagrams

### Process Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SUBTITLE GENERATION FLOW                           │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌───────────┐
    │  START    │
    └─────┬─────┘
          │
          ▼
    ┌───────────────┐     ┌─────────────────┐
    │ Parse YouTube │     │ Invalid URL?    │
    │     URL       │────▶│ Show Error      │───▶ END
    └───────┬───────┘     └─────────────────┘
            │ Valid
            ▼
    ┌───────────────┐     ┌─────────────────┐
    │ Extract Video │     │ Video Private/  │
    │   Metadata    │────▶│ Unavailable?    │───▶ END
    └───────┬───────┘     └─────────────────┘
            │ Available
            ▼
    ┌───────────────┐
    │ Download      │
    │ Audio Stream  │
    │ (yt-dlp)      │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ Transcribe    │
    │ Audio         │
    │ (Whisper)     │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ Process       │
    │ Segments      │◀───────────────────┐
    └───────┬───────┘                    │
            │                             │
            ▼                             │
    ┌───────────────┐                    │
    │ Apply Netflix │     ┌──────────┐   │
    │ Timing Rules  │────▶│ Duration │   │
    └───────┬───────┘     │ Invalid? │───┘
            │             └──────────┘
            │ Valid         Adjust
            ▼
    ┌───────────────┐
    │ Format Text   │
    │ (Line Breaks) │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐     ┌─────────────────┐
    │ Check Reading │     │ CPS > 20?       │
    │ Speed (CPS)   │────▶│ Flag/Adjust     │
    └───────┬───────┘     └────────┬────────┘
            │                       │
            ▼◀──────────────────────┘
    ┌───────────────┐
    │ Generate SRT  │
    │ Output File   │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ Cleanup Temp  │
    │ Files         │
    └───────┬───────┘
            │
            ▼
    ┌───────────┐
    │    END    │
    └───────────┘
```

### State Machine: Subtitle Event Processing

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUBTITLE EVENT STATE MACHINE                  │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │   RAW        │
                    │  SEGMENT     │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ TOO      │ │ VALID    │ │ TOO      │
       │ SHORT    │ │ DURATION │ │ LONG     │
       │ (<833ms) │ │          │ │ (>7000ms)│
       └────┬─────┘ └────┬─────┘ └────┬─────┘
            │            │            │
            ▼            │            ▼
       ┌──────────┐      │      ┌──────────┐
       │ EXTEND   │      │      │ SPLIT    │
       │ END TIME │      │      │ SEGMENT  │
       └────┬─────┘      │      └────┬─────┘
            │            │            │
            └────────────┼────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   TIMING     │
                  │   VALIDATED  │
                  └──────┬───────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
       ┌──────────┐┌──────────┐┌──────────┐
       │  ≤42     ││  43-84   ││   >84    │
       │  CHARS   ││  CHARS   ││  CHARS   │
       └────┬─────┘└────┬─────┘└────┬─────┘
            │           │           │
            │           ▼           ▼
            │    ┌──────────┐ ┌──────────┐
            │    │  SPLIT   │ │  CREATE  │
            │    │  2 LINES │ │ MULTIPLE │
            │    └────┬─────┘ │  EVENTS  │
            │         │       └────┬─────┘
            │         │            │
            └─────────┴────────────┘
                      │
                      ▼
               ┌──────────────┐
               │   COMPLETE   │
               │   SUBTITLE   │
               └──────────────┘
```

### CLI Command Structure

```
Usage: subsync generate <INPUT> [OPTIONS]

Arguments:
  INPUT                  Path to a video or audio file, or a YouTube video URL (required)

Options:
  -l, --language CODE    Spoken language; skips detection (default: auto-detect)
  -m, --model NAME       Whisper model (default: turbo)
  -f, --format srt|vtt   Output format (default: srt, or inferred from -o)
  -o, --output PATH      A folder for the default name, or an exact file path
                         (default: <input folder>/<stem>.<lang>.srt for a file,
                         ./<title>.<lang>.srt for a URL)
  --force                Replace an existing output file
  --prompt TEXT          Words to spell correctly, e.g. "uv, Claude Code, pytest"
  --glossary FILE        Same, one term per line
  -v, --verbose          Debug logs, and a traceback if an error occurs
  --version              Show the version
  -h, --help             Show this help message

Examples:
  subsync generate ~/Videos/ep42.mov
  subsync generate ~/Videos/ep42.mov --glossary ~/yt/terms.txt -o out/
  subsync generate "https://youtu.be/abc123def45" -l en
  subsync generate "https://youtube.com/shorts/abc123def45" -m small
```

The full command surface, messages and exit codes are in [ux-flows.md](product-design/subsync-v1/ux-flows.md).

---

## Appendix A: Language Codes

Whisper supports 99+ languages. Common codes:

| Code | Language | Code | Language |
|------|----------|------|----------|
| en | English | es | Spanish |
| fr | French | de | German |
| it | Italian | pt | Portuguese |
| ru | Russian | ja | Japanese |
| ko | Korean | zh | Chinese |
| ar | Arabic | hi | Hindi |

Full list: https://github.com/openai/whisper/blob/main/whisper/tokenizer.py

---

## Appendix B: Netflix Style Guide References

- [General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617)
- [Timing Guidelines](https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394)
- [English (USA) Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977)
- [Language-Specific Guides](https://partnerhelp.netflixstudios.com/hc/en-us/sections/22463232153235)

---

## Appendix C: YouTube Subtitle Documentation

- [Add subtitles & captions](https://support.google.com/youtube/answer/2734796)
- [Supported file formats](https://support.google.com/youtube/answer/2734698)
- [Tips for creating transcript files](https://support.google.com/youtube/answer/2734799)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | **2025**-12-04 | Initial algorithm design |
| 1.1 | 2026-09-25 | Marked as background for SubSync v1; local-file input, `-m/--model` instead of `-q/--quality`, no `--children`; CLI block aligned with the v1 UX flows |

---

*This document serves as the architectural blueprint for the subsync subtitle generation feature. Implementation should follow these specifications to ensure Netflix compliance and YouTube compatibility.*
