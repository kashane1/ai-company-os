---
status: open
change_id: printify-ebay-crosslisting
owner: founder
last_reviewed: 2026-09-11
---

# Printify to eBay: catalog cross-listing process

**Status:** Process designed; no inventory refresh, store connection, product copy, listing creation, publication, or scheduled run performed. This is an operated workflow and implementation specification, not an installed executable bulk publisher. The owner requested an overview before approving exactly one eBay listing as a test. Later catalog publication requires a separate decision.

**Goal:** Account for every currently published HomeFromWorking Printify product, prepare accurate eBay listings with varied lead photos, and publish only the exact approved subset.

**Architecture:** Use supported Printify reads for inventory and verification, native browser Copy to another store for product preservation, and the native Printify eBay integration for publication and order linkage. Use supported browser controls for mockup ordering. Maintain a resumable local manifest and receipts under `state/home-from-working/ebay/`. No private browser endpoints or new custom order router.

**Tech stack:** Existing Python Printify client and snapshot conventions, JSON manifests, existing shared approval service when automated, and a supported signed-in browser. Browser sign-in does not establish that Printify is already connected to the seller account.

## Decisions and alternatives

Recommended: one eBay fixed-price listing per design and product type, with that product's supported size/color variants. An Etsy tee/hoodie/crewneck group becomes up to three eBay listings, provided all three are verified as currently offered. The pilot means ONE of these listings, not an entire group. Existing mugs, bags, posters, and other published formats remain in scope; do not manufacture additional formats simply to diversify photos.

Printify documents Multi-Product Listings as an Etsy feature. eBay variation listings support similar products in eligible categories; this does not establish that an Etsy mixed-product group can be copied intact. A tee, hoodie, and mug should not be treated as interchangeable eBay variants. Even related garments require category and variation validation. We have no evidence that mixed-product eBay listings would outperform separate listings.

Alternatives considered:

| Approach | Benefit | Limitation |
| --- | --- | --- |
| Native Printify integration and separate product listings | Reuses existing fulfillment; clear matching photos and categories | Browser steps remain; exact copy and image behavior must pass the pilot |
| Custom eBay API listings and custom fulfillment mapping | More control over listing construction | Additional credentials, category validation, order routing, and duplicate-prevention work before any benefit is proven |
| Manually combine different product types into eBay variations | Superficially resembles the Etsy layout | Category/policy uncertainty and unsupported native group transfer; excluded from this process |

## Evidence available now

The September 6 saved Printify snapshot contains 107 visible products, 95 with external links. These are historical inventory counts, NOT a current eligible listing total. `visible` and `external.id` alone do not prove a listing is live today. The 85-record local shirt catalog also includes historical configurations and unresolved records.

The saved Wombat 12-product group receipt describes an unpublished pilot. A local receipt or an unlinked component must not be mistaken for an already-published offer. Public Printify product reads do not supply authoritative Multi-Product Listing membership. Verify ambiguous groups through Printify's supported browser and the source marketplace's current listing/variant state.

Reusable local interfaces:

- `packages/pod/runner.py`: `PrintifyClient.iter_products()` and `get_product()` for source inspection. Inspect its shop-selection behavior before targeting another shop; never let the Etsy shop ID stand in for the destination eBay shop.
- `scripts/home_from_working_printify_snapshot.py`: sanitized inventory pattern. Its summary omits individual SKUs and images; a detailed manifest needs additional fields.
- `packages/pod/template.py`: `mockup_signature()` for preservation checks.
- `scripts/pod_catalog.py`: `_mockup_summary()` as a camera/color parsing reference; historical catalog data is not live authority.
- `docs/founder/printify-shirt-workflow.md` and `printify-multi-product-workflow.md`: native copy preservation and group boundaries.
- `packages/home_from_working/registry.py`: conservative reconciliation patterns. Do not reinterpret Etsy group links as eBay links.

## Phase 1: discover and reconcile, read-only

At the approved start of the process:

1. Confirm the exact Printify source shop(s), eBay seller identity, marketplace, and destination Printify shop if already connected. Start with HomeFromWorking source shop `28779955`; discover other shops without silently adding unrelated stores to scope. The owner already has seller history, so do not create a dummy eBay listing.
2. Page through the complete Printify source inventory. Capture observation time, pagination completeness, IDs, external links, product type/blueprint/provider, full enabled variants, artwork/placement, selected images, and source prices. Save a new run directory; never overwrite old evidence.
3. Establish current published status using marketplace state and group membership as necessary. For each active group, resolve every currently offered component/variant. Draft-only additions remain excluded. Saved but unpublished changes do not become the approved source configuration automatically: record and resolve any mismatch with the live offer.
4. Read existing eBay listings, drafts, seller limits, and the local mapping ledger. Compare destination IDs/SKUs plus design, blueprint, artwork placement, and offered variants. A changed title or hero photo does not make an identical item a new product.
5. Produce an accounting report: source records examined; active source listings; offered component products; ready destination candidates; already listed; draft-only/inactive; unavailable; unsupported; and unresolved. Every source gets an explicit outcome and reason. Incomplete pages or ambiguous identity prevent an assertion of complete coverage.

If Etsy API reads are needed, follow `docs/founder/etsy-credentials.md`; its credentials come only from repository-root `.etsy.env`. Printify retains its existing credential contract. Never collect credentials from the browser or put tokens in manifests.

## Phase 2: construct the queue and lead-photo plan

Normalize each candidate to `(source_shop_id, source_product_id, destination_shop_id)`. Maintain a second semantic duplicate check for the same sellable design/product configuration under different source IDs. Ambiguous duplicates require review; never silently merge distinct designs or publish duplicates.

Default photo interpretation, pending the owner's optional clarification: vary both the product types across the publishing queue and the accurate provider mockup styles within each type. Rotation means different lead photos across listings at creation. It does not mean scheduled photo changes on a live listing or geometric rotation of an image.

Deterministic queue algorithm:

1. Partition eligible candidates by actual product type. Within each bucket, sort by normalized design identity then stable source product ID. Use an explicit product order: tee, hoodie, crewneck, mug, tote, poster, other types sorted by name. Empty buckets are skipped.
2. Emit one candidate from each nonempty bucket in turn until all eligible candidates are included. This balances the initial work queue; it cannot control how eBay later sorts search results or the seller's storefront.
3. For each candidate, classify existing provider images as front/product, model/lifestyle, folded/flat lay, or another accurate product-specific view. Inspect questionable classifications rather than trusting a URL label. Exclude unavailable/unoffered colors, incorrect artwork, unreadable designs, misleading crops, unrelated products, and low-resolution assets.
4. Choose the least-used eligible image style within that product type using already persisted assignments; break ties by a fixed style order, then image identity. Prefer an offered color with strong design contrast. Rotation never outranks accuracy or legibility. If only one image passes, use it and log the fallback; if none pass, hold the candidate for review.
5. Persist the selected hero, full ordered gallery, exact asset URL/identity and hash where available, represented product/color/variants, style, reason, and algorithm version. Reuse this assignment on resume. Adding another candidate must not reshuffle previously assigned images.

A tee listing always leads with that tee; a hoodie listing with that hoodie. Do not use a hoodie photo as the lead for a shirt-only listing. The gallery includes only offered products, useful alternate/color views, and accurate details. Put sizing/care explanations in listing content or supported fields; do not blindly copy Etsy promotional or text-overlay cards into the eBay photo gallery. eBay's picture policy prohibits added borders, watermarks, marketing text, and inaccurate depictions. Use native high-resolution provider images meeting current requirements. No new AI artwork or lifestyle-image generation is part of this initial process.

## Phase 3: prepare each listing's review packet

Each candidate packet must contain:

- Source identity and proof of current publication; source group identity when applicable; precise product type and provider.
- Proposed eBay category, required item specifics, condition, product-specific title of at most 80 characters, and accurate description. Preserve design meaning while removing Etsy-only group copy and references to products absent from this listing.
- Enabled and available variants only, including IDs, exact color/size names, price/cost, and source SKUs. No inferred cross-product mapping by size/color alone.
- Ordered gallery/contact sheet with the chosen hero marked and mapped to an offered variant.
- Proposed destination price ladder and shipping policy, current product and shipping costs, actual applicable eBay fees, insertion/listing allowance impact, and estimated contribution for every variant. Include all fee bases and assumptions; do not hardcode Etsy margins or assume a free listing allowance.
- Shipping destinations, truthful item location, handling time allowing production, and return policy matching the account and fulfillment arrangement. Start with a proposed US domestic scope for review; do not alter account-wide policies. A free-shipping workaround must include the cost in the proposed economics and may not silently change approved prices.
- Seller item/value capacity calculated using proposed quantities across all enabled variants, not simply counting parent listings. Validate category variation limits and actual account allowance. Set an explicit conservative quantity per variant for the pilot; never assume unlimited POD quantity is acceptable.
- Source configuration fingerprint, destination identity if a draft exists, semantic duplicate decision, readiness state, blockers, and the exact planned mutation list.

The owner reviews the exact destination pricing; the process does not change source Etsy prices. Default to no optional promoted listings, paid upgrades, subscriptions, or unrelated policy changes.

Printify documents integration-created defaults including 30-day domestic returns with seller-paid return postage. Verify the actual policy attached to the pilot and expose the potential cost in the packet; Printify's production refund coverage must not be assumed to cover all eBay returns. Printify also documents limitations selecting custom shipping policies during publication. Any necessary later eBay policy reassignment must be explicit in the approved mutation list, not an improvised account-wide change.

## Phase 4: one-listing pilot, only after approval

**Approval unit:** one identified design on one product type, one destination eBay seller/shop, one review revision, maximum one new eBay item ID. The rest of the queue remains pending even if the pilot succeeds. Approval of the general workflow does not authorize full-catalog publication.

The initial approval can authorize preparation of one selected candidate through its draft review. If the request explicitly approves publication of an already presented exact packet, carry out that scope without asking again. If the price, gallery, category, variants, or policies are not yet concrete, prepare them before requesting the final publication decision. Never treat an unnamed approval as permission to publish arbitrary prices or an entire three-product design group.

Pilot operations:

1. Read the packet and refresh its source/destination facts. Reject stale or changed material fields. Acquire a per-candidate lock and reconcile existing destination state.
2. If necessary, use the native Printify connection flow for the exact existing eBay account within the pilot authorization. Record any integration-created payment/return/shipping policy IDs and settings; halt if connecting requires broader unapproved changes. Inspect the destination's order approval/fulfillment settings without silently changing them.
3. Use native **Copy to another store** once for the selected underlying product, into the eBay-connected Printify shop. This is distinct from same-shop Duplicate. Printify documents that copying does not automatically publish to the destination and can take several hours. Inspect the currently offered controls, allow copying to finish, confirm it has not published to eBay, and reconcile the new Printify product ID before editing. Do not require a particular internal UI status label or repeat the copy while it is pending. If grouped components cannot be copied individually through supported controls, stop and report the concrete limitation; do not dismantle the Etsy group or reconstruct artwork through an undocumented route.
4. Record the destination Printify product ID, newly assigned variant SKUs, and source-to-destination mapping. Verify blueprint/provider, full print areas including neck layers, artwork placement, variant enablement, source prices prior to approved destination adjustments, and mockups. A new product ID/SKU is expected; exact SKU reuse is not a preservation requirement.
5. Apply approved destination copy, prices, category, variants, and image selection using supported controls. Prefer setting the hero on the destination Printify product before publication. Verify the saved draft state and capture its review URL.
6. With exact publication approval, publish this product once through Printify. Do not select multiple rows. Treat publication as potentially immediately public. A timeout leaves the candidate `publish_unknown`; inspect Printify and eBay for the item before considering another attempt.
7. Read back the eBay item and check title, description, category, prices, shipping, variant availability, matching variant images, and lead gallery photo. Native hero ordering is a pilot acceptance check, not an assumed capability. If supported destination controls cannot produce the approved image order, pause and report it.
8. Record exactly one gallery owner: `printify` by default, or `ebay` for an explicitly approved eBay-side gallery. If a custom eBay-side gallery edit was explicitly in the approved packet, apply it and retain its manifest. Printify documents a minimum three-minute gap before another Printify update after an eBay edit. For an eBay-owned gallery, exclude mockups from later Printify publications; for a Printify-owned gallery, update images only through that destination product. Always recheck the result. Do not automatically republish merely to test whether an edit will survive.
9. Save the eBay item ID/URL, destination Printify ID, variant/SKU mapping, before/after evidence, exact approval reference, and verification results. Stop after one item.

Publication proves the listing can be created; it does not prove an order was fulfilled correctly. Check available integration/linkage evidence now. Observe the first legitimate order when authorized, recording ordered variant → destination Printify variant, import, production, tracking, and eBay tracking state. Do not fabricate a sale or place a self-purchase to test the workflow. A paid test order needs its own explicit authorization. Printify documents that eBay order import can take up to 24 hours; do not manually duplicate an order while import is unresolved.

## Persistence, retries, and approval enforcement

Future runs write beneath `state/home-from-working/ebay/<run-id>/`: `inventory.json`, `groups.json`, `candidates.json`, `review/<candidate>.json`, contact sheets, and append-only event/receipt records. Maintain a durable mapping index across runs, not just a new per-run list. Store no customer or credential data in planning manifests.

Candidate states: `needs_review`, `ready`, `draft_intent`, `draft_unknown`, `draft_created`, `publish_approved`, `publish_intent`, `publish_unknown`, `published_verified`, `already_listed`, `excluded`, `failed`. Order validation is a separate field so a listing cannot be mislabeled fully fulfillment-tested.

Before each external mutation, persist intent and identifiers. On timeout or crash, reconcile before any retry. One owner/process holds the candidate lock. Discovery reads can retry with bounded backoff; mutations never retry blindly. A material revision invalidates the previous approval. A one-listing approval remains bound to its candidate and cannot be reused for another source product, alternate draft, or batch. If a listing has become live but verification fails, record the problem and stop; do not delete/recreate it, end listings, cancel orders, or refund buyers without authorization.

There is no eBay-specific publisher/gate in the existing repository. Before unattended execution exists, add a dedicated publication action using the shared approval service, not `pod_draft_update`. The automated gate must verify destination identity, revision digest, one-candidate scope, publication budget, and prior/unknown receipts. Do not fabricate approval records or let a local `approved: true` flag grant authority. In the initial operated pilot, enforce the same boundaries from the owner's explicit decision and save the decision reference with the receipt.

## Optional implementation after the operated pilot

Use the pilot's measured supported behavior before writing browser automation around it. Keep the first implementation small:

| Work | Proposed files | Required verification |
| --- | --- | --- |
| Detailed discovery normalization and published/group evidence | `packages/home_from_working/ebay.py`, `scripts/home_from_working_ebay.py` | Unit fixtures covering full pagination, inactive sources, draft-only group members, live-versus-saved changes, and unsupported categories |
| Queue, deduplication, gallery assignments and manifest export | Same module/CLI; reuse read-only Printify helpers | Determinism, stable resume, no omitted records, correct product/color images, missing metadata, equivalent duplicate source products, every variant mapped uniquely |
| Dedicated approval and durable mutation receipts | `packages/policies/ebay.py` plus existing approval service integration | Wrong shop, stale revision, scope expansion, unknown prior publication, concurrent attempt, and second item all rejected |
| Bounded native browser operation and readback | `skills/adapters/codex/printify-ebay-listing.md` after behavior is verified | One draft and one item only; accurate variants/gallery; retry reconciliation; no source mutations |

Logic-bearing changes require corresponding tests under `tests/python/unit/`, such as `test_home_from_working_ebay.py` and `test_ebay_policy.py`. Write failing tests for these behaviors, implement the minimum required code, and run the targeted suite. Offline tests must prove a default planning invocation performs zero writes and that a missing approval cannot reach the publisher. Local tests do not authorize a live pilot. No executable CLI or adapter described in this section has been created yet.

## Review and rollout decision

Pilot acceptance: exactly one eBay item; correct actual product and approved hero; correct every offered variant and SKU mapping; approved economics and policies; no duplicate; source Etsy/Printify configuration preserved; receipt sufficient to resume; all other candidates unprocessed. Report publication checks separately from pending real-order evidence and from sales performance.

After the owner reviews the pilot, prepare a small exact batch with a separate approval. Process sequentially and stop on a mapping, pricing, gallery, or publication error. Continue eventual catalog coverage through explicit receipts and an exceptions list. Image variety is a merchandising choice, not a promise of higher conversion. No recurring automation or automatic catalog rollout is scheduled by this document.

Ongoing operation must account for stock: Printify documents that its eBay integration does not automatically update variant availability. At each authorized maintenance run or stock notification, refresh provider availability and the live eBay variants, propose the necessary inventory update, and use the minimum supported selective publication. Review bundled fields carefully: the variant/SKU selection may include prices, so preserve the approved destination price ladder and mappings. Recheck the gallery and availability afterward. Replenishing sold-out eBay quantities also needs deliberate provider/limit checks. The one-listing launch approval is not a standing authorization to change the entire catalog, and this document does not start a stock monitor. Include who will handle stock notifications and legitimate order exceptions in the pilot handoff.

## Official references checked September 11, 2026

- [Printify eBay connection](https://help.printify.com/hc/en-us/articles/4483617199761-How-can-I-connect-my-eBay-US-store)
- [Printify copying products between stores](https://help.printify.com/hc/en-us/articles/4483625856017-How-do-I-duplicate-products-in-Printify)
- [Printify Multi-Product Listings on Etsy](https://help.printify.com/hc/en-us/articles/45606975744529-How-can-I-create-a-Multi-Product-Listing-on-Etsy)
- [eBay variation listings](https://www.ebay.com/help/selling/listings/creating-managing-listings/creating-listings-variations?id=4150)
- [eBay duplicate listings policy](https://www.ebay.com/help/policies/listing-policies/duplicate-listings-policy?id=4255)
- [eBay picture policy](https://www.ebay.com/help/policies/listing-policies/picture-policy?id=4370)
- [Printify eBay editing and synchronization](https://help.printify.com/hc/en-us/articles/4483615851025-Why-did-the-product-details-I-updated-in-eBay-revert-back-to-their-previous-state)
- [Printify eBay publishing limitations](https://help.printify.com/hc/en-us/articles/4483625269393-Why-can-t-I-publish-my-products-to-eBay-US)
- [Printify eBay seller considerations](https://help.printify.com/hc/en-us/articles/10864541774097-What-should-I-keep-in-mind-when-selling-on-eBay-US)
- [Printify eBay order-import timing](https://help.printify.com/hc/en-us/articles/25599678604433-Why-hasn-t-my-eBay-order-imported-into-Printify-yet)
- [Printify eBay shipping policies](https://help.printify.com/hc/en-us/articles/4483637044241-How-can-I-set-up-shipping-with-eBay-US)
- [Printify eBay selling limits](https://help.printify.com/hc/en-us/articles/4483608584593-What-are-eBay-selling-limits-and-how-can-I-increase-them)
- [Printify out-of-stock synchronization](https://help.printify.com/hc/en-us/articles/4483616024721-What-happens-when-some-product-variants-go-out-of-stock)
- [Printify selective publishing](https://help.printify.com/hc/en-us/articles/4483629961489-How-do-I-use-selective-publishing-on-my-sales-channels)
