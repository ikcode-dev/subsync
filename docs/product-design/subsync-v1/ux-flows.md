# UX: SubSync v1, the `subsync generate` command

Status: **agreed** (milestone 3, 2026-09-25)
Related requirements: [product-brief.md](product-brief.md) R1–R25, P1–P8

This is a command-line product: terminal sections take the place of screens. The sample names used below (`ep42.mov`, `terms.txt`, the timings and counts) are invented.

## Primary journey

- **Actor and situation:** Igor has a finished render on disk, either a private draft or a video he is about to publish. Or the video is already on YouTube and he has its link.
- **Entry point:** his terminal. He has the file path or the URL, and optionally a glossary of his channel's jargon.
- **Desired result:** an `.srt` file next to the video (or where `-o` says), plus a short summary telling him where it is, whether anything needs a look, and how to upload it.
- **Exit and cancellation:** the command never asks questions, so it is safe to script. Ctrl+C stops at any stage and writes nothing (R23). Exit codes are in [Exit codes](#exit-codes).

### Flow

```
subsync generate <INPUT> [-l LANG] [-m MODEL] [-f srt|vtt] [-o PATH] [--force]
                         [--prompt TEXT] [--glossary FILE] [-v]

0  Preflight, silent on success, < 1 s                                         R6 R7 R16 R24
   argument values valid? · FFmpeg on PATH? · glossary file readable?
1  Resolve INPUT                                                               R3
   ├─ existing file ─────────────────────┐        ├─ YouTube URL ──────────────────────────┐
   │ 1F.1 output path free/writable R15  │        │ 1U.1 parse (watch, youtu.be, embed,   │ R2
   │ 1F.2 read media info: duration,     │ R1     │      /v/, /shorts/, m.youtube.com)    │
   │      has audio?                     │        │ 1U.2 fetch video info (needs network) │
   │ 1F.3 extract audio (offline)        │ R4     │ 1U.3 output path free/writable        │ R14 R15
   └─────────────────────────────────────┘        │      (the name needs the title)       │
                                                  │ 1U.4 download audio  (percent)        │ R18
                                                  └───────────────────────────────────────┘
   └─ neither → error, exit 2
2  Load model: cached → "Loaded model"; first use → one-time download notice   R7
3  Transcribe: spinner + elapsed + audio length; language shown once known     R5 R18 R25
4  Format: clean up, split and lay out, timing, line breaks, reading speed     R8–R13, P1
5  Write in one step (UTF-8, no BOM)                                           R16 R17
6  Summary → exit 0                                                            R19 R22
```

The output path is checked **before** any heavy work: at 1F.1 for files, and at 1U.3 for URLs, once the title is known and before the download. A second run on the same video fails in about a second instead of after a full transcription (R15).

## Command surface

| Argument / option | Meaning | Default | Validation (fails at stage 0 or 1, exit 2 unless noted) | Req |
|---|---|---|---|---|
| `INPUT` | Path to a video or audio file, or a YouTube video URL | required | An existing file is treated as a file. Otherwise it must be a supported URL. Otherwise error | R1–R3 |
| `-l, --language CODE` | Spoken language, which skips detection | auto-detect | Must be a language code Whisper knows (e.g. `en`) | R5, R6 |
| `-m, --model NAME` | Whisper model | `turbo` | Must be one of Whisper's model names | R7, P3 |
| `-f, --format srt\|vtt` | Output format | `srt`, or inferred from the extension given to `-o` | If `-o` ends in `.srt`/`.vtt` and `-f` names the other format → error | R16 |
| `-o, --output PATH` | An existing directory, or a path ending in `/`, means "default name inside it". Anything else is used as the exact file path | the input's folder (file) or the current folder (URL) | The parent directory must exist. Folders are never created. Otherwise exit 5 | R14 |
| `--force` | Replace an existing output file | off | — | R15 |
| `--prompt TEXT` | Words to spell correctly, e.g. `"uv, Claude Code, pytest"` | none | — | R25 |
| `--glossary FILE` | Same, read from a file: one term per line, blank lines and `#` comments ignored | none | The file must exist and be readable. Can be combined with `--prompt`: the prompt text comes first, then the glossary terms | R25 |
| `-v, --verbose` | Debug logs, and a traceback if an error occurs | off | — | R20 |
| `--version`, `-h/--help` | Standard | — | — | — |

Running bare `subsync` or `subsync generate` without INPUT prints usage and exits 2.

## Terminal sections

| Section | Responsibility | Content and its source | Stream |
|---|---|---|---|
| Source line | Confirm what is being processed | File: name, duration, "local file". URL: title, duration, channel (from the video info) | stderr |
| Stage lines | Show the run is alive and where it is | One line per stage. It turns into `✓ <stage>  <time>` when the stage is done | stderr |
| Language line | Surface detection early so a wrong guess can be stopped | `Language: English (auto-detected)` or `(set with -l)` | stderr |
| Warnings | Non-fatal issues that affect the result | e.g. vocabulary hint truncated | stderr |
| Summary | Answer: where is the file, is it good, what next | R19 fields, compliance block, up to 5 flagged subtitles, upload hint | stdout |
| Error block | Answer: what failed and what to do next | `✗` headline, one or two lines of what to do next, with the exact command when there is one | stderr |

Progress and errors go to stderr and the summary goes to stdout. Redirecting stdout therefore captures the summary without the progress noise. This was a routine choice; see [Unresolved](#unresolved-questions-and-assumptions).

## Transcripts

### Success: local file, first run, with glossary (terminal)

```
$ subsync generate ~/Videos/ep42.mov --glossary ~/yt/terms.txt
ep42.mov · 14:52 · local file
✓ Extracted audio                                        4s
⠹ Downloading model 'turbo' (one-time)…                 62%
✓ Loaded model turbo on CPU                             11s
  Vocabulary hint: 14 terms from terms.txt
⠼ Transcribing 14:52 of audio… 03:41 elapsed
  Language: English (auto-detected)
✓ Transcribed                                       6m 02s
✓ Formatted 312 segments → 356 subtitles
✓ Wrote subtitles

✓ Subtitles written, 8 to review
  File:      /Users/igor/Videos/ep42.en.srt
  Source:    ep42.mov · 14:52
  Language:  English (auto-detected)
  Model:     turbo on CPU · 6m 21s total
  Subtitles: 356

  Compliance (Netflix timing and layout)
  ✓ Duration 0.83–7 s, gaps ≥ 83 ms     41 adjusted automatically, 0 left short
  ! Line length ≤ 42 chars, ≤ 2 lines   1 over: long word kept whole
  ! Reading speed ≤ 20 CPS              7 above (4 eased by extending)
      00:01:23  So we run uv sync and then pytest -x to…   24.1 CPS
      00:04:10  and the config lives in pyproject.toml…    22.7 CPS
      00:07:02  github.com/ikcode-dev/subsync/blob/main/…  long word
      00:09:44  which is why the lockfile matters here…    21.3 CPS
      00:12:31  Ruff, pytest, and pyright all run in CI…   20.9 CPS
      … 3 more (run with -v to list all)

  Next: YouTube Studio → Subtitles → your video → Add → Upload file → With timing
```

- **Headline** (P2):
  - No warnings: `✓ Subtitles written`.
  - Warnings: `✓ Subtitles written, N to review`.
  - Structural errors: `✗ Written but not compliant, please report with -v output`. Structural errors mean a bug; the exit code is still 0.
- **Flagged subtitles:** the timestamps use `HH:MM:SS`, matching the Studio editor, and are sorted by time. The previewed text is cut to fit the terminal width with `…`. That cut is display-only; the file is never truncated (R12).
- **Later runs:** the model notice reads `✓ Loaded model turbo on CPU` with no download line.
- **Offline:** once the model is cached, this whole run makes no network calls (R4).

### Success: YouTube Short URL (differences only)

```
$ subsync generate https://youtube.com/shorts/AbCdEfGhIjK
"uv in 60 seconds" · 0:58 · ikcode
⠧ Downloading audio…                                    43%
…
  File:      /Users/igor/dev/uv in 60 seconds.en.srt
```

The name comes from the sanitized title (Phase 4 rules: strip `<>:"/\|?*`, cap at 100 characters, fall back to `subtitles`) and is written to the current folder (R14).

### Failure: private video

```
$ subsync generate https://youtu.be/AbCdEfGhIjK
✗ This video is private, so SubSync can't download it.
  If it's your draft, export the file and run:  subsync generate <file>
```
Exit 3 (R21).

### Failure: output already exists

```
$ subsync generate ep42.mov
✗ ep42.en.srt already exists.
  Re-run with --force to replace it, or choose another path with -o.
```
Exit 5, in about a second, before any transcription (R15).

### Cancel

```
⠼ Transcribing 14:52 of audio… 02:10 elapsed
^C
Cancelled. Nothing written.
```
Exit 130. Temporary files are removed (R23).

### Output not to a terminal (piped, CI, cron)

There are no spinners or colors: each stage prints one plain line when it finishes, and the summary is unchanged. Color is also off when `NO_COLOR` is set. `✓ ! ✗` always come with words, so no meaning depends on color (R18).

## States, failures, and recovery

Every row names a message and an exit code. Messages are the intended wording; engineering may adjust the phrasing but not the content.

| # | Trigger | Stage | What the user sees | Recovery offered | Exit | Req |
|---|---|---|---|---|---|---|
| F1 | Missing or unknown option, bad value | 0 | argparse usage plus the specific problem | usage line | 2 | — |
| F2 | `-l xx` | 0 | `Unknown language code 'xx'.` | `Use a code such as en, pl, de.` | 2 | R6 |
| F3 | `-m banana` | 0 | `Unknown model 'banana'.` | lists the valid names | 2 | R7 |
| F4 | `-o out.srt -f vtt` | 0 | `Output name ends in .srt but --format is vtt.` | fix either one | 2 | R16 |
| F5 | `--glossary` file missing or unreadable | 0 | `Can't read glossary terms.txt: <reason>.` | — | 2 | R25 |
| F6 | FFmpeg not on PATH | 0 | `FFmpeg is required but wasn't found.` | `Install it with: brew install ffmpeg` | 1 | R24 |
| F7 | INPUT is neither a file nor a supported URL | 1 | `'foo' is not a file or a supported YouTube URL.` | two example commands | 2 | R3 |
| F8 | INPUT is a folder | 1 | `'clips/' is a folder, not a media file.` | — | 2 | R3 |
| F9 | File has no audio track / can't be decoded | 1F | `No audio track found in ep42.mov.` / `Can't read ep42.mov as audio or video.` | — | 2 | R1 |
| F10 | A YouTube link that isn't a single video (playlist, channel, `music.youtube.com`) | 1U | `This link isn't a single YouTube video.` | `Use the link from the video's Share button.` | 2 | R2 |
| F11 | Output exists, no `--force` | 1F.1 / 1U.3 | `ep42.en.srt already exists.` | `--force` or `-o` | 5 | R15 |
| F12 | Output folder missing / not writable | 1F.1 / 1U.3 | `Can't write to out/: <reason>.` | — | 5 | R14 |
| F13 | Private video | 1U | see transcript | local-file route | 3 | R21 |
| F14 | Deleted, unavailable, region-blocked | 1U | `This video is unavailable (removed or blocked in your region).` | — | 3 | R21 |
| F15 | Age-restricted | 1U | `This video is age-restricted, which SubSync can't download.` | `If it's yours, run SubSync on the exported file.` | 3 | R21 |
| F16 | Live stream or premiere not finished | 1U | `This stream hasn't finished yet.` | `Try again after it ends.` | 3 | R21 |
| F17 | Network failure (retries exhausted) | 1U | `Couldn't reach YouTube: <reason>.` | `Check your connection and re-run.` | 3 | R21, P4 |
| F18 | yt-dlp outdated (YouTube changed) | 1U | `YouTube download failed. yt-dlp is probably out of date.` | the exact upgrade command for how SubSync is installed (E11, E12) | 3 | R21, P7 |
| F19 | Model download failed | 2 | `Couldn't download model 'turbo': <reason>.` | `An internet connection is needed once per model.` | 4 | R7 |
| F20 | Out of memory while loading or transcribing | 2–3 | `Ran out of memory with model 'large-v3'.` | `Try a smaller one: -m small` | 4 | P5 |
| F21 | Other transcription failure | 3 | `Transcription failed: <reason>.` | `Re-run with -v for details.` | 4 | R20 |
| F22 | No speech found, 0 subtitles | 3–4 | `No speech found in ep42.mov, so nothing was written.` | `If the language was misdetected, set it with -l en.` | 4 | P2 |
| F23 | Write failed (disk full, permissions) | 5 | `Couldn't write ep42.en.srt: <OS reason>.` No partial file is left | — | 5 | R17 |
| F24 | Ctrl+C at any stage | any | `Cancelled. Nothing written.` | — | 130 | R23 |
| F25 | Anything unexpected | any | `Something went wrong: <one-line summary>.` | `Re-run with -v and share the output.` | 1 | R20 |
| W1 | Vocabulary hint longer than Whisper can use | 2 | warning: `Vocabulary hint is long; only the first part is used.` | shorten the glossary | — | R25 |
| W2 | Compliance warnings | 4 | counted in the summary, first 5 listed with timestamps | review them in the Studio editor | 0 | R8–R12, R19 |

The ✗ block is never followed by a traceback unless `-v` is set (R20).

## Exit codes

| Code | Meaning | Rows |
|---|---|---|
| 0 | A subtitle file was written. Warnings, and even structural errors, only change the headline (P2) | success, W2 |
| 1 | Environment or unexpected problem | F6, F25 |
| 2 | Bad input or usage | F1–F5, F7–F10 |
| 3 | Source unavailable (YouTube) | F13–F18 |
| 4 | Transcription produced nothing usable | F19–F22 |
| 5 | Output problem | F11, F12, F23 |
| 130 | Cancelled by the user | F24 |

## Layout and input constraints

- **Information priority:** in the summary, the file path comes first (it's what he needs next), then whether anything needs review, then where to look, then how to upload. The stage lines stay above the summary as a record of the run.
- **Terminal width:** designed for 80 columns. Only the flagged-subtitle previews are shortened with `…` to fit. Paths are never shortened.
- **Keyboard:** the only interaction is Ctrl+C. There are no prompts, including for overwriting: `--force` is used instead.
- **Long content:**
  - A 2-hour video keeps showing the elapsed time.
  - A title longer than 100 characters is shortened in the file name only.
  - A flagged list longer than 5 shows `… N more (-v to list all)`.
- **Paths:** paths with spaces work when quoted. `~` is expanded by the shell, not by SubSync.

## Walkthroughs (checked against the brief)

**A. `subsync generate ~/Videos/ep42.mov --glossary ~/yt/terms.txt`, first run, offline after the model download**

| Stage | What happens | Requirements |
|---|---|---|
| 0 | Preflight: default model and format are valid, glossary readable, FFmpeg found | R24, R25 |
| 1 | Input resolves as an existing file → FILE branch. Output pre-check per U1: `~/Videos` is writable and has no `ep42.*.srt` from an earlier run | R3, R14, R15 |
| 1F.2 | Media info read: 14:52, has audio | R1 |
| 1F.3 | Audio extracted with no network | R4 |
| 2 | Model not cached → notice while downloading → loaded on CPU | R7 |
| 3 | Transcribing shows a spinner and elapsed time. `Language: English` appears once known. Glossary terms are applied | R5, R18, R25 |
| 4 | Clean-up, timing, layout, line breaks, reading speed | R8–R13, P1 |
| 5 | Written in one step as UTF-8 without a BOM | R16, R17 |
| 6 | Summary with 8 items to review; exit 0 | R19, R22 |

Every action has an outcome. The only open point is **U1** (below): with auto-detection, the language part of the file name isn't known until after transcription.

**B. `subsync generate https://youtu.be/<private-id>`**

| Stage | What happens | Requirements |
|---|---|---|
| 0 | Preflight passes | R24 |
| 1U.1 | Parsed as a YouTube URL | R2, R3 |
| 1U.2 | Fetching the video info → private → ✗ block with the local-file hint → exit 3. Nothing downloaded, nothing written | R21, R22 |

## Unresolved questions and assumptions

| # | Item | Proposed behavior | Needs |
|---|---|---|---|
| U1 | With auto-detected language, the `.en` in the file name is only known after transcription, which breaks the fail-fast promise of R15 for the default name **Agreed at milestone 3:** before work starts, reject if **any** `<stem>.*.srt` already exists in the output folder, since that is almost certainly a previous run. With `-l`, check the exact name. At write time, re-check the exact name (the one-step write never overwrites without `--force`). `--force` skips both checks | Decided |
| U2 | Whether a transcription percentage and ETA can be shown | Spinner and elapsed time are the v1 minimum. Show a percentage if E3 finds a reliable signal | Engineering (E3) |
| U3 | When the language line can appear | As soon as the engine reports it. At the latest, in the summary | Engineering (E1/E3) |
| U4 | The device label ("CPU", "Apple GPU", "CUDA") | Show whatever the chosen engine actually uses | Engineering (E1) |
| U5 | How long a vocabulary hint can be | Warn (W1) when it gets cut. The limit comes from the engine | Engineering (E5) |
| U6 | Progress to stderr, summary to stdout | Routine choice, recorded here. Revisit if it gets in the way | — |
| U7 | The Studio upload path in the hint | Wording based on the current Studio UI; checked during the first manual upload (A3) | Igor, at the first upload |

No product requirement changed while writing these flows. U1 refines how R15 behaves; Igor agreed to it at milestone 3. U2–U5 are engineering questions and U7 is checked at the first upload.
