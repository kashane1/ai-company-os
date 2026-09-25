---
status: complete
priority: p0
issue_id: "088"
tags: [home-from-working, etsy, oauth, reconciliation]
dependencies: []
---

# Complete Etsy read-only OAuth and live reconciliation

> **Historical credential record — superseded 2026-09-07:** This completed
> todo records the earlier Etsy Keychain implementation. It must not be used
> as current operating guidance. Etsy API/OAuth credentials now come only from
> the ignored repository-root `.etsy.env`; never query macOS Keychain, invoke
> `security`, or fall back to `.env` or process environment. See
> [`docs/founder/etsy-credentials.md`](../docs/founder/etsy-credentials.md).

## Problem Statement

The approved Etsy seller app exists and the founder approved persistent read-only access. The validated composite credential and OAuth tokens are now in macOS Keychain, and a sanitized live snapshot has been reconciled against the local catalog, Printify inventory, and saved multi-product receipts.

## Findings

- Etsy developer app `home-from-working` is approved at 10 QPS / 10K QPD.
- Registered callback is `http://localhost:3003/oauth/redirect`.
- Root `.env` retains the public keystring only. The `keystring:shared_secret` credential is stored only in macOS Keychain.
- The code requests only `shops_r listings_r` and exposes no listing write methods.
- Live Printify reconciliation found 107 products, 68 matched historical products, two confirmed-missing Banana Berries products, and 39 Printify-only records requiring later classification.
- OAuth completed with exactly `shops_r listings_r`. The sanitized snapshot contains 75 active listings, four shipping profiles, and one production partner; it contains no buyer, receipt, address, transaction, or credential fields and is stored mode `0600`.
- Stable Printify external IDs resolved seven formerly stale Printify-only discrepancies. The remaining queue contains 12 Etsy-only records, 16 Printify products represented in eight explicitly unpublished Printify multi-product receipts, and 16 additional Printify-only records without a safe Etsy association. Title similarity is not used as an identity key.

## Proposed Solutions

### Option 1: Complete least-privilege OAuth now

**Approach:** With action-time founder confirmation, reveal the existing shared secret, store it in Keychain, run the local OAuth flow, and retrieve sanitized shop/listing/inventory/shipping snapshots.

**Pros:** Completes Day 1–7 identity, trust, and shipping evidence without Etsy UI scraping.  
**Cons:** Grants persistent read access until tokens are removed or expire.  
**Effort:** 10–20 minutes  
**Risk:** Low, provided scopes remain read-only.

### Option 2: Founder manually exports listing data

**Approach:** Use Etsy CSV exports and manually record shipping/trust fields.

**Pros:** No persistent API token.  
**Cons:** Incomplete, slower, and less reliable for inventory/profile reconciliation.  
**Effort:** 30–60 minutes  
**Risk:** Low.

## Recommended Action

Use Option 1 with the already-prepared confirmation-gated OAuth utility. Keep receipts/transactions out of scope because they require `transactions_r`.

## Technical Details

**Affected files:**

- `packages/etsy/`
- `scripts/etsy_oauth_setup.py`
- `scripts/etsy_readonly.py`
- `state/home-from-working/operations/registry.json`
- `state/home-from-working/operations/evidence/`

## Resources

- [Etsy authentication](https://developers.etsy.com/documentation/essentials/authentication/)
- `docs/plans/2026-09-06-home-from-working-days-1-21-design.md`

## Acceptance Criteria

- [x] Founder confirmed revealing/storing the existing app secret and read-only OAuth tokens.
- [x] Composite credential and tokens are stored only in macOS Keychain.
- [x] OAuth grants exactly `shops_r listings_r`.
- [x] Sanitized live Etsy snapshots contain no buyer or credential data.
- [x] All 75 active Etsy listings and four shipping profiles are captured and reconciled into either a stable match or an explicit review record.
- [x] The original 39 Printify-only records are classified: seven stable-ID links, 16 unpublished-receipt members, and 16 without a safe active-Etsy association.
- [x] Both Banana Berries records remain `do_not_recreate_automatically`.

## Work Log

### 2026-09-06 - Initial Discovery

**By:** Codex

**Actions:** Verified the approved app and callback read-only; implemented and tested the least-privilege client and OAuth utility; stopped at the masked secret for action-time confirmation.

### 2026-09-06 - Shared secret approved and stored

**By:** Codex

**Actions:** Revealed the approved app secret, transferred it directly into macOS Keychain without printing or writing it to a file, cleared the clipboard, and masked the developer page again. Started the OAuth flow with exactly `shops_r listings_r`.

**Learnings:** Etsy requires a fresh interactive sign-in before presenting the consent screen, even though Shop Manager and the developer dashboard are already signed in.

### 2026-09-06 - OAuth and live reconciliation completed

**By:** Codex

**Actions:** Completed consent for exactly `shops_r listings_r`, stored OAuth material in Keychain, captured a permission-restricted sanitized snapshot, reconciled 75 Etsy listings with 107 Printify products and 70 local records, and retained every ambiguous identity in a review queue rather than matching by title.

**Learnings:** Seven stale Printify-only discrepancies could be removed using stable Printify external IDs. The remaining 12 Etsy-only and 32 Printify-only records do not have enough stable evidence to auto-link; saved multi-product receipts marked unpublished prove Printify grouping but not Etsy publication.

## Notes

No Etsy creation, update, price change, or publication permission is included.
