---
applyTo: "spec/tasks/**"
---
# Task Files Guidelines

Task files define **atomic, verifiable work units**. Each task describes **what** and **why** needs to be accomplished and how to verify it's done, leaving **how** to implement to the developer.

## Purpose

Task files answer: **"What does success look like?"**

## What to Include

✅ **Include:**
- Clear, specific objective
- Functional requirements (what the code must do)
- Input/output specifications
- Error handling requirements (what errors to handle, not how)
- Acceptance criteria (observable, testable outcomes)
- Test scenarios to verify completion
- Links to relevant context and plan files
- Dependencies on other tasks

✅ **Allowed for clarity:**
- Example inputs and expected outputs
- Pseudo-code for complex logic
- Decision tables for conditional behavior

❌ **Do NOT include:**
- Implementation code or code snippets
- Specific class/function/method designs
- Internal architecture decisions
- Library-specific syntax

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

## Context
- Related plan: [link to plan file]
- Related context: [link to context file]
- Depends on: [other task if any]

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

## Acceptance Criteria
- [ ] Criterion 1 (observable outcome)
- [ ] Criterion 2 (testable behavior)
- [ ] All tests pass
- [ ] No linting errors

## Test Scenarios

| Scenario | Input | Expected Outcome |
|----------|-------|------------------|
| Valid case | example | expected result |
| Edge case | example | expected result |
| Error case | example | expected error |

## Notes
Any additional context or considerations.
```

## Principles

1. **Describe outcomes, not steps** — "URL validation returns VideoInfo" not "Create a function that..."
2. **Make criteria verifiable** — Each acceptance criterion should be testable
3. **Stay implementation-agnostic** — A task is complete when behavior matches, regardless of how
4. **One responsibility** — Each task should have a single, clear purpose
