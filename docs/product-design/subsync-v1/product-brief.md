# Product brief: SubSync v1

Status: **agreed** (milestone 1, 2026-09-25). See the [index](index.md) for the decision log.

## Audience, problem, outcome

**Audience.** Igor, a solo tech YouTuber who runs his own channels. He works on an Apple Silicon Mac, is fluent with the terminal, and has the rendered video file on disk before he uploads it.

**Problem.** Good subtitles make a video more accessible and help it get found, but they cost time:
- YouTube's automatic captions get technical vocabulary wrong ("uv", "pytest", "Claude Code").
- Automatic captions only appear after the video is published.
- Correcting them by hand in YouTube Studio is slow.
- Cloud transcription services send unpublished material to third parties.

**Intended outcome.** One local command turns a video into a subtitle file that YouTube Studio accepts and that follows Netflix timing and layout rules. This works both for a private draft before upload and for a video that is already on YouTube. Igor then uploads the file by hand.

## Scope

**Required for this outcome**
- Input from a local video or audio file, or from a YouTube URL (D1).
- Subtitles in the spoken language only (D2).
- Netflix rules for timing, line length, line count and reading speed.
- Output as `.srt`, with `.vtt` optional (D3).
- Clear feedback while it runs, a summary at the end, and errors that say what to do next.

**Useful later**
- Translated subtitle tracks (the next increment after v1).
- A post-transcription fix-up map for recurring mis-hearings (R26).
- A `--strict` mode that fails on compliance warnings.
- Writing SRT and VTT in one run.
- Saving the full compliance report to a file.
- Full grammar-aware line breaking (R10, later rules).
- `/live/` URLs for streams that have ended.

**Explicitly excluded from v1**
- Uploading to YouTube through its API (D3).
- Batch or playlist processing.
- A config file.
- Interactive mode.
- TTML, SBV or other formats.
- The children's-content profile (`--children`, 17 CPS).
- Styling: italics, number style, on-screen positioning, speaker labels.
- Speaker diarization, chapters.
- Automatic fallback to a smaller model.
- Choosing an audio track in multi-track recordings.
- Cookies for age-restricted videos.
- `music.youtube.com` URLs.

## Context and evidence

**User decisions (2026-09-25)**

| ID | Decision |
|---|---|
| D1 | Input is a local file **and** a YouTube URL |
| D2 | v1 subtitles are in the spoken language only; translation comes next |
| D3 | Write a subtitle file and upload it by hand in YouTube Studio; no API upload |
| D4 | Discovery covers the brief, the command-line flows and the handoff; no visual directions or HTML prototypes |

**What I inspected (2026-09-25, `main` @ `c659fdd`)**
- **Built and merged:**
  - Phase 1 (errors, data models, URL parser).
  - Phase 2 (yt-dlp metadata and audio download, then Whisper transcription with word timestamps, all run by `pipeline.process_video()`).
  - 87 unit tests, all using stand-ins for yt-dlp and Whisper.
- **Missing:**
  - Phase 3, the compliance processor (`spec/plan/phase-3-netflix-compliance.md`).
  - Phase 4, the SRT/VTT writer and the CLI (`spec/plan/phase-4-cli-output.md`).
  - `src/subsync/cli.py` only prints "Hello World", so today the product cannot produce a subtitle file.
- **Input limits:** `url_handler.py` accepts only `youtube.com`, `www.youtube.com` and `youtu.be` links in watch, embed and `/v/` form. `audio_extractor.py` only builds YouTube URLs.
- **Rule defaults already in code:** `ProcessingConfig` in `models.py` holds 42 characters per line, 2 lines, 833–7000 ms, 83 ms gap and 20 CPS. `OutputConfig` defaults to SRT without a BOM.
- **Transcriber limits:** `transcriber.py` chooses CUDA or CPU, so an Apple Silicon Mac transcribes on the CPU. It reports progress only at 0% and 100%.
- **Whisper capabilities:** the installed Whisper (20250625) supports `initial_prompt`, `carry_initial_prompt` and `hallucination_silence_threshold`.
- **Existing rules and conflicts:**
  - Netflix rules come from `spec/context/netflix-compliance.md`; YouTube format rules from `spec/context/youtube-compatibility.md`.
  - `docs/ALGORITHM.md` contradicts the specs: default model, how short segments are handled, CLI framework, and the extra features it lists.

**Stack and constraints**
- Python 3.13 managed with uv, openai-whisper, yt-dlp, and FFmpeg as a system dependency.
- `rich` is declared for terminal output but not yet used.
- The CLI uses argparse (from the Phase 4 plan).
- Transcription runs locally.
- **Open engineering question:** which Whisper engine to use on Apple Silicon (E1 in the [handoff](handoff.md)).

**Assumptions**

| ID | Assumption | How to check |
|---|---|---|
| A1 | The rendered file exists locally before upload, so the local-file route covers private drafts | Igor confirms his workflow |
| A2 | Most videos have one speaker: screencasts and talking-head videos, with some music intros | Run slice S1 on real episodes |
| A3 | YouTube Studio accepts UTF-8 SRT without a BOM, uploaded with the "With timing" option | Upload one generated file by hand |
| A4 | A 15-minute episode is typical | Igor confirms |
| A5 | ~~Spoken language unknown~~ **Resolved at milestone 1: English.** Videos are in English | — |

## Functional requirements

Priority: **v1** = required for this outcome · **later** = useful later. All items were agreed at milestone 1.
Sample names such as `ep42.mov` are invented.

### Input

| ID | User-visible behavior | Priority | Acceptance examples |
|---|---|---|---|
| R1 | `subsync generate <path>` accepts a local video or audio file (mp4, mov, mkv, webm, m4a, mp3, wav). | v1 | `subsync generate ~/Videos/ep42.mov` writes `~/Videos/ep42.en.srt`. A file with no audio track stops with "No audio track found in ep42.mov" and exit code 2. |
| R2 | It accepts YouTube URLs: watch, `youtu.be`, embed and `/v/` links (already supported), plus `/shorts/<id>` and `m.youtube.com` links. | v1 | `subsync generate https://youtube.com/shorts/<id>` succeeds. The URL of an unlisted video succeeds. |
| R3 | If the input is an existing file it is treated as a file. Otherwise, if it is a YouTube URL it is treated as a URL. Anything else stops with an error that shows both accepted forms. | v1 | `subsync generate foo` with no file named `foo` prints "Not a file or a supported YouTube URL" with examples, and exits 2. |
| R4 | Once the model has been downloaded, processing a local file makes no network calls. The file never leaves the machine. | v1 | With Wi-Fi off and the model cached, `subsync generate draft.mp4` succeeds. |

### Language and model

| ID | User-visible behavior | Priority | Acceptance examples |
|---|---|---|---|
| R5 | The spoken language is detected automatically. The detected language is shown during the run and in the summary, and its ISO code goes into the file name. | v1 | The summary shows "Language: English (auto-detected)" and the file is named `*.en.srt`. |
| R6 | `-l/--language <iso>` forces the language. An invalid code is rejected before any work starts. | v1 | `-l xx` exits 2 with a hint listing example codes. `-l en` on a video with a music intro skips detection. |
| R7 | `-m/--model <name>` selects a standard Whisper model name. The default is `turbo`. The first run shows a notice that the model is being downloaded, so the tool does not look frozen. | v1 | On first use it prints "Downloading model 'turbo' (one-time)…". `-m banana` exits 2 and lists the valid names. |

### Subtitle quality (a subset of the Netflix rules)

| ID | User-visible behavior | Priority | Acceptance examples |
|---|---|---|---|
| R8 | Every subtitle lasts between 833 ms and 7 s. Consecutive subtitles are at least 83 ms apart, never overlap, and stay in order. | v1 | Parsing the generated SRT finds 0 overlaps, 0 gaps under 83 ms, and no subtitle longer than 7 s. Short subtitles that cannot be extended are counted in the summary (P1). |
| R9 | A subtitle has at most 2 lines of at most 42 characters. Longer speech is split into several subtitles at word timestamps. | v1 | A 150-character sentence becomes two or more subtitles, each within 2 × 42 characters, with times taken from the words. |
| R10 | Line breaks are basic and readable: prefer breaking after punctuation, keep the two lines balanced, and never end the first line on an English article or preposition. The videos are in English (A5). The remaining Netflix grammar rules (names, adjective–noun pairs, auxiliary verbs) and rules for other languages come **later**. | v1 (basic) | "We install the package / with uv sync" is acceptable. "We install the / package with uv sync" never appears. |
| R11 | Reading speed: when a subtitle exceeds 20 characters per second (CPS), its end is first extended into the free time that follows (still within 7 s and keeping the 83 ms gap). Only if it is still too fast is it flagged. The text is never changed and the run is never stopped for CPS. | v1 | The summary reports "7 above 20 CPS (4 eased by extending)". A file is still written. |
| R12 | A word longer than 42 characters, such as a URL, package name or CLI flag, is **never shortened**. It goes on its own line and is flagged as a warning. *This replaces the Phase 3 rule that truncated such words with an ellipsis.* | v1 | `github.com/ikcode-dev/subsync/blob/main/README.md` (49 characters) appears unchanged in the output, and the summary lists its timestamp. |
| R13 | Transcript cleanup: drop empty segments and collapse back-to-back identical lines. This targets Whisper's repeat loops over music or silence. | v1 | A music intro that Whisper transcribes as "Thank you." four times appears once, or not at all. |

### Output

| ID | User-visible behavior | Priority | Acceptance examples |
|---|---|---|---|
| R14 | Default file name: `<input folder>/<stem>.<lang>.srt` for a file, and `./<sanitized title>.<lang>.srt` for a URL. `-o <dir>` writes the default name into that folder. `-o <file>` writes exactly that path. | v1 | `subsync generate ep42.mov -o out/` writes `out/ep42.en.srt`. A title with `/:?` produces a valid file name. |
| R15 | An existing output file is never overwritten without `--force`, which protects hand-corrected files. This is checked **before** any download or transcription. With an auto-detected language, any existing `<stem>.*.srt` in the output folder counts (U1, agreed at milestone 3). | v1 | A second run exits 5 within about 1 s with "ep42.en.srt already exists. Use --force or -o." |
| R16 | `-f/--format srt\|vtt` selects the format. The default is `srt`. | v1 | `-f vtt` writes a file that starts with `WEBVTT` and uses `HH:MM:SS.mmm` timestamps. |
| R17 | Files are UTF-8 without a BOM, valid SRT/VTT, and written in one step, so a failure or cancellation never leaves a partial file. | v1 | YouTube Studio accepts a generated file uploaded with "With timing" (checked by hand once, A3). After a failed or cancelled run, no output file exists. |

### Feedback, errors, exit behavior

| ID | User-visible behavior | Priority | Acceptance examples |
|---|---|---|---|
| R18 | Progress is shown for each stage: reading or fetching, extracting or downloading (percentage when known), loading the model, transcribing, formatting, writing. At minimum, transcription shows a spinner with elapsed time, the audio length and the device. | v1 | The display updates at least every ~1 s at every stage. When output is not a terminal, it prints one plain line per stage. |
| R19 | The success summary shows: the absolute path of the output file, the source and its duration, the language (detected or forced), the model and device, the time taken, the number of subtitles, a compliance section, the **first 5 flagged subtitles with timestamps** (so Igor can jump to them in the Studio editor), and a one-line upload hint. | v1 | See the success transcript in [ux-flows](ux-flows.md). `-v` lists every flagged subtitle. |
| R20 | `-v/--verbose` adds debug logging, and a traceback when an error occurs. | v1 | Without `-v`, no Python traceback ever appears. |
| R21 | Each failure class has a message saying what went wrong and what to do next. A private video suggests exporting the file and using the local-file route. | v1 | See the failure table in [ux-flows](ux-flows.md). |
| R22 | Exit codes: 0 means a file was written, even with warnings. 1 = unexpected or environment error. 2 = bad input or usage. 3 = source unavailable. 4 = transcription failed, or no speech found. 5 = output problem. **130 = cancelled with Ctrl+C** (agreed at milestone 1; this changes the Phase 4 plan, which uses 1). | v1 | Each code is covered by a CLI test. |
| R23 | Ctrl+C at any stage stops promptly, removes temporary files and writes nothing. | v1 | Prints "Cancelled. Nothing written." and exits 130. |
| R24 | Before any heavy work: check that FFmpeg is on the PATH (with an install hint), that the output location is writable and not already taken (R15), and that the language, model and format values are valid. | v1 | A missing FFmpeg fails in under 1 s with a `brew install ffmpeg` hint, not after a download. |

### Tech-YouTuber extras

| ID | User-visible behavior | Priority | Acceptance examples |
|---|---|---|---|
| R25 | Vocabulary hint: `--prompt "uv, Claude Code, pytest, Ruff"` or `--glossary terms.txt` makes Whisper spell those terms correctly throughout the video. | v1 (slice S3) | On a sample clip, "you v sync" becomes "uv sync" with the glossary and stays wrong without it. |
| R26 | Fix-up map: a per-channel file of known mis-hearings is applied after transcription ("cloud code" → "Claude Code"). | later | A deterministic backup when R25 is not enough. |

## Rules for open spec questions

These questions are open or contradictory in the Phase 3/4 plans and the algorithm docs. Igor agreed to all of these rules at milestone 1. P8 decides to delete `docs/ALGORITHM.md`.

| ID | Question | Proposed rule | Why |
|---|---|---|---|
| P1 | Merge consecutive short segments? | Merge only as a fallback: when a subtitle under 833 ms cannot be extended because the next one is too close, merge it with a neighbor if the result fits 2 × 42 characters and 7 s. Otherwise keep it and count it in the summary. | Stops one-word flashes without inventing timing. |
| P2 | What counts as a blocking compliance error? | `errors` covers only structural breakage: 0 subtitles (nothing written, exit 4), or an overlap, out-of-order subtitle, end at or before start, or more than 2 lines. The processor should make these impossible, so hitting one is a bug. Everything else is a warning. If a file was written the exit code is 0, and the summary shows "✗ Not compliant" when errors exist. `--strict` comes later. | The exit code should answer one question: did I get a file I can upload? |
| P3 | Model flag: `-q/--quality` (algorithm doc) or `-m/--model` (Phase 4 plan)? | `-m/--model` with standard Whisper names, which stay the same if the transcription engine changes. | The Phase 4 plan and `TranscriptionConfig.model_name` already use it, and the names are well known. |
| P4 | Retries? | Rely on yt-dlp's built-in retries and timeouts. A network failure exits 3 with "check your connection and re-run". | Re-running is cheap for one person at a terminal. |
| P5 | Automatic model fallback? | None. On a memory or load failure, exit 4 and suggest `-m small`. | A quality drop the user doesn't know about is worse than a clear message. |
| P6 | Model cache? | Whisper's own download cache (`~/.cache/whisper`) is enough. Only the first-download notice is needed (R7). | Nothing to build. |
| P7 | Pin the yt-dlp version? | No exact pin. Keep a minimum version plus `uv.lock`, and when a download fails because yt-dlp is out of date, show the upgrade command. | YouTube changes break old yt-dlp versions within weeks. |
| P8 | What to do with `docs/ALGORITHM.md`, the older draft that contradicts the specs? | Delete it (git history keeps it). The alternative is a "superseded by `SUBTITLE_GENERATION_ALGORITHM.md`" banner. | Agents may otherwise follow its interactive mode, YAML config, TTML and `--standards` ideas. |

## Other product constraints

- **Privacy:** local files and their transcripts stay on the machine (R4). Network is used only for URL input and the first model download.
- **Performance** (N1, agreed at milestone 1): a 15-minute episode becomes a subtitle file in ≤ 15 minutes on Igor's Apple Silicon Mac with the default model, with a target of ≤ 5 minutes. Measure it on one real episode after S1. Which engine can achieve this is engineering question E1.
- **Platform:** macOS on Apple Silicon is the main platform. Linux should work but is not a v1 acceptance target.
- **Content:** Netflix style rules that audio cannot supply (italics, positioning) or that would harm tech content (writing numbers as words turns "Python 3" into "Python three") are excluded.
- **Accessibility of the CLI:** the CLI must stay readable without color: the ✓, ! and ✗ symbols are paired with words. It must also work when output is not a terminal, with plain lines (R18).

## Milestone 1 outcome (2026-09-25)

| # | Question | Igor's answer |
|---|---|---|
| Q1 | Accept the R1–R24 v1 set? | Accepted as proposed |
| Q2 | Include R25 (vocabulary hint) in v1? | Yes, as slice S3 |
| Q3 | Include R13 (repeat-line cleanup) in v1? | Yes, in slice S2 |
| Q4 | Exit code 130 for Ctrl+C? | Yes |
| Q5 | P2 blocking-error definition? | Accepted |
| Q6 | `docs/ALGORITHM.md` (P8)? | Delete it |
| Q7 | Spoken language(s)? | English |
| Q8 | P1, P3–P7 and the N1 speed target? | Accepted |

## Open questions

None block design. The remaining questions are for engineering and are listed in the [handoff](handoff.md#remaining-decisions).
