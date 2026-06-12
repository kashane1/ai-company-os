# Outreach Lane Client Status

_Updated: 2026-06-12T05:56:35Z_

Human-gated outbound lane. This list drafts, tracks, and schedules next actions; it does not send email, SMS, Instagram, or Facebook messages.

## Summary

- Total deployed Cohort A prospects: 15
- Ready to send: 5
- Needs bespoke rebuild before outreach: 0
- Sent / waiting: 8
- Follow-up due: 0
- Replied: 0
- Blocked / recheck needed: 2

## Operator List

| Status | Business | City | Type | Channel | Next action | URL | Draft |
|---|---|---|---|---|---|---|---|
| ready_to_send | Fade Factory ATL | Atlanta | barber_shop | instagram_dm | Review draft, personalize one line, send manually via instagram_dm | [site](https://fade-factory-atl.netlify.app) | [draft](state/prospects/sites/ChIJf7r9agAF9YgRd7ObV7mwRpE/outreach.md) |
| ready_to_send | Kelby’s Mobile Servicing | Atlanta | auto_repair | sms_or_call | Review draft, personalize one line, send manually via sms_or_call | [site](https://kelbys-mobile-atlanta.netlify.app) | [draft](state/prospects/sites/ChIJZ28uCZwF9YgRZIvNLyMvRVA/outreach.md) |
| ready_to_send | Envy Nails Uptown | Minneapolis | nail_salon | email | Review draft, personalize one line, send manually via email | [site](https://envy-nails-minneapolis.netlify.app) | [draft](state/prospects/sites/ChIJYySi2H4n9ocR7ubDB1vftGw/outreach.md) |
| ready_to_send | Nghia's Automotive Services Center | Minneapolis | auto_repair | facebook_dm | Review draft, personalize one line, send manually via facebook_dm | [site](https://nghias-auto-minneapolis.netlify.app) | [draft](state/prospects/sites/ChIJV7k2AHwxs1IRnqq-1Yd3OsU/outreach.md) |
| ready_to_send | Bui Phong Bakery | San Jose | bakery | instagram_dm | Review draft, personalize one line, send manually via instagram_dm | [site](https://bui-phong-bakery-sanjose.netlify.app) | [draft](state/prospects/sites/ChIJERIBVTIzjoARlf74SIRNMR4/outreach.md) |
| sent | Legends Barbershop | Albuquerque | barber_shop | email | Wait for reply or log follow-up when due | [site](https://legends-barbershop-abq.netlify.app) | [draft](state/prospects/sites/ChIJT0nDIDkLIocRZbWz7aqzURM/outreach.md) |
| sent | King Auto Repair | Charlotte | auto_repair | email | Wait for reply or log follow-up when due | [site](https://king-auto-repair-charlotte.netlify.app) | [draft](state/prospects/sites/ChIJT1ZBJ8MfVIgRLQIVz8_sNNA/outreach-with-mockup.md) |
| sent | Skyline Nails & Spa | Fort Worth | nail_salon | sms | Wait for reply or log follow-up when due | [site](https://skyline-nails-fortworth.netlify.app) | [draft](state/prospects/sites/ChIJIYKyBuFzToYRpKQSc6Yf9ks/outreach.md) |
| sent | BarberStarz Barbershop | Fresno | barber_shop | sms | Wait for reply or log follow-up when due | [site](https://barberstarz-fresno.netlify.app) | [draft](state/prospects/sites/ChIJPeXznSlclIARPWsj23OiX1k/outreach.md) |
| sent | Bich Nga Hair Design | Houston | beauty_salon | sms | Wait for reply or log follow-up when due | [site](https://bichnga-hair-houston.netlify.app) | [draft](state/prospects/sites/ChIJWdCar2u_QIYRXWTCx8cP65Q/outreach.md) |
| sent | Duval Notary & Apostille Services | Jacksonville | notary | email | Wait for reply or log follow-up when due | [site](https://duval-notary-jacksonville.netlify.app) | [draft](state/prospects/sites/ChIJU6RYyvu55YgRkpkmk2MfVdo/outreach.md) |
| sent | Café Ollama | Kansas City | coffee_shop | sms | Wait for reply or log follow-up when due | [site](https://cafe-ollama-kansascity.netlify.app) | [draft](state/prospects/sites/ChIJE-YLqjPxwIcRBZnvjsRRrew/outreach.md) |
| sent | Nevada Auto Center | Las Vegas | auto_repair | sms | Wait for reply or log follow-up when due | [site](https://nevada-auto-center-lasvegas.netlify.app) | [draft](state/prospects/sites/ChIJHbC9qJHDyIARr0vAZJaxwP8/outreach.md) |
| blocked | Magic Repair Okc | Oklahoma City | auto_repair | recheck_has_site | Recheck owned-site signal before outreach | [site](https://magic-repair-okc.netlify.app) | [draft](state/prospects/sites/ChIJR64Sx7oQsocRRhZ8QZ7wd1k/outreach.md) |
| blocked | FIVE STAR FINANCIAL SERVICES | San Jose | accountant | recheck_has_site | Recheck owned-site signal before outreach | [site](https://five-star-tax-sanjose.netlify.app) | [draft](state/prospects/sites/ChIJu5fd7jfNj4ARk4-FrETV3x4/outreach.md) |

## Manual Logging

After sending by hand, run:

```bash
python scripts/agency/outreach_lane.py log --place-id <PLACE_ID> --channel email --outcome sent --next-follow-up 2026-06-12 --notes "sent manually"
```

Allowed outcomes: blocked, do_not_contact, follow_up_due, left_voicemail, lost, no_answer, replied, sent, won
