---
applyTo: "spec/context/**"
---
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
- Decisions already made and their rationale
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

```markdown
# [Topic Name]

## Overview
Brief description of what this context covers and why it matters.

## Key Concepts
Define important terms and concepts.

## Constraints
List any limitations or requirements that must be respected.

## References
- [Link to official documentation](url)
- [Link to relevant standard](url)

## Notes
Any additional observations or findings.
```

## Maintenance

- Update context files when you discover new relevant information
- Keep references current—broken links reduce value
- Context should be factual, not aspirational
