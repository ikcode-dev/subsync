# Plan Files Guidelines

Plan files define **implementation strategies**—the high-level approach for building features or phases. They describe **what** to build and **why**, leaving **how** to the implementation phase.

## Purpose

Plan files answer: **"What are we building, and what's our approach?"**

## What to Include

✅ **Include:**
- Goals and objectives for the feature/phase
- Architecture decisions with rationale that are local to this phase. A decision that outlives the phase or slice gets a record in [`decisions/`](../../decisions/README.md); the plan links it instead of restating it
- Component breakdown and responsibilities
- Integration points between components
- Data flow descriptions
- Risk identification and mitigation strategies
- Dependencies on other features or external systems
- Acceptance criteria for the overall feature

✅ **Allowed for illustration:**
- Pseudo-code to explain algorithms or logic flow
- Mermaid diagrams (flowcharts, sequence diagrams, architecture diagrams)
- Interface definitions (inputs/outputs, data contracts)
- Example data structures (conceptual, not language-specific)

❌ **Do NOT include:**
- Actual implementation code
- Library-specific API calls or syntax
- Concrete class/function implementations
- Import statements or module structures

## File Naming

Use descriptive names that identify the feature or phase:
- `phase-1-foundation.md` — Foundation setup phase
- `phase-2-core-pipeline.md` — Core processing pipeline
- `user-authentication.md` — Authentication feature

## Structure Template

When creating a plan file, copy [`spec/templates/plan.md`](../templates/plan.md).

## Principles

1. **Describe outcomes, not implementations** — "The system validates URLs" not "Use regex pattern X"
2. **Explain trade-offs** — Document why you chose one approach over alternatives
3. **Stay stable** — A good plan shouldn't need changes when implementation details evolve
