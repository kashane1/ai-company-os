# After Plans

After Plans is now tracked in `ai-company-os` as a managed product with:

- product docs in `docs/products/after-plans/`
- a managed product registry record in `infra/products.json`
- a reserved iOS source root in `products/after-plans-ios/`
- durable execution logging in `state/artifacts/after-plans/codex-append-log.md`

## Source Inputs

Primary source:

- `/Users/simons/Downloads/After_Plans_Founder_Package.docx`

Secondary reference:

- `/Users/simons/Downloads/After_Plans_Founder_Package.pdf`

The DOCX is the source of truth for this ingestion pass. The PDF is only a fallback visual reference if layout context is needed later.

## Repo Placement

- product id: `after-plans`
- docs root: `docs/products/after-plans`
- managed source root: `products/after-plans-ios`
- runtime log root: `state/artifacts/after-plans`

This follows the repo's existing split between product artifacts under `docs/products/`, managed source under `products/`, and runtime-style logs under `state/`.

## Locked Decisions From This Pass

- After Plans stays an iPhone-first product.
- The v1 wedge is post-activity continuation, not event planning, dating, group chat, or public social discovery.
- Joining is easier than creating.
- Shared context outranks broad discovery.
- Known people, same-context people, and prior plan partners outrank strangers.
- The v1 consumer core stays free.
- Trust, moderation, blocking, reporting, and bounded visibility are day-one requirements.
- iOS implementation and App Store release remain separate lanes.

## What This Pass Does

- normalizes the founder package into repo-native product docs
- derives execution-ready product, iOS, trust/safety, App Store, GTM, and launch artifacts
- creates lane-aligned task packets for the next execution steps
- leaves a clean resume boundary after the planning and packetization phases

## What This Pass Does Not Do

- no full iOS implementation
- no backend build-out
- no public discovery or chat system
- no payments, ticketing, or organizer CRM
- no App Store submission or release operations

## Recommended Reading Order

1. `PHASE_STATUS.md`
2. `START_HERE_FOR_CLAUDE.md`
3. `PRODUCT_BRIEF.md`
4. `MVP_SPEC.md`
5. `TASK_BACKLOG.md`
6. `task-packets/`

## Current Status

See `PHASE_STATUS.md` for the live phase boundary and `RESUME_PROMPT.md` for the exact restart instructions.
