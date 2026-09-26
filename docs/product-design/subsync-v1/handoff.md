# Product/design handoff: SubSync v1

**Readiness:** **ready for engineering planning.** Igor agreed at milestone 3 on 2026-09-25. Everything still open is an engineering question.

**User decision status:**
- Agreed: scope decisions D1–D4 and all of milestone 1 (R1–R25, P1–P8, N1) on 2026-09-25.
- Agreed at milestone 3 (2026-09-25): the UX flows, U1, slice order S3 before S4, and readiness for engineering planning.

**Sources:**
- [product-brief.md](product-brief.md) (agreed)
- [ux-flows.md](ux-flows.md) (agreed)
- [index.md](index.md)

## Outcome and boundaries

**Audience, problem, outcome.** Igor, a solo tech YouTuber, gets an `.srt` from one local command that YouTube Studio accepts and that follows Netflix timing and layout rules. The source can be a private draft file or a video already on YouTube, and his technical vocabulary is spelled correctly.

**Required for v1:** R1–R25 (see the [brief](product-brief.md#functional-requirements)).

**Excluded:**
- Translation. It is the next increment, and the `.<lang>.srt` naming leaves room for it.
- Uploading through the API.
- Batch mode.
- A config file or interactive mode.
- TTML.
- Children's content (17 characters per second).
- Styling: italics, number formatting, positioning.
- Speaker diarization.
- Automatic fallback to another model.
- Cookies (for age-restricted videos).

**Project constraints to preserve:**
- Python 3.13 and `uv`. Never use pip.
- argparse and `rich`.
- Use the exceptions in `errors.py`, never a bare `Exception`.
- Use `logging`, not `print`, except for CLI output.
- In dataclasses, write `field(default_factory=lambda: [])`.
- Spec-driven development: `spec/` says what and why, never how. Tasks go per phase in `spec/tasks/`.

**What already exists and should be reused:**
- `pipeline.process_video()` and `pipeline_temp_dir()`
- `audio_extractor.get_video_metadata()` and `download_audio()`
- `transcriber.transcribe_audio(Path, config, cb)`, which already accepts any audio path
- `url_handler.parse_youtube_url()`
- `progress.ProgressMapper`
- `errors.py` exception tree
- `models.py` classes: `Subtitle`, `SubtitleFile`, `ComplianceReport`, `TimingValidation`, `ProcessingConfig`, `OutputConfig`. They exist but nothing uses them yet.

## Traceability

No prototype was built (decision D4), so there is no prototype-evidence column. "Flow" points to [ux-flows.md](ux-flows.md): stage numbers, F-rows (failures), W-rows (warnings), transcripts.

| Req | Flow | Acceptance check (from the brief unless noted) | Slice | Gap |
|---|---|---|---|---|
| R1 local file input | stage 1F; F9 | `generate ep42.mov` → `ep42.en.srt`; no audio → exit 2 | S1 | — |
| R2 YouTube URL incl. `/shorts/` and `m.` | stage 1U.1; F10; Short transcript | a `/shorts/` URL succeeds; an unlisted video succeeds | S4 | `url_handler.py` rejects `/shorts/` and `m.` today |
| R3 file-then-URL resolution | stage 1; F7, F8 | `generate foo` → exit 2 with examples | S1 (file side), S4 (URL side) | — |
| R4 file route offline | stage 1F.3; walkthrough A | Wi-Fi off, model cached → success | S1 | — |
| R5 language auto-detect shown | stage 3; language line | summary and file name show `en` | S1 | U3 (when the line appears) |
| R6 `-l` override | stage 0; F2 | `-l xx` → exit 2 | S1 | — |
| R7 `-m`, turbo default, first-download notice | stages 0 and 2; F3, F19 | first run shows the notice; `-m banana` → exit 2 | S1 | — |
| R8 timing 833 ms–7 s, ≥ 83 ms gap, no overlap | stage 4; compliance block | the SRT invariant checker passes: 0 overlaps, 0 gaps under 83 ms, nothing over 7 s | S1 (extend), S2 (P1 merge fallback) | — |
| R9 ≤ 42 characters × 2 lines, split on word times | stage 4 | a 150-character sentence → 2 or more subtitles within limits | S1 | — |
| R10 line breaks | stage 4 | never "the / package" | S1 (punctuation and balance), S2 (English article/preposition rule) | Full grammar rules are later |
| R11 reading speed: extend, then warn | stage 4; compliance block | "7 above 20 CPS (4 eased by extending)"; the file is still written | S2 | — |
| R12 long words kept whole | stage 4; compliance block (`long word`) | a 49-character URL comes out unchanged, and its timestamp is listed | S1 | Revises Phase 3 (the ellipsis rule) |
| R13 repeat-line cleanup | stage 4 | 4× "Thank you." over the intro appears once at most | S2 | E5 interaction |
| R14 naming and `-o` | stage 1; F12; Short transcript | `-o out/` → `out/ep42.en.srt` | S1 (file), S4 (URL title) | — |
| R15 no overwrite without `--force`, fail fast | stages 1F.1 and 1U.3; F11 | a second run exits 5 in about 1 s | S1 | U1 agreed: fail fast on any existing `<stem>.*.srt` |
| R16 `-f srt\|vtt` | stage 0; F4 | `-f vtt` → a valid `WEBVTT` file | S1 (srt), S5 (vtt) | — |
| R17 UTF-8 without BOM, written in one step | stage 5; F23 | Studio accepts the file (manual, A3); no partial file after a failure | S1 | A3 is checked by hand once |
| R18 progress for each stage | stage lines; non-terminal output | an update at least every ~1 s; plain lines when output isn't a terminal | S1 (plain lines), S2 (spinner and download %), S5 (non-terminal, `NO_COLOR`) | U2 (transcription %) |
| R19 success summary | success transcript | the fields and layout shown in the transcript | S1 (path and count), S2 (full compliance block, first 5 flags) | — |
| R20 `-v`, no tracebacks otherwise | F21, F25 | no traceback unless `-v` is set | S1 | — |
| R21 guidance for each failure | F-table | each F-row's message and next step | S1 (F1–F9, F11, F12, F19–F25), S4 (F10, F13–F18) | E11, E12 for F18 |
| R22 exit codes incl. 130 | exit-code table | one CLI test per code | S1 (0, 1, 2, 4, 5, 130), S4 (3) | Revises Phase 4 (Ctrl+C = 1) |
| R23 clean cancellation | F24; cancel transcript | "Cancelled. Nothing written.", temp files gone, exit 130 | S1 | E8 |
| R24 preflight | stage 0; F6 | missing FFmpeg → fails in < 1 s | S1 | — |
| R25 vocabulary hint | stages 0 and 3; F5, W1 | "uv sync" is spelled correctly with the glossary | S3 | U5, E5 |
| R26 fix-up map | — | — | later | not in v1 |
| N1 speed | model line in the summary | 15-minute episode in ≤ 15 min (target ≤ 5) on Igor's Mac | spike after S1 | E1 |
| P1 short-subtitle merge fallback | stage 4 | a short subtitle that can't be extended is merged, or kept and counted | S2 | — |
| P2 blocking-error definition | headline rules; F22 | 0 subtitles → exit 4; a file with warnings → exit 0 | S1 | — |
| P3–P7 policies | F3, F17, F18, F19, F20 | as listed in the brief | S1, S4 | — |
| P8 delete `docs/ALGORITHM.md` | — | the file is gone and no doc links to it | spec-revision step | — |

## Terminal presentation (in place of a visual design)

- `rich` draws the spinners and stage lines. Progress and errors go to stderr, the summary to stdout (U6).
- The layout is designed for 80 columns. Only the previews of flagged subtitles are cut to fit the width. Paths are never cut.
- The status symbols `✓`, `!` and `✗` always come with words, so nothing depends on color. `NO_COLOR` is respected. When output isn't a terminal, each stage prints one plain line.
- The exact wording is in [ux-flows.md](ux-flows.md). Engineering may rephrase it but must keep what each message says.

## Behavior and content notes

- **States, feedback and recovery:** the [failures table](ux-flows.md#states-failures-and-recovery) (F1–F25, W1–W2) and the [exit codes](ux-flows.md#exit-codes).
- **Content assumptions:**
  - The videos are in English (A5).
  - Most have one speaker, some with a music intro (A2).
  - A typical episode is about 15 minutes (A4).
- **Checks done so far:**
  - The two walkthroughs in ux-flows (a local file, and a private video URL) were traced against the requirements.
  - Every R-ID in the brief appears in this traceability table.
  - The claims about existing code were checked by reading it on `main` @ `c659fdd`.
- **Not done yet:**
  - No real transcription run.
  - No manual upload to YouTube Studio (A3).
  - No speed measurement (N1).
  - The glossary benefit (R25) is untested.
  - These are all acceptance checks inside the slices.

## Suggested delivery slices

Each slice is a vertical cut through processor and CLI that Igor can use on its own. Write the `spec/tasks/` files one slice at a time, pointing into the revised phase plans. Don't do all of Phase 3 first and then all of Phase 4.

| Slice | What Igor can do afterwards | Requirements and acceptance checks | Dependencies / engineering questions |
|---|---|---|---|
| **S1: local file → uploadable SRT** | Run `subsync generate ep42.mov` on a real episode and upload the result | R1, R3 (file side), R4–R9, R10 (punctuation and balance), R12, R14 (file), R15 (+U1), R16 (srt), R17, R18 (plain stage lines), R19 (path and count), R20, R21/R22 (F1–F9, F11, F12, F19–F25), R23, R24, P2. **Checks:** the SRT invariant checker (R8, R9) passes on the output of an opt-in end-to-end run with the `tiny` model on a short clip Igor owns; one real episode is uploaded to Studio by hand (A3) | E2, E4, E7, E8, E9. Spec revisions first (see below) |
| **S2: readable and reviewable** | Trust the file and jump straight to the few subtitles that need a look | R10 (English article/preposition rule), R11, R13, P1, R18 (spinner, elapsed time, download %), R19 (full compliance block, first 5 flags). **Checks:** snapshot tests on Whisper output recorded from one real episode; the summary matches the success transcript | E3, E5 |
| **S3: tech vocabulary** | Get "uv", "Claude Code" and "pytest" spelled right without editing by hand | R25, W1, F5. **Check:** a glossary A/B on a sample clip | E5 |
| **S4: YouTube URL input** | Subtitle a published video or Short from its link | R2, R3 (URL side), R14 (title-based name), R21/R22 (F10, F13–F18), download %, P4, P7. **Checks:** `/shorts/`, `m.` and unlisted URLs succeed; the private-video hint is shown; exit 3 | E6, E11, E12 |
| **S5: VTT and finish** | Use VTT when needed, script SubSync, and install it once to use from anywhere | R16 (vtt), F4, R18 (non-terminal output, `NO_COLOR`), README usage and FFmpeg prerequisite, `--help`, CHANGELOG, install instructions. **Checks:** a VTT file validates; piped output is plain | E12 |
| **Spike (runs alongside, after S1)** | Know whether transcription is fast enough | N1, measured on a 15-minute episode | E1. May swap the transcription engine behind `TranscriptionResult` |

**Order:** S1 → S2 → S3 → S4 → S5. The spike runs alongside once S1 exists. S3 and S4 are technically independent; Igor chose S3 first at milestone 3, because the vocabulary hint helps every video on the main local-file route.

## Changes needed in existing specs (for the engineering planning step)

**`spec/plan/phase-3-netflix-compliance.md`**
- **Reuse as they are:**
  - the four components
  - "Transform, Don't Mutate"
  - "Line Breaking Strategy" (rule-based)
  - Processing Flow: split anything over 7 s or 84 characters, then timing, then lines, then CPS
  - the edge-case rows for empty segments, overlaps, missing word timestamps, all-caps text and Unicode
- **Revise:**
  - "Single word > 42 chars → Truncate with ellipsis", in both Error Handling and Edge Cases, becomes R12: keep the word whole and warn.
  - "Consider merging" becomes P1.
  - "CPS Handling" becomes extend-into-free-time, then warn (R11). This is a timing-only fix: the text is never changed, which is consistent with the plan's reason for not auto-fixing.
  - Add a cleanup step (R13) and the P2 definition of errors vs warnings and `is_compliant`.
  - Line-break word lists apply to English only; other languages are later.
  - Drop the children's profile from scope. The `ProcessingConfig` field can stay.

**`spec/plan/phase-4-cli-output.md`**
- **Reuse:**
  - the Subtitle Writer format sections
  - Filename Sanitization
  - argparse + rich
  - the themes in Error Messages
  - most of the Exit Codes table
- **Revise:**
  - The input `<youtube_url>` becomes `<input>`.
  - Add file-based naming, `--force`, `--prompt`/`--glossary`, and the `-o` directory-vs-file rule.
  - Remove `--children`.
  - Ctrl+C exits 130, not 1.
  - "Show progress with ETA" becomes spinner + elapsed time (U2).
  - "Check disk space" becomes the one-step write.
  - The success and error output mocks are replaced by those in ux-flows.
  - Add the FFmpeg preflight and the private-video hint.
  - "Manual testing with 3+ videos" becomes named cases: a talking-head episode, a screencast full of jargon, and a Short.

**`spec/plan/phase-2-core-pipeline.md`:** record that retry, model fallback, model cache and version pinning are settled by P4–P7.

**Context and docs**
- `spec/context/youtube-compatibility.md`: `/shorts/` and `m.` URL patterns, no BOM, and the route from a private video to a local file.
- `spec/context/netflix-compliance.md`: which rules v1 covers, and the long-word exception.
- `spec/context/dependencies.md`: FFmpeg used directly, the yt-dlp update policy, and a possible engine change.
- `spec/context/data-models.md`: the source/metadata model, if E4 changes it.
- `docs/SUBTITLE_GENERATION_ALGORITHM.md`: local-file input, and `-m` instead of `-q`.
- Delete `docs/ALGORITHM.md` (P8).
- `CLAUDE.md`: phase status, pipeline modules, and a pointer to this folder.
- `README.md`: usage, prerequisites, directory structure.
- `.github/copilot-instructions.md`: directory map.

## Remaining decisions

| Decision or question | Type | Consequence | Next action |
|---|---|---|---|
| ~~U1~~ **Decided at milestone 3:** before any work, refuse if any `<stem>.*.srt` already exists in the output folder. With `-l`, check the exact name. Check the exact name again at write time | Product: decided | A re-run fails in about a second | Part of S1 |
| E1: transcription engine on Apple Silicon: openai-whisper on CPU vs mlx-whisper vs faster-whisper vs whisper.cpp | Engineering | Whether N1 is met, the device label (U4), and whether word timestamps and the prompt option still work | Spike after S1 |
| E2: getting audio from a local file: call FFmpeg directly or use Whisper's built-in decoding; ffprobe for duration and no-audio detection (F9); default track for multi-track files | Engineering | R1, F9 | S1 planning |
| E3: a transcription progress signal | Engineering | U2 (percentage/ETA) and U3 (when the language line appears) | S2 planning |
| E4: one pipeline entry point for both files and URLs; local-file metadata vs the YouTube-only fields in `VideoMetadata` and `SubtitleFile` | Engineering | R1, R14, data-models spec | S1 planning |
| E5: Whisper decoding defaults (`condition_on_previous_text`, `hallucination_silence_threshold`, voice-activity detection); vocabulary-hint length limit | Engineering | R13, R25, W1 | S2/S3 planning |
| E6: yt-dlp retry and timeout options | Engineering | P4, F17 | S4 planning |
| E7: tests: recorded Whisper JSON fixtures, SRT invariant checker, opt-in end-to-end with a clip Igor owns, CI (yes or no) and caching model weights | Engineering | Confidence in regressions for every slice | S1 planning |
| E8: Ctrl+C during native or torch calls: prompt interruption, temp-file cleanup, the one-step write | Engineering | R23 | S1 planning |
| E9: SRT details: line endings (CRLF or LF), trailing newline, how characters per second are counted (spaces and punctuation included; line breaks excluded?) | Engineering | R11, R17 | S1 planning |
| E10: line breaking for languages other than English | Engineering (deferred) | None for v1 (A5) | After v1 |
| E11: telling reliably when a failure is caused by an outdated yt-dlp | Engineering | F18 | S4 planning |
| E12: how Igor installs and runs SubSync from anywhere (`uv tool install` vs `uv run` in the repo) | Engineering | The upgrade command in F18, README install section | S4/S5 planning |

## Next engineering step

Milestone 3 is agreed, so engineering planning can start:
1. Revise the specs listed above using the project's spec-driven-development workflow.
2. Write `spec/tasks/` for **S1** only.
3. Implement S1.

The `product-engineering:planning-implementation` skill (or `spec-driven-development`) can run this. This handoff does not authorize implementation or release.
