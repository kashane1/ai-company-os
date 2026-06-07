# Client SLA & Turnaround

> What Better Business Web commits to, and what's on Google's / a registrar's
> clock (not ours). The whole point of this doc is the **two-bucket split** —
> firm commitments we control vs. best-effort ranges we don't — so a client never
> blames us for Google's queue.
>
> Pairs with: [service-catalog.md](service-catalog.md) · [client-lifecycle.md](client-lifecycle.md) ·
> [domain-dns-runbook.md](domain-dns-runbook.md) · [go-live-checklist.md](go-live-checklist.md).
> Day-range research + sources: [the go-live readiness plan](../plans/2026-06-05-feat-agency-packages-go-live-readiness-plan.md).

## The core principle

Every timeline promise goes in **one of two buckets**. Never blur them.

- **Bucket 1 — we control it → firm date.** Site build, preview link, revisions,
  launch, DNS config, mailbox creation. The "previewed before you pay" model
  already de-risks quality — the only promise that carries time-risk is
  *time-to-preview*, and it's conditional on a complete intake.
- **Bucket 2 — Google / a registrar controls it → range, never a hard date.** GBP
  verification, email propagation, domain transfers, DNS propagation. We submit
  correctly on day one, monitor, and fix rejections — but we cannot accelerate a
  Google review queue or an ICANN lock.

## Turnaround cheat sheet

| Item | Realistic | Worst-case | Controlled by |
|---|---|---|---|
| Preview link (after complete intake) | 2–5 business days | — | **Agency** |
| Revisions (per package limit) | 1–3 business days/round | — | **Agency** |
| Production site live (after content sign-off) | ~48 hours | — | **Agency** |
| DNS records configured + submitted | 1 business day | — | **Agency** |
| Business email mailboxes created + MX/SPF/DKIM/DMARC set | 1 business day | — | **Agency** |
| DNS propagation | a few hours | 24–48h | TTL / resolvers |
| Email fully reliable globally | <1 business day | 48–72h | DNS + Google |
| **Google Business Profile verification** | **5–14 business days** | ~21 days (re-submit) | **Google** |
| Domain transfer (between registrars) | 5–7 days | + 30–60-day lock | Registrar / ICANN |

Notes that set these numbers:

- **GBP** in 2026 defaults to **video verification** (5–14 business days). Exact,
  NAP-consistent address details speed the queue; tell the client to wait the full
  14 days before re-requesting a code (re-requesting early resets it).
- **Email**: Google's official ceiling is 48–72h; in practice mail flows within an
  hour, reliably within a few hours — but publish DKIM (`google._domainkey`) or it
  stays off.
- **Domain**: changing the registrant contact on a freshly registered domain
  triggers ICANN's **60-day transfer lock** (moving to 30-day through 2026, not yet
  uniform — quote 60). No registrar can override it.

## Per-package SLA

All packages start with a free preview; the clocks below start at **content
sign-off** (the client has approved the preview and provided all intake materials).

- **Package A — Presence:** site live ~48h after sign-off; email live within 1
  business day after DNS access; **GBP verification 5–14 business days (Google's
  clock).**
- **Package B — Presence + Capture:** A, plus booking embedded within 1 business
  day of receiving the client's booking-provider link. *Reviews:* Google review
  link + request template + cadence are delivered now; **live review-request SMS is
  not active yet** (pending A2P 10DLC / TCPA compliance — see
  [review-sms-consent-addendum.md](compliance/review-sms-consent-addendum.md)).
- **Package C — Presence + Capture + Growth:** B, plus local-SEO pages and a promo
  landing page within the first build cycle; **monthly reporting** begins the first
  full calendar month after launch; **Google Ads** is set up after the client
  connects their Ads account and approves a daily + monthly budget cap (ads go live
  only after that approval; spend stays in the client's account).

## Managed booking

"Booking — Fully Managed" ($450 setup + $35/mo) and the "Booking Management" add-on
($35/mo) are delivered on a **proven platform** (Calendly / Square / Acuity), set up under
the **client's own account** with us holding delegated admin access. We do not build custom
booking software. Routing + setup: [booking-platform-routing.md](booking-platform-routing.md).

**The $35/mo covers (labor only):**
- Up to ~2 change requests / month: availability + seasonal hours, add/edit/remove a service
  or staff member, price/duration tweaks, reminder/confirmation copy timing.
- A monthly no-show / booking-volume glance from the platform dashboard.
- A booking-link + calendar-sync sanity check.

**Not included (bill separately or out of scope):**
- The client's **platform subscription** (Calendly/Square/Acuity) — the client pays the
  platform directly; our fee is labor only.
- Live / same-day response or real-time calendar management. We are not a receptionist:
  no answering customer messages, manual rebooking, or refund/dispute handling.
- New capabilities (deposits, classes, multi-staff, intake build-outs) — these are one-time
  setup add-ons (`booking_deposits` $120, `booking_multistaff` $150, `booking_classes` $200,
  `booking_intake` $90).

**Reminders** are sent by the platform on its own messaging registration (transactional), so
there is no SMS-compliance burden on the client — we never run a separate texting path.

**Offboarding:** remove our delegated access; the client keeps the account, calendar, and
booking history. Nothing to migrate.

## Scope boundaries (prevent creep)

State these in the OFFER so "can you also…" has a boundary. Every request is
**binary: in-scope (clear yes) or a change order** — there is no free third bucket.

- **Revisions are bounded and countable** — e.g. "2 revision rounds per
  deliverable; unlimited minor edits within a round."
- **"Copy edits included during the build phase only; post-launch revisions billed
  separately."**
- **Hosting includes 2 content updates / month;** additional updates at a stated
  rate.
- **Acceptance clause:** "Deliverables are complete when [objective criteria];
  revisions must be requested within 5 business days of the preview."
- **Exclusions (name them):** extra pages beyond the package's count, copywriting/
  photography beyond what's provided at intake, third-party integrations, future
  features (e-commerce, multilingual) unless in the package.

## Client-facing language (paste into the OFFER)

> **What we commit to.** Your website preview within [2–5] business days of a
> complete intake, and your live site within ~48 hours of your approval. We'll
> configure your DNS and business email within 1 business day of receiving access.
>
> **What's on Google's / your registrar's clock (not ours).** Some steps are
> controlled by Google and domain registrars, not by Better Business Web. These are
> typical estimates, not guarantees:
> - **Google Business Profile verification: usually 5–14 business days** (video
>   verification is now standard); occasionally up to ~3 weeks if Google asks for a
>   re-submission.
> - **Business email reliability: usually live within 1 business day; up to 48–72
>   hours for full global reliability.**
> - **Domain transfers: ~5–7 days, and subject to ICANN's mandatory 30–60-day lock**
>   after registration or a registrant change — which no party can override.
>
> We submit every request promptly and correctly, monitor status, and resolve any
> rejections — but we can't guarantee or speed up Google's review queue or registry
> locks.

## Ownership (set at kickoff, for clean offboarding)

| Asset | Owner | Agency role |
|---|---|---|
| Domain | **Client** (registrant) | Delegated/admin access |
| Google Business Profile | **Client = Primary Owner** | **Manager** (revocable in seconds) |
| Google Workspace email | Client billing where possible | Admin during engagement |
| Hosting (Netlify) | Agency-managed | Transferable to client on exit |
| DNS zone | Whoever owns the domain | Delegated access |

A partner who demands GBP **Primary Owner** is a red flag — Manager is all we need
and it keeps offboarding clean. Details: [domain-dns-runbook.md](domain-dns-runbook.md).
