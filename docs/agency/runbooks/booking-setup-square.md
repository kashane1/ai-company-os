# Runbook — Booking setup on Square Appointments (a "Local-service" path)

> Use for local service businesses that want POS/payments unification, many staff,
> and card-hold no-show protection. Routing: [booking-platform-routing.md](../booking-platform-routing.md).

## When to pick Square
- Client already uses Square for payments, or wants in-person + online payments unified.
- Needs **unlimited staff calendars** (works on **Free**) and/or **card-hold no-show fees**.
- **Free** tier = full booking + email reminders (pay processing only). **Plus ($49)** for
  multi-location/advanced + seller API/webhooks. **Premium ($149)** only if they require SMS
  reminders — otherwise prefer Acuity for SMS. **No partial deposit** (full-prepay or card-hold only).

## 0. Access & ownership
- Account under the **client's email**; client adds the card.
- Add operator as a **team member with a custom permission set** (Appointments + calendar +
  settings) and as an **Authorized Representative** (to contact Square support). Offboard = remove
  the team member; account + history stay with the client.

## 1. Done-for-you setup checklist
- [ ] **Services:** name, duration, price, category; assign to staff.
- [ ] **Staff/resources** (`booking_multistaff`): per-staff calendars, services, hours. *Making a
      team member bookable is Dashboard-only* (not API) — do it in Square.
- [ ] **Availability:** business hours, buffers, min lead time, max booking window.
- [ ] **Payments/deposits** (`booking_deposits`): require **full prepayment** OR **card-on-file for
      no-show** (Square has no partial deposit). Set the no-show/cancellation **fee** (flat /
      per-service / %) and the cancellation cutoff (default 24h; chargeable up to 14 days after).
- [ ] **Classes/group** (`booking_classes`): set capacity + recurring schedule (needs Plus).
- [ ] **Intake** (`booking_intake`): custom intake fields on the booking flow.
- [ ] **Calendar sync:** Google/Outlook.
- [ ] **Confirmations/reminders:** email on all plans; SMS only on Premium. Square Assistant
      (SMS confirm/reschedule/cancel) if on Premium.

## 2. Embed into the client's site
Square's real embed is an **account/location-specific snippet** generated in the dashboard
(Online Booking → embed code / Booking button / Advanced widget) — it is **not** URL-derivable.
Two options:
- **Default (link):** inject a "Book" button to the Square booking site:
  ```bash
  python scripts/agency/inject_booking.py --site-file <dist/index.html> \
    --provider square --booking-url https://book.squareup.com/... --product-id <id>
  ```
- **Advanced widget:** paste the dashboard-generated snippet via the raw-embed path
  (`inject_booking_html_into_file(path, embed_html)`), which injects + replaces idempotently.

## 3. Verify
- [ ] Booking URL/snippet is the **client's** Square account.
- [ ] Real test booking end-to-end; confirmation arrives.
- [ ] If payments/no-show fee on: test the prepay/card-hold and a refund.
- [ ] Record `BookingSetup(provider="square", managed=<…>)`.

## Compliance
Square sends confirmations/reminders from its **own system number** — no agency A2P 10DLC.
No separate Twilio path. Reminder text stays transactional.
