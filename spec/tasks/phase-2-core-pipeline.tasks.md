# Phase 2: Core Pipeline — Tasks

> Consolidated task list for Phase 2 (Audio Extraction & Transcription).
> Based on [phase-2-core-pipeline.md](../plan/phase-2-core-pipeline.md).

**Dependencies**: Phase 1 complete
**Context**: [dependencies.md](../context/dependencies.md), [data-models.md](../context/data-models.md), [netflix-compliance.md](../context/netflix-compliance.md)

---

## Phase-Level Acceptance Criteria

From [the plan](../plan/phase-2-core-pipeline.md):

- [x] Can extract metadata from public YouTube videos
- [x] Can download and extract audio to WAV format
- [x] Can transcribe audio with Whisper
- [x] Word timestamps are included when available
- [x] Language auto-detection works
- [x] GPU used when available, CPU fallback works
- [x] Temporary files are cleaned up automatically
- [x] Progress is reported during long operations
- [x] All unit tests pass
- [x] Error cases produce clear, actionable messages

---

## Task 1: Add Core Dependencies

**Objective**: Install yt-dlp and openai-whisper into the project so downstream tasks can import them.

**Detail Level**: STANDARD

### Context

- yt-dlp: YouTube metadata extraction and audio download (Unlicense)
- openai-whisper: Speech-to-text transcription with timestamps (MIT)
- FFmpeg is a **system** dependency, not a Python package — document but don't install via uv

### Requirements

1. Add `yt-dlp` as a project dependency via `uv add yt-dlp`
2. Add `openai-whisper` as a project dependency via `uv add openai-whisper`
3. Verify both packages import successfully inside the project virtualenv
4. Ensure existing tests still pass after dependency changes

### Acceptance Criteria

- [x] `uv run python -c "import yt_dlp; print(yt_dlp.version.__version__)"` prints a version
- [x] `uv run python -c "import whisper; print(whisper.__version__)"` prints a version
- [x] `pyproject.toml` lists both new dependencies
- [x] `uv run pytest` passes (no regressions)

### Test Scenarios

| # | Scenario | Verification |
|---|----------|-------------|
| 1 | yt-dlp importable | `import yt_dlp` succeeds |
| 2 | whisper importable | `import whisper` succeeds |
| 3 | Existing tests pass | `uv run pytest` — 0 failures |

### Implementation Checklist

1. [x] `uv add yt-dlp`
2. [x] `uv add openai-whisper`
3. [x] Verify imports
4. [x] Run full test suite

---

## Task 2: Audio Extractor — Metadata

**Objective**: Implement `get_video_metadata()` that uses yt-dlp to extract video information without downloading the video.

**Detail Level**: EXPANDED

### Context

- Input: YouTube video ID (11-character string from `url_handler.py`)
- Output: `VideoMetadata` dataclass (already defined in `models.py`)
- Uses yt-dlp's `extract_info(download=False)` to avoid downloading
- Must map yt-dlp errors to SubSync error hierarchy (`errors.py`)

**Error Mapping** (from plan):

| yt-dlp Condition | SubSync Error |
|------------------|---------------|
| Video unavailable | `VideoUnavailableError` |
| Private video | `VideoUnavailableError` |
| Age-restricted | `AgeRestrictedError` |
| Live stream | `LiveStreamError` |

### Requirements

1. Create `src/subsync/audio_extractor.py`
2. Implement `get_video_metadata(video_id: str) -> VideoMetadata`
3. Construct the full URL from the video ID and call yt-dlp
4. Map yt-dlp response fields to `VideoMetadata` fields:
   - `id` → `id`
   - `title` → `title` (sanitized: strip leading/trailing whitespace)
   - `duration` → `duration` (float, seconds)
   - `uploader` or `channel` → `uploader`
   - `upload_date` → `upload_date` (YYYYMMDD string)
5. Map yt-dlp error conditions to SubSync exceptions:
   - Video unavailable / private / deleted → `VideoUnavailableError`
   - Age-restricted → `AgeRestrictedError`
   - Live stream → `LiveStreamError`
6. Use `logging` for debug output, never `print`
7. Suppress yt-dlp console output (set `quiet=True` in yt-dlp options)

### Acceptance Criteria

- [x] `get_video_metadata` accepts a video ID string and returns `VideoMetadata`
- [x] All `VideoMetadata` fields are populated from yt-dlp response
- [x] Unavailable video raises `VideoUnavailableError`
- [x] Age-restricted video raises `AgeRestrictedError`
- [x] Live stream raises `LiveStreamError`
- [x] yt-dlp console output is suppressed
- [x] Unit tests cover success and all error cases (mocked yt-dlp)
- [x] Type hints on all function signatures

### Test Scenarios

| # | Scenario | Input | Expected |
|---|----------|-------|----------|
| 1 | Successful metadata extraction | Mock yt-dlp returns valid info dict | `VideoMetadata` with correct fields |
| 2 | Missing optional fields | Mock info dict with `uploader=None` | Falls back to `channel` or `"Unknown"` |
| 3 | Video unavailable | Mock yt-dlp raises `DownloadError` with "unavailable" | `VideoUnavailableError` |
| 4 | Private video | Mock yt-dlp raises `DownloadError` with "private" | `VideoUnavailableError` |
| 5 | Age-restricted | Mock yt-dlp raises `DownloadError` with "age" | `AgeRestrictedError` |
| 6 | Live stream detected | Mock info dict with `is_live=True` | `LiveStreamError` |
| 7 | Network error | Mock yt-dlp raises `DownloadError` with generic message | `VideoUnavailableError` |

### Implementation Checklist

1. [x] Create `src/subsync/audio_extractor.py` with module docstring
2. [x] Implement `get_video_metadata()` with yt-dlp `YoutubeDL` context manager
3. [x] Configure yt-dlp options: `quiet=True`, `no_warnings=True`, `extract_flat=False`
4. [x] Map info dict fields to `VideoMetadata`
5. [x] Add error mapping logic (parse yt-dlp error messages for classification)
6. [x] Add live stream detection (`is_live` field in info dict)
7. [x] Create `tests/test_audio_extractor.py` with mocked yt-dlp
8. [x] Run `uv run pytest tests/test_audio_extractor.py`
9. [x] Run `uv run ruff check src/subsync/audio_extractor.py`

### Definition of Done

`get_video_metadata()` returns a populated `VideoMetadata` for valid video IDs and raises the appropriate SubSync exception for each error category, all verified by unit tests with mocked yt-dlp.

---

## Task 3: Audio Extractor — Download

**Objective**: Implement `download_audio()` that downloads and converts audio from a YouTube video to a 16kHz mono WAV file suitable for Whisper.

**Detail Level**: EXPANDED

### Context

- Input: video ID + output directory path + optional progress callback
- Output: `Path` to the downloaded WAV file
- yt-dlp handles download and FFmpeg post-processing in one step
- Audio format: 16kHz sample rate, mono channel, WAV — Whisper's optimal input
- Progress callback signature: `Callable[[float], None]` where float is 0.0–1.0

### Requirements

1. Add `download_audio(video_id: str, output_dir: Path, progress_callback: Callable[[float], None] | None = None) -> Path` to `audio_extractor.py`
2. Configure yt-dlp to:
   - Download best audio stream only (no video)
   - Post-process with FFmpeg to WAV (16kHz, mono)
   - Save to the provided `output_dir`
   - Use a predictable filename based on video ID
3. Wire yt-dlp's `progress_hooks` to the optional `progress_callback`
4. Map download errors to SubSync exceptions
5. Return the `Path` to the resulting WAV file
6. Verify the output file exists before returning

### Acceptance Criteria

- [x] `download_audio` returns a `Path` to a valid WAV file
- [x] Output file is 16kHz, mono WAV
- [x] Progress callback receives values between 0.0 and 1.0
- [x] Download errors raise `VideoUnavailableError`
- [x] Output file is in the specified `output_dir`
- [x] Unit tests cover success path and error cases (mocked yt-dlp)
- [x] Type hints on all function signatures

### Test Scenarios

| # | Scenario | Input | Expected |
|---|----------|-------|----------|
| 1 | Successful download | Mock yt-dlp completes | Path to WAV file returned |
| 2 | Progress reporting | Mock yt-dlp progress hooks | Callback called with increasing values |
| 3 | Download failure | Mock yt-dlp raises `DownloadError` | `VideoUnavailableError` |
| 4 | No progress callback | `progress_callback=None` | No error, download completes |
| 5 | Output dir validation | Provide valid output dir | File written to correct directory |

### Implementation Checklist

1. [x] Add `download_audio()` to `audio_extractor.py`
2. [x] Configure yt-dlp download options:
   - `format`: `"bestaudio/best"`
   - `postprocessors`: FFmpeg extract audio to WAV
   - `postprocessor_args`: `["-ar", "16000", "-ac", "1"]` (16kHz mono)
   - `outtmpl`: `output_dir / "{video_id}.%(ext)s"`
3. [x] Implement progress hook adapter (yt-dlp `d["status"]` → callback float)
4. [x] Add error handling and mapping
5. [x] Verify output file existence
6. [x] Add tests to `tests/test_audio_extractor.py`
7. [x] Run tests and linter

### Definition of Done

`download_audio()` uses yt-dlp to download audio and convert it to 16kHz mono WAV in the specified directory, reporting progress via callback, verified by mocked unit tests.

---

## Task 4: Transcriber

**Objective**: Implement `transcribe_audio()` that uses OpenAI Whisper to transcribe an audio file, returning word-level timestamps.

**Detail Level**: EXPANDED

### Context

- Input: audio file path + `TranscriptionConfig` + optional progress callback
- Output: `TranscriptionResult` (already defined in `models.py`)
- Whisper model defaults: `"turbo"`, `word_timestamps=True`, `device="auto"`
- Device selection: `"auto"` → try CUDA, fall back to CPU
- Progress callback: whisper doesn't have native progress — use a best-effort approach

### Requirements

1. Create `src/subsync/transcriber.py`
2. Implement `transcribe_audio(audio_path: Path, config: TranscriptionConfig | None = None, progress_callback: Callable[[float], None] | None = None) -> TranscriptionResult`
3. Device resolution:
   - `"auto"` → check `torch.cuda.is_available()`, use `"cuda"` if true, else `"cpu"`
   - `"cuda"` explicitly → use CUDA (let it fail naturally if unavailable)
   - `"cpu"` explicitly → use CPU
4. Load the Whisper model by name from `config.model_name`
5. Call `whisper.transcribe()` with:
   - `language=config.language` (None for auto-detect)
   - `word_timestamps=config.word_timestamps`
6. Map Whisper output to `TranscriptionResult`:
   - `result["language"]` → `language`
   - Compute `duration` from audio file or last segment end time
   - `result["segments"]` → list of `TranscriptionSegment`
   - Each segment's `"words"` → list of `Word`
7. Handle missing word timestamps gracefully (empty `words` list)
8. Wrap Whisper exceptions in `TranscriptionError`
9. Handle GPU out-of-memory: catch CUDA OOM error and log a warning suggesting a smaller model or CPU — do not auto-retry (let the caller decide)

### Acceptance Criteria

- [x] `transcribe_audio` returns a `TranscriptionResult`
- [x] Segments contain word-level timestamps when available
- [x] Language is auto-detected when `config.language` is None
- [x] Device resolution works for auto/cuda/cpu
- [x] Whisper errors are wrapped in `TranscriptionError`
- [x] Default config is used when `config` parameter is None
- [x] Unit tests cover all paths (mocked whisper)
- [x] Type hints on all function signatures

### Test Scenarios

| # | Scenario | Input | Expected |
|---|----------|-------|----------|
| 1 | Successful transcription | Mock whisper returns segments with words | `TranscriptionResult` with segments and words |
| 2 | Auto-detect language | `config.language=None` | Language field populated from whisper result |
| 3 | Explicit language | `config.language="en"` | Passed to whisper, returned in result |
| 4 | No word timestamps | Mock whisper segments without `words` key | Segments with empty `words` list |
| 5 | Device auto — CUDA available | Mock `torch.cuda.is_available()` → True | Model loaded on `"cuda"` |
| 6 | Device auto — CPU fallback | Mock `torch.cuda.is_available()` → False | Model loaded on `"cpu"` |
| 7 | Whisper model load fails | Mock `whisper.load_model` raises | `TranscriptionError` |
| 8 | Whisper transcribe fails | Mock `model.transcribe` raises | `TranscriptionError` |
| 9 | Default config used | `config=None` | Uses `TranscriptionConfig()` defaults |
| 10 | GPU out-of-memory | Mock `model.transcribe` raises CUDA OOM | `TranscriptionError` with OOM context in message |

### Implementation Checklist

1. [x] Create `src/subsync/transcriber.py` with module docstring
2. [x] Implement device resolution helper: `_resolve_device(device: str) -> str`
3. [x] Implement `transcribe_audio()`
4. [x] Map whisper result dict to `TranscriptionResult` / `TranscriptionSegment` / `Word`
5. [x] Handle edge cases: missing words, empty segments
6. [x] Wrap all whisper/torch exceptions in `TranscriptionError`
7. [x] Handle CUDA OOM specifically — include actionable message (suggest smaller model or CPU)
8. [x] Create `tests/test_transcriber.py` with comprehensive mocked tests
9. [x] Run tests and linter

### Definition of Done

`transcribe_audio()` loads a Whisper model, transcribes audio with word-level timestamps, returns a `TranscriptionResult`, and handles all error cases — verified by mocked unit tests.

---

## Task 5: Temporary File Management

**Objective**: Implement a context manager that creates a temporary directory for pipeline intermediary files (WAV audio) and guarantees cleanup on exit.

**Detail Level**: STANDARD

### Context

- The pipeline downloads WAV files that should not persist after processing
- Must clean up on both success and failure (exceptions)
- Python's `tempfile.TemporaryDirectory` provides most of this out of the box
- A thin wrapper allows logging and custom prefix for debugging

### Requirements

1. Create a context manager `pipeline_temp_dir()` in `src/subsync/pipeline.py`
2. Yields a `Path` to a temporary directory
3. Directory is created on enter, removed on exit (success or failure)
4. Add a `subsync_` prefix to the temp directory name for easy identification
5. Log directory creation and cleanup at DEBUG level

### Acceptance Criteria

- [x] Context manager yields a valid `Path` to an existing directory
- [x] Directory and contents are removed after context exits normally
- [x] Directory and contents are removed after context exits via exception
- [x] Temp directory name starts with `subsync_`
- [x] Creation and cleanup are logged at DEBUG level
- [x] Unit tests verify both cleanup paths

### Test Scenarios

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Normal exit | Directory removed |
| 2 | Exception exit | Directory removed |
| 3 | Files inside temp dir | Files and directory removed |
| 4 | Directory name | Starts with `subsync_` |

### Implementation Checklist

1. [x] Create `src/subsync/pipeline.py` with module docstring
2. [x] Implement `pipeline_temp_dir()` context manager using `tempfile.TemporaryDirectory`
3. [x] Create `tests/test_pipeline.py` with cleanup tests
4. [x] Run tests and linter

---

## Task 6: Pipeline Orchestrator

**Objective**: Implement `process_video()` that coordinates the full URL-to-transcription pipeline: parse URL, get metadata, download audio, transcribe, and clean up.

**Detail Level**: EXPANDED

### Context

- Orchestrates: URL Handler → Audio Extractor → Transcriber
- Uses `pipeline_temp_dir()` from Task 5 for file lifecycle
- Reports progress across stages via callback
- Pipeline stages with approximate progress mapping:
  1. Parse URL → 0%
  2. Get Metadata → 5%
  3. Download Audio → 5–50%
  4. Transcribe → 50–100%

### Requirements

1. Add `process_video()` to `src/subsync/pipeline.py`
2. Signature: `process_video(url: str, transcription_config: TranscriptionConfig | None = None, progress_callback: Callable[[float, str], None] | None = None) -> tuple[VideoMetadata, TranscriptionResult]`
3. Progress callback signature: `(progress: float, stage: str) -> None`
   - `progress`: 0.0–1.0 overall progress
   - `stage`: human-readable stage name (e.g., `"Downloading audio"`)
4. Pipeline steps:
   a. Parse URL via `parse_youtube_url()` from `url_handler.py`
   b. Get metadata via `get_video_metadata()`
   c. Create temp directory
   d. Download audio via `download_audio()` — map download progress to 5–50%
   e. Transcribe via `transcribe_audio()` — map transcription progress to 50–100%
   f. Cleanup temp directory (automatic via context manager)
5. Return both `VideoMetadata` and `TranscriptionResult`
6. Let SubSync exceptions propagate (don't swallow them)
7. Wrap unexpected exceptions in `SubSyncError`

### Acceptance Criteria

- [x] `process_video` accepts a YouTube URL and returns `(VideoMetadata, TranscriptionResult)`
- [x] All pipeline stages execute in order
- [x] Temporary files are cleaned up after processing
- [x] Progress callback reports stage names and progress values
- [x] SubSync exceptions propagate unchanged
- [x] Unexpected exceptions are wrapped in `SubSyncError`
- [x] Unit tests cover the full pipeline with all components mocked
- [x] Type hints on all function signatures

### Test Scenarios

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Full pipeline success | Returns `(VideoMetadata, TranscriptionResult)`, temp dir cleaned |
| 2 | Invalid URL | `URLParseError` propagated |
| 3 | Video unavailable | `VideoUnavailableError` propagated, temp dir cleaned |
| 4 | Transcription failure | `TranscriptionError` propagated, temp dir cleaned |
| 5 | Progress reporting | Callback called with increasing values and stage names |
| 6 | No progress callback | `progress_callback=None` — no error |
| 7 | Default transcription config | `config=None` → uses `TranscriptionConfig()` defaults |

### Implementation Checklist

1. [x] Add `process_video()` to `pipeline.py`
2. [x] Implement progress mapping helpers for download (5–50%) and transcription (50–100%)
3. [x] Wire all components together inside `pipeline_temp_dir()`
4. [x] Add tests to `tests/test_pipeline.py`
5. [x] Run full test suite: `uv run pytest`
6. [x] Run linter: `uv run ruff check .`

### Definition of Done

`process_video()` orchestrates the full pipeline from URL to `TranscriptionResult`, manages temporary files via context manager, reports progress, and propagates errors correctly — verified by unit tests with all components mocked.

---

## Task 7: Progress Reporting Infrastructure

**Objective**: Create a progress reporting utility that components can use to emit structured progress updates, decoupling progress display from pipeline logic.

**Detail Level**: STANDARD

### Context

- Both `download_audio` and `transcribe_audio` accept progress callbacks
- The pipeline orchestrator maps sub-progress ranges to overall progress
- A reusable helper simplifies mapping partial ranges (e.g., download = 5–50%)
- This keeps progress math out of the orchestrator and into a dedicated utility

### Requirements

1. Create `src/subsync/progress.py`
2. Implement `ProgressMapper` class:
   - Constructor: `__init__(self, callback: Callable[[float, str], None] | None, start: float, end: float, stage: str)`
   - Method: `update(self, fraction: float) -> None` — maps `fraction` (0.0–1.0) to the `[start, end]` range and calls `callback`
   - Method: `complete(self) -> None` — calls `callback` with `end` value
   - If `callback` is None, all calls are no-ops
3. Type hints on all signatures

### Acceptance Criteria

- [x] `ProgressMapper` maps sub-progress to overall range
- [x] `update(0.0)` → callback receives `start` value
- [x] `update(1.0)` → callback receives `end` value
- [x] `update(0.5)` with range `(0.1, 0.5)` → callback receives `0.3`
- [x] None callback → no errors (no-op)
- [x] Unit tests cover mapping math and edge cases

### Test Scenarios

| # | Scenario | Input | Expected |
|---|----------|-------|----------|
| 1 | Start of range | `update(0.0)` on range `(0.05, 0.50)` | Callback called with `0.05` |
| 2 | End of range | `update(1.0)` on range `(0.05, 0.50)` | Callback called with `0.50` |
| 3 | Midpoint | `update(0.5)` on range `(0.0, 1.0)` | Callback called with `0.5` |
| 4 | None callback | Any update call | No error |
| 5 | Complete | `complete()` on range `(0.5, 1.0)` | Callback called with `1.0` |

### Implementation Checklist

1. [x] Create `src/subsync/progress.py`
2. [x] Implement `ProgressMapper`
3. [x] Create `tests/test_progress.py`
4. [x] Run tests and linter

---

## Task 8: Final Verification

**Objective**: Verify all Phase 2 components work together, all tests pass, linting is clean, and the module structure is correct.

**Detail Level**: STANDARD

### Context

This is a verification-only task — no new code to write. Ensures that all Phase 2 tasks are integrated correctly.

### Verification Checklist

1. **Dependencies**: `yt-dlp` and `openai-whisper` importable
2. **Module structure**: `audio_extractor.py`, `transcriber.py`, `pipeline.py`, `progress.py` exist in `src/subsync/`
3. **Tests pass**: `uv run pytest` — all pass, 0 failures
4. **Linting clean**: `uv run ruff check .` — no errors
5. **Formatting clean**: `uv run ruff format --check .` — no changes needed
6. **No orphaned imports**: All new modules can be imported from `subsync` package
7. **Type hints**: All public function signatures have type hints

### Expected Module Structure

```
src/subsync/
    __init__.py
    cli.py              # Phase 1
    errors.py           # Phase 1
    models.py           # Phase 1
    url_handler.py      # Phase 1
    audio_extractor.py  # Phase 2 (Tasks 2, 3)
    transcriber.py      # Phase 2 (Task 4)
    pipeline.py         # Phase 2 (Tasks 5, 6)
    progress.py         # Phase 2 (Task 7)
```

### Acceptance Criteria

- [x] All unit tests pass
- [x] Linting produces no errors
- [x] Formatting is consistent
- [x] All new modules are importable
- [x] No phase 1 regressions

### Implementation Checklist

1. [x] Run `uv run pytest` — verify all tests pass
2. [x] Run `uv run ruff check .` — verify no lint errors
3. [x] Run `uv run ruff format --check .` — verify formatting
4. [x] Verify module imports: `uv run python -c "from subsync import audio_extractor, transcriber, pipeline, progress"`
5. [x] Review test coverage for new modules

### Verification

- Test run: `uv run pytest` — 87 passed, 0 failed.
- Lint: `uv run ruff check .` — All checks passed.
- Format: `uv run ruff format --check .` — 15 files already formatted.
- Imports: `from subsync import audio_extractor, transcriber, pipeline, progress` — All modules importable.

### Definition of Done

All Phase 2 code is complete, tested, linted, and integrated with the existing Phase 1 foundation.

---

## Task Execution Order

```
Task 1: Add Core Dependencies
  └─► Task 2: Audio Extractor — Metadata
       └─► Task 3: Audio Extractor — Download
            └─► Task 4: Transcriber
                 └─► Task 5: Temporary File Management
                      └─► Task 7: Progress Reporting Infrastructure
                           └─► Task 6: Pipeline Orchestrator
                                └─► Task 8: Final Verification
```

Tasks 2–4 can be developed somewhat independently but are ordered for logical progression. Task 6 depends on Tasks 2–5 and 7. Task 8 is always last.

---

## Definition of Done (Phase Level)

- [x] `yt-dlp` and `openai-whisper` installed and importable
- [x] `audio_extractor.py` implements `get_video_metadata()` and `download_audio()`
- [x] `transcriber.py` implements `transcribe_audio()` with device auto-detection
- [x] `pipeline.py` implements `pipeline_temp_dir()` and `process_video()`
- [x] `progress.py` implements `ProgressMapper`
- [x] All yt-dlp errors map to SubSync exception hierarchy
- [x] Temporary files are cleaned up on success and failure
- [x] `uv run pytest` passes with no failures
- [x] `uv run ruff check .` passes with no errors
- [x] `uv run ruff format --check .` reports no changes needed

---

## Next Phase

Phase 2 complete → proceed to **[Phase 3: Netflix Compliance](../plan/phase-3-netflix-compliance.md)**, which processes `TranscriptionResult` into Netflix-compliant subtitles.
