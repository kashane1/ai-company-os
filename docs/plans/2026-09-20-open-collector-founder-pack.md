# Open Collector Implementation Plan

**Goal:** Independently build a free Mac-first collector watch and evidence app, with a public standalone application repository and a gated path to shopping assistance.

**Architecture:** Proposed SwiftUI modular application with local SQLite state, deterministic rules, durable scheduling and permitted data adapters. The first version has browser handoff and no purchase authority. Separate source-feasibility and pilot gates prevent a synthetic demo from being described as a production monitoring service.

**Tech stack:** Proposed Swift/SwiftUI, SQLite, URLSession and local notifications; direct distribution signing/notarization after a release spike. No application implementation was created during the audit and planning task.

**Status:** Founder-review draft, 2026-09-20. User requested a complete audit and founder pack. The pack is delivered; implementation is future work. Public repository visibility is required; the final owner/name/license and initial permitted source remain setup decisions.

Use the [founder pack](../products/open-collector/README.md) as the canonical design, [execution plan](../products/open-collector/05-execution-plan.md) for milestones, and [implementation task cards](../products/open-collector/08-first-implementation-task-cards.md) for files, dependencies and verification. Future agents should use the executing-plans workflow task by task after the proposed direction is confirmed, without importing any private audit evidence or vendor source.
