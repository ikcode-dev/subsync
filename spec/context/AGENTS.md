# Context Files Guidelines

Context files capture **domain knowledge** that informs the project. They are reference material—facts, constraints, and research findings.

## Purpose

Context files answer: **"What do we know, and why does it matter?"**

## What to Include

✅ **Include:**
- Domain knowledge and terminology definitions
- External documentation references and summaries
- Technical constraints (platform limitations, compliance requirements)
- Research findings from investigating technologies or approaches
- Constraints that follow from decisions already made (link the record in [`decisions/`](../../decisions/README.md) rather than restating its reasoning)
- Links to authoritative sources (official docs, standards, RFCs)

❌ **Do NOT include:**
- Implementation code or code snippets
- Task lists or action items (those belong in `tasks/`)
- Feature plans or architecture (those belong in `plan/`)

## File Naming

Use descriptive, kebab-case names that identify the domain area:
- `netflix-compliance.md` — Netflix subtitle requirements
- `youtube-compatibility.md` — YouTube API constraints
- `data-models.md` — Core domain entities and their relationships

## Structure Template

When creating a context file, copy [`spec/templates/context.md`](../templates/context.md).

## Maintenance

- Update context files when you discover new relevant information
- Keep references current—broken links reduce value
- Context should be factual, not aspirational
