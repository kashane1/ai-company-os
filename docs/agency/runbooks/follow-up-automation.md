# Runbook — Automated Follow-Up (`follow_up_automation`, $125 + $39/mo)

> Email-first lead follow-up built in the client's CRM (default **HubSpot**): an
> instant new-lead reply, a 2-day reminder, and owner task reminders. **SMS is
> deferred** unless the client is on a compliant SMS-capable platform.
>
> Catalog: [service-catalog.md](../service-catalog.md). Depends on
> [crm-setup.md](crm-setup.md). Record: `packages/agency/follow_up.py`.

## Channels
- ✅ **Email + task reminders** — live, on HubSpot (or the client's CRM).
- ⛔ **Auto-text (SMS)** — **deferred**. Sending SMS via our own number re-imposes
  the A2P 10DLC / TCPA burden on us. It's enabled **only** on a compliant
  SMS-capable platform (**GoHighLevel**) where the platform / client owns the A2P
  registration. On HubSpot it stays email-first until the client upgrades. **Never
  wire our own Twilio** for client follow-up. (`sms_enabled=True` is rejected unless
  `platform` is SMS-capable.)

## Done-for-you setup — HubSpot (default)
0. Requires `crm_setup` done first (the pipeline + email templates seed this).
1. **Instant new-lead reply:** workflow triggered on new contact/lead → send the
   "new-lead reply" email template immediately.
2. **2-day reminder:** if no reply/stage change in 2 days → send the follow-up
   template; create an **owner task** to call within 1 business day.
3. **Light nurture (optional):** a day-5 check-in email for unconverted leads.
4. **Stop conditions:** exit the sequence on reply / stage = Won or Lost (don't keep
   emailing a closed lead).
5. **Record it:** `FollowUpSetup(product_id, platform="hubspot", email_enabled=True,
   sms_enabled=False, steps=[…], completed_at=…)` via `save_follow_up_setup`.

## SMS upgrade path — GoHighLevel
If the client wants missed-call text-back or SMS follow-up, move follow-up to
**GoHighLevel** (see [crm-setup.md](crm-setup.md) upgrade path) and register A2P
**in-platform under the client's business**. Then `platform="gohighlevel",
sms_enabled=True` is allowed (the platform is the sender; compliance stays off us).

## Monthly (recurring $39/mo)
`retainer_ops` plans a `review_follow_up` action each month: check open-rate / reply
signals, tune copy + timing, prune dead steps, confirm stop conditions still fire.
Keep all messages transactional and accurate.

## Boundaries
- The client owns the CRM + sequences; we build + tune.
- We do not answer leads for the client or run our own SMS. Email content stays
  truthful and on the client's voice.
