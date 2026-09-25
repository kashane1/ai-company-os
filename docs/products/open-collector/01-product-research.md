# Open Collector: public product and market research

Research date: 2026-09-20.  This is a public-source product brief for a
separately designed, potentially open-source collector tool. “Open Collector”
is a working descriptor only. It is not a request to use Guppy’s name, code,
copy, artwork, UI, or proprietary data.

## Method and confidence

This research used public first-party web pages, app-store listings, and terms
linked below, plus a limited anonymized, read-only UI observation summary from
the concurrent local audit. It does **not** inspect Guppy’s local code,
network traffic, implementation, account data, or create a purchase mission.
Therefore it supports product planning, not a security verdict or a claim
about how the installed binary behaves.

Labels used below:

- **Observed** means a public page visibly stated the feature, price, or flow
  on the research date. The few concurrent UI observations are called out as
  such rather than presented as public-source evidence.
- **Claimed** means a vendor’s statement, not independently tested evidence.
- **Inferred** means a product conclusion drawn from the observed material.

## Product identity: Guppy / DropKit

### What it is

- **Observed:** [Guppy’s site](https://www.guppy.so/) currently describes a
  membership for sealed Pokémon-card buying, nearby-stock notifications, and
  drop-day queue assistance. Its public terms identify the provider as DropKit,
  Inc. doing business as Guppy Labs and apply to its site, mobile and browser
  apps, extensions, and related services. [Terms, updated June 24,
  2026](https://www.guppy.so/legal/terms-of-service).
- **Observed:** The [iOS App Store listing](https://apps.apple.com/us/app/guppy-collector-copilot/id6756319687)
  presents a broader collector assistant: user-defined missions, maximum-price
  rules, product watching, local inventory and restock alerts, and desktop
  extension-dependent automated checkout.
- **Claimed:** [The company’s about page](https://www.guppy.so/about) says its
  agent watches drops, helps obtain scarce stock, and tracks a collection. It
  names Clay Kohut as founder, and lists Sam Torgove and Grant Zinn as team
  members. The same page claims more than 10,000 early-access collectors and
  daily updates; those numbers and cadence were not independently verified.
- **Inferred:** The present product is best understood as a consumer
  collector-commerce service with an automation component, rather than only a
  card-price app or only a restock-alert service. Its direct comparison set is
  therefore split between stock/checkout services and collection/market-data
  products.

### Publicly documented user flow

1. **Observe —** A collector finds an item, adds it to a watch/mission, and
   sets constraints such as a maximum price. This is explicitly described in
   the [iOS listing](https://apps.apple.com/us/app/guppy-collector-copilot/id6756319687)
   and aligns with the service’s terms.
2. **Monitor —** Guppy says it detects restocks, prices, availability, and
   queues; its public roadmap names product-watch missions, priority alerts,
   eBay price overlays, local stock radar, and community signals.
   [Homepage roadmap](https://www.guppy.so/).
3. **Decide —** The user’s maximum price, quantities, saved retailer account
   state, and chosen mission decide whether an item is eligible. Guppy’s terms
   say a user remains responsible for agent configuration and outcomes.
4. **Execute locally when enabled —** The terms say some auction-bidding and
   checkout-assistance functions may automate actions in the user’s browser
   session on the device. They require the device and browser to be online and
   the merchant session to be logged in with shipping and payment settings
   ready. [Terms §4](https://www.guppy.so/legal/terms-of-service).
5. **Outcome —** Its site says auto-join and auto-checkout are early access,
   need the desktop application, and are not guaranteed to succeed.
   [Homepage](https://www.guppy.so/).

This describes the advertised flow, not a reverse-engineered workflow.

### Platform, availability, and update provenance

- **Observed:** Guppy publicly advertises a desktop application for macOS and
  Windows, and lists mobile apps on the [Apple App Store](https://apps.apple.com/us/app/guppy-collector-copilot/id6756319687)
  and [Google Play](https://play.google.com/store/apps/details?id=com.guppylabs.guppy).
  Its terms also cover browser applications and extensions. The Google Play
  listing identifies the developer as DropKit Inc.
- **Observed:** The public roadmap calls the desktop app new and says updates
  ship weekly; the about page claims daily shipping. Neither statement is a
  versioned public changelog, signed release-feed specification, SBOM, or
  reproducible-build attestation.
- **Unknown:** The public material reviewed does not specify desktop update
  signing/key rotation, release notes by desktop version, source availability,
  third-party dependency inventory, vulnerability disclosure policy, or a
  complete extension permission list. Those are verification questions for
  the local audit, not evidence of malicious behavior.

### Publicly stated privacy and security posture

- **Claimed:** Guppy says automation uses the customer’s browser session,
  that it does not require merchant passwords, and that checkout assistance
  may run locally. [Terms §4](https://www.guppy.so/legal/terms-of-service).
  The marketing site goes further, saying credentials stay under user control.
  That is a vendor claim, not an independent security assessment.
- **Observed:** Its [privacy policy, updated July 23,
  2026](https://www.guppy.so/legal/privacy-policy) says it collects account
  data, device/technical data (including IP, approximate region, OS, browser,
  version, crash diagnostics, and interaction events), payment-processor
  tokens/last four digits, and inferred shopping interests. It says full card
  numbers are not stored by Guppy Labs.
- **Observed:** The policy says it discloses information to hosting, analytics,
  security, payment and support providers; merchants selected by a user;
  affiliate/attribution partners; and legal/safety recipients. It says it does
  not sell personal information, but may share limited data for targeted
  advertising with consent. It also says processing/storage occurs in the U.S.
  and provides access/deletion/portability contact at `privacy@guppy.so`.
- **Observed:** The [terms](https://www.guppy.so/legal/terms-of-service) place
  merchant interaction and beta reliability risk on the user, reserve service
  changes/suspension, and prohibit multi-accounting, attempts to evade limits,
  and external automation. They also state a U.S. initial territory and
  personal/noncommercial use.
- **Inferred:** For a new product, “local execution” is useful only if it is
  independently inspectable: every requested permission, credential boundary,
  network destination, action proposal, action result, and update signature
  should be visible to the owner. A marketing promise alone cannot establish
  that boundary.

### Current commercial offer (publicly displayed)

- **Observed:** Guppy’s [pricing page](https://app.guppy.so/pricing) listed
  Plus at $12.99/month for 30 simultaneous auto-buy missions and $119.99/year
  ($9.99/month equivalent) for 100. Listed benefits include beta auto-checkout
  at Walmart and Target; beta queue joining for Pokémon Center, Walmart, and
  Costco; alerts, local radar, Discord, and member buying-club access.
- **Observed:** The [public site](https://www.guppy.so/) says the membership
  price and product purchase are separate, and describes pooled member demand,
  batch purchasing, limits per member, and product allocation. This is an
  inventory/commerce operation, not a software-only feature.
- **Caution:** Prices, store coverage, mission limits, statistics, and beta
  status are time-sensitive. They must be rechecked before any pricing or
  comparison claim is published.

## Public concept inventory

The table separates valuable problem ideas from Guppy-specific implementation
or commercial choices. “Adopt” always means independently designed behavior
and language, with independently licensed data and brand assets.

| Publicly visible concept | Decision | Why and independent direction |
| --- | --- | --- |
| A watchlist of scarce products | **Adopt** | This is the durable core job: remember what a collector wants and reduce checking. Use canonical product IDs, aliases, variants, conditions, region, and retailer scope. |
| Max-price and quantity guardrails | **Adopt and expand** | Make these mandatory for any execution-capable plan. Add all-in price, tax/shipping estimate, per-day/per-week budget, per-retailer caps, and an explicit “never buy” list. |
| Restock, price, and availability alerts | **Adopt** | Begin with transparent read-only monitoring and notifications. Show observation time, source, price components, region, confidence, and a direct merchant link. |
| Local inventory / radius view | **Adapt** | Useful only where authorized inventory data is reliable. Require source and freshness labels; never imply in-store certainty from stale data. |
| Queue event awareness | **Defer** | It is technically fragile, retailer-sensitive, and difficult to justify before product-market fit. Begin with user notifications and an optional “open the page” handoff. |
| Browser-session assisted checkout | **Defer behind an explicit policy gate** | It is the highest-risk capability for account safety, retailer terms, reliability, and support. Do not build it in MVP. If later approved, use an owner-visible, local-only extension with a per-action confirmation mode first. |
| Full unattended purchasing | **Skip at launch** | It expands financial, security, and merchant-policy risk disproportionately. A trustworthy product can deliver most early value through discovery, verification, and alert-to-cart handoff. |
| Community signals / trend feed | **Adapt later** | The idea can improve discovery, but anonymous hype and manipulation create low-signal noise. Only ship provenance, votes, rate limits, conflict reporting, and no paid placement disguised as community signal. |
| Portfolio / collection value | **Adopt narrowly** | Add a local collection ledger and cost basis with price-source attribution. Do not call estimates “true value,” and make imports/exports first-class. |
| Card scanning and visual identification | **Defer** | Good convenience, but it requires expensive/accurate catalog and image matching. Start with barcode/UPC, exact catalog search, CSV import, and manual entry. |
| Market price overlays and deal scoring | **Adapt** | Use a price-source panel, observed-sales window, fees, shipping, condition/grade, and confidence range. Never collapse heterogeneous listings into a deceptively precise price. |
| Member purchasing club / direct inventory | **Skip initially** | This changes the business into retail: supplier relationships, inventory, fulfillment, chargebacks, tax, returns, product authenticity, and allocation fairness. Revisit only after software retention is demonstrated. |
| “Anti-scalper” one-person limits | **Adopt as a policy principle** | Make it enforceable in product design: no multi-account support, no bulk automation, quantity one by default for scarce releases, and no resale-optimization features. The product must also honor merchant rules. |
| Discord-first community | **Defer** | Community can be a discovery channel, but it is not a safe substitute for in-product support, auditability, moderation, or data ownership. |
| Frequent feature shipping / early access | **Adapt** | Use a public changelog, signed releases, stable/beta channels, feature flags with explanations, and a rollback path rather than a generic “early access” label. |
| Mission status UX | **Adopt and expand** | One unified timeline should show intent → monitoring evidence → recommendation → handoff → user decision → outcome. This is the strongest UI and trust opportunity. |
| Product search by title, set, or retailer URL | **Adopt** | A concurrent local UI review reports this as an input path. It is a useful low-friction onboarding concept; independently implement it through a permissioned importer that previews the canonical product match before saving anything. |
| Category-specific discovery filters | **Adopt** | A concurrent local UI review reports filters for Pokémon, Magic, One Piece, and Lorcana. Start with one category but use a category-agnostic product model to avoid a rewrite. |
| Retailer account readiness health | **Adopt, without credential inspection** | A concurrent local UI review reports account-health status. A new product should only report whether a user-approved connector is ready, never collect retailer passwords or inspect payment fields. |
| Local session-recording / “black box” control | **Adapt and expand** | A concurrent local UI review reports recording, quality, processing, purge, and CPU-saving controls. For Open Collector’s alert-first MVP, retain a local, user-controlled event log rather than video. If execution is ever approved, offer encrypted local recording with short retention, explicit consent, and a one-click purge. |
| Mission history and cancel countdown | **Adopt** | A concurrent local UI review reports history and a cancel grace period. A reusable operation timeline plus reversible cancellation is a strong trust pattern, even for notification-only rules. |
| Community feature voting | **Adapt later** | A concurrent local UI review reports an ideas/voting area. Use a public roadmap and issue voting after core signal quality is proven; protect it with abuse prevention and show resolution status. |
| Cross-site catalogue | **Defer** | Catalog normalization creates a major ongoing data-quality burden. Seed one category and a small source set, prove alert freshness, then expand by demand. |
| Collection marketplace / listings | **Skip initially** | A marketplace adds fraud, payments, identity verification, tax, moderation, dispute resolution, and liquidity challenges. Export-to-existing-marketplace is a lower-risk later integration. |
| Analytics-based personalization | **Adapt with data minimization** | Personalize from user-owned explicit preferences first. Make telemetry opt-in where feasible, list fields and recipients, and provide deletion/export. |

## Product opportunities revealed by the landscape

### 1. The user need is a control problem, not merely a speed problem

All four adjacent products concentrate on parts of the collector loop:

- finding stock and sending alerts (HotStock);
- tracking a collection, wants, and price movement (PriceCharting and
  Collectr); and
- scanning, valuing, organizing, and selling (LUDEX).

**Inferred:** A differentiated product can connect the loop without pretending
to be a fully autonomous shopper: *what do I want, what can I afford, what
evidence says it is available or fairly priced, and what did I decide?*

### 2. Defensible wedge: an open, local-first collector decision console

Proposed positioning, independently worded:

> A collector-controlled watch, evidence, and budget workspace that turns
> noisy product drops into clear, reversible decisions.

The wedge is not “faster botting.” It is **verifiable intent and evidence**:

1. The user creates an item rule, spending boundary, source set, and alert
   preference.
2. The product records observations with timestamp, URL/source, regional
   context, price components, and freshness.
3. It explains why a notification fired and why it did not fire.
4. The user opens the merchant page and completes the purchase in their own
   normal session.
5. The product records an optional local outcome, updating collection and
   budget history without requiring a commerce platform.

This is defensible because it turns trust into a product primitive: user-owned
rules and data; open connector interfaces; source provenance; deterministic
alert decisions; export; no hidden spending; and publicly reviewable client
code. It also avoids depending on a retail supply operation to provide value.

### 3. Where to be meaningfully better

| Area | Product decision |
| --- | --- |
| Trust | Default to read-only data access; show connector permissions and outbound destinations; use signed updates; publish SBOMs and a security-contact/disclosure process. |
| Money safety | Separate “watch,” “recommend,” “open merchant page,” and any future “act” capability. Require all-in price and a budget before a purchase-capable rule can exist. |
| Alert quality | Give every alert its observation evidence, freshness, region/store setting, and deduplication reason. Track false-positive feedback. |
| Data ownership | Local app-scoped storage, CSV/JSON export, and a portable watchlist/collection schema. The proposed v1 store is not promised to be fully encrypted by the app; sensitive future artifacts need explicit encryption. Optional future cloud sync needs its own encryption/recovery design before any end-to-end encryption claim. |
| UI | One calm chronological activity stream, an uncluttered item detail page, and a clear distinction between confirmed observation, estimated value, and user-entered data. |
| Scope | Serve one collector category and a limited set of legitimate data sources very well before adding more retailers, games, or a marketplace. |
| Reliability | Public health/status pages per connector, observation freshness indicators, test fixtures, connector versioning, and a visible changelog. |

## Adjacent-product comparison (public primary sources)

| Product | Documented core | Automation / execution | Current public price evidence | Planning implication |
| --- | --- | --- | --- | --- |
| **Guppy** | Collectible purchase club, restock/local-stock discovery, product missions, queues and desktop browser assistance | Guppy publicly says its beta desktop capability can join queues and attempt checkout in the user’s browser session. | [Guppy pricing](https://app.guppy.so/pricing): $12.99/month or $119.99/year on 2026-09-20. | Closest composite competitor; software-only MVP should not inherit its retail/inventory operation. |
| **HotStock** | Broad hard-to-get product monitoring and mobile alerts across retailers | [AutoBuy FAQ](https://www.hotstock.io/faq-autobuy) says iOS/Android assisted checkout, price limit, one-item quantity, device-local retailer credentials, and foreground-app constraint. | The public FAQ says AutoBuy is an add-on but did not display a web price during this review. | Validates alert-to-action demand and shows mobile OS limits; its local-credential claim is a useful design benchmark, not verified fact. |
| **PriceCharting** | Price lookup, collection/wishlist, portfolio history, marketplace, deal alerts, and paid data tools | Its public feature pages describe notifications and market scanning, not retailer checkout automation. | [PriceCharting Pro](https://www.pricecharting.com/pricecharting-pro?f=lotAutomater): free account; Collector $6/month or $59/year; Legendary $49/month on 2026-09-20. | Demonstrates low-price willingness for price/collection workflow; an open product needs a legitimate, sustainable data strategy rather than copying price feeds. |
| **Collectr** | TCG portfolio tracking, scanning, data-driven value tracking, exports, dashboards and social features | No purchase automation found in the reviewed public tracking and subscription pages. | [Collectr PRO](https://app.getcollectr.com/?intent=subscribe): $7.99/month or $59.99/year on 2026-09-20. | Strong reference for collection-first retention; it leaves room for decision-quality alerts and local-first trust. |
| **LUDEX** | Sports/TCG card scanning, valuation, portfolio, trend information, and eBay listing workflow | [Membership page](https://www.ludex.com/membership/) describes creation of eBay listings from a portfolio; no automatic retail checkout found. | Free tier; Lite $4.99/month, Standard $9.99/month, Pro $24.99/month (with stated annual options) on 2026-09-20. | Shows scanning and sell-side workflow can monetize, but also explains why scanning should wait until the core watch/decision loop has traction. |

These are functional comparators, not claims of equivalent quality, legality,
or market share. The prices are point-in-time web observations and should be
dated wherever they are reused.

## Business-model options

### Option A — free, open-source local app; paid managed connectors

The desktop/mobile client, local schema, alert-rule evaluator, imports/exports,
and connector SDK are openly licensed. A paid optional service provides
maintained, rate-limited official/authorized data connectors, hosted alert
delivery, encrypted sync, and expanded history.

- **Strengths:** strongest trust narrative; open source can be reviewed;
  credible “free forever” base; costs map to the services that cost money.
- **Risks:** hosted data costs can exceed conversion; connector terms may limit
  commercial use; an open connector library does not grant data rights.
- **Pricing hypothesis:** free local app; $3–5/month personal managed-alert
  service; $8–10/month for multi-device encrypted sync and advanced alert
  history. These are hypotheses, not recommended public prices yet.

### Option B — free core; single low-price Plus plan

Free: local watchlists, manual imports, a small number of alerts, collections,
and exports. Plus: unlimited hosted alerts, source health, multi-device sync,
and advanced decision/budget analytics.

- **Strengths:** easy explanation and aligns with the observed $5–13/month
  range in adjacent services.
- **Risks:** artificial alert caps can erode the trust-based wedge; users may
  assume the product will enable automated checkout.
- **Pricing hypothesis:** $4.99/month or $39/year, with no direct purchase
  automation in the plan’s promise.

### Option C — one-time desktop license plus optional cloud

Sell a perpetual local application with an included period of managed
connectors, then renew cloud features annually. Keep the source-available/open
client commitment explicit.

- **Strengths:** appealing to privacy-oriented collectors; cash arrives early;
  operational cost is not hidden.
- **Risks:** continued connector maintenance can become underfunded; mobile
  distribution and cross-device support complicate the model.
- **Pricing hypothesis:** $29–49 initial license with $15–25/year optional
  managed-alert/sync service.

### Recommended validation order

Start with Option A or B only after testing whether collectors value the
evidence and control model. Do not set a “cheaper than Guppy” public promise
until the recurring cost of each authorized data source, notifications,
support, and security maintenance is known. Direct comparison is misleading
while the initial product deliberately excludes a buying club and beta
checkout automation.

## Validation questions before building

1. Which initial buyer is most reachable: sealed Pokémon buyers, broader TCG
   collectors, sports-card collectors, or limited-edition hobby buyers?
2. Do 15–20 target users prefer (a) browser/page handoff with transparent
   evidence or (b) automation enough to accept the extra risk and responsibility?
3. Which official APIs, affiliate feeds, retailer integrations, or user-facing
   page interactions are contractually permitted for monitoring? Obtain written
   terms/permission before prioritizing a connector.
4. What is the alert’s required freshness for the first category, and can the
   permitted data source support it at a viable cost?
5. What all-in price calculation do people trust: item only, item plus tax and
   shipping, or a user-set ceiling that includes a buffer?
6. Would collectors pay $4–5/month for auditable alerts and encrypted sync if
   the core local app remains free? Test conversion against a prototype, not a
   survey alone.
7. What import/export format prevents lock-in for the first cohort (CSV,
   PriceCharting export, custom JSON), and are terms/licenses compatible with
   any requested importer?
8. What should be explicitly out of scope in the first public release:
   checkout automation, payment storage, retailer login collection, social
   trading, marketplace, and direct inventory are the recommended exclusions.
9. What regulatory, tax, consumer-protection, and merchant-policy obligations
   would be triggered if any future version accepts money or places orders?
10. Can security-conscious users independently verify the desktop release,
    permissions, updates, and network behavior from the first beta?

## Recommended founder decisions for the wider pack

1. Confirm the first wedge: **collector decision console**, not an automated
   purchasing bot and not an inventory business.
2. Choose the initial category and three or fewer authorized data sources.
3. Commit to an open-source license and clarify whether hosted connectors are
   proprietary, open, or separately licensed.
4. Choose one of: local-only MVP, optional encrypted sync, or account-first
   hosted service. Local-only is the strongest initial trust posture.
5. Establish a written no-autopurchase rule for the MVP; any later execution
   feature needs a distinct product, security, legal, and merchant-policy
   review.
6. Set a public product standard: every alert is explainable, every data source
   is named, and every user can export/delete their data.

## Source register

- Guppy: [public homepage](https://www.guppy.so/),
  [about](https://www.guppy.so/about),
  [pricing](https://app.guppy.so/pricing),
  [terms](https://www.guppy.so/legal/terms-of-service),
  [privacy](https://www.guppy.so/legal/privacy-policy),
  [iOS listing](https://apps.apple.com/us/app/guppy-collector-copilot/id6756319687),
  [Android listing](https://play.google.com/store/apps/details?id=com.guppylabs.guppy).
- HotStock: [US site](https://www.hotstock.io/us),
  [AutoBuy FAQ](https://www.hotstock.io/faq-autobuy).
- PriceCharting: [collection tracker](https://www.pricecharting.com/page/collection-tracker),
  [subscription page](https://www.pricecharting.com/pricecharting-pro?f=lotAutomater).
- Collectr: [tracking product page](https://getcollectr.com/track),
  [PRO subscription page](https://app.getcollectr.com/?intent=subscribe).
- LUDEX: [product page](https://www.ludex.com/),
  [membership page](https://www.ludex.com/membership/),
  [collection product page](https://collections.ludex.com/).
