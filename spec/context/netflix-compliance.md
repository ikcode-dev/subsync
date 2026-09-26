# Netflix Timed Text Style Guide - Compliance Context

## Overview

This document captures the Netflix Timed Text Style Guide requirements that SubSync must adhere to for professional-quality subtitles.

**Source**: [Netflix Partner Help - Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617)

**Revised 2026-09-25 for SubSync v1**: adds [v1 coverage](#v1-coverage), the long-word exception, the CPS counting rule and the "extend, then flag" reading-speed policy agreed in the [product brief](../../docs/product-design/subsync-v1/product-brief.md) (R8–R12, P1, P2).

---

## v1 Coverage

SubSync v1 follows a subset of the style guide: the rules that audio can supply and that suit tech content. Videos are in English (A5).

| Covered in v1 | Requirement |
|---|---|
| Timing: 833 ms–7 s per subtitle, ≥ 83 ms gap, no overlap, in order | R8, P1 |
| Layout: at most 2 lines of at most 42 characters | R9 |
| Basic English line breaks: after punctuation, balanced lines, never ending line 1 on an article or preposition | R10 (basic) |
| Reading speed: 20 CPS (adult) | R11 |
| A word longer than 42 characters kept whole (exception below) | R12 |

| Excluded from v1 | Why |
|---|---|
| Italics (off-screen, narration, lyrics, emphasis) | Audio can't tell when they apply |
| Positioning (top placement over on-screen text) | Audio can't tell where graphics are |
| Number style (spelling out one through ten) | Harms tech content: "Python 3" must not become "Python three" |
| Children's reading speed (17 CPS) | The channel isn't children's content |
| Full grammar-aware breaks (names, adjective–noun pairs, auxiliary verbs) and other languages | Later increments (R10 later rules, E10) |

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

### Long-Word Exception (SubSync v1)

A single word longer than 42 characters — a URL, package name or CLI flag such as `github.com/ikcode-dev/subsync/blob/main/README.md` (49 characters) — is **never shortened**. It goes on its own line unchanged and is reported as a warning with its timestamp, so it can be checked in the Studio editor (R12). This supersedes the earlier plan to truncate such words with an ellipsis: tech tokens must stay exact and copy-pasteable.

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

**Counting rule (SubSync v1, E9)**: count every displayed character, including spaces and punctuation, and exclude line breaks. For a two-line subtitle this is the sum of both line lengths.

When CPS exceeds limits:
1. **Option A**: Extend subtitle duration (if no timing conflict)
2. **Option B**: Flag for manual review
3. **Option C**: Split into multiple subtitle events

**SubSync v1 policy: extend, then flag** (R11). Apply Option A first — extend the end into the free time that follows, staying within 7 s and keeping the 83 ms gap to the next subtitle — then Option B for whatever is still too fast. Subtitles are never split, condensed or rewritten for reading speed, and a high CPS never stops the run. The summary reports both counts, e.g. "7 above 20 CPS (4 eased by extending)".

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
1. All timing rules are enforced during subtitle processing; a short subtitle that can't be extended is merged with a neighbor only if the result fits 2 × 42 characters and 7 s, otherwise kept and counted (P1)
2. CPS is eased by extending into free time, then flagged for review; it is a warning, never a blocker (R11)
3. Line breaking is rule-based; the word lists are English-only in v1
4. Text is never shortened or rewritten: long words stay whole and are flagged (R12)
5. Only structural breakage (overlap, out of order, end at or before start, more than 2 lines) counts as a compliance error; everything else is a warning (P2)
6. Typography is handled at output format level (SRT/VTT): UTF-8 without BOM, no styling tags
7. The rule values live in `ProcessingConfig` (see [data-models.md](data-models.md)); the phase plan is [phase-3-netflix-compliance.md](../plan/phase-3-netflix-compliance.md)
