# Task 4: Implement URL Handler

## Objective

Create a YouTube URL parser that extracts video IDs from various URL formats and validates them.

---

## Context

- **Plan**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 4. URL Handler"
- **Context**: [youtube-compatibility.md](../../context/youtube-compatibility.md)
- **Depends on**: [Task 2](./02-error-definitions.md), [Task 3](./03-data-models.md)

---

## Requirements

### Functional Requirements

The URL handler must:
- Accept a YouTube URL string as input
- Return the 11-character video ID
- Raise `URLParseError` for invalid or unsupported URLs

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
- Case-sensitive

### Error Handling

Raise `URLParseError` with descriptive message when:
- URL is not from YouTube domain
- URL doesn't contain a video ID
- Video ID format is invalid

---

## Acceptance Criteria

- [ ] Function `parse_youtube_url(url: str) -> str` exists in `src/subsync/url_handler.py`
- [ ] All supported URL patterns return correct video ID
- [ ] Non-YouTube URLs raise `URLParseError` with message containing "not a YouTube URL"
- [ ] Missing video ID raises `URLParseError` with message containing "video ID"
- [ ] Invalid video ID format raises `URLParseError` with message containing "11 characters"
- [ ] Video IDs with underscore and hyphen characters are accepted
- [ ] All unit tests pass
- [ ] Linting passes

---

## Test Scenarios

| Scenario | Input | Expected Outcome |
|----------|-------|------------------|
| Standard URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| Short URL | `https://youtu.be/dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| Embed URL | `https://www.youtube.com/embed/dQw4w9WgXcQ` | Returns `dQw4w9WgXcQ` |
| URL with timestamp | `https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42` | Returns `dQw4w9WgXcQ` |
| URL with playlist | `https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxyz` | Returns `dQw4w9WgXcQ` |
| ID with special chars | `https://www.youtube.com/watch?v=abc_def-123` | Returns `abc_def-123` |
| Non-YouTube URL | `https://vimeo.com/12345` | Raises `URLParseError` |
| Missing video ID | `https://www.youtube.com/watch` | Raises `URLParseError` |
| Short video ID | `https://www.youtube.com/watch?v=short` | Raises `URLParseError` |
| Long video ID | `https://www.youtube.com/watch?v=wayTooLongVideoId` | Raises `URLParseError` |
| Invalid chars in ID | `https://www.youtube.com/watch?v=abc!def@123` | Raises `URLParseError` |
| Empty URL | `` | Raises `URLParseError` |
| Channel URL | `https://www.youtube.com/c/SomeChannel` | Raises `URLParseError` |
| Playlist URL (no video) | `https://www.youtube.com/playlist?list=PLxyz` | Raises `URLParseError` |

---

## Definition of Done

- `src/subsync/url_handler.py` exists with `parse_youtube_url` function
- All supported URL formats parse correctly
- Invalid URLs raise `URLParseError` with helpful messages
- Tests exist in `tests/test_url_handler.py`
- All tests pass
- Linting passes

---

## Notes

- Use standard library for URL parsing (`urllib.parse`)
- Video ID regex pattern: `^[a-zA-Z0-9_-]{11}$`
- Supported domains: `youtube.com`, `www.youtube.com`, `youtu.be`

---

## Next Task

After verification, proceed to → [05-final-verification.md](./05-final-verification.md)
