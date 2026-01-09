# Task 4: Implement URL Handler

## Overview

Implement the YouTube URL parser and validator. This module extracts video IDs from various YouTube URL formats.

**Plan Reference**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 4. URL Handler"

**Context Reference**: [youtube-compatibility.md](../../context/youtube-compatibility.md)

**Depends On**: [Task 2](./02-error-definitions.md), [Task 3](./03-data-models.md)

---

## Objective

Create `src/subsync/url_handler.py` that parses YouTube URLs and extracts the 11-character video ID.

---

## Requirements

### Supported URL Patterns

| Pattern | Example |
|---------|---------|
| Standard watch URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| Short URL | `https://youtu.be/dQw4w9WgXcQ` |
| Embed URL | `https://www.youtube.com/embed/dQw4w9WgXcQ` |
| Old embed URL | `https://www.youtube.com/v/dQw4w9WgXcQ` |
| With extra params | `https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42&list=PLxyz` |
| Without www | `https://youtube.com/watch?v=dQw4w9WgXcQ` |
| HTTP (not just HTTPS) | `http://www.youtube.com/watch?v=dQw4w9WgXcQ` |

### Video ID Validation

- Exactly 11 characters
- Contains only `[a-zA-Z0-9_-]`
- YouTube video IDs are case-sensitive

### Error Handling

Raise `URLParseError` with descriptive message when:
- URL is not from YouTube domain
- URL doesn't contain a video ID
- Video ID is invalid format

---

## Implementation

### File: `src/subsync/url_handler.py`

```python
"""YouTube URL parsing and validation."""

import re
from urllib.parse import parse_qs, urlparse

from subsync.errors import URLParseError


# YouTube video ID pattern: exactly 11 chars, alphanumeric + _ and -
VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")

# Supported YouTube domains
YOUTUBE_DOMAINS = {"youtube.com", "www.youtube.com", "youtu.be"}


def parse_youtube_url(url: str) -> str:
    """Extract video ID from a YouTube URL.

    Supports multiple URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - URLs with additional parameters

    Args:
        url: YouTube video URL.

    Returns:
        The 11-character video ID.

    Raises:
        URLParseError: If URL is invalid or not a YouTube URL.
    """
    # Implementation here
    ...


def _validate_video_id(video_id: str) -> str:
    """Validate that a video ID has correct format.

    Args:
        video_id: Candidate video ID.

    Returns:
        The validated video ID.

    Raises:
        URLParseError: If video ID format is invalid.
    """
    if not VIDEO_ID_PATTERN.match(video_id):
        raise URLParseError(
            f"Invalid video ID format: '{video_id}'. "
            "Video ID must be exactly 11 characters (a-z, A-Z, 0-9, -, _)."
        )
    return video_id
```

### Key Implementation Points

1. Use `urllib.parse.urlparse` to parse the URL
2. Check domain against `YOUTUBE_DOMAINS`
3. Extract video ID based on URL path structure:
   - `/watch` → get `v` parameter from query string
   - `/embed/VIDEO_ID` → extract from path
   - `/v/VIDEO_ID` → extract from path
   - `youtu.be/VIDEO_ID` → extract from path
4. Validate extracted ID with regex
5. Return validated video ID or raise `URLParseError`

---

## Tests to Implement

### File: `tests/test_url_handler.py`

```python
"""Tests for YouTube URL parsing."""

import pytest

from subsync.errors import URLParseError
from subsync.url_handler import parse_youtube_url


class TestParseYoutubeUrl:
    """Tests for parse_youtube_url function."""

    # === Valid URL formats ===

    def test_standard_watch_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_old_embed_url(self):
        url = "https://www.youtube.com/v/dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_without_www(self):
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_http_not_https(self):
        url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_with_timestamp(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_with_playlist(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        assert parse_youtube_url(url) == "dQw4w9WgXcQ"

    def test_video_id_with_underscore(self):
        url = "https://www.youtube.com/watch?v=abc_def-123"
        assert parse_youtube_url(url) == "abc_def-123"

    def test_video_id_with_hyphen(self):
        url = "https://www.youtube.com/watch?v=abc-def_123"
        assert parse_youtube_url(url) == "abc-def_123"

    # === Invalid URLs ===

    def test_non_youtube_url_raises(self):
        with pytest.raises(URLParseError, match="not a YouTube URL"):
            parse_youtube_url("https://vimeo.com/12345")

    def test_invalid_domain_raises(self):
        with pytest.raises(URLParseError):
            parse_youtube_url("https://notyoutube.com/watch?v=dQw4w9WgXcQ")

    def test_missing_video_id_raises(self):
        with pytest.raises(URLParseError, match="video ID"):
            parse_youtube_url("https://www.youtube.com/watch")

    def test_empty_video_id_raises(self):
        with pytest.raises(URLParseError):
            parse_youtube_url("https://www.youtube.com/watch?v=")

    def test_short_video_id_raises(self):
        with pytest.raises(URLParseError, match="11 characters"):
            parse_youtube_url("https://www.youtube.com/watch?v=short")

    def test_long_video_id_raises(self):
        with pytest.raises(URLParseError, match="11 characters"):
            parse_youtube_url("https://www.youtube.com/watch?v=wayTooLongVideoId")

    def test_invalid_chars_in_video_id_raises(self):
        with pytest.raises(URLParseError):
            parse_youtube_url("https://www.youtube.com/watch?v=abc!def@123")

    def test_empty_url_raises(self):
        with pytest.raises(URLParseError):
            parse_youtube_url("")

    def test_non_url_string_raises(self):
        with pytest.raises(URLParseError):
            parse_youtube_url("not a url at all")

    def test_youtube_channel_url_raises(self):
        with pytest.raises(URLParseError):
            parse_youtube_url("https://www.youtube.com/c/SomeChannel")

    def test_youtube_playlist_url_raises(self):
        with pytest.raises(URLParseError):
            parse_youtube_url("https://www.youtube.com/playlist?list=PLxyz")
```

---

## Verification Checklist

- [ ] File created at `src/subsync/url_handler.py`
- [ ] `parse_youtube_url` function implemented
- [ ] All URL formats from requirements supported
- [ ] Clear error messages in `URLParseError`
- [ ] Tests created at `tests/test_url_handler.py`
- [ ] All tests pass
- [ ] `task lint` passes

### Quick Test

```bash
uv run python -c "from subsync.url_handler import parse_youtube_url; print(parse_youtube_url('https://youtu.be/dQw4w9WgXcQ'))"
```

Expected output: `dQw4w9WgXcQ`

---

## Definition of Done

- `src/subsync/url_handler.py` exists with `parse_youtube_url` function
- All supported URL formats parse correctly
- Invalid URLs raise `URLParseError` with helpful messages
- All unit tests pass
- Linting passes

---

## Next Task

After verification, proceed to → [05-final-verification.md](./05-final-verification.md)

---

## User Verification Required

**STOP** after completing this task. Present the changes to the user and wait for verification before proceeding to the next task.
