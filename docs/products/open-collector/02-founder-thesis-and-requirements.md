# Open Collector — founder thesis and product requirements

Prepared 2026-09-20. Proposed design, ready for founder review and engineering feasibility work. “Open Collector” is a descriptor, not a cleared product name. The requested deliverable is a founder pack; no application, new repository, or public launch has been created by this planning task.

## The product we should build

A free, public-source Mac app that helps collectors find a wanted product at a price they chose, understand whether a stock signal is current, and act confidently. Over time it can support bounded shopping assistance. The initial experience should be useful without an account, saved payment card, access to the user's normal browser profile, or a background cloud subscription.

The long-term ambition covers Guppy's useful collector workflow: discover → set intent → monitor → evaluate → act → review. The first release deliberately covers fewer execution capabilities. It must never be marketed as a feature-equivalent replacement for unattended checkout while it only provides alerts.

**Core promise:** “Know what is available, why it matters, and what happens next.”

**Working assumptions:** one founder; macOS first; US online shopping first; one sealed trading-card category; free local client; optional paid services later. A preference question was offered during the audit; these remain proposals unless the founder confirms them. Real-time nationwide inventory access, retailer cooperation, free commercial price data, and customer willingness to pay are not established facts.

## Three product directions

| Direction | Main value | Advantages | Cost and weakness | Decision |
|---|---|---|---|---|
| Local watch-and-decide app | Trustworthy alerts, clear evidence, budget context, browser handoff | Smallest permission surface; free distribution plausible; strongest first implementation | Does not win checkout races; usefulness depends on accessible data | Recommended first release |
| Purchase-assistance agent | Help complete a retailer-approved purchase with explicit limits | Closest to Guppy's automation appeal; stronger convenience | Session security, changing checkout flows, account risk, duplicate orders, maintenance burden | Planned second product stage after feasibility gates |
| Full collector platform | Inventory, price charts, social discovery, buying club, mobile and desktop | Broad engagement and multiple revenue paths | Several businesses at once; licensed data and physical operations overwhelm a side project | Select pieces later; skip retail supply business |

## Customer and problem

Initial customer: a hobby collector who currently revisits retailer tabs or notification communities to obtain specific sealed products near a chosen price. They want fewer false alerts, clear retailer/seller identity, and less concern about handing an opaque app their accounts and money.

Primary jobs:

1. “Remember the exact product and variant I want; tell me when a matching offer meets my limits.”
2. “Tell me whether this is actual recent stock, a stale listing, or an estimate.”
3. “Let me open the right retailer page quickly without exposing passwords to another service.”
4. “Show what happened while I was away, including when my Mac was asleep and no check occurred.”
5. “Help me avoid buying the same item twice or blowing my hobby budget.”

Secondary users later: collectors of other games, consoles, and limited household goods. Businesses seeking high-volume resale automation are outside the initial segment. That is a scope decision, not a claim that every other use is unlawful.

## What makes it ours

The improvement is specific, measurable behavior—not a claim that our code will automatically be better.

- **An evidence card for each alert.** Item, variant, seller, price components, store/region, source, observation time, freshness, and reason the rule matched.
- **Capabilities stated in plain language.** “Can read this store's stock”; “Can open a page”; future “Can propose a cart.” Watching and permission to spend are different switches.
- **A calm action inbox.** Group duplicate signals and show the one next decision. Optional trends never crowd out owned watchlists.
- **Honest status.** Paused, stale, sleeping, blocked by source, expired session, and needs your attention are distinct. No “online” badge when the connector is failing.
- **Money precision.** An item-price target is different from an all-in spending ceiling. Unknown tax or shipping must remain unknown.
- **User-owned data.** Local operation, documented export format, account-free onboarding, inspectable changes, and a public issue/release history.
- **Visible maintenance.** Connector health and last verified version; a broken connector stops and explains itself instead of silently continuing.

## Release scope and acceptance requirements

Priority means release sequence, not the importance of a capability to Guppy's overall proposition.

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R01 | Account-free local onboarding | Fresh install reaches a synthetic sample watch without signup, payment, or OS privacy grants |
| R02 | Exact product input | Manual entry, permitted product URL, or CSV; preview canonical identity and variant before saving; unsupported sources explain their limitation |
| R03 | Explicit source choice | Watch displays enabled sources and approved polling interval; no scanning unrelated domains |
| R04 | Stock and price rules | Only explicit in-stock evidence plus correct product/seller/region and threshold produces a matching alert; unknown remains unknown |
| R05 | Freshness and provenance | Every offer shows observed-at and retrieved-at timestamps, source link, and configured freshness threshold |
| R06 | Clear alert intent | Default mode is Notify; no browser login or payment collection is required for that mode |
| R07 | Notification controls | Request notifications only after the user enables an alert; support quiet hours, item-level pause, deduplication, and global pause |
| R08 | Browser handoff | Opens only a validated HTTPS merchant destination after a user action; no checkout button clicks or session import |
| R09 | Local history and export | Export/import documented versioned JSON and useful CSV; round-trip rules and outcomes; secrets never included |
| R10 | Resource and sleep honesty | Sleep/wake creates explicit gaps; no default sleep prevention; resume uses source limits and avoids a notification storm |
| R11 | Data and permission controls | Show storage location, retention, connector permissions, telemetry state, and data removal preview; telemetry off by default |
| R12 | Accessible interface | Complete keyboard navigation, VoiceOver labels and announcements, visible focus, reduced motion, and non-color-only status |
| R13 | Reliable local scheduler | Crash restart preserves watch state; one active evaluation per watch; replayed observations do not create duplicate alerts |
| R14 | Secure distribution | Signed/notarized Mac release, signed update metadata/artifacts as applicable, dependency inventory, supported runtime, documented vulnerability contact |
| R15 | Source failure behavior | Rate limit, malformed data, CAPTCHA, access denial, and unavailable API become stopped/backoff states; no evasion or fabricated observations |
| R16 | Personal budget view | Optional manually entered purchase/outcome totals; explicitly incomplete if purchases elsewhere are not entered |

R02–R05 cannot be called production-ready using only synthetic fixtures. At least one lawful, sustainable real data source must pass the connector gate in the execution plan.

## Future parity, with explicit limits

| Capability | Stage and condition | Expansion beyond the reference concept |
|---|---|---|
| Assisted cart | After one approved retailer integration and a sandbox/test account are available | Re-confirm exact product, quantity, seller, shipping method, final amount, and destination |
| User-approved purchase | After independent review, transactional tests, and a clear merchant authorization model | Approval binds an immutable proposal; changes invalidate it; ambiguous submission enters reconciliation |
| Unattended purchase | Optional later track, not launch promise; founder must choose this risk and support burden | Short-lived authority, per-rule and global budgets, quantity limits, stop control, duplicate-order protection, receipt reconciliation |
| Queue assistance | Only via permissible interfaces; initially reminders/open-page handoff | Queue state and expiration visible; never multi-account or bypass queue controls |
| Local store radar | After licensed/authorized store-level data with measured freshness | Distinguish shelf inventory from online availability; store-specific confidence and timestamps |
| Collection ledger | After alert retention is proven | Cost basis, owned/wanted separation, duplicates, import/export; no opaque financial-return score |
| Market comparisons | After suitable data rights and matching quality | Separate sold/listed price, fees, condition, grade, source age, and estimated range |
| Community insights | After moderation capacity exists | Opt-in aggregation, source provenance, abuse controls, conflict labels; no automatic retry from unverified community posts |
| Cloud alerts and mobile | After source economics and sleep-time demand are measured | Explicitly show local versus cloud monitoring; optional data-minimized account |

## Deliberate exclusions

No Guppy backend, catalog extraction, private API dependence, source reuse, branded images, or recreated pixel layout. No bulk buying, anti-bot bypass service, CAPTCHA-solving integration, proxy rotation for access evasion, credential harvesting, or import of an entire normal browser profile. No inventory buying club, fulfillment, or marketplace at launch. No LLM in the spending-authority path; an optional later assistant may explain observations but cannot grant itself capabilities.

## Success measures and decision gates

These are pilot targets, not existing results:

- Ten collector interviews; at least six independently describe the same alert trust/control problem. If they mainly want checkout speed, reassess the proposed first release before building a polished alert app.
- Five prototype sessions; at least four users can explain the difference between a watch and a spending authorization without help.
- One authorized source and 20–50 products observed over 7–14 days. Record all discrepancies. Initial target: at least 95% of delivered availability alerts agree with a prompt manual check; report sample size and uncertainty.
- At least 99% of eligible scheduled evaluations execute within their defined interval plus tolerance while the Mac is awake and the source is healthy. Report outages and sleep gaps separately.
- No duplicate notification within a configured cooldown for the same material observation. No silent monitoring gaps, unauthorized outbound requests, or secret-bearing exports in the release tests.
- After a four-week pilot, six of ten participants still use the app weekly and at least five say they would miss it. If not, interview and adjust the product before expanding retailer count.

Business questions for the founder: Is automatic purchasing essential to the initial value? How much weekly maintenance can this side project absorb? Is the objective a useful free tool, portfolio project, sustainable small business, or a larger service? The pack uses the free-tool-first path while preserving the other decisions.
