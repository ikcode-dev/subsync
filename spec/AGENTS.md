# Spec Directory Guidelines

The `spec/` directory contains the **specification** for the project—defining **what** to build and **why**, never **how** to implement it.

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `spec/context/` | Domain knowledge, constraints, research, external references |
| `spec/plan/` | Feature/phase implementation strategies and architecture |
| `spec/tasks/` | Atomic, verifiable work units with acceptance criteria |
| `spec/templates/` | Starter files for new context, plan and task documents |

Each of `context/`, `plan/` and `tasks/` has its own `AGENTS.md` with file-specific rules. Read it before writing in that directory; open a template only when creating a new file.

## Where Specs Sit

- **Product intent** comes first: the agreed documents in [`docs/product-design/`](../docs/product-design/subsync-v1/index.md) say what SubSync must do for the user. Specs turn that into a technical baseline; when they disagree, the product documents win and the spec is revised.
- **Delivery order** lives in the [implementation roadmap](../docs/product-engineering/subsync-v1/implementation-roadmap.md), not in specs.
- **Cross-cutting decisions** that outlive a phase or slice are recorded in [`decisions/`](../decisions/README.md). Specs link the record rather than restate its reasoning.

## Core Principle

> **Specifications define the WHAT and WHY. The HOW is determined during implementation.**

This separation ensures:
- Specs remain stable even when implementation evolves
- Developers have freedom to find the best solution
- Documentation doesn't become outdated with code changes

## What Belongs in Specs

✅ **Include:**
- Requirements and acceptance criteria
- Constraints and boundaries
- Rationale and trade-off discussions
- Pseudo-code to illustrate algorithms or flow
- Mermaid diagrams for architecture, sequence, or data flow
- Interface definitions (inputs/outputs, data contracts)
- Error conditions and edge cases
- Verification criteria

❌ **Do NOT include:**
- Actual implementation code
- Specific code patterns or library-specific syntax
- Internal class/function designs
- Import statements or concrete API calls

## Writing Style

- Use clear, precise language
- Be explicit about requirements vs. nice-to-haves
- Reference other spec files using relative links: `[data models](context/data-models.md)`
- Use Markdown formatting consistently
