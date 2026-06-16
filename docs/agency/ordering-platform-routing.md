# Online Ordering — platform routing & managed model

> We don't build ordering or payment software. We set up branded online ordering
> on a proven POS, **on the client's own account**, hosted/embedded only — the
> money always flows through the client's own merchant account, so the agency is
> never a payment facilitator and never touches funds, refunds, or chargebacks.
> This doc is the operator's decision guide: which POS for which client, what
> each ordering SKU means, the Toast gate, and the liability line.
>
> Catalog SoT: [service-catalog.md](service-catalog.md) · SLA: [client-sla.md](client-sla.md) ·
> Sibling model: [booking-platform-routing.md](booking-platform-routing.md).

## The catalog SKUs (pick-one base + modifiers)

`exclusive_group: ordering_base` — pick exactly one base:

| SKU | What it is | Bill |
|---|---|---|
| `ordering_connect` | Connect: "Order Online" buttons → the client's **existing** Square/Clover ordering page, styled to match | $200 one-time |
| `ordering_setup` | Done-for-you: we set up branded ordering + checkout on the client's POS, configure menu/tax/pickup, test end-to-end | $600 one-time |

Modifiers (`requires_group: ordering_base`, stack on either base):
`ordering_menu_entry` → **"Menu Build"** ($250 one-time — enter the full menu into the POS
if it isn't already there) · `ordering_management` → **"Menu Management"** ($40/mo — ongoing
specials / price / 86 / seasonal edits, ~2 change requests/mo).

## Build depth: hosted/embedded only (v1)

We sell **Connect** and **Done-for-you Setup** only. Both put the checkout on the POS's own
hosted/embedded flow. We do **not** build a custom cart → API → fulfillment ("Premium") tier on
the open site — it carries real payment, refund, and order-accuracy liability plus ongoing
maintenance. Premium is **assess-on-request only**, gated behind confirmed POS API access + budget,
and never auto-sold.

## Platform capability + routing matrix (2026)

| Need | Square | Clover | Toast |
|---|---|---|---|
| Online ordering API | **full** (Catalog/Orders/Payments/Checkout) | full (Ecommerce/Orders) | partner-gated, restaurant-only |
| Free hosted ordering site | ✓ (Square Online) | ✓ | bundled w/ Toast plan |
| Write access (push orders) | open | open | **gated by integration type** |
| Best fit | cafés, retail, quick-serve, most SMBs | retail + restaurants on Clover hardware | full-service restaurants already on Toast |

**Routing rule:**
- **Default to Square.** Easiest API, free hosted ordering, covers cafés / quick-serve / retail —
  the bulk of our prospects (see the coffee + taco demos).
- **Already on Clover hardware → keep them on Clover.** Don't migrate POS just to sell ordering.
- **Toast → assess first, never promise.** Toast's write API is partner-gated and restaurant-only.
  Confirm the client's integration tier grants ordering write access **before** quoting. If it
  doesn't, sell `ordering_connect` against their existing Toast online-ordering link, not a setup.
  **Toast is never listed as "supported" on the public site.**

> ⚠️ The pitch is **commission savings**, not "nicer checkout." A shop bleeding 15–30% per order to
> DoorDash/Uber Eats keeps far more by taking pickup orders on its own site at ~2.9% card fees.
> Many already have a free POS ordering page — our value is branded integration + getting them off
> marketplace commissions + the Menu Management retainer, not the checkout tech itself.

## Scope fence (what v1 covers)

- **In:** pickup, curbside, dine-in/table ordering, pay-online.
- **On request only:** delivery — it needs the client's own drivers or a DoorDash Drive / Uber
  Direct integration. Never promise delivery on the site.
- **In:** food/menus now; the SKUs are named generically enough that a retail "Online Store" line
  can slot in later without a rework.

## The liability firewall (why this line is low-risk)

Money flows through the **client's own** Square/Clover merchant account. We are **not** a payment
facilitator: we never hold funds, never process refunds, never own a chargeback. The customer pays
the restaurant directly; we built and styled the pipe. Keep it that way — never route a client's
order payments through an agency account or a third-party PSP we control.

## Access & ownership (set at kickoff → clean offboarding)

**The client owns the POS account** (their email, their card, their bank deposit). We hold
**delegated admin / team-member** access — never a shared password.
- **Square:** add operator as a team member with a custom permission set (Online/Items/Orders) +
  Authorized Representative. Offboard = remove the team member.
- **Clover:** owner invites operator as an employee with Admin/Manager role. Offboard = owner
  removes the employee.

No formal partner program is required for Square or Clover online ordering setup.

## The `$40/mo` Menu Management retainer (what it is / isn't)

See [client-sla.md](client-sla.md) for bindable scope. In short: ~2 change requests/mo (specials,
prices, 86'd items, seasonal menus, item options) + a monthly ordering-link/checkout sanity check.
**Not** order operations: no live order monitoring, no answering customers, no refund/dispute
handling, no kitchen/fulfillment work — those stay with the client. Menu Build and new modifiers
are one-time setup add-ons. The client pays the POS subscription + processing separately.
