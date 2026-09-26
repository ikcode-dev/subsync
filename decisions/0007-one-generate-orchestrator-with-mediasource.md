# 0007: One source-agnostic `generate()` orchestrator with a `MediaSource` model

- Status: accepted
- Date: 2026-09-25

## Context

Phase 2 built `process_video()`, which runs URL → YouTube metadata → download → transcription and is built around `VideoMetadata` (video ID, uploader, upload date). v1 adds local-file input (D1), which has none of those fields, and both routes must share naming, the output pre-check, progress, cancellation and the summary. `SubtitleFile` also carried a YouTube-only `video_id`. This was engineering question E4, decided by Igor while planning S1.

## Options

1. **Parallel entry points**, `process_file()` beside `process_video()`. Rejected: two orchestrators to keep in sync for stage order, cleanup and cancellation.
2. **Reuse `VideoMetadata` for files.** Rejected: local files would need fake IDs, which muddles naming.
3. **One orchestrator and a source model.** A single `generate()` runs every stage after input resolution for both routes, with a `MediaSource` describing the input.

## Decision

Option 3 ([phase 4 plan, One Orchestrator for Files and URLs](../spec/plan/phase-4-cli-output.md#one-orchestrator-for-files-and-urls-e4)).

- `MediaSource` holds the kind (file or YouTube), display name, output stem, default output folder, duration, and the YouTube-only fields (video ID, channel) when they apply.
- `SubtitleFile` drops `video_id`.
- S1 builds the file branch of `generate()`. S4 folds the URL steps of `process_video()` into `generate()` and retires `process_video()`.
- `pipeline_temp_dir()`, `get_video_metadata()`, `download_audio()`, `transcribe_audio()` and `ProgressMapper` are reused.

## Consequences

- Stage order, cleanup, cancellation and progress live in one place for both routes.
- Until S4, `process_video()` and `generate()` coexist; new work goes into `generate()`.
- The data-models spec changes: `MediaSource` added, `SubtitleFile.video_id` removed.
