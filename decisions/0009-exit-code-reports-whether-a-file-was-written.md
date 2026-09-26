# 0009: Exit code answers "was an uploadable file written"; warnings never fail the run

- Status: accepted
- Date: 2026-09-25

## Context

The phase 3 and 4 plans left open what counts as a blocking compliance error. Most findings (fast reading speed, long words, short subtitles) are expected on real tech videos and are resolved by review in Studio, not by re-running. Igor runs SubSync by hand and may script it; the exit code needs one clear meaning. This was rule P2, agreed at milestone 1.

## Options

1. **Fail on any compliance violation.** Strict, but most real videos would fail and no file would be written for findings that only need a glance.
2. **Separate structural errors from warnings.** Only breakage that makes the file invalid counts as an error; everything else is a warning shown in the summary.

## Decision

Option 2 ([brief, rule P2](../docs/product-design/subsync-v1/product-brief.md#rules-for-open-spec-questions); [phase 3 plan, Errors vs Warnings](../spec/plan/phase-3-netflix-compliance.md#errors-vs-warnings-p2)).

- Report `errors` cover only structural breakage: an overlap, an out-of-order subtitle, an end at or before its start, or more than 2 lines. The processor must make these impossible, so an error means a bug.
- Every other finding is a warning. `is_compliant` is true exactly when there are no errors.
- If a file was written, the exit code is 0, even with warnings; the summary headline shows "✗ Not compliant" when errors exist.
- Zero subtitles is "no speech found": nothing is written, exit 4.
- A `--strict` mode that fails on warnings is a later feature.

## Consequences

- Scripts and the user can trust exit 0 to mean "there is a file to upload".
- Quality problems surface in the summary, not the exit code; a user who ignores the summary can upload a flagged file.
- Adding `--strict` must not change the default meaning of exit 0.
