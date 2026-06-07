# Booking — platform routing & managed model

> We don't build booking software. We set up + (optionally) run booking on a
> proven platform, on the client's own account. This doc is the operator's
> decision guide: which platform for which client, what each booking SKU means,
> how access/ownership works, and the compliance line.
>
> Catalog SoT: [service-catalog.md](service-catalog.md) · SLA: [client-sla.md](client-sla.md) ·
> Plan: [2026-06-06 managed-booking](../plans/2026-06-06-feat-managed-booking-on-platforms-plan.md).
> Per-platform setup: [runbooks/booking-setup-calendly.md](runbooks/booking-setup-calendly.md) ·
> [-square.md](runbooks/booking-setup-square.md) · [-acuity.md](runbooks/booking-setup-acuity.md).

## The catalog SKUs (pick-one base + modifiers)

`exclusive_group: booking_base` — pick exactly one base:

| SKU | What it is | Bill |
|---|---|---|
| `booking_connect` | Connect: embed the client's **existing** tool | $150 one-time |
| `booking_setup` | Done-for-you: we pick + configure the right platform, client manages after | $350 one-time |
| `booking_native` → **"Booking — Fully Managed"** | We set up **and run** it on the platform for the client (ongoing) | $450 + $35/mo |

Modifiers (`requires_group: booking_base`, stack on any base): `booking_deposits` ($120),
`booking_multistaff` ($150), `booking_classes` ($200), `booking_intake` ($90),
`booking_management` ($35/mo — the ongoing-management add-on for Connect/Done-for-you;
Fully Managed already includes it).

## The three paths

| Path | Platform | When |
|---|---|---|
| **Connect** | the client's existing tool | they already book somewhere real (verify it's their own account) |
| **Simple** | **Calendly** | appointments, discovery calls, estimates, consults — no payments/staff/classes |
| **Local-service** | **Square** or **Acuity** | needs payments, deposits, staff, classes, forms, reminders |

## Platform capability + routing matrix (2026)

| Need | Calendly | Square Appointments | Acuity |
|---|---|---|---|
| Deposits | full-pay only | full-prepay / card-hold (**no partial**) | **true % deposit** |
| Multi-staff | weak | **unlimited (Free)** | up to 6 (Standard) |
| Classes/group | ✗ | ✓ (Plus) | ✓ (Standard) |
| Intake forms | basic | ✓ | **rich** |
| SMS reminders | 250/seat/mo cap | **Premium only ($149)** | **Standard, no extra fee** |
| Free tier | ✓ | ✓ (pay processing) | trial only |
| Paid entry | Std $12 | Plus $49 | Standard $27–34 |

**Routing rule (tell the client which platform to buy):**
- **Deposits + classes + SMS + intake on one cheap plan → Acuity Standard (~$27–34/mo).** Default for most local-service clients.
- **Already on Square / wants POS + card-hold no-show protection → Square Plus ($49).** Only go Square **Premium ($149)** if they truly need SMS *and* won't use Acuity.
- **Just "let people book a call" → Calendly Free or Standard.**
- The **client pays the platform**; our `$35/mo` (Fully Managed / Management) is **labor only**.

> ⚠️ Don't accidentally upsell a client to Square Premium ($149) just for SMS reminders —
> Acuity Standard does SMS for ~$30. Square's "no partial deposit" also pushes deposit-heavy
> clients to Acuity.

## Access & ownership (set at kickoff → clean offboarding)

**The client owns the account** (created under their email + their card). We hold **delegated
admin** access — never a shared password.

- **Square:** client = account owner; add operator as a **team member with a custom permission
  set** (Appointments/calendar/settings) + **Authorized Representative**. Offboard = remove the
  team member.
- **Acuity:** client = owner; invite operator as a **contributor with Admin** (can do everything
  except delete the account, change owner, or change the subscription). Requires Standard+.
  Offboard = owner removes the contributor. Never share one login (concurrent logins lock out).
- **Calendly:** Teams plan; add operator as an org admin seat.

No formal agency/partner program is required for any of these.

## Compliance: SMS reminders are the platform's job (a win)

All three send appointment confirmations/reminders from **their own** numbers under **their own**
A2P 10DLC registration (Square system number; Acuity's Twilio integration; Calendly's pooled
numbers), with STOP/HELP handled by the platform. Appointment reminders are **transactional**
(a booking the customer initiated), not marketing.

- The agency does **NOT** register A2P 10DLC for platform-sent reminders.
- **Guardrail:** never wire a separate Twilio/Zapier SMS path for a client — that re-imposes
  A2P 10DLC / TCPA on us (the burden we gated off for the review-SMS lane). Use platform-native
  reminders only, and keep reminder text strictly transactional (no offers/promos).

## The `$35/mo` managed-booking retainer (what it is / isn't)

See [client-sla.md](client-sla.md#managed-booking) for the bindable scope. In short: ~2 change
requests/mo (availability, services, staff, prices, reminder copy) + a monthly no-show glance +
a booking-link/calendar-sync sanity check. **Not** a receptionist: no live/same-day response, no
answering customers, no manual rebooking, no refund/dispute handling. New modifiers are one-time
setup add-ons. The client pays the platform subscription separately.
