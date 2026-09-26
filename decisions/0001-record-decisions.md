# 0001: Record decisions as short records in `decisions/`

- Status: accepted
- Date: 2026-09-26

## Context

SubSync's decisions are scattered: product choices sit in the [discovery index](../docs/product-design/subsync-v1/index.md) and the [product brief](../docs/product-design/subsync-v1/product-brief.md), engineering choices in the [implementation roadmap](../docs/product-engineering/subsync-v1/implementation-roadmap.md) and in the "Architecture Decisions" sections of each phase plan. Agents and future contributors see the resulting code and specs, not the reasons, and can quietly undo a choice they cannot find. There is no single place to look a decision up.

## Options

1. **No records.** Reasons stay in the brief, the plans, commit messages and chat history. Cheap, and they keep scattering.
2. **Full ADR tooling.** `adr-tools`, `log4brains` or the full MADR template. More structure than a solo project needs; long templates invite filler.
3. **Short records with an index.** One file per decision in `decisions/`, four sections, listed in `decisions/README.md`, which `AGENTS.md` links to.

## Decision

Option 3.

- Files are `decisions/NNNN-kebab-title.md`, numbered from 0001, never renumbered or reused.
- Each record has `# NNNN: Title`, `- Status:`, `- Date:`, then Context, Options, Decision, Consequences, one to two pages. `- Supersedes:` and `- Superseded by:` appear only when they apply.
- Statuses: proposed, accepted, deprecated, superseded. An accepted record is never edited except for typos and dead links; a new record supersedes it and both link to each other.
- `decisions/README.md` indexes every record. `AGENTS.md` links the index with a plain markdown link, not an import, so it loads only when a task needs it.
- Records hold decisions that outlive a single phase or slice and that an agent could plausibly undo. Phase-local design choices stay in the phase plans; specs link a record rather than restate it.
- Decisions agreed before this log existed may be backfilled, dated when they were made, with options taken only from the documents of the time.

## Consequences

- Reasons survive the sessions that produced them. Agents read the index first and open records on demand.
- A structural or cross-cutting change without a record is incomplete work.
- Some overlap with the brief and phase plans remains for backfilled decisions; the record links its source, and a later change supersedes the record rather than editing either copy silently.
- A small writing cost on every significant choice.
