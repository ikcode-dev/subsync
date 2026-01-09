# Task 2: Create Error Definitions

## Overview

Implement a custom exception hierarchy for SubSync. This establishes consistent error handling patterns used throughout the application.

**Plan Reference**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 3. Error Definitions"

**Context Reference**: [data-models.md](../../context/data-models.md) → Section "Error Models"

**Depends On**: [Task 1](./01-install-dependencies.md)

---

## Objective

Create `src/subsync/errors.py` with a well-structured exception hierarchy that enables:
- Granular error handling in calling code
- User-friendly error messages in CLI
- Clear categorization of failure modes

---

## Requirements

### Exception Hierarchy

```
SubSyncError (base)
├── URLParseError          # Invalid/unsupported YouTube URL
├── VideoUnavailableError  # Private, deleted, region-locked
├── AgeRestrictedError     # Requires age verification
├── LiveStreamError        # Live streams not supported
└── TranscriptionError     # Audio transcription failures
```

### Design Principles

1. All exceptions inherit from `SubSyncError`
2. Each exception should have a meaningful default message
3. Exceptions should support custom messages
4. Follow Python exception naming conventions (`*Error` suffix)
5. Include docstrings explaining when each exception is raised

---

## Implementation

### File: `src/subsync/errors.py`

```python
"""Custom exceptions for SubSync."""


class SubSyncError(Exception):
    """Base exception for all SubSync errors.

    All SubSync-specific exceptions inherit from this class,
    enabling catch-all handling when needed.
    """
    pass


class URLParseError(SubSyncError):
    """Invalid or unsupported YouTube URL.

    Raised when:
    - URL is not from youtube.com or youtu.be domain
    - URL does not contain a valid video ID
    - Video ID format is invalid (not 11 characters, invalid chars)
    """
    pass


class VideoUnavailableError(SubSyncError):
    """Video is not accessible.

    Raised when:
    - Video is private
    - Video has been deleted
    - Video is region-locked
    - Video requires purchase
    """
    pass


class AgeRestrictedError(SubSyncError):
    """Video requires age verification.

    Raised when video is age-restricted and no cookies are provided
    for authentication.
    """
    pass


class LiveStreamError(SubSyncError):
    """Live streams are not supported.

    Raised when the URL points to an active live stream rather than
    a completed video.
    """
    pass


class TranscriptionError(SubSyncError):
    """Error during audio transcription.

    Raised when:
    - Whisper model fails to load
    - Audio file is corrupted or unreadable
    - Transcription process fails
    """
    pass
```

---

## Verification Checklist

- [ ] File created at `src/subsync/errors.py`
- [ ] All 6 exception classes implemented
- [ ] All exceptions inherit from `SubSyncError`
- [ ] All exceptions have docstrings
- [ ] `from subsync.errors import SubSyncError, URLParseError, ...` works
- [ ] `task lint` passes

### Quick Import Test

```bash
uv run python -c "from subsync.errors import SubSyncError, URLParseError, VideoUnavailableError, AgeRestrictedError, LiveStreamError, TranscriptionError; print('All errors imported successfully')"
```

---

## Definition of Done

- `src/subsync/errors.py` exists with all exception classes
- All exceptions are importable from `subsync.errors`
- Docstrings explain when each exception is raised
- Linting passes

---

## Next Task

After verification, proceed to → [03-data-models.md](./03-data-models.md)

---

## User Verification Required

**STOP** after completing this task. Present the changes to the user and wait for verification before proceeding to the next task.
