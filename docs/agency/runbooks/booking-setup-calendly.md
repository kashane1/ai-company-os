# Runbook — Booking setup on Calendly (the "Simple" path)

> Use for appointments, discovery calls, estimates, consults. No deposits-with-
> staff-and-classes — for that use Square/Acuity. Routing: [booking-platform-routing.md](../booking-platform-routing.md).

## When to pick Calendly
- 1:1 appointments / calls; no multi-staff calendars, no classes, no partial deposits.
- Free tier works for confirmations-only; **Standard ($12/mo)** for reminders + payments;
  **Teams** if you (operator) need an admin seat. SMS reminders cap at 250/seat/mo.

## 0. Access & ownership
- Create the account under the **client's email**; client adds the card.
- For managed clients: **Teams plan**, add the operator as an org admin seat. Never share a login.

## 1. Done-for-you setup checklist
- [ ] **Event type(s):** name, duration, location (phone/Zoom/in-person), description.
- [ ] **Availability:** business hours, date ranges, buffers before/after, min scheduling notice, daily cap.
- [ ] **Calendar sync:** connect Google/Outlook/iCloud (two-way).
- [ ] **Intake questions** (`booking_intake`): custom questions on the booking form + a consent checkbox if collecting phone for SMS.
- [ ] **Payments** (`booking_deposits`): connect Stripe or PayPal on the event type → "require payment to book." Calendly takes **full payment at booking only** (no partial deposit) and needs **Professional+**. If the client needs a partial deposit, route to Acuity instead.
- [ ] **Reminders/confirmations:** enable email; SMS via Workflows (watch the 250/seat/mo cap). Keep text transactional.
- [ ] **Reschedule/cancel:** include reschedule + cancel links in confirmations; set a cancellation window.

## 2. Embed into the client's site
Calendly is a copy-paste embed — fits `scripts/agency/inject_booking.py`:
```bash
python scripts/agency/inject_booking.py --site-file <dist/index.html> \
  --provider calendly --booking-url https://calendly.com/<user>/<event> --product-id <id>
```
This injects the inline widget (`widget.js` + `data-resize="true"`) idempotently.
(Popup/badge is also available if the client prefers a floating button.)

## 3. Verify (do not skip)
- [ ] Confirm the booking URL is the **owner's** account (not an aggregator/reseller link).
- [ ] Make a **real test booking** end-to-end; confirm the email/SMS confirmation arrives.
- [ ] If payments on: run a **test charge and refund**.
- [ ] Record it: `BookingSetup(provider="calendly", managed=<true for Fully Managed>)`.

## Compliance
Reminders are sent by **Calendly** on its own numbers/registration — no agency A2P 10DLC.
Never add a separate Twilio path. Keep reminder text transactional (no promos).
