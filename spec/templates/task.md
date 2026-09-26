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
