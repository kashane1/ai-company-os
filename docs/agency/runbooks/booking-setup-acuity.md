# Runbook — Booking setup on Acuity Scheduling (the default "Local-service" path)

> The best all-rounder for local service: true % deposits, classes/group, rich
> intake, and SMS reminders at no extra fee. **Default for deposit-/SMS-heavy
> clients.** Routing: [booking-platform-routing.md](../booking-platform-routing.md).

## When to pick Acuity
- Client needs **partial % deposits**, **classes/group**, **rich intake forms**, and/or
  **SMS reminders** without Square Premium's $149.
- **Standard ($27–34/mo)** covers deposits + SMS + classes + up to 6 calendars. No free tier
  (7-day trial). Client pays the subscription.

## 0. Access & ownership
- Account under the **client's email**; client adds the card; choose **Standard+** (multi-user
  + SMS need Standard).
- Invite operator as a **contributor with Admin** (everything except delete account / change owner
  / change subscription). Offboard = owner removes the contributor. Never share one login.

## 1. Done-for-you setup checklist
- [ ] **Appointment types:** name, duration, price, category (these are set in the Acuity UI; the
      API is mostly read/booking-only, so this is operator work).
- [ ] **Availability:** hours, buffers, min lead time, max future window; per-calendar.
- [ ] **Staff/resources** (`booking_multistaff`): multiple calendars (up to 6 on Standard).
- [ ] **Classes/group** (`booking_classes`): capacity + recurring schedule.
- [ ] **Intake** (`booking_intake`): custom forms + T&C/consent checkbox.
- [ ] **Payments/deposits** (`booking_deposits`): connect Stripe / Square / PayPal; set a **% deposit
      (rec. 20–50%)** or fixed, or full prepay, or save-card-to-charge-later (save-card needs Stripe
      or Square as sole processor, not PayPal).
- [ ] **Calendar sync:** Google/Outlook/iCloud.
- [ ] **Reminders/confirmations:** email + **SMS** (Standard+, no extra fee); include reschedule/
      cancel links; set the cancellation cutoff.

## 2. Embed into the client's site
Acuity is a copy-paste iframe embed — fits `scripts/agency/inject_booking.py`:
```bash
python scripts/agency/inject_booking.py --site-file <dist/index.html> \
  --provider acuity --booking-url https://<biz>.acuityscheduling.com/schedule.php --product-id <id>
```
This injects the iframe + Acuity's `embed.js` (auto-resizes to content height) idempotently.
Deep-link a specific service with `?appointmentType=<id>` on the URL if desired.

## 3. Verify
- [ ] Booking URL is the **client's own** Acuity account (not an aggregator).
- [ ] Real test booking end-to-end; email + SMS confirmation arrives.
- [ ] If deposits on: test the deposit charge + a refund.
- [ ] Record `BookingSetup(provider="acuity", managed=<…>)`.

## Compliance
Acuity sends SMS via **its own** Twilio integration from an Acuity-assigned number, with STOP/START
handled by Acuity — no agency A2P 10DLC, no separate Twilio path. Reminder text stays transactional.
