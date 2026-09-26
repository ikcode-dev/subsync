# Task Files Guidelines

Task files define **atomic, verifiable work units**. Each task describes **what** and **why** needs to be accomplished and how to verify it's done, leaving **how** to implement to the developer.

## Purpose

Task files answer: **"What does success look like?"**

Tasks should be **self-contained execution units** — a novice developer or simpler LLM should be able to complete the task without navigating to external files.

## What to Include

✅ **Include:**
- Clear, specific objective
- Functional requirements (what the code must do)
- Input/output specifications
- Error handling requirements (what errors to handle, not how)
- Acceptance criteria (observable, testable outcomes)
- Test scenarios to verify completion
- **Inlined context summary** (don't just link — summarize key facts)
- **Explicit dependency contracts** (what exactly is used from dependencies)
- **Implementation checklist** (step-by-step verification)

✅ **Allowed for clarity:**
- Example inputs and expected outputs
- Pseudo-code for complex logic
- Decision tables for conditional behavior
- Interface contracts (function signatures, return types)
- Minimal structural templates (not full implementations)

❌ **Do NOT include:**
- Full implementation code
- Internal architecture decisions beyond interface contracts
- Library-specific implementation details

## Task Expansion Protocol

Each task should declare its **detail level** to set clear expectations:

### EXPANDED (Recommended)

Task includes all necessary context inline. No external file reading required.

Use for:
- Tasks that will be executed by less capable agents
- Critical path tasks where errors are costly
- Tasks with complex domain knowledge

### REFERENCE-BASED

Task references external files for full details. Implementer must read linked files.

Use for:
- Simple tasks with obvious context
- Tasks where context files are short and focused
- When context is too large to inline (>100 lines)

**Always specify which sections** of referenced files are relevant.

## File Naming

Three layouts exist in this directory. Match the layout of the phase or slice you are working in.

**Per-phase folder** with a README and numbered task files (used by phase 1):
```
spec/tasks/
  phase-1/
    README.md           # Phase overview
    01-install-deps.md
    02-error-handling.md
    03-data-models.md
```

**Consolidated file** with all tasks for a phase as sections of one document (used by phase 2):
```
spec/tasks/
  phase-2-core-pipeline.tasks.md
```

**Consolidated file per v1 slice** (used from SubSync v1 onward): the v1 slices S1–S5 cut across phases 3 and 4, so each slice gets one consolidated file, written one slice at a time. Its task sections reference the revised [phase 3](../plan/phase-3-netflix-compliance.md) and [phase 4](../plan/phase-4-cli-output.md) plans and the [implementation roadmap](../../docs/product-engineering/subsync-v1/implementation-roadmap.md):
```
spec/tasks/
  slice-1-local-file-srt.tasks.md
```
Name them `slice-N-<slug>.tasks.md`.

## Structure Template

When writing a task, copy [`spec/templates/task.md`](../templates/task.md): as a whole file in the per-phase folder layout, or as one section per task in a consolidated file.

## Principles

1. **Self-contained by default** — Inline context so tasks can be executed standalone
2. **Describe outcomes, not steps** — "URL validation returns VideoInfo" not "Create a function that..."
3. **Make criteria verifiable** — Each acceptance criterion should be testable
4. **Explicit dependencies** — State exactly what is imported from dependency tasks
5. **Stay implementation-agnostic** — A task is complete when behavior matches, regardless of how
6. **One responsibility** — Each task should have a single, clear purpose
