# Phase 2: Core Pipeline (Audio Extraction & Transcription)

## Overview

This phase implements the core processing pipeline: extracting audio from YouTube videos and transcribing it to text with timestamps. This is the technical heart of SubSync.

**Estimated Effort**: 3-4 hours
**Dependencies**: Phase 1 complete

---

## Goals

1. Implement video metadata extraction via yt-dlp
2. Implement audio download and extraction
3. Implement Whisper transcription integration
4. Establish temporary file management
5. Add progress reporting infrastructure

---

## Architecture Decisions

### Temporary File Management

**Decision**: Use Python's `tempfile` module with context managers.

**Rationale**:
- Automatic cleanup on success or failure
- Cross-platform compatibility
- No orphaned files on crashes

**Pattern**:
```python
with tempfile.TemporaryDirectory() as tmpdir:
    audio_path = download_audio(video_id, tmpdir)
    result = transcribe(audio_path)
# Automatic cleanup here
```

### Whisper Model Selection

**Decision**: Default to "turbo" model with CLI override.

**Rationale**:
- Best balance of speed and accuracy
- ~6GB VRAM fits most modern GPUs
- 8x faster than large-v3 with similar quality

### Audio Format

**Decision**: Extract to WAV format (16kHz, mono).

**Rationale**:
- Whisper's optimal input format
- No lossy compression artifacts
- Larger file size acceptable for temporary files

---

## Components

### 1. Audio Extractor (`audio_extractor.py`)

**Responsibilities**:
- Extract video metadata without downloading
- Download audio stream
- Convert to Whisper-optimal format

**Interface**:
```python
def get_video_metadata(video_id: str) -> VideoMetadata:
    """
    Extract metadata for a YouTube video.

    Raises:
        VideoUnavailableError: Video doesn't exist or is private
        AgeRestrictedError: Requires age verification
        LiveStreamError: Live streams not supported
    """

def download_audio(
    video_id: str,
    output_dir: Path,
    progress_callback: Callable[[float], None] | None = None
) -> Path:
    """
    Download and extract audio from YouTube video.

    Returns:
        Path to the extracted WAV file
    """
```

**yt-dlp Configuration**:
```python
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': str(output_dir / '%(id)s.%(ext)s'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
    }],
    'postprocessor_args': [
        '-ar', '16000',  # 16kHz sample rate
        '-ac', '1',      # Mono
    ],
    'quiet': True,
    'no_warnings': True,
    'progress_hooks': [progress_hook] if progress_callback else [],
}
```

**Error Mapping**:
| yt-dlp Error | SubSync Error |
|--------------|---------------|
| Video unavailable | `VideoUnavailableError` |
| Private video | `VideoUnavailableError` |
| Age-restricted | `AgeRestrictedError` |
| Live stream | `LiveStreamError` |

### 2. Transcriber (`transcriber.py`)

**Responsibilities**:
- Load Whisper model (with caching)
- Transcribe audio to text with timestamps
- Handle GPU/CPU fallback

**Interface**:
```python
def transcribe_audio(
    audio_path: Path,
    config: TranscriptionConfig,
    progress_callback: Callable[[float], None] | None = None
) -> TranscriptionResult:
    """
    Transcribe audio file to text with timestamps.

    Args:
        audio_path: Path to audio file (WAV recommended)
        config: Transcription settings
        progress_callback: Optional progress reporting (0.0-1.0)

    Returns:
        TranscriptionResult with segments and word timestamps

    Raises:
        TranscriptionError: If transcription fails
    """
```

**Implementation Notes**:
```python
import whisper

# Model caching (load once, reuse)
_model_cache: dict[str, whisper.Whisper] = {}

def _get_model(model_name: str, device: str) -> whisper.Whisper:
    cache_key = f"{model_name}:{device}"
    if cache_key not in _model_cache:
        _model_cache[cache_key] = whisper.load_model(model_name, device=device)
    return _model_cache[cache_key]
```

**Whisper Options**:
```python
result = model.transcribe(
    str(audio_path),
    language=config.language,  # None for auto-detect
    task="transcribe",
    word_timestamps=config.word_timestamps,
    verbose=False,
)
```

### 3. Pipeline Orchestrator (`pipeline.py`)

**Responsibilities**:
- Coordinate the full processing pipeline
- Manage temporary files
- Report overall progress

**Interface**:
```python
def process_video(
    url: str,
    config: ProcessingConfig,
    progress_callback: Callable[[str, float], None] | None = None
) -> TranscriptionResult:
    """
    Full pipeline: URL → Audio → Transcription.

    Args:
        url: YouTube video URL
        config: Processing configuration
        progress_callback: (stage_name, progress) callback

    Returns:
        TranscriptionResult ready for subtitle processing
    """
```

**Pipeline Stages**:
1. Parse URL → Extract video ID
2. Get metadata → Validate video availability
3. Download audio → Progress: 0-50%
4. Transcribe → Progress: 50-100%
5. Cleanup → Automatic via context manager

---

## Testing Strategy

### Unit Tests

**Audio Extractor** (mocked yt-dlp):
```python
def test_get_metadata_returns_video_info(mock_ytdlp):
    mock_ytdlp.return_value = {'id': 'abc123', 'title': 'Test', ...}
    metadata = get_video_metadata('abc123')
    assert metadata.id == 'abc123'

def test_private_video_raises_error(mock_ytdlp):
    mock_ytdlp.side_effect = DownloadError('Private video')
    with pytest.raises(VideoUnavailableError):
        get_video_metadata('private123')
```

**Transcriber** (mocked Whisper):
```python
def test_transcribe_returns_segments(mock_whisper):
    mock_whisper.transcribe.return_value = {
        'text': 'Hello world',
        'segments': [{'start': 0, 'end': 1, 'text': 'Hello world'}]
    }
    result = transcribe_audio(Path('test.wav'), TranscriptionConfig())
    assert len(result.segments) == 1
```

### Integration Tests (Optional, Slow)

```python
@pytest.mark.integration
@pytest.mark.slow
def test_full_pipeline_with_real_video():
    """Test with a short, public domain video."""
    result = process_video(
        "https://www.youtube.com/watch?v=SHORT_PUBLIC_VIDEO",
        ProcessingConfig()
    )
    assert len(result.segments) > 0
```

---

## Progress Reporting

**Console Output** (via `rich`):
```
[1/4] Fetching video metadata...
[2/4] Downloading audio... ━━━━━━━━━━━━━━━━━━━━ 100%
[3/4] Transcribing audio... ━━━━━━━━━━━━━━━━━━━━ 100%
[4/4] Processing complete!
```

---

## Acceptance Criteria

- [ ] Can extract metadata from public YouTube videos
- [ ] Can download and extract audio to WAV
- [ ] Can transcribe audio with Whisper
- [ ] Word timestamps are included when available
- [ ] Language auto-detection works
- [ ] GPU used when available, CPU fallback works
- [ ] Temporary files are cleaned up
- [ ] Progress is reported during long operations
- [ ] All unit tests pass
- [ ] Error cases produce clear, actionable messages

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| yt-dlp API changes | Breaks extraction | Pin version, monitor updates |
| Large videos timeout | User frustration | Add timeout config, show progress |
| Whisper OOM on GPU | Crash | Catch exception, retry on CPU |
| No word timestamps | Less precise subtitles | Fall back to segment timing |

---

## Performance Considerations

| Video Length | Download Time | Transcribe Time (turbo, GPU) |
|--------------|---------------|------------------------------|
| 5 min | ~30s | ~30s |
| 30 min | ~2 min | ~3 min |
| 2 hours | ~10 min | ~15 min |

**Recommendations**:
- Show progress for operations > 5 seconds
- Consider async processing for very long videos
- Document expected processing times

---

## Next Phase

After Phase 2 completion, proceed to [Phase 3: Netflix Compliance](./phase-3-netflix-compliance.md) which processes the transcription into compliant subtitles.
