# Phase 2: Core Pipeline (Audio Extraction & Transcription)

## Overview

This phase implements the core processing pipeline: extracting audio from YouTube videos and transcribing it to text with timestamps. This is the technical heart of SubSync.

**Estimated Effort**: 3-4 hours
**Dependencies**: Phase 1 complete

**Status**: merged (`main` @ `c659fdd`). **Revised 2026-09-25 for SubSync v1**: retry, model fallback, model cache and version pinning are settled by the agreed rules P4–P7 ([product brief](../../docs/product-design/subsync-v1/product-brief.md#rules-for-open-spec-questions)); see [Settled Policies](#settled-policies-v1). The Error Handling and Risks tables below were corrected to match.

---

## Goals

1. Extract video metadata via yt-dlp
2. Download and convert audio to optimal format
3. Transcribe audio using Whisper with timestamps
4. Establish temporary file management
5. Add progress reporting infrastructure

---

## Architecture

### Pipeline Flow

```mermaid
flowchart LR
    VID[Video ID] --> META[Get Metadata]
    META --> DL[Download Audio]
    DL --> WAV[Convert to WAV]
    WAV --> TR[Transcribe]
    TR --> RESULT[TranscriptionResult]

    subgraph "Temp Directory"
        WAV
    end
```

### Component Responsibilities

| Component | Input | Output | Responsibility |
|-----------|-------|--------|----------------|
| Audio Extractor | Video ID | VideoMetadata | Extract video information |
| Audio Extractor | Video ID, Output Dir | Audio File Path | Download and convert audio |
| Transcriber | Audio Path, Config | TranscriptionResult | Speech-to-text with timestamps |
| Pipeline Orchestrator | URL | TranscriptionResult | Coordinate full pipeline |

---

## Architecture Decisions

### Temporary File Management

**Decision**: Use context managers for automatic cleanup.

**Rationale**:
- Automatic cleanup on success or failure
- Cross-platform compatibility
- No orphaned files on crashes

### Whisper Model Selection

**Decision**: Default to "turbo" model with CLI override.

**Rationale**:
- Best balance of speed and accuracy
- ~6GB VRAM fits most modern GPUs
- 8x faster than large-v3 with similar quality

**Trade-offs**:
- Pro: Fast processing
- Pro: Good accuracy for most content
- Con: Requires GPU for reasonable speed

**v1 note**: on Igor's Apple Silicon Mac openai-whisper runs on the CPU. Whether that meets the speed target (N1) is measured in the E1 spike after slice S1; a different engine may replace it behind `TranscriptionResult`, keeping the standard model names (P3).

### Settled Policies (v1)

| Topic | Rule | Consequence for this phase's components |
|---|---|---|
| Retries (P4) | Rely on yt-dlp's built-in retries and timeouts. A network failure exits 3 with "check your connection and re-run" | No retry loop in SubSync; options chosen in S4 (E6) |
| Model fallback (P5) | None. On a memory or load failure, exit 4 and suggest `-m small` | The transcriber raises a clear error instead of retrying with a smaller model or another device |
| Model cache (P6) | Whisper's own download cache (`~/.cache/whisper`) | Nothing to build; SubSync only detects whether a model is cached to show the one-time download notice (R7) |
| Version pinning (P7) | No exact yt-dlp pin: a minimum version plus `uv.lock`; show the upgrade command when yt-dlp is out of date | Error classification for "outdated yt-dlp" is added in S4 (E11) |

### Orchestrator Evolution (E4)

`process_video()` (URL → metadata → download → transcription) is not called by the CLI. SubSync v1 adds one source-agnostic orchestrator, `generate`, and a `MediaSource` model for both local files and YouTube URLs ([phase 4 plan](./phase-4-cli-output.md#one-orchestrator-for-files-and-urls-e4)). Slice S1 builds the local-file branch; slice S4 folds the URL steps of `process_video()` into `generate` and retires `process_video()`. `pipeline_temp_dir()`, `get_video_metadata()`, `download_audio()`, `transcribe_audio()` and `ProgressMapper` are reused.

### Audio Format

**Decision**: Convert to WAV format (16kHz, mono).

**Rationale**:
- Whisper's optimal input format
- No lossy compression artifacts
- Larger file size acceptable for temporary files

---

## Components

### 1. Audio Extractor

**Responsibilities**:
- Extract video metadata without downloading video
- Download audio stream only
- Convert to Whisper-optimal format (16kHz mono WAV)
- Report download progress

**Behavior**:

```
GIVEN a valid video ID
WHEN extracting metadata
THEN return VideoMetadata with title, duration, uploader, upload_date

GIVEN an unavailable video ID
WHEN extracting metadata
THEN raise appropriate error (VideoUnavailableError, AgeRestrictedError, etc.)

GIVEN a video ID and output directory
WHEN downloading audio
THEN save WAV file to output directory and return path
```

**Error Mapping**:

| yt-dlp Condition | SubSync Error |
|------------------|---------------|
| Video unavailable | VideoUnavailableError |
| Private video | VideoUnavailableError |
| Age-restricted | AgeRestrictedError |
| Live stream | LiveStreamError |

### 2. Transcriber

**Responsibilities**:
- Load Whisper model (with caching for reuse)
- Transcribe audio with word-level timestamps
- Handle GPU/CPU device selection and fallback
- Report transcription progress

**Behavior**:

```
GIVEN an audio file path and config
WHEN transcribing
THEN return TranscriptionResult with segments and word timestamps

GIVEN a config with language=null
WHEN transcribing
THEN auto-detect language and include in result

GIVEN GPU unavailable
WHEN loading model with device="auto"
THEN fall back to CPU automatically
```

### 3. Pipeline Orchestrator

**Responsibilities**:
- Coordinate the full URL → Transcription flow
- Manage temporary directory lifecycle
- Report overall progress across stages
- Ensure cleanup on success or failure

**Pipeline Stages**:

```
1. Parse URL → Extract video ID
2. Get Metadata → Validate video availability
3. Download Audio → Progress: 0-50%
4. Transcribe → Progress: 50-100%
5. Cleanup → Automatic via context manager
```

---

## Interface Definitions

### Audio Extractor

**get_video_metadata**:
- Input: video_id (string)
- Output: VideoMetadata
- Errors: VideoUnavailableError, AgeRestrictedError, LiveStreamError

**download_audio**:
- Input: video_id (string), output_dir (path), progress_callback (optional)
- Output: Path to WAV file
- Errors: VideoUnavailableError, network errors

### Transcriber

**transcribe_audio**:
- Input: audio_path (path), config (TranscriptionConfig), progress_callback (optional)
- Output: TranscriptionResult
- Errors: TranscriptionError

---

## Error Handling

| Error Condition | Error Type | Recovery |
|-----------------|------------|----------|
| Video not found | VideoUnavailableError | User message with URL check suggestions |
| Private video | VideoUnavailableError | User message about privacy |
| Age-restricted | AgeRestrictedError | User message (no workaround without cookies) |
| Live stream | LiveStreamError | User message to wait for completion |
| Model load failure | TranscriptionError | No fallback (P5): exit 4 with a `-m small` hint |
| Network timeout | Source-unavailable category (classified in S4) | yt-dlp's built-in retries only (P4), then exit 3: check connection and re-run |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| yt-dlp API changes | Breaks extraction | Minimum version + `uv.lock`, no exact pin; upgrade hint when yt-dlp is out of date (P7) |
| Large videos timeout | User frustration | Add timeout config, show progress |
| Whisper OOM | Crash | Catch the error and exit 4 with a `-m small` hint; no automatic retry (P5) |
| No word timestamps | Less precise subtitles | Fall back to segment timing |

---

## Performance Considerations

| Video Length | Expected Download Time | Expected Transcribe Time (turbo, GPU) |
|--------------|------------------------|---------------------------------------|
| 5 min | ~30s | ~30s |
| 30 min | ~2 min | ~3 min |
| 2 hours | ~10 min | ~15 min |

**Recommendations**:
- Show progress for operations > 5 seconds
- Document expected processing times for users
- Consider async processing for very long videos (future enhancement)

---

## Acceptance Criteria

- [ ] Can extract metadata from public YouTube videos
- [ ] Can download and extract audio to WAV format
- [ ] Can transcribe audio with Whisper
- [ ] Word timestamps are included when available
- [ ] Language auto-detection works
- [ ] GPU used when available, CPU fallback works
- [ ] Temporary files are cleaned up automatically
- [ ] Progress is reported during long operations
- [ ] All unit tests pass
- [ ] Error cases produce clear, actionable messages

---

## Dependencies

- [dependencies.md](../context/dependencies.md) - yt-dlp and Whisper details
- [data-models.md](../context/data-models.md) - VideoMetadata, TranscriptionResult

---

## Next Phase

After Phase 2 completion, proceed to [Phase 3: Netflix Compliance](./phase-3-netflix-compliance.md) which processes the transcription into compliant subtitles.
