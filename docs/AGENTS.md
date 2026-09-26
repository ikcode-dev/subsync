# docs — product and engineering documents

What lives here and which document wins. Project-wide rules are in the [root AGENTS.md](../AGENTS.md).

| Path | What it is | Rule |
|---|---|---|
| `product-design/<release>/` | Discovery output for a release: `index.md` (status and decision log), `product-brief.md`, `ux-flows.md`, `handoff.md`. Written with the product-design skills | Source of truth for what SubSync does for the user. Agreed documents change only with Igor's agreement; record the change in the document's own index |
| `product-engineering/<release>/` | Engineering planning for a release, such as `implementation-roadmap.md` (packages, order, engineering decisions E1–E12, status) | Source of truth for delivery order and status. Update package status as evidence arrives |
| `product-engineering/<work-item>/` | Per-work-item artifacts from the product-engineering loop: `spec.md`, `roadmap.md`, `plans/NN-slug.md` | Created by those skills; follow their templates |
| `product-engineering/verification-profile.md` | How to verify changes: commands, starting the app, allowed environments | Not written yet; created by the `defining-verification` skill |
| `SUBTITLE_GENERATION_ALGORITHM.md` | Background technical design | Not a source of truth. Where it differs from the product documents or `spec/`, they win |

Decisions that outlive one release or document go to [`decisions/`](../decisions/README.md), not here. Technical specs (context, plans, tasks) live in [`spec/`](../spec/AGENTS.md).
