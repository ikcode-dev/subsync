# 0002: Organize agent instructions as a root AGENTS.md map with nested AGENTS.md per directory

- Status: accepted
- Date: 2026-09-26

## Context

Until 2026-09-25 SubSync kept agent guidance in `CLAUDE.md` plus GitHub Copilot primitives in `.github/` (instructions, scoped `.instructions.md` files, custom agents, commit-message instructions). Commit `2940f27` replaced them with a root `AGENTS.md` and nested `AGENTS.md` files under `spec/`, because Claude Code reads `AGENTS.md` natively (since v2.1.277) and other agents (Codex, Copilot, Cursor) read the same file. After the migration the root file still carried everything — module map, Python and testing conventions, transient slice status — and each nested spec file embedded a long authoring template, so every session loaded far more than its task needed. Harnesses also differ in how they load nested files: some load them when a file in that directory is read, others only from the repository root down to the working directory.

## Options

1. **Root file only.** One `AGENTS.md` with everything. Simple, but every session pays for every rule, and it grows with each slice.
2. **`CLAUDE.md` plus Claude-specific `.claude/rules/`.** Path-scoped rules load precisely, but only in Claude Code; other agents see nothing.
3. **Root map plus nested `AGENTS.md` per directory, templates in separate files.** Portable across agents; each area's rules sit next to the code they govern; the root links every nested file so harnesses that do not auto-load them still find them.

## Decision

Option 3.

- Root `AGENTS.md` holds only what is true for every task: project summary, commands, `uv` only, a map of directories with a link to each nested `AGENTS.md`, the source-of-truth order, the Decisions section and commit rules. It tells agents to read a directory's `AGENTS.md` before working there.
- Each directory with its own rules gets an `AGENTS.md`: `src/subsync/` (modules, Python and behavior rules), `tests/`, `spec/` and its `context/`, `plan/`, `tasks/`, and `docs/`.
- Templates and long references live in separate files opened only when needed, such as `spec/templates/`.
- No `CLAUDE.md` and no `.claude/rules/`. Transient status (current slice, package progress) lives in the implementation roadmap, not in instruction files.
- Links are plain markdown links, never `@` imports, so linked files load on demand.

## Consequences

- Sessions load less: an agent implementing a task no longer loads the task template, and an agent editing specs does not load Python conventions.
- Every new directory with its own rules needs an `AGENTS.md` and a row in the root map; a nested file missing from the map may go unread.
- Rules must be placed deliberately: a rule true everywhere belongs in the root, a rule for one area in that area's file, never both.
- Instruction-file changes are `human`-category pull requests under the product-engineering defaults, so Igor reviews them.
