# 0010: No CI until slice S5; tests and lint run locally

- Status: accepted
- Date: 2026-09-25

## Context

Engineering question E7 asked how v1 is tested, including whether to run CI and whether to cache Whisper model weights. The agreed test layers depend on the local machine: integration tests use real FFmpeg, and the opt-in end-to-end tests generate a speech clip with macOS `say` and run Whisper `tiny`. macOS on Apple Silicon is the main platform. Igor decided the question while planning S1; the planning documents record the choice and its revisit point, not a longer rationale.

## Options

1. **CI from S1.** Every push checked on a hosted runner; needs FFmpeg on the runner, a decision on the macOS-only e2e tests, and possibly cached model weights.
2. **No CI until S5.** `task test` and `task lint` run locally on Igor's Mac; CI is decided when v1 is finished.

## Decision

Option 2 ([roadmap, Engineering decisions E7](../docs/product-engineering/subsync-v1/implementation-roadmap.md#engineering-decisions); [phase 4 plan, Testing Strategy](../spec/plan/phase-4-cli-output.md#testing-strategy-e7)). Until slice S5, there is no CI configuration in the repository. Each slice's required checks (`task test`, `task test:e2e` once it exists, `task lint`) run locally on the slice head before its pull request merges. S5 includes the CI decision.

## Consequences

- No runner setup or model caching while the pipeline is still changing.
- Nothing checks a pull request automatically; the verification report in each PR is the evidence, and a forgotten local run goes unnoticed.
- Tooling that assumes required CI checks, such as merge gates, has no checks to wait for until S5.
- Revisit in S5, or earlier if a regression slips through.
