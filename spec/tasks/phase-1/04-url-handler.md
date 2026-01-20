# Task 4: Implement URL Handler

## Objective

Create a YouTube URL parser that extracts and validates video IDs from various URL formats.

## Detail Level

EXPANDED

---

## Context

### References

- **Plan**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 4. URL Handler"
- **Context**: [youtube-compatibility.md](../../context/youtube-compatibility.md)

### Dependencies

- **Task 2**: Uses `URLParseError` from `subsync.errors`
- **Task 3**: *(Sequencing only — URL handler doesn't use models)*

### Context Summary

#### YouTube Video ID Format

YouTube video IDs have been consistent since 2009:

| Property | Value | Rationale |
|----------|-------|-----------|
| Length | Exactly 11 characters | Base64-like encoding provides ~73 quintillion unique IDs |
| Characters | `[a-zA-Z0-9_-]` | URL-safe base64 alphabet |
| Case | Sensitive | `dQw4w9WgXcQ` ≠ `DQW4W9WGXCQ` |

#### Supported URL Patterns

YouTube URLs come in several formats that all need to be handled:

| Pattern | Format | Video ID Location |
|---------|--------|-------------------|
| Standard watch | `https://www.youtube.com/watch?v=VIDEO_ID` | Query parameter `v` |
| Short link | `https://youtu.be/VIDEO_ID` | Path segment |
| Embed | `https://www.youtube.com/embed/VIDEO_ID` | Path segment after `/embed/` |
| Legacy embed | `https://www.youtube.com/v/VIDEO_ID` | Path segment after `/v/` |

**Domain variations**: All patterns work with or without `www.`, and with `http://` or `https://`.

**Extra parameters**: URLs may include `&t=123` (timestamp), `&list=PLxyz` (playlist), etc. — these should be ignored.

#### Invalid URLs to Reject

| URL Type | Example | Why Invalid |
|----------|---------|-------------|
| Non-YouTube domain | `https://vimeo.com/12345` | Wrong platform |
| Channel URL | `https://www.youtube.com/c/ChannelName` | No video ID |
| Playlist-only | `https://www.youtube.com/playlist?list=PLxyz` | No video ID |
| Missing ID | `https://www.youtube.com/watch` | No `v` parameter |
| Invalid ID chars | `watch?v=abc!def@123` | Contains `!` and `@` |
| Wrong ID length | `watch?v=short` or `watch?v=wayTooLong123` | Not 11 chars |

---

## Requirements

### Functional Requirements

- Accept a YouTube URL string as input
- Return the 11-character video ID as a string
- Raise `URLParseError` for any invalid or unsupported URL

### Interface Contract

```python
def parse_youtube_url(url: str) -> str:
    """Extract video ID from YouTube URL.

    Args:
        url: A YouTube video URL in any supported format.

    Returns:
        The 11-character video ID.

    Raises:
        URLParseError: If URL is invalid, not YouTube, or missing video ID.
    """
```

### Error Messages

Error messages should be helpful for users:

| Condition | Message Should Contain |
|-----------|------------------------|
| Non-YouTube domain | "not a YouTube URL" |
| Missing video ID | "video ID" |
| Invalid ID format | "11 characters" |

---

## Acceptance Criteria

- [x] Function `parse_youtube_url(url: str) -> str` exists in `src/subsync/url_handler.py`
- [x] Standard watch URL returns correct video ID
- [x] Short URL (`youtu.be`) returns correct video ID
- [x] Embed URL returns correct video ID
- [x] Legacy embed URL (`/v/`) returns correct video ID
- [x] URLs with extra parameters still work
- [x] Non-YouTube URLs raise `URLParseError` with "not a YouTube URL"
- [x] Missing video ID raises `URLParseError` with "video ID"
- [x] Invalid ID format raises `URLParseError` with "11 characters"
- [x] Video IDs with `_` and `-` are accepted
- [x] Tests exist at `tests/test_url_handler.py`
- [x] `task test` passes
- [x] `task lint` passes

---

## Test Scenarios

| Scenario | Input | Expected Outcome |
|----------|-------|------------------|
| Standard URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| Short URL | `https://youtu.be/dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| Embed URL | `https://www.youtube.com/embed/dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| Legacy embed | `https://www.youtube.com/v/dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| Without www | `https://youtube.com/watch?v=dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| HTTP (not HTTPS) | `http://www.youtube.com/watch?v=dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| With timestamp | `https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42` | Returns `dQw4w9WgXcQ` |
| With playlist | `https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxyz` | Returns `dQw4w9WgXcQ` |
| ID with underscore | `https://www.youtube.com/watch?v=abc_def_123` | Returns `abc_def_123` |
| ID with hyphen | `https://www.youtube.com/watch?v=abc-def-123` | Returns `abc-def-123` |
| Non-YouTube URL | `https://vimeo.com/12345` | Raises `URLParseError` ("not a YouTube URL") |
| Missing video ID | `https://www.youtube.com/watch` | Raises `URLParseError` ("video ID") |
| Short video ID | `https://www.youtube.com/watch?v=short` | Raises `URLParseError` ("11 characters") |
| Long video ID | `https://www.youtube.com/watch?v=wayTooLongVideoId` | Raises `URLParseError` ("11 characters") |
| Invalid chars in ID | `https://www.youtube.com/watch?v=abc!def@123` | Raises `URLParseError` |
| Empty URL | `` | Raises `URLParseError` |
| Channel URL | `https://www.youtube.com/c/SomeChannel` | Raises `URLParseError` |
| Playlist-only URL | `https://www.youtube.com/playlist?list=PLxyz` | Raises `URLParseError` |

---

## Implementation Checklist

1. [x] Create file: `src/subsync/url_handler.py`
2. [x] Add imports: `from urllib.parse import urlparse, parse_qs` and `import re`
3. [x] Import: `from subsync.errors import URLParseError`
4. [x] Define: `parse_youtube_url(url: str) -> str`
5. [x] Implement domain validation (youtube.com, www.youtube.com, youtu.be)
6. [x] Implement video ID extraction for each URL pattern
7. [x] Implement video ID validation: regex `^[a-zA-Z0-9_-]{11}$`
8. [x] Create tests: `tests/test_url_handler.py`
9. [x] Run: `task test` — verify pass
10. [x] Run: `task lint` — verify pass

## Verification

- Test run: `uv run pytest` — 38 passed, 0 failed.
- Lint: `uv run ruff check .` — All checks passed.

---

## Definition of Done

- `src/subsync/url_handler.py` exists with `parse_youtube_url` function
- All URL patterns parse correctly
- Invalid URLs raise `URLParseError` with helpful messages
- Tests cover all scenarios above
- All tests pass
- Linting passes

---

## Notes

- Use `urllib.parse` from standard library (no external dependencies)
- Video ID regex: `^[a-zA-Z0-9_-]{11}$`
- Supported domains: `youtube.com`, `www.youtube.com`, `youtu.be`
- `youtu.be` URLs have video ID as first path segment
- `/embed/` and `/v/` URLs have video ID as second path segment

---

## Next Task

→ [05-final-verification.md](./05-final-verification.md)
