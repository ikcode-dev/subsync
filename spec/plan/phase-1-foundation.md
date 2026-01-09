# Phase 1: Foundation & Project Setup

## Overview

This phase establishes the project foundation, including dependency installation, project structure, and core data models. No external service integration yet.

**Estimated Effort**: 1-2 hours
**Dependencies**: None (starting point)

---

## Goals

1. Set up project dependencies and verify they work
2. Create the module structure for clean separation of concerns
3. Implement core data models
4. Implement YouTube URL parsing and validation
5. Establish error handling patterns

---

## Architecture Decisions

### Module Structure

```
src/subsync/
├── __init__.py          # Package exports
├── cli.py               # CLI entry point (exists)
├── models.py            # Data classes
├── errors.py            # Custom exceptions
├── url_handler.py       # YouTube URL parsing
└── utils.py             # Shared utilities
```

**Rationale**: Flat structure for simplicity. Can add subdirectories if complexity grows.

### Data Classes vs Pydantic

**Decision**: Use standard `@dataclass` for now.

**Rationale**:
- Simpler, no additional dependency
- Sufficient for our validation needs
- Can migrate to Pydantic later if needed

### Exception Hierarchy

**Decision**: Custom exception hierarchy rooted at `SubSyncError`.

**Rationale**:
- Enables granular error handling
- CLI can catch specific exceptions for user-friendly messages
- Follows Python best practices

---

## Components

### 1. Dependencies Setup

Install and verify all required dependencies:

```bash
uv add yt-dlp openai-whisper rich
uv add --group dev pytest pytest-cov
```

Verify FFmpeg is available in PATH.

### 2. Data Models (`models.py`)

Implement all models from [data-models.md](../context/data-models.md):

- `VideoMetadata`
- `Word`, `TranscriptionSegment`, `TranscriptionResult`
- `Subtitle`, `SubtitleFile`
- Configuration dataclasses

### 3. Error Definitions (`errors.py`)

```python
class SubSyncError(Exception): ...
class URLParseError(SubSyncError): ...
class VideoUnavailableError(SubSyncError): ...
class AgeRestrictedError(SubSyncError): ...
class LiveStreamError(SubSyncError): ...
class TranscriptionError(SubSyncError): ...
```

### 4. URL Handler (`url_handler.py`)

**Responsibility**: Parse and validate YouTube URLs, extract video ID.

**Supported URL Patterns**:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://www.youtube.com/v/VIDEO_ID`
- URLs with additional parameters (playlist, timestamp)

**Interface**:
```python
def parse_youtube_url(url: str) -> str:
    """
    Extract video ID from YouTube URL.

    Args:
        url: YouTube video URL

    Returns:
        11-character video ID

    Raises:
        URLParseError: If URL is invalid or not a YouTube URL
    """
```

**Validation Rules**:
- Video ID is exactly 11 characters
- Video ID contains only `[a-zA-Z0-9_-]`
- URL is from youtube.com or youtu.be domain

---

## Testing Strategy

### Unit Tests for URL Handler

```python
# tests/test_url_handler.py

def test_parse_standard_url():
    assert parse_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_parse_short_url():
    assert parse_youtube_url("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_parse_embed_url():
    assert parse_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_parse_with_extra_params():
    assert parse_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42") == "dQw4w9WgXcQ"

def test_invalid_url_raises():
    with pytest.raises(URLParseError):
        parse_youtube_url("https://vimeo.com/12345")

def test_invalid_video_id_raises():
    with pytest.raises(URLParseError):
        parse_youtube_url("https://www.youtube.com/watch?v=short")
```

### Model Tests

- Test dataclass instantiation
- Test computed properties (cps, duration_ms, char_count)
- Test model serialization if needed

---

## Acceptance Criteria

- [ ] All dependencies installed successfully
- [ ] FFmpeg available and verified
- [ ] Models importable from `subsync.models`
- [ ] Errors importable from `subsync.errors`
- [ ] URL handler parses all supported formats
- [ ] URL handler rejects invalid URLs with clear errors
- [ ] All unit tests pass
- [ ] `task lint` passes with no errors

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FFmpeg not installed | Blocks audio extraction | Document in README, check at startup |
| Whisper model download slow | Poor first-run experience | Document expected download time |
| GPU/CUDA issues | Transcription very slow | Auto-fallback to CPU, document |

---

## Next Phase

After Phase 1 completion, proceed to [Phase 2: Core Pipeline](./phase-2-core-pipeline.md) which implements the audio extraction and transcription modules.
