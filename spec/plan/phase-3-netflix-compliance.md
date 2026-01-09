# Phase 3: Netflix Compliance Processing

## Overview

This phase implements the subtitle processor that transforms raw transcription segments into Netflix-compliant subtitle events. This is where the intelligence lives—timing adjustments, text segmentation, and compliance validation.

**Estimated Effort**: 4-5 hours
**Dependencies**: Phase 2 complete

---

## Goals

1. Implement timing validation and adjustment
2. Implement intelligent text segmentation (line breaks)
3. Implement reading speed (CPS) validation
4. Generate compliant `Subtitle` events from transcription
5. Produce compliance reports for user feedback

---

## Architecture Decisions

### Approach: Transform, Don't Mutate

**Decision**: Processing creates new subtitle objects rather than modifying transcription segments.

**Rationale**:
- Clear separation between raw data and processed output
- Easier to debug and test
- Can compare before/after if needed

### Line Breaking Strategy

**Decision**: Rule-based breaking with linguistic heuristics.

**Rationale**:
- Predictable, testable behavior
- No ML dependency for text processing
- Can be tuned with configuration

**Alternative Considered**: NLP-based sentence parsing
- Rejected: Overkill for subtitle line breaks, adds dependency

### CPS Handling

**Decision**: Warn but don't block on CPS violations.

**Rationale**:
- Transcription accuracy shouldn't be sacrificed
- User can review flagged subtitles
- Automatic fixes may worsen quality

---

## Components

### 1. Timing Processor (`timing_processor.py`)

**Responsibilities**:
- Validate subtitle durations (833ms - 7000ms)
- Ensure minimum gaps between subtitles (83ms)
- Adjust timings when violations detected
- Split long segments

**Interface**:
```python
def validate_timing(subtitle: Subtitle, previous_end: timedelta | None) -> TimingValidation:
    """Check if subtitle timing meets Netflix requirements."""

def adjust_duration(subtitle: Subtitle, min_ms: int = 833) -> Subtitle:
    """Extend subtitle duration to meet minimum."""

def ensure_gap(subtitle: Subtitle, previous_end: timedelta, min_gap_ms: int = 83) -> Subtitle:
    """Adjust start time to ensure minimum gap from previous subtitle."""

def split_long_segment(segment: TranscriptionSegment, max_duration_ms: int = 7000) -> list[TranscriptionSegment]:
    """Split segment that exceeds maximum duration."""
```

**Timing Rules Implementation**:

```
┌─────────────────────────────────────────────────────────────┐
│                    TIMING DECISION TREE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: segment (start, end, text)                          │
│                                                              │
│  1. Calculate duration = end - start                        │
│                                                              │
│  2. IF duration < 833ms:                                    │
│     └─▶ Extend end = start + 833ms                         │
│         (unless would overlap next segment)                 │
│                                                              │
│  3. IF duration > 7000ms:                                   │
│     └─▶ Split using word timestamps                        │
│         └─▶ Find break point near middle                   │
│         └─▶ Prefer breaking at sentence/clause boundaries  │
│         └─▶ Create 2+ segments                             │
│                                                              │
│  4. IF gap from previous < 83ms:                            │
│     └─▶ Adjust start = previous.end + 83ms                 │
│         └─▶ Recalculate duration, may need adjustment      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Text Segmenter (`text_segmenter.py`)

**Responsibilities**:
- Split text into 1-2 lines
- Respect 42 character per line limit
- Apply linguistic line break rules
- Handle text that requires multiple subtitle events

**Interface**:
```python
def segment_text(text: str, max_chars_per_line: int = 42) -> list[str]:
    """
    Split text into lines for a single subtitle.

    Returns:
        List of 1-2 lines, each <= max_chars_per_line

    Note:
        If text cannot fit in 2 lines, only first 84 chars used.
        Caller should split into multiple subtitles for longer text.
    """

def find_break_point(text: str, target_position: int) -> int:
    """
    Find the best position to break text near target_position.

    Applies Netflix line break rules in priority order.
    """

def needs_multiple_subtitles(text: str, max_total_chars: int = 84) -> bool:
    """Check if text requires splitting into multiple subtitle events."""
```

**Line Break Priority** (from Netflix Style Guide):

```python
BREAK_AFTER_PRIORITY = [
    # Priority 1: Punctuation (best breaks)
    r'[.!?]',           # End of sentence
    r'[,;:]',           # Clause boundaries

    # Priority 2: Conjunctions
    r'\s+(and|but|or|so|yet)\s+',

    # Priority 3: Prepositions
    r'\s+(in|on|at|to|for|of|with|from|by)\s+',
]

AVOID_BREAKING = [
    r'\b(the|a|an)\s+\w+',      # Article + noun
    r'\b(very|really|quite)\s+\w+',  # Adverb + adjective
    # More patterns...
]
```

### 3. CPS Validator (`cps_validator.py`)

**Responsibilities**:
- Calculate characters per second
- Flag subtitles exceeding limits
- Suggest adjustments when possible

**Interface**:
```python
def calculate_cps(subtitle: Subtitle) -> float:
    """Calculate characters per second for a subtitle."""

def validate_cps(
    subtitle: Subtitle,
    max_cps: float = 20.0
) -> tuple[bool, str | None]:
    """
    Validate reading speed.

    Returns:
        (is_valid, warning_message)
    """

def suggest_cps_fix(
    subtitle: Subtitle,
    max_cps: float,
    available_extension_ms: int
) -> Subtitle | None:
    """
    Suggest a duration extension to meet CPS target.

    Returns:
        Adjusted subtitle or None if cannot fix.
    """
```

### 4. Subtitle Processor (`subtitle_processor.py`)

**Responsibilities**:
- Orchestrate the full processing pipeline
- Convert `TranscriptionResult` to `list[Subtitle]`
- Generate compliance report

**Interface**:
```python
def process_transcription(
    transcription: TranscriptionResult,
    config: ProcessingConfig
) -> tuple[list[Subtitle], ComplianceReport]:
    """
    Process transcription into Netflix-compliant subtitles.

    Returns:
        (subtitles, compliance_report)
    """
```

**Processing Flow**:

```
┌───────────────────────────────────────────────────────────────────┐
│                    SUBTITLE PROCESSING FLOW                        │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Input: TranscriptionResult.segments                              │
│                                                                    │
│  FOR each segment:                                                │
│    │                                                               │
│    ├──▶ 1. Check if needs splitting (duration > 7s OR chars > 84)│
│    │       └─▶ Split into multiple sub-segments                   │
│    │                                                               │
│    ├──▶ 2. For each (sub-)segment:                               │
│    │       │                                                       │
│    │       ├──▶ Apply timing rules                               │
│    │       │    └─▶ Adjust duration, ensure gaps                 │
│    │       │                                                       │
│    │       ├──▶ Segment text into lines                          │
│    │       │    └─▶ Apply break rules, max 2 lines               │
│    │       │                                                       │
│    │       ├──▶ Validate CPS                                     │
│    │       │    └─▶ Flag warnings if exceeded                    │
│    │       │                                                       │
│    │       └──▶ Create Subtitle object                           │
│    │                                                               │
│    └──▶ 3. Add to results, increment index                       │
│                                                                    │
│  Output: list[Subtitle], ComplianceReport                         │
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests

**Timing Processor**:
```python
def test_short_duration_extended():
    subtitle = make_subtitle(start_ms=0, end_ms=500, text="Hi")
    adjusted = adjust_duration(subtitle, min_ms=833)
    assert adjusted.duration_ms == 833

def test_long_segment_split():
    segment = make_segment(start=0, end=10, text="Very long text...")
    splits = split_long_segment(segment, max_duration_ms=7000)
    assert len(splits) == 2
    assert all(s.end - s.start <= 7.0 for s in splits)

def test_gap_enforcement():
    prev_end = timedelta(seconds=5)
    subtitle = make_subtitle(start_ms=5020, end_ms=7000, text="Next")
    adjusted = ensure_gap(subtitle, prev_end, min_gap_ms=83)
    assert adjusted.start_time >= prev_end + timedelta(milliseconds=83)
```

**Text Segmenter**:
```python
def test_short_text_single_line():
    lines = segment_text("Hello world")
    assert lines == ["Hello world"]

def test_long_text_two_lines():
    text = "This is a somewhat longer piece of text that needs two lines"
    lines = segment_text(text)
    assert len(lines) == 2
    assert all(len(line) <= 42 for line in lines)

def test_break_after_punctuation():
    text = "Hello, world. This is a test for breaking."
    lines = segment_text(text)
    # Should break after period if near middle
    assert lines[0].endswith('.')

def test_avoid_breaking_article_noun():
    text = "She walked into the beautiful garden slowly"
    # Should NOT break between "the" and "beautiful"
    lines = segment_text(text)
    assert "the\n" not in "\n".join(lines)
```

**CPS Validator**:
```python
def test_cps_calculation():
    subtitle = make_subtitle(text="Hello world", duration_ms=1000)
    assert calculate_cps(subtitle) == 11.0  # 11 chars / 1 sec

def test_cps_warning_when_exceeded():
    subtitle = make_subtitle(text="X" * 25, duration_ms=1000)  # 25 CPS
    is_valid, warning = validate_cps(subtitle, max_cps=20.0)
    assert not is_valid
    assert "25.0" in warning
```

### Integration Tests

```python
def test_full_processing_pipeline():
    transcription = TranscriptionResult(
        language="en",
        duration=60.0,
        segments=[...]
    )
    subtitles, report = process_transcription(transcription, ProcessingConfig())

    assert len(subtitles) > 0
    assert all(s.duration_ms >= 833 for s in subtitles)
    assert all(len(line) <= 42 for s in subtitles for line in s.lines)
```

---

## Acceptance Criteria

- [ ] Short segments (< 833ms) are extended
- [ ] Long segments (> 7000ms) are split
- [ ] Minimum 83ms gap between consecutive subtitles
- [ ] Lines respect 42 character limit
- [ ] Maximum 2 lines per subtitle
- [ ] Line breaks follow Netflix priority rules
- [ ] CPS calculated correctly
- [ ] High CPS subtitles flagged in compliance report
- [ ] Compliance report summarizes all issues
- [ ] All unit tests pass

---

## Edge Cases to Handle

| Case | Expected Behavior |
|------|-------------------|
| Empty segment text | Skip segment |
| Single word > 42 chars | Truncate with ellipsis, warn |
| Overlapping timestamps | Adjust to create gaps |
| No word timestamps | Use segment timing for splits |
| Consecutive short segments | May merge if combined < 7s |
| All caps text | Preserve (don't modify case) |
| Special characters | Preserve Unicode, escape if needed |

---

## Performance Considerations

Processing is CPU-bound and fast:
- 1000 segments: < 100ms
- No external calls
- Memory: O(n) where n = number of subtitles

---

## Next Phase

After Phase 3 completion, proceed to [Phase 4: CLI & Output](./phase-4-cli-output.md) which implements the subtitle writer and CLI interface.
