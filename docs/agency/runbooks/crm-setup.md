# Runbook — CRM Setup (`crm_setup`, $250)

> Stand up a clean CRM the owner can actually run. **Default: HubSpot Free**
> (lowest friction for small businesses). **GoHighLevel** is the recommended paid
> upgrade when a client needs SMS-heavy / advanced automation.
>
> Catalog: [service-catalog.md](../service-catalog.md). Record:
> `packages/agency/crm_setup.py` (`save_crm_setup`).

## Platform choice

| Need | Use |
|---|---|
| Clean pipeline, lead stages, email templates, form routing — most small businesses | **HubSpot Free** (default) |
| SMS-heavy follow-up, missed-call text-back, automated reminders, reputation/review campaigns, unified ops dashboard | **GoHighLevel** (paid upgrade) |
| Client already standardized on Zoho / Pipedrive | match them (supported, runbook-by-analogy) |

Standardizing on HubSpot Free keeps delivery repeatable and the client's cost at
$0; reach for GoHighLevel only when the client's needs (esp. compliant SMS)
justify the paid platform — and there the **platform owns the A2P 10DLC**
registration, not us.

## Done-for-you setup — HubSpot Free (default)

0. **Account & access:** create the HubSpot account under the **client's email**;
   add the operator as a user. Client owns the account (clean offboarding).
1. **Pipeline + lead stages:** one deal pipeline with the default stages
   (`New lead → Contacted → Quoted → Won → Lost`; override per business).
2. **Contact properties:** the fields the business actually uses (service needed,
   source, address/service area, preferred contact, budget if relevant).
3. **Form routing:** connect the site's leads into HubSpot. Options:
   - embed a HubSpot form on the site (HubSpot captures directly), **or**
   - keep the `contact_forms` function and forward leads to the client's HubSpot
     inbound address / via the HubSpot Forms API.
   Then set the `contact_forms` record's `crm="hubspot"`.
4. **Email templates:** 2–4 reusable templates (new-lead reply, quote follow-up,
   thanks/won). These also seed the `follow_up_automation` workflows.
5. **Client handoff doc:** a one-pager — how to log in, where leads land, how to
   move a deal through stages, how to send a template. Save its path/URL on the
   record.
6. **Record it:** `CrmSetup(product_id, platform="hubspot", pipeline_name, stages,
   handoff_doc, completed_at)` via `save_crm_setup`.

## Upgrade path — GoHighLevel (when SMS / advanced automation is needed)

When a client wants SMS follow-up, missed-call text-back, or a unified marketing
dashboard, set up **GoHighLevel** instead (or migrate): pipeline + automations +
messaging in one place. Register the A2P 10DLC brand/campaign **inside GHL under
the client's business** — the platform/client is the sender, so the SMS
compliance burden stays off us (the same principle as platform-sent booking
reminders). Record with `platform="gohighlevel"`.

## Boundaries
- The client owns the CRM account and data; we build + hand off.
- This service is the **setup**. Ongoing sequence changes belong to
  `follow_up_automation` (recurring). See
  [follow-up-automation.md](follow-up-automation.md).
