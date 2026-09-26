# Discovery: SubSync v1

Last updated: 2026-09-25 · Coordinator: `product-design:guiding-product-discovery`

## Intent and project context

- **Audience, problem, outcome:** Igor, a solo tech YouTuber, wants one local command that turns a video into an `.srt` file ready to upload, following Netflix timing and layout rules. It must work on private drafts before upload and on videos already on YouTube. Full brief: [product-brief.md](product-brief.md).
- **In scope:**
  - Input from a local file or a YouTube URL.
  - Subtitles in the spoken language.
  - Netflix timing, layout and reading-speed rules.
  - SRT output (VTT optional).
  - Feedback during the run, a summary, and errors that say what to do next.
- **Out of scope:**
  - Translation (next increment).
  - Upload through the YouTube API.
  - Batch mode.
  - Config file.
  - Styling rules.
  - Children's profile.
- **Instructions and artifacts inspected:**
  - `CLAUDE.md` and `README.md`.
  - `spec/context/*` and `spec/plan/phase-1..4`.
  - `spec/tasks/phase-1/*` and `spec/tasks/phase-2-core-pipeline.tasks.md`.
  - `docs/SUBTITLE_GENERATION_ALGORITHM.md` and `docs/ALGORITHM.md`.
  - `src/subsync/*`, `tests/*`, `pyproject.toml`, `Taskfile.yml`, `.github/*`.
- **Stack and feasibility:**
  - Python 3.13 with uv, openai-whisper, yt-dlp, FFmpeg and `rich` (declared).
  - The CLI will use argparse (Phase 4 plan).
  - Open question: which Whisper engine to use on Apple Silicon (E1).
- **Visual relationship:** not applicable (terminal output). Visual directions and HTML prototypes are skipped by decision D4.

## Where the product stands (2026-09-25, `main` @ `c659fdd`)

| Phase | Spec | Code | User-visible |
|---|---|---|---|
| 1 Foundation | tasks all ticked | merged | no |
| 2 Core pipeline (yt-dlp → WAV → Whisper) | tasks all ticked, 87 tests that use stand-ins for yt-dlp and Whisper | merged, but `process_video()` is called nowhere | no |
| 3 Netflix compliance | plan only | missing | — |
| 4 Writer and CLI | plan only | missing; `cli.py` prints "Hello World" | — |

About half of the engineering plan is built, but none of it reaches the user yet: the tool cannot yet produce a subtitle file.

## Current artifacts

| Artifact | Location | Status | What it resolves |
|---|---|---|---|
| Product brief | [product-brief.md](product-brief.md) | **agreed** (milestone 1, 2026-09-25) | Audience, scope, requirements R1–R26, rules P1–P8, assumptions A1–A5 |
| UX flows (CLI) | [ux-flows.md](ux-flows.md) | **agreed** (milestone 3, 2026-09-25) | Command surface, journey, transcripts, failures F1–F25 / W1–W2, exit codes, U1–U7 |
| Visual directions / prototypes | — | skipped (D4) | Not applicable to a CLI |
| Handoff | [handoff.md](handoff.md) | **agreed: ready for engineering planning** (milestone 3) | Traceability, slices S1–S5 + spike, spec revisions, engineering questions E1–E12, readiness |

## Decisions and assumptions

| Choice or assumption | Type | Rationale or evidence | Revisit when |
|---|---|---|---|
| D1: input from a local file **and** a YouTube URL | User decision | Private drafts can't be fetched by URL; published videos can | — |
| D2: spoken language only in v1 | User decision | Fastest route to a usable tool; translation is next | After v1 ships |
| D3: write a file, upload by hand | User decision | Avoids Google Cloud, OAuth and quota setup | If manual upload becomes the bottleneck |
| D4: brief + CLI flows + handoff; no visual directions or prototypes | User decision | Terminal product | — |
| R1–R24 as the v1 set (milestone 1, Q1) | User decision | Derived from the Phase 3/4 plans and D1–D3 | — |
| R25 vocabulary hint in v1, as slice S3 (Q2) | User decision | Installed Whisper supports `initial_prompt` and `carry_initial_prompt` | If the S3 A/B shows no benefit |
| R13 repeat-line cleanup in v1 (Q3) | User decision | Whisper repeat loops over music or silence | — |
| R22 exit code 130 on Ctrl+C (Q4) | User decision | Shell convention; revises the Phase 4 plan | — |
| P2 blocking-error definition (Q5) | User decision | The exit code answers "did I get an uploadable file?" | If `--strict` is added |
| P8 delete `docs/ALGORITHM.md` (Q6) | User decision | It contradicts the specs | — |
| Videos are in English (Q7, closes A5) | User decision | Only the English line-break rules are needed in v1 | If a non-English channel starts |
| P1, P3–P7 and the N1 speed target (Q8) | User decision | See the brief | N1: after the spike following S1 |
| Progress to stderr, summary to stdout (U6) | Routine choice made during the flows | Redirecting captures a clean summary | If it gets in the way |
| U1: fail fast on any existing `<stem>.*.srt` when the language is auto-detected (milestone 3) | User decision | Keeps R15's fail-fast promise | — |
| Slice order: S3 (vocabulary) before S4 (URL input) (milestone 3) | User decision | Local files are the main route; the vocabulary hint helps every video | If the back catalogue becomes urgent |
| Flows and handoff ready for engineering planning (milestone 3) | User decision | All product/design questions are closed; E1–E12 are engineering | — |
| A1–A4 | Assumption | See the brief | A3 at the first manual upload; A2 and A4 during S1 |

## Next action

- **Product/design status:** complete. All three documents are agreed (2026-09-25). No product decision is open.
- **Next deliverable (engineering):**
  1. Revise `spec/plan/phase-3|4` and the context docs as listed in [handoff.md](handoff.md#changes-needed-in-existing-specs-for-the-engineering-planning-step).
  2. Delete `docs/ALGORITHM.md` (P8).
  3. Update `CLAUDE.md` and the README.
  4. Write `spec/tasks/` for slice **S1**.
- **Engineering questions to settle while planning S1:** E2, E4, E7, E8, E9.
- **Decision needed from Igor:** when to start engineering planning. This handoff does not authorize implementation.
- **Engineering planning started 2026-09-25:** see [implementation-roadmap.md](../../product-engineering/subsync-v1/implementation-roadmap.md).
