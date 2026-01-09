# Task 3: Implement Data Models

## Overview

Implement all core data models as Python dataclasses. These models define the data structures flowing between modules throughout the pipeline.

**Plan Reference**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 2. Data Models"

**Context Reference**: [data-models.md](../../context/data-models.md)

**Depends On**: [Task 2](./02-error-definitions.md)

---

## Objective

Create `src/subsync/models.py` with all data classes defined in the context, including computed properties for validation and compliance checking.

---

## Requirements

### Core Models to Implement

| Model | Purpose |
|-------|---------|
| `VideoMetadata` | YouTube video information |
| `Word` | Individual word with timing |
| `TranscriptionSegment` | Segment of transcribed speech |
| `TranscriptionResult` | Complete transcription output |
| `Subtitle` | Single subtitle event with computed properties |
| `SubtitleFile` | Container for subtitle file |

### Validation Models

| Model | Purpose |
|-------|---------|
| `TimingValidation` | Result of timing validation |
| `ComplianceReport` | Aggregate compliance status |

### Configuration Models

| Model | Purpose |
|-------|---------|
| `TranscriptionConfig` | Transcription settings |
| `ProcessingConfig` | Subtitle processing settings |
| `OutputConfig` | Output generation settings |

---

## Implementation

### File: `src/subsync/models.py`

Implement all models from [data-models.md](../../context/data-models.md).

Key implementation notes:

1. **Use standard library only**: `dataclasses`, `datetime`, `pathlib`
2. **Type hints on all fields**: Use `list[X]` not `List[X]` (Python 3.10+)
3. **Computed properties**: `Subtitle` has `char_count`, `duration_ms`, `cps` properties
4. **Default values**: Configuration models have sensible defaults
5. **Optional fields**: Use `| None` syntax for optional fields

### Key Computed Properties (Subtitle class)

```python
@property
def char_count(self) -> int:
    """Total characters across all lines."""
    return sum(len(line) for line in self.lines)

@property
def duration_ms(self) -> int:
    """Duration in milliseconds."""
    return int((self.end_time - self.start_time).total_seconds() * 1000)

@property
def cps(self) -> float:
    """Characters per second."""
    duration_secs = self.duration_ms / 1000
    return self.char_count / duration_secs if duration_secs > 0 else 0
```

---

## Tests to Implement

### File: `tests/test_models.py`

```python
"""Tests for data models."""

from datetime import timedelta

import pytest

from subsync.models import (
    VideoMetadata,
    Word,
    TranscriptionSegment,
    TranscriptionResult,
    Subtitle,
    SubtitleFile,
    TimingValidation,
    ComplianceReport,
    TranscriptionConfig,
    ProcessingConfig,
    OutputConfig,
)


class TestVideoMetadata:
    def test_create_video_metadata(self):
        meta = VideoMetadata(
            id="dQw4w9WgXcQ",
            title="Test Video",
            duration=180.0,
            uploader="Test Channel",
            upload_date="20240115",
        )
        assert meta.id == "dQw4w9WgXcQ"
        assert meta.duration == 180.0


class TestWord:
    def test_create_word(self):
        word = Word(word="hello", start=0.0, end=0.5)
        assert word.word == "hello"
        assert word.start == 0.0
        assert word.end == 0.5


class TestSubtitle:
    def test_char_count_single_line(self):
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=2),
            text="Hello world",
            lines=["Hello world"],
        )
        assert subtitle.char_count == 11

    def test_char_count_multiple_lines(self):
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=2),
            text="Hello world, how are you?",
            lines=["Hello world,", "how are you?"],
        )
        assert subtitle.char_count == 24  # 12 + 12

    def test_duration_ms(self):
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=1),
            end_time=timedelta(seconds=3, milliseconds=500),
            text="Test",
            lines=["Test"],
        )
        assert subtitle.duration_ms == 2500

    def test_cps_calculation(self):
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=2),
            text="Hello world",
            lines=["Hello world"],  # 11 chars
        )
        # 11 chars / 2 seconds = 5.5 cps
        assert subtitle.cps == 5.5

    def test_cps_zero_duration(self):
        subtitle = Subtitle(
            index=1,
            start_time=timedelta(seconds=1),
            end_time=timedelta(seconds=1),  # Same time = 0 duration
            text="Test",
            lines=["Test"],
        )
        assert subtitle.cps == 0  # Avoid division by zero


class TestConfigDefaults:
    def test_transcription_config_defaults(self):
        config = TranscriptionConfig()
        assert config.model_name == "turbo"
        assert config.language is None
        assert config.word_timestamps is True
        assert config.device == "auto"

    def test_processing_config_defaults(self):
        config = ProcessingConfig()
        assert config.max_chars_per_line == 42
        assert config.max_lines == 2
        assert config.min_duration_ms == 833
        assert config.max_duration_ms == 7000
        assert config.min_gap_ms == 83
        assert config.max_cps_adult == 20.0
        assert config.max_cps_children == 17.0
        assert config.is_children_content is False

    def test_output_config_defaults(self):
        config = OutputConfig()
        assert config.format == "srt"
        assert config.output_path is None
        assert config.include_bom is False
```

---

## Verification Checklist

- [ ] File created at `src/subsync/models.py`
- [ ] All 11 model classes implemented
- [ ] All type hints present
- [ ] All docstrings present
- [ ] `Subtitle` computed properties work correctly
- [ ] Configuration defaults match spec
- [ ] Tests created at `tests/test_models.py`
- [ ] `task test` passes
- [ ] `task lint` passes

### Quick Import Test

```bash
uv run python -c "from subsync.models import VideoMetadata, Word, TranscriptionSegment, Subtitle; print('All models imported')"
```

---

## Definition of Done

- `src/subsync/models.py` exists with all 11 model classes
- All models have type hints and docstrings
- Computed properties on `Subtitle` work correctly
- Unit tests pass
- Linting passes

---

## Next Task

After verification, proceed to → [04-url-handler.md](./04-url-handler.md)

---

## User Verification Required

**STOP** after completing this task. Present the changes to the user and wait for verification before proceeding to the next task.
