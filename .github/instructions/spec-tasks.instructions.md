---
applyTo: "spec/tasks/**"
---
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

Use numbered, descriptive names within phase folders:
```
spec/tasks/
  phase-1/
    README.md           # Phase overview
    01-install-deps.md
    02-error-handling.md
    03-data-models.md
```

## Structure Template

```markdown
# Task: [Task Name]

## Objective

One-sentence description of what this task accomplishes.

## Detail Level

EXPANDED | REFERENCE-BASED

---

## Context

### References
- **Plan**: [link] → Section "X"
- **Context**: [link] → Section "Y"

### Dependencies
- **Task N**: Uses `SpecificClass` from `module.submodule`
- **Task M**: *(Sequencing only — no direct imports)*

### Context Summary
*(For EXPANDED tasks: inline the relevant domain knowledge)*

Key facts with rationale:
- Fact 1: Why this matters
- Fact 2: Why this constraint exists

---

## Requirements

### Functional Requirements
- The system must...
- When X happens, Y should...

### Input Specification
- What inputs are accepted
- Valid/invalid input examples

### Output Specification
- What outputs are produced
- Format and structure

### Error Handling
- What error conditions must be handled
- What information errors should convey

---

## Acceptance Criteria

- [ ] Criterion 1 (observable outcome)
- [ ] Criterion 2 (testable behavior)
- [ ] All tests pass
- [ ] No linting errors

---

## Test Scenarios

| Scenario | Input | Expected Outcome |
|----------|-------|------------------|
| Valid case | example | expected result |
| Edge case | example | expected result |
| Error case | example | expected error |

---

## Implementation Checklist

1. [ ] Create file: `path/to/file.py`
2. [ ] Import dependencies: `from module import X`
3. [ ] Define interface: `function_name(args) -> return_type`
4. [ ] Create tests: `tests/test_file.py`
5. [ ] Run: `task test` — verify pass
6. [ ] Run: `task lint` — verify pass

---

## Definition of Done

- File exists at specified path
- All acceptance criteria met
- Tests pass
- Linting passes

---

## Notes

Any additional context or considerations.
```

## Principles

1. **Self-contained by default** — Inline context so tasks can be executed standalone
2. **Describe outcomes, not steps** — "URL validation returns VideoInfo" not "Create a function that..."
3. **Make criteria verifiable** — Each acceptance criterion should be testable
4. **Explicit dependencies** — State exactly what is imported from dependency tasks
5. **Stay implementation-agnostic** — A task is complete when behavior matches, regardless of how
6. **One responsibility** — Each task should have a single, clear purpose
