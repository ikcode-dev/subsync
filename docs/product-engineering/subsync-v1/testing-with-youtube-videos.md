# Testing SubSync on real YouTube videos (S1)

Last updated: 2026-09-26 · Applies to `feat/s1-local-file-srt` @ `864ed3a` (S1.1–S1.7)

How to run SubSync on a real YouTube episode, and how to work through the [S1.8 acceptance checklist](../../../spec/tasks/slice-1-local-file-srt.tasks.md#task-s18-acceptance-on-real-episodes).

## Can I pass a YouTube link?

Not yet. URL input arrives in S4. Until then, SubSync recognizes a YouTube URL and stops with exit code 2:

```text
$ uv run subsync generate "https://www.youtube.com/watch?v=VIDEO_ID"
✗ YouTube links aren't supported yet.
  Export or download the video and run: subsync generate <file>
```

So get the video onto disk first, then run SubSync on the file. SubSync accepts video or audio-only files; it extracts the audio either way.

## 1. Set up

```sh
cd ~/dev/ikcode-dev/subsync
git switch feat/s1-local-file-srt
task install                      # uv sync
ffmpeg -version | head -1         # must print a version
mkdir -p ~/subsync-test           # keep test media and SRTs out of the repo
```

The SRT is written next to the input file, as `<name>.<language>.srt`.

The default model, `turbo`, is about 1.5 GB. It downloads once, on the first run, into `~/.cache/whisper`. Only `tiny` is cached on this Mac today.

## 2. Get the video file

Use one of these three sources. All of them keep the exact timeline of the video on YouTube, so the SRT lines up when you upload it.

| Source | When to use it | How |
|---|---|---|
| **A. Your original export** | You still have the file you uploaded | Use it directly (`.mov`, `.mp4`). Don't use it if you trimmed the video in the Studio editor after uploading |
| **B. YouTube Studio download** | Your own published episode | Studio → **Content** → hover the video → **⋮ Options** → **Download** |
| **C. yt-dlp** | Any video you have the rights to (yours or Creative Commons) | See below. yt-dlp is already a project dependency |

With yt-dlp, download the audio only. It's about a tenth the size of the video and is all SubSync needs:

```sh
cd ~/subsync-test
uv run --project ~/dev/ikcode-dev/subsync yt-dlp --js-runtimes node \
  -f "bestaudio[ext=m4a]/bestaudio" \
  -o "%(title)s [%(id)s].%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

- `--js-runtimes node` uses your Node for YouTube's JavaScript challenge. yt-dlp enables only Deno by default and warns without a runtime.
- A "YouTube is forcing SABR streaming" warning is harmless if the download reaches 100%.
- Drop `-f …` to download the full video instead.

Then point a variable at the file, so the commands below stay short:

```sh
cd ~/dev/ikcode-dev/subsync
EP="$HOME/subsync-test/<file name>.m4a"
```

## 3. Smoke test (seconds)

Run with the small `tiny` model first to confirm the setup:

```sh
uv run subsync generate "$EP" -m tiny
```

Expected: stage lines on stderr, then a `✓ Subtitles written` summary with the SRT path and exit 0. Delete the `.en.srt` it wrote before step 4, or step 4 stops with exit 5.

Optionally, check the file against the Netflix rules and the SRT format with the test suite's checker:

```sh
uv run python -c "import sys; sys.path.insert(0, 'tests'); from srt_invariants import find_srt_violations; v = find_srt_violations(open(sys.argv[1], 'rb').read()); print('\n'.join(v) or 'OK: no violations')" "<path to .srt>"
```

## 4. S1.8 acceptance run

You need two videos:

- **A published, talking-head episode of about 15 minutes.** It covers steps 1–6, 8 and 9.
- **A jargon-heavy screencast.** It covers step 7.

The step numbers match the S1.8 checklist.

| # | Do | Expect | Record |
|---|---|---|---|
| 1 | `time uv run subsync generate "$EP"` (default `turbo`, first run) | `Downloading model 'turbo' (one-time)…`, then the stage lines and summary; exit 0 | Summary text, total time, number of subtitles to review |
| 2 | Turn Wi-Fi off, then `uv run subsync generate "$EP" --force; echo "exit=$?"` | Same result offline (R4) | Exit code |
| 3 | Wi-Fi back on. `time uv run subsync generate "$EP"; echo "exit=$?"` (no `--force`) | Stops at once: the output already exists; exit 5 in about 1 s | Exit code and time |
| 4 | `uv run subsync generate "$EP" --force; echo "exit=$?"`, then press **Ctrl+C** once `Transcribing … of audio…` appears | `Cancelled. Nothing written.`; exit 130; prompt back within 2 s (E8); the existing SRT's timestamp in `ls -l` is unchanged | Seconds from ^C to the prompt |
| 5 | Open the `.srt` in an editor | At most 2 lines of 42 characters per subtitle; long words such as URLs stay whole on their own line (R12) | Anything that reads badly |
| 6 | Studio → **Subtitles** → the video → **Add** (under Subtitles) → **Upload file** → **With timing** → choose the `.srt` → **Publish**. Play a few passages | File accepted; the text matches the speech in time (A3) | Accepted? Does the summary's `Next:` hint match what Studio shows (U7)? |
| 7 | `uv run subsync generate "<screencast file>"` | Runs; tech terms may be mis-heard | Mis-heard terms and what was said (baseline for S3) |
| 8 | Dump the raw transcript of the published episode with the script below | A `.transcript.json` next to the media | Keep the file; it becomes an S2 fixture, committed in S2 |
| 9 | Take the total time from step 1 | N1: at most 15 min, target 5 min | Wall time and episode length (input for the E1 spike) |

### Step 8: transcript dump script

Save this as `~/subsync-test/dump_transcript.py`. It stays outside `src/` by design. It writes JSON in the format of `tests/fixtures/transcripts/`, so S2 can load it with `transcript_fixtures.transcript_from_dict`.

```python
"""Dump SubSync's raw Whisper transcript as JSON (S1.8 step 8).

Usage: uv run python ~/subsync-test/dump_transcript.py MEDIA [MODEL]
Writes MEDIA.transcript.json in the format of tests/fixtures/transcripts/.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

from subsync.models import TranscriptionConfig
from subsync.transcriber import load_model, transcribe_with_model

media = Path(sys.argv[1]).expanduser().resolve()
config = TranscriptionConfig(model_name=sys.argv[2] if len(sys.argv) > 2 else "turbo")
result = transcribe_with_model(load_model(config), media, config)

out = media.with_name(media.stem + ".transcript.json")
data = {"description": f"Raw {config.model_name} transcript of {media.name}.", **asdict(result)}
out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{out} ({len(result.segments)} segments, language {result.language})")
```

Run it from the repo so it uses the project environment:

```sh
uv run python ~/subsync-test/dump_transcript.py "$EP"
```

## 5. Report the results

Send the recorded values to the agent that owns the slice, which records them in the S1 row of the [implementation roadmap](implementation-roadmap.md). A failed Studio upload (A3), or a Ctrl+C that takes longer than 2 s (E8), blocks the S1 PR.

## Exit codes and troubleshooting

| Exit | Meaning |
|---|---|
| 0 | Subtitle file written, even when some subtitles are flagged for review |
| 1 | FFmpeg missing, or an unexpected error (re-run with `-v`) |
| 2 | Bad input: a YouTube URL, a folder, a missing file, a file with no audio, an unknown `-l` or `-m` |
| 4 | Model download, memory, transcription, or no speech found |
| 5 | Output exists (use `--force` or `-o`), or the `-o` folder is missing |
| 130 | Cancelled with Ctrl+C; nothing written |

| Problem | Fix |
|---|---|
| yt-dlp: "Sign in to confirm you're not a bot" | Add `--cookies-from-browser chrome` (or `safari`, `firefox`) |
| yt-dlp: HTTP 403 or "Requested format is not available" | Try the newest yt-dlp without touching `uv.lock`: replace `uv run --project … yt-dlp` with `uvx yt-dlp@latest`. Or drop `-f` |
| The SRT drifts out of sync in Studio | The local file isn't the version on YouTube (for example, it was trimmed in the Studio editor). Use Studio download or yt-dlp |
| Wrong language detected | Set it: `-l en` or `-l pl` |
| Need details on a failure | Add `-v` for SubSync's debug log and a traceback |
