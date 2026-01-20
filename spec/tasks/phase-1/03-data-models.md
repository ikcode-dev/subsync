# Task 3: Implement Data Models

## Objective

Create all data models as Python dataclasses that define the data structures flowing between SubSync modules.

## Detail Level

EXPANDED

---

## Context

### References

- **Plan**: [phase-1-foundation.md](../../plan/phase-1-foundation.md) → Section "Components → 3. Data Models"
- **Context**: [data-models.md](../../context/data-models.md)

### Dependencies

- **Task 2**: *(Sequencing only — no imports needed)*

### Context Summary

SubSync uses dataclasses to define contracts between pipeline stages:

```
URL Handler → VideoMetadata
Transcriber → TranscriptionResult (containing TranscriptionSegment, Word)
Processor → Subtitle, SubtitleFile, ComplianceReport
```

**Why Dataclasses (not Pydantic)**:
- Zero additional dependencies
- Sufficient for current validation needs
- Standard library familiarity
- Can migrate to Pydantic later if advanced validation needed

#### Model Categories

**Core Domain Models** (data flowing through pipeline):

| Model | Fields | Purpose |
|-------|--------|---------|
| `VideoMetadata` | id, title, duration, uploader, upload_date | YouTube video info |
| `Word` | word, start, end | Single word with timing |
| `TranscriptionSegment` | id, start, end, text, words | Speech segment |
| `TranscriptionResult` | language, duration, segments | Whisper output |
| `Subtitle` | index, start_time, end_time, text, lines | SRT/VTT event |
| `SubtitleFile` | format, language, video_id, subtitles | Complete file |

**Validation Models** (compliance checking):

| Model | Fields | Purpose |
|-------|--------|---------|
| `TimingValidation` | is_valid, duration_ok, gap_ok, issues | Single subtitle check |
| `ComplianceReport` | total_subtitles, timing_issues, cps_warnings, ... | File-level report |

**Configuration Models** (settings with defaults):

| Model | Key Defaults | Purpose |
|-------|--------------|---------|
| `TranscriptionConfig` | model="turbo", word_timestamps=True | Whisper settings |
| `ProcessingConfig` | max_chars=42, max_lines=2, min_duration=833ms | Netflix rules |
| `OutputConfig` | format="srt", include_bom=False | Output settings |

#### Subtitle Computed Properties

The `Subtitle` class needs computed properties for compliance checking:

| Property | Calculation | Why Needed |
|----------|-------------|------------|
| `char_count` | Sum of characters across all lines | CPS calculation |
| `duration_ms` | (end_time - start_time) in milliseconds | Duration validation |
| `cps` | char_count / (duration_ms / 1000) | Netflix CPS check |

#### Netflix Compliance Values (from ProcessingConfig defaults)

| Setting | Default | Netflix Rule |
|---------|---------|--------------|
| `max_chars_per_line` | 42 | Maximum characters per line |
| `max_lines` | 2 | Maximum lines per subtitle |
| `min_duration_ms` | 833 | Minimum 5/6 second display |
| `max_duration_ms` | 7000 | Maximum 7 second display |
| `min_gap_ms` | 83 | Minimum 2 frames gap |
| `max_cps_adult` | 20.0 | Adult reading speed |
| `max_cps_children` | 17.0 | Children reading speed |

---

## Requirements

### Functional Requirements

- All models are Python `@dataclass` classes
- All fields have type hints
- All models have docstrings
- `Subtitle` has `char_count`, `duration_ms`, `cps` properties
- Configuration models have defaults matching Netflix requirements
- Optional fields use `| None` syntax

### Interface Contract

```python
# Core models require all fields:
meta = VideoMetadata(id="...", title="...", duration=180.0, uploader="...", upload_date="...")

# Config models have defaults:
config = TranscriptionConfig()  # All defaults applied
config = ProcessingConfig(max_chars_per_line=50)  # Override one default

# Subtitle computed properties:
subtitle = Subtitle(index=1, start_time=timedelta(0), end_time=timedelta(seconds=2),
                    text="Hello", lines=["Hello"])
print(subtitle.cps)  # 2.5
```

### Models to Implement

| # | Model | Required Fields |
|---|-------|-----------------|
| 1 | `VideoMetadata` | id, title, duration, uploader, upload_date |
| 2 | `Word` | word, start, end |
| 3 | `TranscriptionSegment` | id, start, end, text, words |
| 4 | `TranscriptionResult` | language, duration, segments |
| 5 | `Subtitle` | index, start_time, end_time, text, lines + properties |
| 6 | `SubtitleFile` | format, language, video_id, subtitles |
| 7 | `TimingValidation` | is_valid, duration_ok, gap_ok, issues |
| 8 | `ComplianceReport` | total_subtitles, timing_issues, cps_warnings, line_length_issues, is_compliant, warnings, errors |
| 9 | `TranscriptionConfig` | model_name, language, word_timestamps, device |
| 10 | `ProcessingConfig` | max_chars_per_line, max_lines, min_duration_ms, max_duration_ms, min_gap_ms, max_cps_adult, max_cps_children, is_children_content |
| 11 | `OutputConfig` | format, output_path, include_bom |

---

## Acceptance Criteria

- [ ] File exists at `src/subsync/models.py`
- [ ] All 11 model classes implemented as dataclasses
- [ ] All fields have type hints
- [ ] All models have docstrings
- [ ] `Subtitle.char_count` returns sum of line lengths
- [ ] `Subtitle.duration_ms` returns duration in milliseconds
- [ ] `Subtitle.cps` returns characters per second (0 if zero duration)
- [ ] `TranscriptionConfig()` defaults: model_name="turbo", word_timestamps=True, device="auto"
- [ ] `ProcessingConfig()` defaults match Netflix values above
- [ ] `OutputConfig()` defaults: format="srt", include_bom=False
- [ ] Tests exist at `tests/test_models.py`
- [ ] `task test` passes
- [ ] `task lint` passes

---

## Test Scenarios

| Scenario | Input | Expected Outcome |
|----------|-------|------------------|
| Create VideoMetadata | All fields provided | Instance with correct values |
| Create Word | word="hello", start=0.0, end=0.5 | Instance with correct values |
| Subtitle char_count (single line) | lines=["Hello world"] | Returns 11 |
| Subtitle char_count (two lines) | lines=["Hello world,", "how are you?"] | Returns 24 |
| Subtitle duration_ms | start=1s, end=3.5s | Returns 2500 |
| Subtitle cps | 11 chars, 2s duration | Returns 5.5 |
| Subtitle cps (zero duration) | start=end=1s | Returns 0 (no division error) |
| TranscriptionConfig defaults | `TranscriptionConfig()` | model_name="turbo", language=None, word_timestamps=True, device="auto" |
| ProcessingConfig defaults | `ProcessingConfig()` | max_chars=42, max_lines=2, min_duration=833, etc. |
| OutputConfig defaults | `OutputConfig()` | format="srt", output_path=None, include_bom=False |

---

## Implementation Checklist

1. [ ] Create file: `src/subsync/models.py`
2. [ ] Add imports: `from dataclasses import dataclass, field` and `from datetime import timedelta` and `from pathlib import Path`
3. [ ] Define: `VideoMetadata` dataclass
4. [ ] Define: `Word` dataclass
5. [ ] Define: `TranscriptionSegment` dataclass (words field has default empty list)
6. [ ] Define: `TranscriptionResult` dataclass
7. [ ] Define: `Subtitle` dataclass with `char_count`, `duration_ms`, `cps` properties
8. [ ] Define: `SubtitleFile` dataclass
9. [ ] Define: `TimingValidation` dataclass
10. [ ] Define: `ComplianceReport` dataclass
11. [ ] Define: `TranscriptionConfig` dataclass with defaults
12. [ ] Define: `ProcessingConfig` dataclass with Netflix defaults
13. [ ] Define: `OutputConfig` dataclass with defaults
14. [ ] Create tests: `tests/test_models.py`
15. [ ] Run: `task test` — verify pass
16. [ ] Run: `task lint` — verify pass

---

## Definition of Done

- `src/subsync/models.py` exists with all 11 dataclasses
- All type hints and docstrings present
- Computed properties work correctly
- Configuration defaults match spec
- Tests pass
- Linting passes

---

## Notes

- Use `field(default_factory=lambda: [])` for list defaults (Pyright compatibility)
- Use `timedelta` from `datetime` for time fields in `Subtitle`
- Use `Path | None` for optional path fields
- Properties don't need `@dataclass` — they're regular Python properties

---

## Next Task

→ [04-url-handler.md](./04-url-handler.md)
