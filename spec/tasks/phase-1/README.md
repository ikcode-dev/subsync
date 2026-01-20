# Phase 1: Foundation & Project Setup - Tasks

## Overview

This directory contains atomic, self-contained tasks for Phase 1 of the SubSync project.

**Plan Reference**: [phase-1-foundation.md](../../plan/phase-1-foundation.md)

**Detail Level**: All tasks in this phase are **EXPANDED** — they contain inlined context and can be executed without reading external files.

---

## Task Execution Order

| # | Task | File | Dependencies |
|---|------|------|--------------|
| 1 | Install Dependencies | [01-install-dependencies.md](./01-install-dependencies.md) | *(None)* |
| 2 | Create Error Definitions | [02-error-definitions.md](./02-error-definitions.md) | Task 1 *(sequencing only)* |
| 3 | Implement Data Models | [03-data-models.md](./03-data-models.md) | Task 2 *(sequencing only)* |
| 4 | Implement URL Handler | [04-url-handler.md](./04-url-handler.md) | Task 2: `URLParseError` from `subsync.errors` |
| 5 | Final Verification | [05-final-verification.md](./05-final-verification.md) | Tasks 1-4 |

---

## Context Files (for reference)

These files contain domain knowledge used in tasks. Tasks inline the relevant portions, so reading these is optional:

- [data-models.md](../../context/data-models.md) — Data structure definitions
- [dependencies.md](../../context/dependencies.md) — Dependency information
- [youtube-compatibility.md](../../context/youtube-compatibility.md) — YouTube URL patterns
- [netflix-compliance.md](../../context/netflix-compliance.md) — Compliance rules

---

## Definition of Done (Phase Level)

- [ ] All dependencies installed and verified
- [ ] FFmpeg available in PATH
- [ ] Error hierarchy implemented in `src/subsync/errors.py`
- [ ] All data models implemented in `src/subsync/models.py`
- [ ] URL handler implemented in `src/subsync/url_handler.py`
- [ ] `task lint` passes with no errors
- [ ] `task test` passes with no failures
