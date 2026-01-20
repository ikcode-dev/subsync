# Task 2: Create Error Definitions

## Objective

Create a custom exception hierarchy for SubSync that enables granular error handling and user-friendly CLI messages.

## Detail Level

EXPANDED

---

## Context

### References

- **Plan**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 2. Error Definitions"
- **Context**: [data-models.md](../../context/data-models.md) → Section "Error Categories"

### Dependencies

- **Task 1**: *(Sequencing only — no imports needed)*

### Context Summary

SubSync needs a custom exception hierarchy for two main reasons:

1. **Granular CLI handling**: Different errors need different user messages
   - `URLParseError` → "Invalid YouTube URL, please check the format"
   - `AgeRestrictedError` → "Video requires age verification, provide cookies"

2. **Catch-all capability**: CLI can catch `SubSyncError` for unexpected failures

**Exception Hierarchy Design**:
```
SubSyncError (base)
├── URLParseError          # Invalid/unsupported YouTube URL
├── VideoUnavailableError  # Private, deleted, region-locked
├── AgeRestrictedError     # Requires age verification
├── LiveStreamError        # Live streams not supported
└── TranscriptionError     # Audio transcription failures
```

**Why These Specific Errors**:
| Error | Trigger Scenario | User Action |
|-------|------------------|-------------|
| `URLParseError` | Malformed URL, wrong domain, invalid video ID | Fix the URL |
| `VideoUnavailableError` | Video deleted, private, region-locked | Choose different video |
| `AgeRestrictedError` | Age verification required | Provide browser cookies |
| `LiveStreamError` | URL points to active livestream | Wait for stream to end |
| `TranscriptionError` | Whisper fails, audio corrupt | Retry or report bug |

---

## Requirements

### Functional Requirements

- All exceptions inherit from `SubSyncError`
- Each exception supports custom messages
- Each exception has a docstring explaining when it's raised
- Follow Python naming convention (`*Error` suffix)

### Interface Contract

```python
# All exceptions work like standard Python exceptions:
raise URLParseError("not a YouTube URL")
raise URLParseError()  # Also valid, uses default behavior

# Catch-all pattern:
try:
    ...
except SubSyncError as e:
    print(f"SubSync error: {e}")
```

### Error Definitions

| Exception | When Raised |
|-----------|-------------|
| `SubSyncError` | Base class — never raised directly |
| `URLParseError` | URL not YouTube domain, missing video ID, invalid ID format |
| `VideoUnavailableError` | Video private, deleted, region-locked, requires purchase |
| `AgeRestrictedError` | Video needs age verification, no cookies provided |
| `LiveStreamError` | URL points to active livestream |
| `TranscriptionError` | Whisper model fails, audio corrupt, transcription fails |

---

## Acceptance Criteria

- [x] File exists at `src/subsync/errors.py`
- [x] All 6 exception classes implemented
- [x] All exceptions inherit from `SubSyncError`
- [x] All exceptions have docstrings
- [x] All exceptions importable: `from subsync.errors import SubSyncError, URLParseError, ...`
- [x] `task lint` passes

---

## Test Scenarios

| Scenario | Code | Expected Outcome |
|----------|------|------------------|
| Import all | `from subsync.errors import SubSyncError, URLParseError, VideoUnavailableError, AgeRestrictedError, LiveStreamError, TranscriptionError` | No import error |
| Raise with message | `raise URLParseError("bad url")` | Exception with message "bad url" |
| Raise without message | `raise URLParseError()` | Exception with empty message |
| Catch base class | `except SubSyncError` | Catches `URLParseError` |
| Inheritance check | `isinstance(URLParseError(), SubSyncError)` | Returns `True` |

---

## Implementation Checklist

1. [x] Create file: `src/subsync/errors.py`
2. [x] Define: `SubSyncError(Exception)` with docstring
3. [x] Define: `URLParseError(SubSyncError)` with docstring
4. [x] Define: `VideoUnavailableError(SubSyncError)` with docstring
5. [x] Define: `AgeRestrictedError(SubSyncError)` with docstring
6. [x] Define: `LiveStreamError(SubSyncError)` with docstring
7. [x] Define: `TranscriptionError(SubSyncError)` with docstring
8. [x] Verify imports: `uv run python -c "from subsync.errors import SubSyncError, URLParseError, VideoUnavailableError, AgeRestrictedError, LiveStreamError, TranscriptionError; print('OK')"`
9. [x] Run: `task lint` — verify pass

---

## Definition of Done

- `src/subsync/errors.py` exists with all exception classes
- All exceptions importable from `subsync.errors`
- Docstrings explain when each exception is raised
- Linting passes

---

## Notes

- No need to add tests for exceptions — they're simple classes
- Python exceptions work with both `raise Error()` and `raise Error("message")`
- Keep docstrings concise but include "Raised when:" section

---

## Next Task

→ [03-data-models.md](./03-data-models.md)
