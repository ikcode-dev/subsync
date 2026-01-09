---
applyTo: "spec/**"
---
# Spec Directory Guidelines

The `spec/` directory contains the **specification** for the project—defining **what** to build and **why**, never **how** to implement it.

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `spec/context/` | Domain knowledge, constraints, research, external references |
| `spec/plan/` | Feature/phase implementation strategies and architecture |
| `spec/tasks/` | Atomic, verifiable work units with acceptance criteria |

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
