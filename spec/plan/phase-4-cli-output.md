# Phase 4: CLI & Output Generation

## Overview

This phase completes the application by implementing the subtitle file writer, CLI interface, and user experience polish. This is where everything comes together into a usable tool.

**Estimated Effort**: 3-4 hours
**Dependencies**: Phase 3 complete

---

## Goals

1. Implement SRT and VTT file writers
2. Implement full CLI with `generate` command
3. Add progress display and user feedback
4. Handle errors gracefully with actionable messages
5. Document usage and provide examples

---

## Architecture Decisions

### CLI Framework

**Decision**: Use `argparse` (stdlib) with `rich` for output.

**Rationale**:
- No additional CLI framework dependency
- `argparse` is sufficient for our needs
- `rich` provides beautiful progress bars and output
- Can migrate to `typer` or `click` later if needed

### Output File Naming

**Decision**: `{sanitized_title}.{language}.{format}`

**Example**: `My Video Title.en.srt`

**Rationale**:
- Includes language code for multi-language support
- Title makes files identifiable
- Standard extension for format recognition

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Video unavailable |
| 4 | Transcription failed |
| 5 | File write error |

---

## Components

### 1. Subtitle Writer (`subtitle_writer.py`)

**Responsibilities**:
- Generate SRT format output
- Generate VTT format output
- Handle file encoding (UTF-8)

**Interface**:
```python
def write_srt(subtitles: list[Subtitle], output_path: Path) -> None:
    """Write subtitles to SRT file."""

def write_vtt(subtitles: list[Subtitle], output_path: Path) -> None:
    """Write subtitles to VTT file."""

def format_srt_time(td: timedelta) -> str:
    """Format timedelta as SRT timestamp: HH:MM:SS,mmm"""

def format_vtt_time(td: timedelta) -> str:
    """Format timedelta as VTT timestamp: HH:MM:SS.mmm"""

def write_subtitles(
    subtitles: list[Subtitle],
    output_path: Path,
    format: str = "srt"
) -> None:
    """Write subtitles to file in specified format."""
```

**SRT Format**:
```
1
00:00:00,000 --> 00:00:02,500
Hello everyone and welcome
to today's video.

2
00:00:02,583 --> 00:00:05,000
Today we're going to discuss
something very important.
```

**VTT Format**:
```
WEBVTT

00:00:00.000 --> 00:00:02.500
Hello everyone and welcome
to today's video.

00:00:02.583 --> 00:00:05.000
Today we're going to discuss
something very important.
```

### 2. CLI Implementation (`cli.py`)

**Command Structure**:
```
subsync generate <youtube_url> [OPTIONS]
```

**Options**:
```
Arguments:
  youtube_url            YouTube video URL (required)

Options:
  -l, --language TEXT    Audio language code (default: auto-detect)
  -o, --output PATH      Output file path (default: ./{title}.{lang}.srt)
  -f, --format TEXT      Output format: srt, vtt (default: srt)
  -m, --model TEXT       Whisper model: tiny, base, small, medium, large-v3, turbo
                         (default: turbo)
  --children             Apply stricter reading speed for children's content
  -v, --verbose          Show detailed progress and debug info
  --version              Show version and exit
  --help                 Show this help message
```

**Implementation Skeleton**:
```python
import argparse
import sys
from rich.console import Console
from rich.progress import Progress

console = Console()

def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    try:
        return run_generate(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        return 1
    except SubSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        return e.exit_code

def run_generate(args) -> int:
    """Execute the generate command."""
    with Progress(...) as progress:
        # 1. Parse URL
        # 2. Get metadata
        # 3. Download audio
        # 4. Transcribe
        # 5. Process subtitles
        # 6. Write output
        # 7. Show summary
    return 0
```

### 3. Progress Display

**Using `rich` Progress**:
```python
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )
```

**Expected Output**:
```
⠋ Fetching video metadata...
✓ Video: "Introduction to Python" (12:34)

⠋ Downloading audio... ━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
✓ Audio extracted

⠋ Transcribing audio... ━━━━━━━━━━━━━━━━━━━━ 100% 0:00:12
✓ Transcription complete (45 segments)

⠋ Processing subtitles...
✓ Generated 52 subtitles

Output: Introduction to Python.en.srt

Compliance Report:
  ✓ All timing requirements met
  ⚠ 3 subtitles exceed recommended reading speed (20 CPS)
```

### 4. Error Messages

**User-Friendly Error Display**:
```python
ERROR_MESSAGES = {
    VideoUnavailableError: (
        "Video not found or unavailable.\n"
        "Please check:\n"
        "  • The URL is correct\n"
        "  • The video is public\n"
        "  • The video hasn't been deleted"
    ),
    AgeRestrictedError: (
        "This video requires age verification.\n"
        "SubSync cannot process age-restricted content."
    ),
    LiveStreamError: (
        "Live streams are not supported.\n"
        "Please wait for the stream to end and try again."
    ),
    TranscriptionError: (
        "Transcription failed.\n"
        "Try:\n"
        "  • Using a smaller model (--model small)\n"
        "  • Checking if the video has clear audio"
    ),
}
```

### 5. Filename Sanitization

```python
import re

def sanitize_filename(title: str, max_length: int = 100) -> str:
    """
    Create a safe filename from video title.

    Removes/replaces characters that are invalid in filenames.
    """
    # Remove characters invalid on any OS
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace multiple spaces/underscores with single space
    sanitized = re.sub(r'[\s_]+', ' ', sanitized)
    # Trim whitespace
    sanitized = sanitized.strip()
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rsplit(' ', 1)[0]
    return sanitized or "subtitles"
```

---

## Testing Strategy

### Unit Tests

**Subtitle Writer**:
```python
def test_format_srt_time():
    td = timedelta(hours=1, minutes=23, seconds=45, milliseconds=678)
    assert format_srt_time(td) == "01:23:45,678"

def test_format_vtt_time():
    td = timedelta(seconds=90, milliseconds=500)
    assert format_vtt_time(td) == "00:01:30.500"

def test_write_srt_creates_valid_file(tmp_path):
    subtitles = [make_subtitle(index=1, text="Hello")]
    output = tmp_path / "test.srt"
    write_srt(subtitles, output)

    content = output.read_text()
    assert "1\n" in content
    assert "Hello" in content
    assert "-->" in content

def test_sanitize_filename():
    assert sanitize_filename("My Video: Part 1") == "My Video Part 1"
    assert sanitize_filename("Test???") == "Test"
```

**CLI** (using subprocess or click testing):
```python
def test_cli_help():
    result = subprocess.run(["subsync", "--help"], capture_output=True)
    assert result.returncode == 0
    assert "generate" in result.stdout.decode()

def test_cli_invalid_url():
    result = subprocess.run(
        ["subsync", "generate", "not-a-url"],
        capture_output=True
    )
    assert result.returncode == 2
```

### End-to-End Test

```python
@pytest.mark.e2e
@pytest.mark.slow
def test_full_generate_command(tmp_path):
    """Test complete flow with a short public video."""
    output = tmp_path / "output.srt"
    result = subprocess.run([
        "subsync", "generate",
        "https://www.youtube.com/watch?v=SHORT_PUBLIC_VIDEO",
        "-o", str(output),
        "--model", "tiny"  # Fast for testing
    ], capture_output=True)

    assert result.returncode == 0
    assert output.exists()
    content = output.read_text()
    assert "1\n" in content
    assert "-->" in content
```

---

## Acceptance Criteria

- [ ] `subsync generate <url>` works end-to-end
- [ ] SRT files are valid and uploadable to YouTube
- [ ] VTT files are valid (when `--format vtt`)
- [ ] Progress is displayed during processing
- [ ] Compliance report shown after generation
- [ ] Errors display helpful, actionable messages
- [ ] `--help` shows complete usage information
- [ ] Exit codes are correct for different error types
- [ ] Output filename is safe for all operating systems
- [ ] `--verbose` shows additional debug information

---

## User Experience Polish

### Success Output
```
✓ Subtitles generated successfully!

  File: Introduction to Python.en.srt
  Duration: 12:34
  Subtitles: 156
  Language: English (detected)

  Compliance:
    ✓ Timing: All requirements met
    ⚠ Reading Speed: 3 subtitles exceed 20 CPS (flagged for review)

  Ready to upload to YouTube!
```

### Error Output
```
✗ Error: Video not found or unavailable

  Please check:
  • The URL is correct
  • The video is public
  • The video hasn't been deleted

  URL: https://www.youtube.com/watch?v=INVALID
```

---

## Documentation Updates

After Phase 4, update:

1. **README.md**: Installation, quick start, examples
2. **--help**: Ensure comprehensive and accurate
3. **CHANGELOG.md**: Document initial release

---

## Future Enhancements (Post-MVP)

Not in scope for Phase 4, but designed for:

- [ ] `subsync translate` command
- [ ] Batch processing multiple videos
- [ ] Configuration file support
- [ ] Custom Netflix profile selection
- [ ] SRT/VTT input for re-processing

---

## Completion Checklist

After all phases complete:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] `task lint` passes
- [ ] `task format` produces no changes
- [ ] README updated with usage instructions
- [ ] Manual testing with 3+ different videos
- [ ] Test on macOS, Linux, Windows (if available)
