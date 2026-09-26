# 0006: Deliver v1 in vertical slices S1–S5, not phase by phase

- Status: accepted
- Date: 2026-09-25

## Context

The original plan built SubSync in four horizontal phases: foundation, core pipeline, Netflix compliance (processor), then CLI and output. After phases 1 and 2 merged, about half the engineering plan existed but none of it reached the user: `process_video()` was called nowhere and the CLI printed "Hello World". Phases 3 and 4 were still ahead, so the tool would produce no subtitle file until both were complete.

## Options

1. **Finish Phase 3, then Phase 4.** Follows the existing plans; nothing usable until the end.
2. **Vertical slices across phases 3 and 4.** Each slice cuts through processor and CLI and leaves Igor with something he can use on its own.

## Decision

Option 2 ([handoff, Suggested delivery slices](../docs/product-design/subsync-v1/handoff.md#suggested-delivery-slices); order agreed at milestone 3).

- S1: local file → uploadable SRT. S2: readable and reviewable. S3: tech vocabulary. S4: YouTube URL input. S5: VTT and finish.
- Order S1 → S2 → S3 → S4 → S5. S3 comes before S4 because local files are the main route and the vocabulary hint helps every video.
- The spike on the transcription engine (E1) runs alongside once S1 is merged.
- The phase 3 and 4 plans stay as the technical baseline; each slice gets one task file, `spec/tasks/slice-N-<slug>.tasks.md`, written after the previous slice merges.
- Each slice lands on `main` as one pull request.

## Consequences

- A usable tool exists after S1, and real episodes feed later slices (transcript fixtures for S2 and S3).
- Phase plans no longer map one-to-one to delivery; the [implementation roadmap](../docs/product-engineering/subsync-v1/implementation-roadmap.md) is where slice scope, order and status are tracked.
- Later slices revisit code written in earlier ones (processor in S1 and S2, CLI in every slice), so shared files need clear ownership per package.
