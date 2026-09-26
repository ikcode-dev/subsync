# 0004: Transcribe locally; media never leaves the machine

- Status: accepted
- Date: 2026-09-25

## Context

SubSync subtitles videos for Igor's YouTube channels, including private drafts before upload. The [product brief](../docs/product-design/subsync-v1/product-brief.md#audience-problem-outcome) lists the problems with the existing routes: YouTube's automatic captions get technical vocabulary wrong and appear only after publishing, and cloud transcription services send unpublished material to third parties. Igor works on an Apple Silicon Mac.

## Options

1. **YouTube automatic captions.** No setup; wrong on technical terms and unavailable before publishing.
2. **Cloud transcription service.** Good accuracy with no local compute; sends unpublished videos to a third party.
3. **Local speech-to-text model.** OpenAI Whisper running on the Mac; slower, but nothing leaves the machine.

## Decision

Option 3. Transcription runs locally with a Whisper model. Once the model is downloaded, processing a local file makes no network calls (R4); the network is used only for YouTube URL input and the first model download. Temporary audio is deleted after each run. Which local engine runs Whisper (openai-whisper, mlx-whisper, faster-whisper, whisper.cpp) is left to spike E1; the standard model names (`-m`) stay the same whichever engine is chosen (P3).

## Consequences

- Private drafts can be subtitled safely, and the file route works offline.
- Speed depends on Igor's hardware; the N1 target (a 15-minute episode in ≤ 15 minutes, aiming for ≤ 5) is measured after slice S1, and the engine may change behind `TranscriptionResult`.
- The first run downloads a model and shows a one-time notice (R7).
- Adding a cloud transcription option later would need a new record superseding this one.
