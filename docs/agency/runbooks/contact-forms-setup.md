# Runbook — Contact Forms & Lead Routing (`contact_forms`, $75)

> Wire a client site's contact form to real lead routing: **form → the owner's
> inbox**. The form + handler ship in the scaffold; this is the per-client config,
> test, and record.
>
> Catalog: [service-catalog.md](../service-catalog.md) · Plan:
> [2026-06-05 readiness](../../plans/2026-06-05-feat-agency-packages-go-live-readiness-plan.md).

## What ships in the scaffold (already built)
- The contact form on the client site posts to **`/.netlify/functions/contact`**
  (`packages/web/scaffold/.../src/pages/index.astro`, honeypot included).
- The handler **`netlify/functions/contact.mjs`**: persists each lead to a Netlify
  Blob (`inbound-leads`) first, then best-effort emails the owner via Resend; 303s
  to `/thanks/` either way. Native Netlify Forms is **not** used (our file-digest
  deploy doesn't trigger form detection — same reason as the BBW site).

## Scope (what `contact_forms` is vs `website`)
The `website` service includes the contact form **UI**. `contact_forms` is the
**routing backend**: this handler + the per-client delivery config + monitoring.
- ✅ **form → email** — live (below).
- ⛔ **form → SMS** — gated. Sending lead-alert SMS via our own number hits the same
  **A2P 10DLC / TCPA** gate as review-SMS. Keep `sms_enabled=False`. If a client
  wants SMS alerts, use a platform's own notifications or defer until A2P lands.
- 🔜 **CRM routing** — delivered by the `crm_setup` service; once a CRM exists, set
  `crm` on the record and route leads there.

## Per-client setup
1. **Resend sender** (once per sending domain): verify SPF/DKIM/DMARC on a
   `send.<domain>` subdomain; never send from `@resend.dev` in production. (See the
   deliverability guidance in the go-live readiness plan.)
2. **Set the client site's Netlify env** (server-side only, never in `dist/`):
   - `RESEND_API_KEY` — the Resend key
   - `LEAD_NOTIFY_EMAIL` — **the client's inbox** (where leads go)
   - `LEAD_FROM_EMAIL` — a verified `…@send.<domain>` sender
3. **Deploy the site + functions:** `netlify deploy --prod --functions netlify/functions`
   (the dist-only deploy does not ship functions).
4. **Test end-to-end:** submit the form → lands on `/thanks/`, the owner email
   arrives within seconds, and the Blob (`inbound-leads`) holds the typed record.
5. **Record it:**
   `ContactFormsSetup(product_id, notify_email, sms_enabled=False, crm="", completed_at=…)`
   via `packages/agency/contact_forms.py` (`save_contact_forms_setup`).

## Verify / monitor
- A real submission emails the owner and persists to the Blob.
- If `RESEND_API_KEY`/`LEAD_NOTIFY_EMAIL` are unset, the lead still persists (no
  email) — the function logs and still 303s. Watch for that in the client's Netlify
  function logs.

## Rollback
Unset `RESEND_API_KEY` (leads still capture, just no email), or point the form
`action` back to a no-op. The durable record is the Blob, so no lead is lost.
