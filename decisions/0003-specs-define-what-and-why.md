# 0003: Specs define what and why, never how

- Status: accepted
- Date: 2026-01-09

## Context

SubSync is built by a solo developer working with AI coding agents, often in fresh sessions without earlier context. Each piece of work needs a stable description of the goal, its constraints and how to tell it is done. Specs that describe code go stale as soon as the implementation changes, and agents then follow the outdated instructions.

## Options

1. **Code first, no specs.** Fast to start; requirements and acceptance criteria live only in chat and commit messages, which fresh agent sessions cannot see.
2. **Specs that include implementation.** Code snippets, class designs and library calls in the spec. Rejected in the spec guidelines because the documents become outdated whenever the code evolves, and they remove the implementer's freedom to find the best solution.
3. **Layered what-and-why specs.** `spec/context/` (domain knowledge and constraints), `spec/plan/` (phase strategy), `spec/tasks/` (atomic work units with acceptance criteria and test scenarios), all free of implementation code.

## Decision

Option 3. Specs contain requirements, constraints, rationale, interface contracts, pseudo-code, Mermaid diagrams, acceptance criteria and test scenarios. They never contain implementation code, library-specific syntax, internal class designs or import statements. Work flows context → plan → tasks → implementation; an implementer reads the task spec first and marks its acceptance criteria done once verified. Authoring rules live in [`spec/AGENTS.md`](../spec/AGENTS.md) and its subdirectories.

## Consequences

- Specs stay valid while the code changes; tasks can be executed by an agent without earlier context.
- Writing and keeping specs current costs time before each phase or slice.
- Since v1, the agreed product documents in `docs/product-design/` sit above the specs: when they disagree, the spec is revised.
