# Open Collector — founder pack

Prepared September 20, 2026. **Status: proposed product and execution plan; no app built or new repository published.** Open Collector is a working descriptor. The founder requested an independently written alternative inspired by Guppy's concepts, with better UX and a lower price or free distribution, and a public application repository.

## Start here

Build a free Mac-first collector watchlist with dependable evidence, honest monitoring status, and fast browser handoff. Use it to establish demand and a sustainable data source before adding purchase assistance. Keep the long-term direction broad enough to cover valuable Guppy concepts while being explicit about what the first release cannot do.

**Proposed stack:** SwiftUI, small Swift domain modules, SQLite, source-specific permitted adapters, local notifications. **Proposed license:** Apache-2.0 for original application code, docs, and fixtures, confirmed at project setup; third-party materials retain their own licenses. **Distribution:** public standalone repository and signed/notarized Mac builds after release checks. **Business:** useful free local client; optional funded hosted alerts later. All are proposals except the founder's requirement that the eventual application repository be public.

The decisive feasibility question is access to useful, timely stock data. The decisive product question is whether collectors value this experience without automatic checkout. Resolve both before spending weeks polishing UI. A local-only synthetic demo can prove architecture; it cannot prove live monitoring value.

## Contents and reading order

| Document | What it settles |
|---|---|
| [Product and market research](01-product-research.md) | Guppy identity/features/pricing/privacy claims, five product comparisons, concept-by-concept adopt/adapt/defer/skip decisions, primary sources |
| [Founder thesis and requirements](02-founder-thesis-and-requirements.md) | Customer, three approaches, recommended first product, 16 acceptance requirements, future parity and exclusions |
| [Experience and UI](03-experience-and-ui.md) | Original screen structure, wireframe, onboarding, key flows, failure states, money authority, accessibility and usability tests |
| [Architecture and security](04-architecture-and-security.md) | Stack options, modules, data contracts, permissions, source adapters, state machines, threat model, signing and updates |
| [Execution plan](05-execution-plan.md) | Dependency-linked milestones, estimates, first sprint, source spikes, public repository shape, release gates and later purchase safety |
| [Business, validation and launch](06-business-validation-and-launch.md) | Free/paid tradeoffs, illustrative unit economics, interviews/pilot, pricing experiments, launch steps and operating risks |
| [Independent build and repository handoff](07-independent-build-and-repository-handoff.md) | No-code-copy boundary, what can enter the public repo, license decision, project-creation checklist and agent handoff prompt |
| [First implementation task cards](08-first-implementation-task-cards.md) | Small engineering tickets with proposed files, dependencies, test scenarios and intended verification commands |

## What to keep, change and skip

Keep exact-product watches, threshold alerts, retailer links, search by product or permitted URL, history, and clear pause controls. Improve source freshness, seller/variant matching, all-in money semantics, diagnostics consent, data export, crash recovery, and visible authority.

Partially adopt discovery, collection history, local inventory, recordings, and community signals only when they improve the core workflow. Defer assisted purchase, queues, mobile, sync, and unattended spending until their source, permission, reliability and support requirements are proven. Skip a buying club, physical inventory/fulfillment operation, broad social network, and mass-purchase optimization. The detailed reasoning is in the concept inventory and parity tables.

## Execution expectations

The first two-week sprint produces a local synthetic vertical slice. A credible real-source beta is roughly a multi-week 7–11-week engineering effort under the plan's assumptions, with source access and pilot observation potentially extending calendar time. There is no fixed launch date and no promise that broad retailer checkout will be available in that window.

The source charter, initial retailer/data integration, supported macOS floor, final name, license confirmation, and founder maintenance budget remain M0 decisions. Work can begin with evidence gathering and the synthetic slice; do not represent unresolved integrations as working features.

## Audit boundary

The separate Guppy workstation audit found authenticity evidence and specific maintenance/privacy concerns. Its machine evidence, extracted security-review files, account observations, and potential vulnerability details stay in a locally excluded private directory, outside this pack. This pack contains independently written requirements and appropriately attributed public/UI concepts. It does not certify Guppy safe or unsafe, and it does not license Guppy's code, assets, services, or data for reuse.

Do not publish this entire existing operations repository. The implementation gets a fresh repository, fresh history, independent source and permitted data. Review the selected project documents before copying them into that public repository; market research and internal audit-process notes need not ship with the application.
