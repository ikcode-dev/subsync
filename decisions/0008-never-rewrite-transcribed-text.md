# 0008: Never rewrite transcribed text; fix timing and warn

- Status: accepted
- Date: 2026-09-25

## Context

Netflix rules limit lines to 42 characters and reading speed to 20 characters per second. SubSync's videos are tech content full of long tokens (URLs, package names, CLI flags) that must stay copy-pasteable, and fast speech. The earlier phase 3 plan truncated any word over 42 characters with an ellipsis, and only warned on reading-speed violations. The brief also excludes Netflix style rules that would harm tech content, such as writing numbers as words ("Python 3" → "Python three").

## Options

1. **Truncate or shorten text to comply.** The earlier rule: cut long words with an ellipsis. Produces compliant but wrong subtitles.
2. **Warn only.** Leave text and timing as transcribed and flag every violation.
3. **Fix timing, never text, then warn.** Adjust timing within the rules where there is room; flag what remains.

## Decision

Option 3 ([phase 3 plan, Text Is Never Changed and Reading Speed](../spec/plan/phase-3-netflix-compliance.md#text-is-never-changed); R11, R12).

- The processor never shortens, truncates or rewrites transcribed words.
- A word longer than 42 characters goes on its own line unchanged and is flagged as a warning (R12).
- A subtitle over 20 CPS has its end extended into the following free time, within 7 s and keeping the 83 ms gap; only if it is still too fast is it flagged (R11).
- Processing never stops for these findings.

## Consequences

- Subtitles always match what was said; a flagged, correct subtitle beats a compliant, wrong one.
- Some output is not fully Netflix-compliant; the summary lists flagged subtitles with timestamps for review in the Studio editor.
- Text fixes, if ever needed, come from explicit user input (vocabulary hint R25, fix-up map R26), not from the compliance processor.
