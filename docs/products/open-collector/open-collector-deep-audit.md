# Open Collector — deep product, engineering, and business audit

Prepared September 20–21, 2026 · Decision document · Original nine planning files reviewed in full

> **TL;DR:** continue only as a tightly bounded validation project. The deciding risk is a permitted, useful stock data source at sustainable cost; see §6 and the [data-source plan](../../plans/2026-09-25-collector-radar-data-sources-plan.md). First customer hypothesis: a US hobby collector who wants specific sealed Pokémon products within a budget and acts manually on restocks that stay available for minutes. Keep the local app free and test one optional hosted plan at $5.99/month. Proceed only with source rights, alerts that measurably beat the customer's current method, and retention that pays for maintenance.

## 1. Recommendation

**Continue with a tightly bounded validation project. Do not yet commit to the full application roadmap or a paid launch.** The pack is thoughtful about permission, secrets, purchase safety, and honest status. Its weakest point is whether a sufficiently useful, permitted data source can serve the intended customer at a sustainable cost. Its most significant technical error is the assumption that a reused macOS notification identifier guarantees no repeated alert.

The proposed product combines three different ambitions: a free local utility, a scarce-drop purchasing assistant, and a subscription monitoring business. They have different customers, delivery requirements, and economics. The first decision is which job the initial product will reliably complete.

My recommended first customer hypothesis is **a US hobby collector who wants specific sealed Pokémon products within a budget and is willing to act manually on replenishments that remain available for minutes**. Validate that opportunity duration; it is not established by the research. A product intended to win seconds-long checkout races would need a different feasibility case.

Recommended commercial direction:

- Keep the local app free, with useful saved watches, transparent limitations, and portable user-authored data.
- Test one optional hosted plan at **$5.99/month**, adding **$59/year only after reliability and retention are demonstrated**. Those are recommended experiments, not a proven optimum.
- Sell continuity and relevant, actionable alerts. Open source and privacy support trust; they do not by themselves establish willingness to pay.
- Start with one useful source, or a small merchant partnership. Do not promise Target, Walmart, Pokémon Center, or Amazon coverage before the exact use is permitted and demonstrated.
- Move live-source feasibility and customer comparison ahead of a two-week synthetic implementation sprint.
- Add goal-based watches and explicit completion controls before collection valuation, social feeds, scanning, or checkout automation.

**Three conditions decide whether to proceed:** usable source rights and data; demonstrably useful alerts compared with the customer's existing method; and retention plus contribution economics that justify ongoing maintenance.

## 2. Scope and evidence

Reviewed: README and documents 01 through 08. Findings reference their filenames and section names so they can become edits or tickets. No source files were changed. No app, executable, live connector, retailer account, customer interview, acquisition campaign, or payment flow was tested. No outreach or publication was performed.

The report distinguishes:

- **Plan finding:** follows directly from the supplied documents.
- **Verified source fact:** supported by linked primary documentation or vendor pages accessed during this audit.
- **Inference:** a conclusion drawn from those facts, not a measured customer result.
- **Experiment/assumption:** a proposed price, threshold, cost, or behavior to test.

Competitor features are vendor claims, not independent performance tests. Some sites were inaccessible or JavaScript-only; those details remain unverified. This is a launch-risk review, not a determination of every legal obligation or a security certification. Source-specific contracts and the eventual paid offer need review against their actual terms.

## 3. What the existing plan gets right

Preserve the narrow category, account-free baseline, absence of checkout authority, explicit unknown values, variant/seller awareness, source review gates, separation of item price from final purchase cost, consented diagnostics, and independent public repository. Keep transactionally recorded alerts, race checks for pause/edit, safe SQLite backup, signed distribution, and refusal to treat a browser open as a completed purchase.

The pack already covers ordinary duplicate alerts, sleep gaps, currency mismatch, wrong variants, missing shipping/tax, URL allowlists, recovery, redaction, and speculative scope expansion. Repeating those as newly discovered omissions would be misleading. The findings below concern contradictions, insufficient specifications, or additional cases.

## 4. Highest-priority findings

Severity is a decision priority: **P0** blocks a product promise or release; **P1** should be resolved before a meaningful beta; **P2** matters before charging or expanding. A finding can block one capability without blocking all prototype work.

| ID | Priority | Finding and evidence in the pack | Required change / completion evidence |
|---|---|---|---|
| A01 | P0 | The decisive live-source question is acknowledged, but 05's first sprint and 08/T08 postpone the live integration until after substantial synthetic work. | Run an inexpensive, bounded real-source feasibility probe alongside interviews first. A production adapter can still follow tested contracts later. A synthetic demo is not evidence of market feasibility. |
| A02 | P0 | Scarce-drop customer + awake-only Mac + no checkout + deferred phone delivery may be an incompatible promise. 02 Customer, 04 Product boundary, 06 Recommendation. | Measure stock-window duration, customer response time, and actual availability after opening. Narrow to a job that the delivery path can complete. |
| A03 | P0 | 04 says notification replay is safe because the OS identifier is the dedupe key; 05/M3 and 08/T05 imply stronger guarantees than this provides. | Guarantee one logical inbox event; specify best-effort OS alert delivery with an explicit ambiguous-send policy. See section 8. |
| A04 | P0 | Source approval is treated mainly as access permission; retained history/export also require rights. 02/R09 and 04 append-only observations. | Add per-field retention, display, export, redistribution, and deletion rules. Do not promise universal evidence history for every adapter. |
| A05 | P0 | No verified way to distribute a useful source credential with a public, account-free local client is selected. | Choose approved unauthenticated reads, provider-supported public-client authorization, user-supplied credentials where permitted, or a funded backend. Never embed a shared confidential API secret in a desktop binary or public repository. |
| A06 | P1 | 01 omits close substitutes: free restock services and configurable/open-source monitors. | Benchmark against the customer's current tool and direct competitors in section 5. 'Free and open' is insufficient differentiation. |
| A07 | P1 | The product promises multi-source, seller and regional rules, while 04 ties a product to a source URL and keeps one alert state per watch. | Separate collector intent, source listing, contextual offer, observation, and alert state—or explicitly limit v1 to one exact offer context per watch. |
| A08 | P1 | Lease expiry recovery does not explicitly reject a late response from the old lease owner. 04 Crash-safe polling. | Use a fencing generation; at commit verify current lease ownership, generation, rule revision, and source policy. Old responses cannot overwrite current state. |
| A09 | P1 | Freshness is checked at evaluation, but pending alerts can outlive stock, quiet hours, sleep, or an outage. | Add alert expiry and latest-evidence validation immediately before dispatch. Historical matches remain history rather than fresh-stock alerts. |
| A10 | P1 | 95% agreement among delivered alerts measures precision, not missed opportunities or usefulness. 02 Success measures, 06 Validation. | Measure coverage, observation lag, independently observed opportunities, actionability, and false negatives. Report unknown ground truth honestly. |
| A11 | P1 | 99% schedule compliance is conditional on 'healthy' sources and an awake Mac. It can hide most customer downtime. | Publish both scheduler performance under defined conditions and end-to-end coverage over the customer's intended watch window. |
| A12 | P1 | A Mac being awake does not establish that the app is running promptly; lifecycle details are underspecified. | Test hidden/minimized/window-closed, App Nap, login/logout, power changes, quit/relaunch, notifications disabled, and Focus. Show measured state. |
| A13 | P1 | `NotModified`, upstream cache age, missing observed-at timestamps, and backorder/preorder semantics are not fully specified. | Add explicit freshness and fulfillment contracts. Retrieval time cannot fabricate source observation time. |
| A14 | P1 | Generic 401/403 suspension can misclassify source-specific quota failures. | Let adapters classify typed errors using status plus documented response semantics. Preserve fail-closed behavior on genuine denial. |
| A15 | P1 | An edited rule 'never emits automatically' is ambiguous about all subsequent checks. 04 and 05. | Define whether Save arms future checks and separately asks about an immediate current match. Avoid permanently silent edited watches. |
| A16 | P1 | Re-arm logic can miss a restock if an out-of-stock interval occurs between polls; it also lacks price-flap tolerance. | Define latch scope, hysteresis, minimum state duration, repeat policy, and unknown-gap behavior. Never claim to know unobserved transitions. |
| A17 | P1 | 03 promises unexpected redirects during browser handoff produce a warning. The app cannot generally enforce later navigation in the user's browser. | Validate the initial destination and adapter redirects; state that subsequent browser navigation is controlled by the browser/merchant. |
| A18 | P1 | Append-only storage, deletion controls, immutable evidence, bounded disk use, and source expiration are not reconciled. | Separate retained immutable records from authorized deletion/expiry. Specify compaction, tombstones where allowed, caps, and stale-data removal. |
| A19 | P1 | Reliable polling does not imply useful onboarding: a new watch could never trigger. | Measure first useful evidence and first real opportunity separately. Explain unsupported products before setup and preserve them as unmonitored wants. |
| A20 | P1 | 05 estimates assume an experienced macOS engineer plus reviewer; actual staffing and weekly hours are unsettled. | Estimate in focused hours and convert using real availability. Label the 7–11 weeks conditional; add approval and pilot calendar time. |
| A21 | P2 | $4/month economics exclude important costs and hold support constant as users grow. 06 Unit economics. | Include free users, annual discounts, subscription fees, incident labor, data minimums, churn, and acquisition. See section 11. |
| A22 | P2 | Paid cloud/mobile is treated as later expansion, although off-device monitoring may be central to the promise. | Test demand for continuity early without building a full cloud platform. A phone relay only forwards checks that actually happened. |
| A23 | P2 | 'Anti-scalper' controls cannot enforce one-human limits in a forkable, account-free app. 01 concept inventory. | Describe supported product behavior and hosted-service controls, not a guarantee about users or forks. |
| A24 | P2 | Public repo timing and signed-release language differ between README, 05, 07 and 08. | Choose one creation milestone and distinguish public source/developer build from signed consumer release. |
| A25 | P2 | Test commands and modules omit some acceptance requirements, including budget/outcomes, full import, quiet hours, retention, and source controls. | Add a requirement-to-ticket matrix; remove/defer features without an owner and acceptance case. |
| A26 | P1 | 04's state diagram mixes polling with alert delivery and omits an unchanged-match/unknown completion path. | Polling must continue after a committed observation even if notification delivery fails. Keep the two lifecycles independent. |
| A27 | P1 | A rule revision number and evidence hash alone cannot reproduce an old explanation after rule/evaluator changes. | Retain permitted minimal rule snapshots, evaluator version, fingerprint version and explanation codes. A local hash is not proof of retailer authenticity. |
| A28 | P1 | No-cookies/no-raw-response intentions omit HTTP session defaults. | Configure isolated transport, cache/cookie/credential behavior and allowlisted error logging explicitly; inspect actual persistence. |
| A29 | P2 | Alpha has no telemetry, but the measurement collection method is unspecified. | Use participant-owned local summaries and consented interviews; do not silently add analytics to obtain retention numbers. |
| A30 | P2 | 01 offers 'unlimited hosted alerts' while 06 warns against unlimited checks, and multiple prices coexist. | Distinguish delivery volume from monitoring workload; retire conflicting active offers and nominate one bounded pricing experiment. |

## 5. Competitive research and positioning

The strongest comparator is not always Guppy. Customers can use retailer notifications, free mobile restock alerts, community channels, generic monitors, and collection tools together. A collector may also choose to stop chasing scarce items. Interview about that choice.

| Product | Verified public offer / capability | Implication for Open Collector |
|---|---|---|
| Guppy | Plus displayed at $12.99/month or $119.99/year; offer includes additional purchasing/club capabilities. [Pricing](https://app.guppy.so/pricing). | A cheaper alert-only product is a narrower offer, not equivalent value for less money. |
| HotStock | US App Store lists Premium $5.49/month and AutoBuy $10.99/month; basic restock alert experience also exists. These are listed purchases, not proof of checkout results or a combined required price. [US listing](https://apps.apple.com/us/app/hotstock-in-stock-alerts/id1257690900). | Around $6/month already has a recognizable mobile-alert competitor. Phone delivery and source coverage matter. |
| TrackaLacker | Advertises free restock alerts, with mobile apps. [Official site](https://www.trackalacker.com/). | Free alerts are already available; charge only for a tested improvement customers value. |
| Distill | Free plan lists 25 monitors including 5 cloud monitors; local monitoring is an existing category. [Pricing](https://distill.io/pricing/). | Native polish must reduce setup and false matches enough to beat a configurable monitor. |
| changedetection.io | Open-source website monitoring; hosted service advertised at $8.99/month. [Official site](https://changedetection.io/). | Openness is not unique. Collector-specific identity, budgets, and decisions are the potential advantage. |
| PriceCharting | Collector offer displayed at $6/month or $59/year. [Pro plans](https://www.pricecharting.com/pricecharting-pro?f=lotAutomater). | Competes for the same hobby subscription budget, although valuation is a different job. |
| Collectr / LUDEX | Existing collection/scanning comparators are useful secondary context. Prices quoted in 01 should be rechecked at purchase; they are not necessary to justify this audit's pricing. | Avoid expanding into their mature workflows before proving the watch experience. |

Exact prices can vary by storefront, plan, and change date. Public pricing does not prove conversion, profitability, satisfaction, or market size. No defensible total addressable market or competitor performance ranking emerged from this research.

**Recommended positioning hypothesis:** a wanted-product watchlist that filters for the exact item, seller, and budget, explains the evidence, and helps you stop looking once your goal is met.

Lead customer messaging with fewer irrelevant alerts and less manual checking. Explain no retailer-password collection, open code, and export underneath that promise. Do not lead with 'decision console,' 'agent,' 'source adapter,' or an architecture diagram. Do not advertise guaranteed stock, guaranteed savings, fastest alerts, nationwide shelf inventory, or automatic purchasing.

Open-source code is a credibility mechanism and distribution asset. A more durable advantage could be well-matched product data, permitted merchant relationships, trustworthy operational history, and exceptionally simple workflows. All remain hypotheses until demonstrated.

## 6. Data feasibility: the business-critical dependency

Permission must cover the actual workflow: polling, commercial use, client distribution, caching, derived histories, user export, public fixture redistribution, attribution, and termination. An accessible endpoint, an affiliate account, and an open-source adapter each answer different questions.

| Source route | What current primary material establishes | Planning consequence |
|---|---|---|
| Best Buy APIs | Terms restrict credential disclosure and third-party API access, cap temporary content caching at 72 hours, require attribution/branding, and list 50,000 calls/day and 5/second per key. A quota overrun can return 403. [Official terms](https://developer.bestbuy.com/legal). | Plausible investigation candidate, not approved coverage. Determine the permitted client/service model and whether the desired history/export is allowed. Batch where permitted. |
| Amazon Associates data | Policies restrict price tracking/alerts without agreement and constrain client-side storage/caching of Product Advertising Content. [Official program policies](https://affiliate-program.amazon.com/help/operating/policies). | Do not treat an Associates integration as default authorization for this product. Obtain the specific agreement or exclude it. |
| Target | Terms reviewed restrict automated scraping/commercial reuse and require authorization for agentic interactions. [Target terms](https://www.target.com/c/terms-conditions/-/N-4sr7l). | A customer's permission is not retailer authorization. No assumed Target connector or checkout roadmap. |
| Walmart / Pokémon Center | Useful, authorized, consumer-monitoring access was not established by this audit. Marketplace/seller APIs are not automatically a consumer-wide inventory feed. | Record as unproven, not impossible; do not sell coverage. |
| eBay | Official Buy APIs are a possible marketplace path, subject to approval, limits and terms. [Buy API requirements](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html). | Seller/listing/condition matching and marketplace noise make it a different wedge from first-party sealed restocks. |
| TCGplayer | Official documentation says it is no longer granting new API access. [Getting started](https://docs.tcgplayer.com/docs/getting-started). | Do not schedule a new direct integration as routine work or use someone else's grandfathered key. |
| PriceCharting data | API documentation provides current values, not historical prices or sales. [API documentation](https://www.pricecharting.com/api-documentation). | A potential licensed valuation input is different from a live restock feed or historical comparable-sales source. |
| Direct merchant partnership | Shopify documents inventory-related webhooks as an alternative to polling; delivery may be duplicated, missed, or out of order. [Shopify webhooks](https://shopify.dev/docs/apps/build/webhooks). | Explore a willing card shop's authorized feed. This requires merchant permission, scoped access, reconciliation, and usually a service endpoint. It is not permission to monitor arbitrary Shopify stores. |

**An underexplored strategy:** work with one to three independent card shops that want interested buyers. Ask whether they can supply an approved availability/price feed, with agreed freshness and display rights. This might produce both data and a recruitment channel. It could also fail because shops do not need help selling popular stock or refuse integration work. Test that incentive directly; do not build merchant software first.

Add these fields to every source charter:

| Area | Required answer |
|---|---|
| Identity | Merchant, data provider, permission holder, API/version, geographic coverage |
| Access | Public versus confidential credential; who may hold it; distribution and per-user rights |
| Semantics | Seller, fulfillment, variant, condition, preorder/backorder, membership, location, source timestamp |
| Work budget | Per-key/per-account/per-IP/per-merchant limits, batching, burst caps, retries, permitted cadence |
| Rights | Display, caching TTL, history, aggregates, export, fixtures, images, attribution, affiliate links |
| Operations | Cost minimums, termination, policy-review date, outage contact, disable behavior, deletion obligations |
| Product fit | Product coverage and opportunity duration for this cohort; measured usable lag and mismatch rate |

Every source should advertise capabilities such as `can_monitor_stock`, `can_show_price`, `can_retain_history`, `can_export_evidence`, and `requires_attribution`. User-authored wants and notes should remain exportable even when third-party content cannot be included.

If no qualifying source exists, the result is a valid feasibility finding. Keep the work a manual/prototype utility or change the customer/source strategy. Do not describe that as a successful live-restock launch.

## 7. Correct the product and measurement contract

### The timing problem

Suppose an offer remains available for 60 seconds and a healthy monitor checks every five minutes. With a uniformly random restock start, instantaneous current source data, and instantaneous requests, its chance of overlapping that stock window is only `60/300 = 20%`. If monitoring covers half of the day and events are uniformly distributed across that day, that illustrative chance becomes about 10%. Source lag, notification delay, and human response can reduce it further. These are simplifying examples, not observed retailer statistics.

A five-minute poll has an average wait of 2.5 minutes for a randomly timed persistent change. It cannot credibly support a blanket 'instant restock' promise. Conversely, a replenishment lasting hours may work perfectly well with that cadence. **Choose the opportunity duration before choosing the product promise.**

### Replace the success dashboard

| Measure | Definition | Why it matters |
|---|---|---|
| Supported-want coverage | Wanted listings the product can actually monitor / eligible wants submitted by pilot users | A perfect connector for unwanted products is not product-market fit. |
| Monitoring coverage | Time the configured watch had sufficiently fresh usable evidence / intended monitoring time | Includes sleep and outages; no success-only denominator. |
| Conditional scheduler reliability | Checks started within tolerance / due checks under explicitly defined runnable conditions | Useful engineering measure, separate from customer coverage. |
| Alert precision | Verified correct item/seller/price/availability alerts / alerts independently assessed | Captures false positives; report the assessment delay. |
| Opportunity capture | Relevant events detected / relevant events independently established | Requires reference evidence. If unknown, report unknown rather than 100%. |
| Evidence lag | Receipt time minus trustworthy source observation time | Distinguishes a fast poller from a stale upstream feed. |
| Reference detection lag | Our detection minus a reference observer's detection | Label as relative lag; it is not necessarily time since actual restock. |
| Actionability | Assessed alerts for which the offer remained purchasable when opened / assessed alerts | Closer to value; affected by user delay and retailer conditions. |
| Time saved | Participant-reported reduction in manual checks, supported by diary examples | Do not turn guessed savings into marketing dollars. |
| Ongoing value | Participants maintaining useful wants, evaluating alerts, or explicitly retaining monitoring after four weeks | Weekly app opens undercount the value of a quiet background utility. |
| Cost and maintenance | Cost per useful observation; support minutes; connector repair hours; incidents | Determines sustainable scope and price. |

The existing 95% pilot target is reasonable as a directional check, but sample size matters. **19 correct alerts out of 20 is 95%, with a roughly 76% lower bound on a two-sided 95% Wilson interval.** Even 95/100 has a lower bound around 89%. Repeated observations of the same stock event are correlated and should not inflate the effective sample size.

Use independent offer episodes across days, products, and failure states. Record false negatives separately; random background spot checks help uncover them. A sold-out page five minutes after an alert may be a real short-lived opportunity rather than a false positive. Keep timestamped evidence for that distinction within source rights.

For early validation, use the pack's 10 interviews and 10-person pilot as qualitative decision aids. Add a second cohort before treating conversion or retention percentages as stable. Ask at least some non-Mac users about the problem so the platform choice is not validated solely by a Mac-only recruitment filter.

## 8. Technical and security corrections

### Notification delivery: fix the impossible guarantee

Apple documents that reusing an identifier for an already delivered notification can alert the user again while replacing the prior notification. Therefore an outbox key is not an exactly-once delivery primitive. [Apple notification request initializer](https://developer.apple.com/documentation/usernotifications/unnotificationrequest/init(identifier:content:trigger:)).

Recommended model:

1. Create one durable logical alert in the application inbox, transactionally with eligible evidence.
2. Track OS notification attempts separately from the logical event. States include pending, attempting, accepted by OS, failed, expired, and outcome uncertain.
3. Expire stale alerts and recheck current rule, source status, and consent immediately before submitting.
4. On an ambiguous crash boundary, reconcile available OS state. An absent notification is not definitive proof it was never shown; the user may have dismissed it. [Apple delivered-notification API](https://developer.apple.com/documentation/usernotifications/unusernotificationcenter/getdeliverednotifications(completionhandler:)).
5. Choose a documented tradeoff. For this calm-alert product, prefer avoiding automatic audible replay of an uncertain attempt, while preserving its inbox record. Explicit user-requested resend is separate.
6. Treat OS acceptance as acceptance, not proof the person saw a banner. Focus, settings and delivery behavior remain outside the app's full control. [Apple scheduling API](https://developer.apple.com/documentation/usernotifications/unusernotificationcenter/add(_:withcompletionhandler:)).

Test a crash after OS submission but before persistence on a real supported macOS build. Mocks alone cannot validate platform behavior.

### Data model: distinguish the thing wanted from the offer observed

| Concept | Example / invariant |
|---|---|
| Goal | 'Obtain one copy of this product under my limit.' Later may accept several explicit alternatives. |
| Product/variant | Exact edition, language, sealed condition, package type, pack count; stable identity where available. |
| Source listing | Retailer/provider identifier and validated canonical destination; URL is not the only identity. |
| Offer context | Listing + seller + fulfillment + region/store + currency + membership conditions. |
| Observation | Facts supplied for that context, with source time if known, retrieval time, expiration, and permitted evidence. |
| Rule | User constraint with version, threshold basis, accepted contexts, quantity semantics and notification policy. |
| Match state | Per rule and offer context; source A's no-match cannot re-arm source B's unchanged match. |
| Grouped alert | One understandable decision can summarize matching offers without erasing their separate evidence. |

A v1 limited to one exact offer context per watch can use a smaller schema, but the UI and requirements must say so. One listing alone may still contain multiple sellers or fulfillment options. Do not build global catalog reconciliation just to anticipate a future multi-retailer platform.

### Scheduler and policy mechanics

- Add a monotonic **lease generation/fencing token**. A timed-out request may return after a replacement run starts; only the active generation may update current state or alert eligibility.
- Persist source-policy generation as a real schema field. Make deletion/global pause invalidate in-flight runs as well as watch-specific edits.
- Schedule one permitted fetch per identical offer context and fan out evaluation to applicable rules. Identical URLs are not sufficient when store, seller or account context differs.
- Admit work according to source capacity. If users add more watches than the quota can serve, show the achievable cadence or decline new active monitoring. Do not silently fall behind.
- Scope circuit breakers appropriately: one malformed product should not necessarily disable the entire retailer; source-wide denial should not trigger per-watch retries.
- Implement `Retry-After`, bounded jitter, response deadlines and byte/decompression limits. Do not retry a permanent failure as transient.
- Resolve `304 Not Modified` using the cached representation and the source contract. HTTP validation cannot invent newer inventory evidence than the upstream system provides.
- Define quiet hours across midnight and daylight-saving changes. After a quiet period, send an optional summary of still-relevant items rather than every queued historical alert.
- Record a heartbeat and reconstruct uncertain monitoring gaps after a crash; do not invent exact sleep/quit timestamps that were never recorded.
- Keep polling independent of delivery: unchanged matches and unknown results also complete a run and schedule the next check. A stuck notification outbox cannot freeze observation.
- Store the rule's relevant historical contents and evaluator/fingerprint versions with an explanation, within retention rights. Revision numbers alone cannot reconstruct old behavior.

### Platform, storage and release

The native modular monolith remains a reasonable Mac implementation choice. Rust helpers, a distributed event platform, and a full cloud control plane would add complexity before the source/customer gate. Modular contracts matter more than having six separately published packages.

Mac lifecycle testing must include App Nap and timer throttling; being awake is not a scheduling guarantee. Keep permission claims tied to measured behavior. [Apple energy-efficiency guidance](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/AppNap.html).

SQLite's current documentation describes a WAL-reset race fixed in 3.51.3 and later, with backports including 3.44.6 and 3.50.7. The affected conditions involve multiple connections writing/checkpointing concurrently. Record the actual SQLite build and checkpoint topology; do not infer that macOS system SQLite is affected without inspection. [SQLite WAL documentation](https://www.sqlite.org/wal.html#walreset). Also distinguish process-crash durability from power-loss durability when choosing synchronous settings. [SQLite synchronous settings](https://www.sqlite.org/pragma.html#pragma_synchronous).

Add disk-full behavior, bounded history, interrupted imports, backup restoration, unknown future schemas, and old app/new database handling. 'Rollback' should normally mean a safe forward fix or restoration of a validated backup, not blindly reversing arbitrary migrations.

URL validation must handle userinfo, lookalike hosts, encoded separators, nonstandard ports, shorteners and redirects. Remote images, if later added, are another outbound network surface. Sanitize titles and error strings before UI/log display. CSV exports need formula-injection protection while preserving underlying data for JSON round trips.

Configure HTTP persistence explicitly. An ephemeral session avoids persistent cache/cookie/credential storage but may still hold state in memory. Disable unwanted cookie handling and authentication behavior separately; errors can contain sensitive URLs even when the database does not. [Apple ephemeral URLSession configuration](https://developer.apple.com/documentation/foundation/urlsessionconfiguration/ephemeral).

Source revocation remains a real operating issue even with no cloud account. An old local version can continue polling after policy changes. Choose either an explicit supported-version/renewed-policy process with honest offline limits, or a minimal authenticated, non-executable policy update channel. Never claim a reliable remote kill switch that has not been built.

Keep direct public consumer downloads signed and notarized. Unsigned builds can remain developer artifacts with distinct labels. Isolate stable/beta data and separately coordinate active monitoring ownership; isolated databases alone do not prevent duplicate polling. A checksum, reproducible build, code signature and notarization answer different trust questions; none is a blanket safety certification.

## 9. Edge-case register

These supplement the existing test plan. Some are expansions of existing controls rather than wholly absent topics. Resolve core cases before beta; defer future-only cases with the corresponding feature.

| # | Scenario | Required behavior / test |
|---:|---|---|
| 1 | Retailer changes a listing from one box to a bundle while retaining URL | Detect identity drift; require renewed match confirmation. |
| 2 | Same artwork, different language or special edition | Match explicit variant evidence; no title-only confidence. |
| 3 | Price refers to one pack, thumbnail shows a display box | Store unit and pack count; show the priced unit prominently. |
| 4 | Marketplace seller changes under the same product page | Seller constraint is evaluated per observation. |
| 5 | Product available to preorder/backorder but not ready to ship | Distinct fulfillment states; default in-stock watch excludes them. |
| 6 | Membership, coupon, subscription or new-customer-only price | Label conditional price; do not treat it as generally available. |
| 7 | Online shipping available but not for the selected region | Match deliverability context; unknown region eligibility remains unknown. |
| 8 | Pickup inventory and shipping inventory disagree | Never collapse them into one available flag. |
| 9 | Available quantity is unknown but user wants two | Do not promise two units; show quantity uncertainty or restrict v1 to availability of one. |
| 10 | Retailer min quantity, multipack or case-only sale | Evaluate actual purchasable unit and total item price. |
| 11 | User sets an unattainable threshold | Show tracking history and rule summary without falsely promising likely fulfillment. |
| 12 | Tax/shipping unknown, but item price qualifies | Alert explicitly on item price; do not label the total under budget. |
| 13 | Threshold changes from $40 to $50 during fetch | Old revision cannot trigger; Save semantics define future arming. |
| 14 | Price flips around threshold every poll | Apply documented material-change/hysteresis policy. |
| 15 | Out-of-stock episode occurs entirely between polls | Do not claim to have observed the restock; disclose cadence limits. |
| 16 | Source A stays matched; source B toggles stock | Separate state avoids repeat alerts for A. |
| 17 | Two watches refer to the same offer with different budgets | Share permissible fetch, evaluate rules independently, group carefully. |
| 18 | A timed-out request completes after lease replacement | Fencing rejects its state/alert commit. |
| 19 | Pause/delete occurs during fetch or OS submission | Prevent future eligible work; document that an already submitted OS notification may still appear. |
| 20 | Rule deleted, then imported under a new ID | Import cannot replay old outbox or restore spending authority. |
| 21 | OS accepts notification, app crashes before recording it | Use uncertain-delivery policy; no unconditional replay. |
| 22 | Notification dismissed before crash recovery | Absence from Notification Center is not proof of non-delivery. |
| 23 | Focus or permission suppresses a banner | Preserve inbox state; distinguish OS acceptance from human visibility. |
| 24 | Quiet hours end after stock has disappeared | Expire alert or summarize historical activity without a fresh-stock claim. |
| 25 | User opens an alert days later | Show age/current status; offer retailer link without implying current stock. |
| 26 | Mac awake but app quit, hidden, throttled or logged out | Show truthful reconstructed coverage, not continuous monitoring. |
| 27 | Clock jumps or user changes timezone | Persist UTC; use monotonic delays in process; recompute due/quiet-hour state. |
| 28 | 100 watches become overdue on wake | Bounded catch-up and latest-evidence alerts; no replay storm. |
| 29 | Source returns cached success with old data | Preserve upstream age; retrieval success does not refresh truth. |
| 30 | HTTP 304 without usable local representation | Retry within policy or mark unknown; never fabricate an observation. |
| 31 | HTTP 200 contains login/CAPTCHA/maintenance content | Typed failure; no parser fallback to in stock. |
| 32 | 403 indicates quota rather than forbidden access | Source-specific error classification and appropriate backoff. |
| 33 | One malformed listing among otherwise healthy products | Isolate watch failure when evidence supports isolation. |
| 34 | No source timestamp or timestamp from the future | Mark source time unknown/invalid; record receipt time separately. |
| 35 | Source rights change or a license expires | Disable affected capability; expire content per agreed terms. |
| 36 | Browser changes destination after handoff | Do not claim app control of subsequent browser navigation. |
| 37 | CSV starts a cell with formula syntax | Safe presentation export; raw text stays data, never executable formula. |
| 38 | Huge/deep/malformed import or response | Size/depth/time limits; no partial destructive import. |
| 39 | Disk fills mid-transaction | Preserve committed data; stop/recover visibly without reset. |
| 40 | Exporter holds a database read transaction too long | Bound transaction duration and checkpoint growth. |
| 41 | Deletion request conflicts with append-only evidence | Implement defined erasure/expiry policy; preserve only permitted metadata. |
| 42 | Backup restores old alert state on another install | Import watches paused; do not restore active delivery attempts. |
| 43 | Stable and beta run simultaneously | Isolate state and monitoring or enforce single ownership. |
| 44 | User buys elsewhere or no longer wants the item | 'Got it' and 'No longer wanted' pause linked watches; no fake purchase detection. |
| 45 | Paid cloud and local monitor the same goal later | Explicit ownership and cross-device logical-event dedupe. |
| 46 | Payment fails, plan expires, source disappears | Clear grace/stop policy; saved wants/export remain available; no surprise overage. |
| 47 | Cloud webhook arrives twice or out of order | Verify signature, dedupe event IDs and reconcile authoritative state. |
| 48 | User forgets that budget totals are manually entered | Label budget completeness and last manual update. |

Shopify's product schema explicitly distinguishes an available-for-sale variant from a currently-out-of-stock variant that can still be purchased, illustrating why a generic purchasable flag is insufficient. [ProductVariant reference](https://shopify.dev/docs/api/storefront/latest/objects/ProductVariant).

## 10. New product opportunities

The pack already proposes budgets, exact matches, evidence cards, history, export, local inventory, collection ledgers, discovery, and future sync. Those should not be presented as new ideas. The following are new workflows or meaningful extensions.

| Idea | User benefit | Complexity / risk | Recommendation and validation |
|---|---|---|---|
| **Goal-based alternatives** | 'Either of these editions is fine; I only want one.' Group explicitly accepted products into one goal. | Medium: alternative rules and alert grouping; substitutions must be opt-in. | Highest-priority differentiator after one-listing reliability. Test with people already maintaining several duplicate wants. |
| **Got it / stop looking** | One click completes a goal and pauses related watches, including purchases made elsewhere. | Low locally; needs clear undo. | Add early. Track whether it reduces unwanted follow-up alerts. |
| **Why no alert?** | Explain no checks, stale evidence, price too high, wrong seller, or suppressed duplicate. | Low–medium using existing decision records. | Early extension of evidence inspector. Do not expose debug jargon. |
| **Coverage preview before setup** | Tell users immediately whether their retailer/item/region can be monitored and at what cadence. | Low once capability registry exists. | Core onboarding change; measure fewer abandoned or falsely configured watches. |
| **Deadline and delivery-window wants** | Gift or release goal expires after a date; alert only if arrival evidence is adequate. | Medium; delivery estimates are often unknown. | Pilot a simple watch-expiry date first. Do not promise delivery without evidence. |
| **Pack/unit comparison** | Compare cost per booster across eligible sealed formats without confusing a pack with a box. | Medium; exact contents and bonuses matter. | Test as an optional explanatory field, not automatic equivalence. |
| **Budget cooling-off mode** | Pause opportunity prompts until a chosen date or budget reset. | Low for manual state; avoid paternalistic overrides. | Small, distinctive option for users who want less spending pressure. |
| **Opportunity-duration history** | Show how long observed stock episodes lasted so users can choose a realistic monitoring mode. | Medium–high: sampling bounds and data retention rights. | Later experiment. Label observed lower/upper bounds; avoid predictive guarantees. |
| **Small-shop feed partnerships** | More relevant permitted inventory with a direct merchant relationship. | High business effort; smaller catalogs; uncertain incentives. | Research now; only implement after a willing partner and user demand. |
| **Portable goal bundles** | Import a curated list of wanted products/rules without requiring an account. | Medium: data rights, untrusted links, preview and opt-in. | Growth experiment after import safety; shared lists cannot silently activate monitoring. |
| **Phone notification bridge** | Receive an actual local alert while away from the desk without a full native mobile app. | Medium: separate credentials, provider privacy, latency and support. | Test earlier if phone delivery matters. It does not make a sleeping Mac monitor. |
| **Named gift coordination** | Family members can mark an item claimed and avoid buying duplicates. | High: accounts/sharing, privacy and conflicts. | Later only after goal completion works locally. |
| **Purchase-window follow-up** | User-entered purchase date can produce return/price-adjustment reminders. | Medium: merchant rules and privacy. | Later bounded feature; no inbox scanning or guaranteed eligibility by default. |
| **Natural-language rule draft** | Translate 'new, sold by the retailer, under $40' into a visible editable rule. | Medium: interpretation mistakes and AI expense. | Optional late convenience. Deterministic validation and user confirmation remain authoritative. |

An existing notification service such as ntfy demonstrates that a phone bridge need not start with a full mobile client. Its public unauthenticated topic model also illustrates why integration requires explicit privacy/authentication design rather than sending shopping details to a guessable channel. [ntfy documentation and product](https://ntfy.sh/).

For the first release, select at most three additions: coverage preview, goal completion, and 'why no alert?' Goal alternatives follow once identity and state are stable. New features cannot compensate for weak source coverage.

## 11. What to charge and whether it can make money

### One simple offer to test

| Offer | Recommended experiment | What the customer gets / limits |
|---|---:|---|
| Local | **Free** | Official signed client, saved wants, eligible local monitoring, clear history within data rights, import/export of user-owned data. Active work remains subject to source capacity. |
| Cloud | **$5.99/month** | Permitted hosted monitoring while the Mac is unavailable, plus one supported remote notification channel. Begin with a proposed cap of 20 active retailer listings; validate cost before promising the cap or cadence. |
| Cloud annual | **$59/year**, later | Same service after monthly reliability and renewal evidence. Roughly 18% below twelve monthly payments. |
| Supporter | Optional voluntary contribution | Funds the free project without an indefinite support or hosting promise. Keep official signed downloads accessible. |

Keep unlimited **saved wants** distinct from unlimited **active checks**. A goal spanning three listings consumes three plan targets even if the implementation can fetch them in one permitted request. Internal batching reduces cost without making the allowance unpredictable. Explain the limit in normal product language; customers should not face surprise API-unit bills.

Cloud monitoring, cloud sync and native mobile apps are separate capabilities. A first paid monitoring service can deliver one channel without syncing an entire collection. Do not include SMS, multiple native platforms, encrypted sync, full valuation, or automated checkout in a $5.99 promise before costing them.

This price is a starting hypothesis. It is close enough to established alert subscriptions that the product must demonstrate an actual advantage. If costs require $7.99 and customers will not pay for the delivered service, the correct response may be smaller scope or a free project—not a permanently loss-making $3.99 plan. Test sequential offers with comparable cohorts; tiny samples cannot establish a statistically optimal price.

Do not introduce annual prepayment merely to cover cash shortages. It creates an obligation to provide the service. Do not promise lifetime cloud access, unlimited source work, or permanent support for a retailer that may withdraw access. If demand is seasonal, test a clearly nonrenewing 30-day pass later rather than manufacturing engagement to discourage cancellation.

### The original spreadsheet arithmetic is not the main problem

06's approximately 114-customer break-even is consistent with its stated assumptions. The problem is those assumptions: six support hours stay fixed from 50 to 500 customers, annual pricing is absent, and several recurring costs are excluded. The polling calculation for 20 products every five minutes across 12 hours is also correct.

For comparison, current US Stripe standard domestic card processing is 2.9% + $0.30; pay-as-you-go Stripe Billing adds 0.7% of Billing volume. The following model assumes both, with no custom contract. Other methods, cross-border charges, tax tools, refunds and disputes can differ. [Stripe Payments pricing](https://stripe.com/pricing), [Stripe Billing pricing](https://stripe.com/billing/pricing).

**Illustrative scenario, not a forecast or supplier quote:** per paying customer per month, $1 data/compute/delivery + two support minutes at $45/hour ($1.50) + $0.12 loss reserve. Fixed monthly costs are $900: an assumed $780 routine maintenance allowance and $120 fixed operations/memberships. New feature development, tax, acquisition, free-user cost and additional data-license minimums are excluded and must be separately budgeted.

`monthly contribution/customer = price − (0.036 × price + 0.30) − 1.00 − 1.50 − 0.12`

| Monthly price | Payments + Billing | Contribution per customer | Contribution as % of revenue | Paying customers to cover $900 fixed |
|---:|---:|---:|---:|---:|
| $4.00 | $0.44 | $0.94 | 23.4% | 962 |
| $4.99 | $0.48 | $1.89 | 37.9% | 477 |
| **$5.99** | **$0.52** | **$2.85** | **47.7%** | **316** |
| $7.99 | $0.59 | $4.78 | 59.9% | 189 |

Calculations use unrounded intermediate values. 'Contribution' here includes an allocation for variable support; it is not accounting net profit.

For annuals, allocate net annual revenue across the full service year. In the same scenario, **$36/year leaves only about $0.25/month contribution**, whereas **$59/year leaves about $2.09/month**, requiring approximately 430 annual subscribers to cover the assumed fixed cost. A blended customer base needs weighted margins.

At 500 monthly subscribers paying $5.99, revenue is $2,995/month but this scenario leaves **about $527/month after fixed costs**, before the omitted items. An additional $1,000 monthly license minimum would require about 351 more monthly subscribers at the same margin. Two thousand free users costing only $0.10 each add $200/month. A ten-minute support incident costs $7.50 at the assumed labor rate.

These numbers do not show the business cannot work. They show why cheap pricing, unlimited promises and uncounted founder labor can make an apparently successful launch unprofitable. Measure actual support frequency, data cost, and source repair time before deciding the steady-state price.

### Cost drivers and capacity

Hosted monitoring runs 24 hours, so the pack's local example doubles: 20 listings checked every five minutes produce 172,800 checks per 30-day month before batching/sharing. At 1,000 such accounts, naïve individual polling means 172.8 million checks.

If all users share the same 100 eligible listing contexts, five-minute polling needs 864,000 monthly requests instead, assuming one request per context. At 1,000 distinct contexts it is 8.64 million. Batching can reduce requests; different sellers, stores, geography, membership or user-specific data can prevent sharing. Terms may restrict redistribution even where sharing is technically easy.

Model source work by **unique authorized offer context × cadence**, then add fan-out delivery, storage, billing and support. Measure retry work and failures, not just successful observations. Avoid caching or retention shortcuts that violate source terms to make the model appear affordable.

### Acquisition and churn

At the scenario's $2.8544 monthly contribution, a three-month acquisition payback target allows only about **$8.56 acquisition cost per paying customer**. This is a chosen conservative operating target, not a universal industry rule.

| Assumed monthly churn | Simplified contribution lifetime value (`2.8544 / churn`) | One-third of that value |
|---:|---:|---:|
| 3% | $95.15 | $31.72 |
| 6% | $47.57 | $15.86 |
| 10% | $28.54 | $9.51 |

Constant-churn models are crude, especially for an episodic collecting product. Annual subscribers require a different renewal model. Use actual cohorts and the tighter cash/payback constraint before scaling acquisition. Count creative production and founder time in acquisition costs.

## 12. How to market the product

### The first audience and message

Recruit collectors already tracking a few specific products who can show recent frustrating alert experiences. Include paid-tool users, free-alert users and people who stopped using alerts. Exclude high-volume resale automation from the first offer. Record Windows/phone-only interest even if the pilot is Mac-first.

Test three benefits independently: exact item/seller/price relevance, less manual checking, and calmer goal completion. Ask participants which matters in their last actual buying attempt. Privacy and open code may be decisive for a subset; do not assume they dominate for everyone.

The first landing page should show:

1. A short explanation of the specific collector outcome.
2. A 30–45-second original demo, with synthetic evidence clearly labeled if used.
3. Exactly which sources, product types and regions are supported.
4. A realistic example showing seller, variant, item price, unknown fees, and observation age.
5. Mac/local monitoring limitations before download; hosted differences beside any future price.
6. A signed download when ready, or a clearly labeled opt-in pilot invitation before that.
7. Independent branding, concise privacy facts, and an honest support route.

Do not publish unsupported retailer logos as a coverage wall. Do not turn a sample alert into a testimonial or use a guessed 'money saved' counter. A comparison page can explain verified capability differences with a dated source; it should not imply Guppy is unsafe or that this untested app has superior purchase success.

### Channels and experiments

| Channel | First experiment | Measure / stopping rule |
|---|---|---|
| Collector network and card-show conversations | Conduct 10–15 initial interviews, then invite qualified participants into an opt-in pilot. Use a QR demo only where organizers permit it. | Actual problem fit and real supported watches. Track founder hours. |
| Collector communities | Obtain posting permission; share one useful demo or transparent pilot result. Answer replies personally. | Qualified activations and useful outcomes, not likes. Stop if the audience mainly wants unsupported checkout races. |
| Small collector creators | Invite two or three relevant creators to test the real workflow; disclose any benefit or sponsorship. | Retained activations and later renewals, with a bounded test cost. No large upfront campaign before margin is known. |
| Independent card shops | Explore an approved inventory feed and collector pilot referral together. | Merchant willingness, usable data and buyer outcomes. No paid ranking disguised as relevance. |
| Search content | Publish a few accurate guides about product variants, marketplace sellers, pack counts and alert limitations. | Supported-watch activation from search. Avoid mass-generated empty product pages. |
| GitHub and Mac communities | Explain the independent code, build process, limitations and contribution needs. | Trusted installs and useful contributors. Stars do not establish customer demand. |
| Optional referrals | After a useful outcome, offer a shareable read-only goal template or referral link. | New retained users. No address-book access or automated invitations. |
| Paid ads | Defer until measured contribution and repeat payments; then run one capped test. | All-in CAC and cash payback. Stop when the measured ceiling fails. |

Begin with **two channels**, probably founder collector contacts and one permitted collector community. Maintaining eight channels would consume the same limited time needed to repair connectors and help users.

An illustrative funnel shows the scale challenge: 1,000 qualified visitors → 200 downloads → 120 real activations → 60 retained users → 12 paid users generates $71.88 monthly revenue at $5.99. These conversion rates are assumptions, not benchmarks. Track each denominator and the number excluded because their desired source or device is unsupported.

Define activation as a real wanted supported listing, understood limits, fresh useful observation, and a tested reachable alert path. A sample watch, download, GitHub star or waitlist email is not activation. A click to a retailer is not a completed purchase.

### Retention that fits a collector utility

The product should help users finish goals, including deciding not to buy. Distinguish successful-completion churn, seasonal pauses, source-loss churn, price churn, and dissatisfaction. A background watch that remains useful does not need weekly app opens to justify its existence.

Test whether people create their next goal, keep a wanted item monitored, or renew after their first success. Do not add a noisy feed merely to manufacture weekly active usage. A calm optional summary can report valid opportunities and reasons a rule stayed silent without pushing more spending.

## 13. Revised execution and validation sequence

These are calendar checkpoints, not a promise that a part-time founder ships in 90 days. Proceed only after the preceding evidence supports the next investment.

| Period | Work | Go / narrow / stop evidence |
|---|---|---|
| Days 1–14 | Write a one-page customer/occasion charter. Interview 10–15 collectors. Review one primary source and a backup route. Run a permitted bounded data probe. Test notification crash semantics and a simple UI concept. | Useful access, relevant wanted products, and opportunity windows compatible with the delivery path. If any fails, change the source/customer promise before a full app sprint. |
| Days 15–30 | Extend source observation toward 7–14 days where permitted. Compare with participants' existing workflow. Resolve source auth/retention and the local-versus-service decision. | At least six of ten interviewed users describe a recurring problem; multiple independently assessed opportunities show credible actionability. These are proposed directional gates, not proof of product-market fit. |
| Days 31–60, when build is ready | Build the smallest signed real-source slice and run a 10–15-person pilot. Gather weekly participant-approved local summaries. Exercise outages, stale outbox, sleep, import and recovery. | Several users report concrete useful decisions; correct identity/price and coverage metrics are acceptable for the chosen use. Maintain the original 6/10 continued-value gate but do not equate it with app opens. |
| Days 61–90, conditional | Expand only enough to test one paid hosted offer with 20 qualified prospects. Run at most two acquisition channels. Record starts, refunds, support and renewals. | A provisional learning gate is five paid starts out of 20 eligible offers plus evidence of repeat payment; insufficient alone to prove pricing. If users only want a free tool, keep it bounded or revise the paid value. |
| After repeated paid cohorts | Add one source or one important workflow at a time; assess source concentration and acquisition payback. | Positive measured contribution, acceptable maintenance workload, repeat utility and demonstrated demand for the expansion. |

No paid experiment should begin before the service exists sufficiently to deliver the stated offer, with clear terms and support. This report recommends experiments; it does not authorize collecting money or contacting prospective users by itself.

### Re-scope the first build

Use one source, one category, one permitted fulfillment mode, USD, quantity one, and one exact offer context per watch if source/customer research supports those limits. Include evidence, pause, truthful status, an inbox, safe handoff, portable user-owned configuration, and the minimum necessary recovery/release controls.

Keep full collection accounting, valuation, broad discovery, store radar, scanning, encrypted sync, checkout, queues and community moderation deferred. Move the R16 personal budget view to a clearly owned ticket or defer it explicitly; do not leave it in release acceptance while excluding it from the implementation plan.

A source permission probe is not a production adapter. It can resolve field availability, applicant eligibility, latency and data rights before building the entire module structure. Production integration still requires the tested contracts.

Convert estimates into focused effort and actual weekly capacity. If an estimate implied 280–440 focused hours, 10 hours/week would imply 28–44 weeks before external delays; that is an arithmetic illustration, not a fresh estimate for this implementation. External access approval and pilot observation can run in parallel with some development but cannot be compressed by code generation alone.

### Explicit stop and pivot options

| Failure evidence | Appropriate response |
|---|---|
| No useful permitted feed | Stop promising restock automation. Explore a partner feed or keep a manual local utility. |
| Most value requires seconds-long checkout races | Change initial customer or independently reassess authorized purchase assistance; do not smuggle it into alert scope. |
| Useful alerts but almost all customers need phones/continuous monitoring | Revisit delivery architecture before polishing a Mac-only application. |
| Retention exists but willingness to pay does not | Keep a small free project with a maintenance budget; test a materially different paid service. |
| People pay but source/license costs erase contribution | Narrow source/cadence/cap, renegotiate, or increase price and revalidate. |
| Connector maintenance exceeds the founder's weekly budget | Reduce supported sources and commitments; do not expand platforms. |

## 14. Paid-launch, privacy, licensing, and operating checks

These are tied to the proposed offer, rather than a reason to build compliance infrastructure into the local prototype.

| Topic | Concrete requirement to settle |
|---|---|
| Recurring billing | Clear renewal/price terms, affirmative consent, receipt/acknowledgment, accessible cancellation, required notices, billing-failure and refund handling. California's current rules need offer-specific review. [California BPC §17602](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=17602.). |
| Federal rule freshness | Do not copy obsolete summaries of the 2024 federal negative-option rule. The FTC's March 2026 announcement refers to its vacatur and new rulemaking. Existing applicable laws still matter; recheck at launch. [FTC announcement](https://www.ftc.gov/news-events/news/press-releases/2026/03/ftc-seeks-public-comment-response-advance-notice-proposed-rulemaking-regarding-negative-option). |
| Existing federal subscription duties | ROSCA requires material-term disclosure, informed consent and a simple way to stop covered recurring charges. The vacated rule does not remove these obligations. [ROSCA statutory text](https://www.ftc.gov/system/files/documents/statutes/restore-online-shoppers-confidence-act/online-shoppers-enrolled.pdf). |
| Affiliate/creator relationships | Explain compensation where the recommendation appears; preserve objective ranking and non-affiliate results. Do not budget speculative commissions as guaranteed revenue. [FTC endorsement guidance](https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking). |
| Email | Separate operational alerts/billing from promotion; test unsubscribe and required sender information. Marketing opt-out must not silently cancel paid monitoring. [FTC CAN-SPAM guide](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business). |
| Code and data licenses | Apache-2.0 does not license third-party catalogs, imagery or merchant marks. Maintain separate rights and notices. A use restriction such as 'no resellers' is not the same open-source licensing model. [Apache license](https://www.apache.org/licenses/LICENSE-2.0), [Open Source Definition](https://opensource.org/osd). |
| Brand | Clear the final name through relevant trademark, app, domain and common-law searches. Do not imply Pokémon/retailer affiliation. 'Open Collector' remains a working name. [USPTO search guidance](https://www.uspto.gov/trademarks/search). |
| Audience and data | An adult-directed pilot is simpler, but a label alone does not settle children's privacy obligations. Review actual audience and collection before adding accounts, location or communities. [FTC COPPA guidance](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions). |
| Distribution | Ordinary Apple Developer Program membership is $99/year under published terms. Direct Mac distribution and later App Store distribution have different obligations and economics. [Apple program](https://developer.apple.com/programs/), [Mac distribution](https://developer.apple.com/macos/distribution/). |
| Taxes and business identity | Review the actual service, billing geography and tax obligations with an accountant before charging. Payment processing alone does not settle them. |

Differentiate six user actions: pausing alerts, stopping cloud monitoring, deleting local data, deleting a cloud account, unsubscribing from marketing, and canceling recurring billing. Users should not discover after deletion that a subscription still renews.

For a lost data source, publish what happens to service and billing: notice, replacement if genuinely comparable, cancellation/refund choices consistent with the offer and applicable rules, and continued export of user-owned wants. An annual subscriber losing the only source they use is a product problem, not just a disclaimer problem.

Set operating ownership before charging: source review/repair, support response window, incident communications, release signing/key recovery, billing support, and end-of-service policy. Keep security reports private by default where necessary; scrubbed diagnostics should not be auto-posted into public issues.

Hosted monitoring reveals at least some shopping selectors to the service that performs it. Optional end-to-end encrypted sync would not automatically make server-side monitoring private from that server. Map actual data flows before making encryption/privacy claims.

## 15. Exact amendments to the nine documents

| Document | Keep | Amend first |
|---|---|---|
| README.md | Decisive source/customer questions and clear proposed status | State the chosen initial buying occasion; qualify timeline; align public repo and signed consumer release milestones. |
| 01-product-research.md | Concept inventory, primary-source method, separation from proprietary implementation | Add TrackaLacker, Distill and changedetection.io; mark unreverified prices; add source retention/auth findings; replace 'defensible' assertion with a hypothesis; retire inactive unlimited/pricing alternatives. |
| 02-founder-thesis-and-requirements.md | Exactness, data ownership, no v1 spending | Narrow offer scope; separate logical alert from banner delivery; add actionable coverage/recall metrics; clarify R16 ownership and what user-owned exports exclude. |
| 03-experience-and-ui.md | Calm interface, permissions, visible unknown costs | Coverage preview, stale notification behavior, rule arming, goal completion, explicit import preview, actual browser boundary, privacy-safe lock-screen option. |
| 04-architecture-and-security.md | Modular monolith, transactional persistence, least privilege | Fix notification mechanism; add offer-context state, fenced leases, independent polling/delivery, cache freshness, immutable rule snapshots, session policy, retention and credential topology. |
| 05-execution-plan.md | Dependency-linked gates and release evidence | Move source/lifecycle probes before heavy implementation; add runtime inventory, source capacity admission, hostile imports, signing provenance, safe schema rollback and paid-source loss drill. |
| 06-business-validation-and-launch.md | Free local baseline and explicit assumptions | One active price experiment; annual/support/free-user costs; channel funnel; cohort renewals; source discontinuation/refunds; consented measurement and operating owner. |
| 07-independent-build-and-repository-handoff.md | Fresh repo/history and independent source boundary | Keep internal audit/market material private unless deliberately selected; review fixture/data licenses separately; describe supported service rules without promising control of forks. |
| 08-first-implementation-task-cards.md | Small contracts, targeted tests and completion evidence | T00 adds auth/rights/capacity; T02 offer semantics; T03 retention/provenance; T04 fencing; T05 honest delivery/expiry; T07 safe imports; T08 real-source fit; T09 runtime/release proof. Add owned tickets for any retained acceptance requirement absent from these cards. |

## 16. Next decisions and concrete next work

The next deliverable should be a **short evidence packet**, not a larger feature specification:

1. One chosen customer and buying occasion, with five concrete recent user examples.
2. One candidate source packet covering actual eligibility, credentials, fields, rights, quota and cost.
3. A small permitted observation report with source age, matching accuracy and opportunity duration.
4. A corrected notification experiment and state contract that does not promise exactly-once banners.
5. A prototype of coverage preview → exact watch → useful evidence → handoff → goal completion.
6. A measured maintenance budget and a revised local-versus-hosted decision.

Keep the $5.99 hosted offer as a hypothesis until that packet supports it. If it does, there is a plausible path to a useful, trusted collector utility and a small service business. The decision should rest on usable opportunities and repeat customer value, not feature parity, low price, or the amount of architecture already written.
