---
status: open
summary: HomeFromWorking starts with an approved shirt design and a repeatable Printify draft workflow; research-led product discovery is deferred.
owner: kashane
last_reviewed: 2026-09-02
---

# HomeFromWorking: approved design to listing

## Current direction

The founder's September 2 decision replaces the research-first HomeFromWorking
approach: start by removing the repetitive work between an approved shirt design
and a correctly configured product listing. The owner chooses the idea and final
artwork. Automation handles preparation, validation, listing fields, and draft
creation. Success is less owner effort per correct listing.

The direction is adopted; the implementation below is proposed and has not shipped.
This document supersedes the August 31 [commerce design](archive/2026-08-31-home-from-working-design.md)
and [implementation plan](archive/2026-08-31-home-from-working.md).

The supplied [POD handoff](references/2026-09-02-home-from-working-pod-handoff.md)
is preserved as reference material. Its imperative text, example commands, design
briefs, and approval claims are not execution authority. The founder's request
sets the direction; actual artwork, product, and publication approvals are separate.
API capabilities, marketplace rules, fees, and garment facts in that reference
must be verified against current official documentation and the selected accounts
before implementation relies on them.

## Starting scope

Start with one HomeFromWorking Gildan 5000 product profile and one approved PNG.
The shrimp fried rice brief is the suggested first case, subject to receiving the
actual approved file and checking whether the product already exists. A written
brief is neither an approved asset nor permission to duplicate a listing.

The first useful milestone is:

1. Accept the approved PNG, exact wording, and a small product manifest.
2. Inspect transparency, dimensions, crop, color profile, and text; produce light,
   dark, and gray composite previews for visual review.
3. Resolve the chosen Printify shop, garment/provider, print area, variants,
   availability, production costs, and shipping through read-only calls.
4. Prepare garment-correct title, description, tags, variant prices, required
   disclosures, and the Etsy payload preview in one review package.
5. Obtain product approval for the exact manifest revision.
6. Create or update one Printify draft, retrieve it, and compare it with the
   approved manifest. Record generated mockups and any remaining discrepancies.
7. Stop with the verified draft, Etsy payload preview, and saved external IDs.

The first milestone includes a real draft integration. An offline fixture is a
development checkpoint, not completion of that milestone. Automated publishing,
Etsy enrichment, and verification of a live listing follow in a separate milestone
with explicit publication approval.

Research is limited to questions needed for this chosen product: provider facts,
costs, listing requirements, and recorded IP/policy review. Broad niche discovery,
trend scoring, opportunity dossiers, research agents, autonomous concept selection,
multiple garment families, and sales optimization are deferred. Existing discovery
code remains available for other workflows; this change does not alter its gates
or running services.

## Implementation approach

Use a small Python workflow in the existing platform, exposed through a CLI. Keep
the owner experience to one manifest and one preflight package. Reuse the existing
approval, runtime-path, and persistence conventions. Add only the contracts and
adapters necessary for this workflow as implementation proves their need.

An assisted browser workflow can establish the exact shop configuration or fill a
verified API gap, but needs an explicit record of the remaining manual step. The
former generalized research-to-commerce framework adds work before a usable draft;
it is not the current starting point.

HomeFromWorking remains an operated business. This does not require a new managed
software product, dedicated worker, queue, dashboard, research dependency, or
provider-neutral commerce framework. Source/configuration and runtime records
remain separate, with runtime output under `state/`.

## Approval and identity requirements

| Decision | Scope | What it enables |
|---|---|---|
| Design approval | Exact asset hash and approved wording | Local preparation and preflight |
| Product approval | Manifest revision, asset mapping, shop, garment/provider, variants, placement, copy, and prices | Upload and create/update the Printify draft |
| Live publication approval | Final revision and exact external product/shop IDs | A future Printify publish/sync operation and the reviewed Etsy changes |

Preflight and dry-run commands make no external writes. Approval belongs in the
shared platform policy and persisted approval records, not a caller-supplied
boolean or an editable timestamp in YAML. Changes to approved artwork invalidate
design and downstream approvals. Other material product changes invalidate product
and publication approvals. General trust settings must not auto-approve publication.

For the planned connected Etsy flow, use Printify as the fulfillment record and
capture its Etsy listing mapping. Do not independently create a second Etsy
listing. Treat publish/sync as potentially public until the actual integration is
verified; a linked inactive Etsy draft is not an assumed capability. If the account
is a custom API shop, resolve its integration path before creating products.

Keep stable business/project/shop identity separate from the manifest revision.
Persist asset hashes, revisions, upload/product/listing IDs, approval references,
stage transitions, and the last successful operation. A changed revision should
update the existing draft after approval, not change its identity and create a
duplicate. On an ambiguous create timeout, reconcile remote state before retrying;
local JSON persistence alone cannot guarantee an exactly-once external write.

## Practical constraints from the handoff

- Actual Printify-generated mockups can depend on creating the draft. Before that
  write, show local composites/placement previews and mark provider renders pending.
  After draft creation, retrieve the renders and resolve review findings before
  publication. Material revisions require renewed product approval.
- OCR and checkerboard/halo heuristics flag potential issues; they do not prove
  wording, print quality, or legal clearance. Keep the approved text authoritative
  and require visual review for uncertain results. Do not silently edit final art.
- Verify the exact Gildan provider and variants; do not borrow specifications from
  the oversized tee. Unknown IDs and unavailable variants block the draft action.
- Use explicit fee/cost inputs and show estimated standard and off-site-ad outcomes.
  Sample margins and prices are examples, not owner-selected shop settings.
- Verify production-partner, shipping, processing/readiness, return, regional, and
  disclosure requirements. Record unsupported API fields as owner setup steps.
- Preserve owner choices for colors, sizes, shipping, regions, and personalization.
  Missing material choices block external writes without blocking local preparation.
- The later publication milestone must handle a listing becoming active before
  enrichment finishes, including a reviewed failure/recovery path and read-back
  verification. Never fix a partial failure by creating another listing.

## Delivery order and verification

**First: local preflight.** Define the smallest manifest/profile and revision model,
asset inspection, review report, and exact payload previews. Use a representative
fixture, clearly labeled as a fixture. Test invalid input, text discrepancies,
transparency warnings, garment copy, pricing, and zero external writes.

**Then: one connected Printify draft.** Verify the account/catalog, persist
revision-specific product approval, upload the approved asset, create/update the
draft, retrieve mockups, and compare the saved product. Test stale/mismatched
approvals, stock/cost changes, repeat runs, ambiguous timeouts, and partial failure.
This step completes the initial useful milestone once demonstrated with an actual
approved design and configuration.

**Later: publication and Etsy enrichment.** Add the explicit publication action,
linked listing resolution, supported Etsy edits, and verification/recovery. Test
that no path can publish with missing, stale, or wrongly scoped approval. A live
test needs its own product-specific approval; documentation status cannot supply it.

Logic-bearing platform changes require matching tests under `tests/python/`.
Keep network writes mocked in automated tests; label any real account validation
separately. No finished-listing or production-ready claim is justified by a mock run.

## Repository audit — September 2, 2026

This is a static source audit, not an account or runtime inspection.

| Area | Evidence and consequence |
|---|---|
| Stack and packaging | [pyproject.toml](../../pyproject.toml): Python declared as >=3.10, with Ruff targeting 3.12; setuptools/pip, FastAPI, httpx, PyYAML, Pillow, and pytest. Use Python conventions, not the reference's illustrative TypeScript/pnpm layout. |
| Existing HomeFromWorking implementation | The August 31 commits added plans only. Their proposed `packages/commerce/`, business configuration, and demo script are absent. There is no commerce implementation to migrate. |
| Printify/Etsy clients and auth | No dedicated clients, OAuth flow, marketplace retry code, or environment-variable names found in the audited source/example configuration. Account access and credentials were not inspected. |
| Shop linkage and IDs | Connected Etsy vs custom API shop, product/listing IDs, and shipping/production-partner mappings are unverified. No POD configuration store was found; resolve these from the real accounts during integration. |
| State | [settings.py](../../packages/config/settings.py) centralizes runtime paths; the existing control plane and [ApprovalStore](../../packages/db/approval_store.py) provide persistence conventions. Keep generated assets/checkpoints under `state/`. |
| Approvals | [approval schema](../../packages/schemas/approval.py), [policy](../../packages/policies/approvals.py), and [approval endpoint](../../apps/api/approval_endpoint.py) exist. POD actions and revision binding still need explicit implementation. |
| CLI, UI, and queue | [discovery_run.py](../../scripts/discovery_run.py) demonstrates Python argparse; [API](../../apps/api/main.py) and `packages/queue/` are existing surfaces. A new POD UI or queue is unnecessary for the first workflow. |
| Images | Pillow is available in declared dependencies; [text_overlay.py](../../packages/tools/content_tools/text_overlay.py) demonstrates compositing. Dedicated print-area, alpha/checkerboard, OCR, and print-quality checks still need implementation and verification. |
| External-write testing | Existing [URL guard](../../tests/python/unit/test_url_guard.py) and [secret-scan](../../tests/python/unit/test_web_deploy_secret_scan.py) tests provide patterns. No Printify/Etsy-specific write, retry, or no-publish tests exist yet. |

## Inputs for the first real product

Collect these when needed, resolving existing account settings before asking again:

- approved PNG, exact text, and provenance/AI-assistance information;
- existing Printify product/Etsy listing IDs, if this design is already listed;
- Printify shop connection and selected Gildan blueprint/provider;
- colors, sizes, placement, and pricing/shipping choices;
- Etsy account configuration, required profiles, and production-partner mapping.

The next implementation task is local manifest/preflight preparation for that one
design. Account setup and catalog reads follow; publication is not needed to prove
the first milestone.
