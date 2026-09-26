# Decisions

Short records of the decisions that shape SubSync. Read this index first; open a record only when you need the reasoning. New records take the next number. Accepted records are never edited or renumbered, only superseded by a newer record. To add one, use the `decision-records` skill.

| # | Decision | Status | Summary |
|---|---|---|---|
| [0001](0001-record-decisions.md) | Record decisions as short records in `decisions/` | accepted | Four-section records, indexed here, linked from `AGENTS.md`. Supersede, never rewrite. |
| [0002](0002-agent-instructions-in-nested-agents-md.md) | Organize agent instructions as a root AGENTS.md map with nested AGENTS.md per directory | accepted | Root holds a map and always-on rules; each area's rules live in its own `AGENTS.md`; templates load on demand. No `CLAUDE.md`. |
| [0003](0003-specs-define-what-and-why.md) | Specs define what and why, never how | accepted | `spec/` context → plan → tasks, with acceptance criteria and no implementation code. |
| [0004](0004-transcribe-locally.md) | Transcribe locally; media never leaves the machine | accepted | Local Whisper; no network for local files once the model is cached. Engine choice left to spike E1. |
| [0005](0005-manual-upload-no-youtube-api.md) | Write a subtitle file for manual upload; no YouTube API upload | accepted | No Google Cloud, OAuth or quota; Igor uploads the file in Studio (D3). |
| [0006](0006-deliver-v1-in-vertical-slices.md) | Deliver v1 in vertical slices S1–S5, not phase by phase | accepted | Each slice cuts through processor and CLI and is usable alone; order S1 → S5, one task file and one PR per slice. |
| [0007](0007-one-generate-orchestrator-with-mediasource.md) | One source-agnostic `generate()` orchestrator with a `MediaSource` model | accepted | Files and URLs share one orchestrator; `process_video()` retires in S4 (E4). |
| [0008](0008-never-rewrite-transcribed-text.md) | Never rewrite transcribed text; fix timing and warn | accepted | Long words stay whole, fast subtitles are extended into free time, the rest is flagged (R11, R12). |
| [0009](0009-exit-code-reports-whether-a-file-was-written.md) | Exit code answers "was an uploadable file written"; warnings never fail the run | accepted | Only structural breakage is an error; a written file exits 0 (P2). |
| [0010](0010-no-ci-until-s5.md) | No CI until slice S5; tests and lint run locally | accepted | `task test` and `task lint` on Igor's Mac per slice; CI decided in S5 (E7). |

Statuses: `proposed` (under discussion), `accepted` (in force), `deprecated` (no longer applies and nothing replaces it), `superseded` (replaced by a newer record; both records link to each other).
