# Netflix Timed Text Style Guide - Compliance Context

## Overview

This document captures the Netflix Timed Text Style Guide requirements that SubSync must adhere to for professional-quality subtitles.

**Source**: [Netflix Partner Help - Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617)

---

## Timing Requirements

| Rule | Value | Notes |
|------|-------|-------|
| **Minimum Duration** | 833ms (5/6 sec) | 20 frames at 24fps |
| **Maximum Duration** | 7000ms (7 sec) | Per subtitle event |
| **Minimum Gap** | 83ms (2 frames) | Between consecutive subtitles |
| **Frame Rate Reference** | 24fps | Standard for calculations |

### Timing Rationale

- **Minimum 833ms**: Ensures subtitles are readable; too short causes flashing
- **Maximum 7s**: Prevents cognitive overload; long text should be split
- **83ms gap**: Provides visual separation between subtitle events

---

## Character & Line Limits

| Rule | Value |
|------|-------|
| **Max Characters/Line** | 42 |
| **Max Lines/Subtitle** | 2 |
| **Max Total Characters** | 84 (42 × 2) |

### Line Break Rules (Priority Order)

**PREFER breaking:**
- After punctuation marks (. , ! ? :)
- Before conjunctions (and, but, or)
- Before prepositions (in, on, at, to)

**AVOID breaking:**
- Between article and noun ("the | dog" ❌)
- Between adjective and noun ("big | house" ❌)
- Between first and last name ("John | Smith" ❌)
- Between verb and subject pronoun
- Between verb and auxiliary

---

## Reading Speed

| Content Type | Max CPS (Characters Per Second) |
|--------------|----------------------------------|
| **Adult Programs** | 20 |
| **Children's Programs** | 17 |

### CPS Calculation

```
CPS = total_characters / duration_seconds
```

When CPS exceeds limits:
1. **Option A**: Extend subtitle duration (if no timing conflict)
2. **Option B**: Flag for manual review
3. **Option C**: Split into multiple subtitle events

---

## Typography & Positioning

| Element | Specification |
|---------|---------------|
| **Font Family** | Arial (proportionalSansSerif) |
| **Font Color** | White |
| **Encoding** | UTF-8 |
| **Justification** | Center |
| **Position** | Bottom of screen (default) |

### Special Positioning

- Top positioning when avoiding on-screen text/graphics
- Speaker identification for off-screen dialogue

---

## Style Conventions

### Italics Usage
- Off-screen dialogue
- Narration
- Song lyrics
- Foreign words
- Internal thoughts
- Emphasis

### Numbers
- Spell out one through ten
- Use numerals for 11 and above
- Always use numerals for time, dates, percentages

### Punctuation
- Use ellipsis (...) for trailing off
- Use em-dash (—) for interruptions
- No double punctuation

---

## References

- [General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617)
- [Timing Guidelines](https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394)
- [English (USA) Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977)
- [Language-Specific Guides](https://partnerhelp.netflixstudios.com/hc/en-us/sections/22463232153235)

---

## Implementation Notes

For SubSync implementation:
1. All timing rules are enforced during subtitle processing
2. CPS validation is a warning, not a blocker (flagged for review)
3. Line breaking is algorithmic with configurable strictness
4. Typography is handled at output format level (SRT/VTT)
