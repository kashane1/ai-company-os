# Business, validation, and launch

2026-09-20. All proposed prices, costs, conversion rates, and milestone targets below are planning assumptions. None are customer evidence or a revenue forecast. Current competitor evidence is in [the research brief](01-product-research.md).

## Recommendation

Release the local client free under a real open-source license and make the eventual application repository public. Start with a small Mac pilot. Charge later only for services that deliver recurring value and incur recurring cost: permitted hosted monitoring, optional sync, or support. The free client should remain useful without an artificial watchlist cap, and it must clearly disclose the limits of local monitoring.

Being cheaper than Guppy is possible at a narrower scope; equivalent nationwide data coverage, queue assistance, and unattended checkout at a fraction of the cost is unproven. Guppy's observed September 20 offer is $12.99/month or $119.99/year, per its [pricing page](https://app.guppy.so/pricing). Do not advertise feature parity or superior purchase success without comparative evidence.

## Business choices

| Model | Concrete offer | Strength | Constraint | Suggested decision |
|---|---|---|---|---|
| Fully free, sponsor-funded | Free app, bring-your-own authorized data where needed, donations/sponsorship | Simple trust story, low billing/support complexity | Founder funds maintenance; donated revenue unpredictable | Start here for local alpha |
| Free client + optional hosted service | Local features free; test $4/month or $36/year hosted alerts | Price maps to a real ongoing benefit, especially while Mac sleeps | Data rights, monitoring costs, infrastructure and support must work | Preferred experiment after retention |
| Paid signed convenience build/support | Public source, self-build free, test $19 one-time supported release | Can fund distribution effort without locking data away | One-time price cannot fund indefinite feeds/support; license must permit redistribution | Secondary experiment, time-bound support promise |
| Paid full automation | Test only after robust retailer integration, transaction safety and support | Strong convenience and potential willingness to pay | Highest risk and upkeep; competing chiefly on price can destroy margins | Defer until real demand and costs are known |

No price is approved for publication. Do not promise lifetime cloud monitoring, unlimited checks, or one-time unlimited support. The source license and charging model are separate decisions; a public repository alone does not grant users reuse rights.

## Unit economics worksheet

For the illustrative $4/month hosted service, use:

`monthly contribution = paying users × (price − payment processing − variable service cost) − fixed service cost − support labor`

Example assumptions: $0.42 processing per monthly charge (illustrative, not a quoted processor rate), $0.75 variable service cost per paying user, $80 fixed service cost/month, and 6 support hours/month valued at $40/hour. Taxes, refunds, disputes, data-license minimums, and development time are excluded and must be added before pricing.

| Paying users | Revenue | Processing | Variable service | Fixed service | Support labor | Contribution before omitted costs |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | $200 | $21 | $37.50 | $80 | $240 | −$178.50 |
| 200 | $800 | $84 | $150 | $80 | $240 | $246 |
| 500 | $2,000 | $210 | $375 | $80 | $240 | $1,095 |

Under those assumptions, labor-inclusive break-even is approximately 114 paying users, before the omitted costs. If variable cost becomes $2.75, per-user contribution falls to $0.83 and break-even rises to approximately 386 users. A license minimum can invalidate both cases.

**Polling cost check:** 20 products checked every 5 minutes for 12 awake hours produce 2,880 product checks/day per user, or 86,400 in a 30-day month. At 1,000 users that is 86.4 million checks before deduplication. One request may return multiple products, and shared authorized feeds may reduce load dramatically; the numbers show why a free client is not a promise of free unlimited monitoring infrastructure. Respect source limits even when a user requests faster polling.

Use a measured cost-per-successful-observation and alert precision before setting plans. Meter optional hosted work; show limits clearly. Never monetize by silently selling shopping histories or inserting undisclosed affiliate rankings.

## Validation program

| Experiment | Method | Decision threshold | What failure means |
|---|---|---|---|
| Problem interview | Ten collectors; ask about last actual missed/bad alert and current workflow before presenting a solution | Six independently identify trust/control/friction as a recurring problem | Reconsider wedge; it may be a checkout-speed problem instead |
| Data feasibility | One permitted source; 20–50 products; 7–14 days with manual spot-checks | Rights documented, acceptable interval, ≥95% sampled delivered-alert agreement, measured outages/cost | Do not build a broad live-monitoring promise around inaccessible data |
| UI comprehension | Five moderated sessions with synthetic alerts and sleep/error states | Four of five finish essential watch tasks; all understand whether money can be spent | Revise language and interaction before implementation expands |
| Private local pilot | Ten volunteers, four weeks, explicit consent for any optional diagnostics | Six weekly active at week four; five would miss it; few avoidable false alerts | Improve retention/value before adding platforms |
| Price experiment | Show free local versus optional hosted service to actual retained users | At least five credible opt-ins or paid pilot commitments under disclosed terms | Keep free project smaller or revise service value |
| Maintenance trial | Founder operates connector with simulated breaking changes and a real update | Defined detection, stop, repair, test and signed release path fits chosen time budget | Reduce retailer scope before launch |

Small samples are directional; document denominators and selection bias. Interview notes belong in private research storage with participant consent, not the public app repo. Do not send outreach or collect money as part of this planning task.

## Interview guide

Ask about the last product they tried to buy, where they looked, why an alert failed or helped, which accounts/software they trusted, how they budget, and what they would lose if their current tool disappeared. Ask them to show their process using a non-sensitive example. Only then show the prototype. Avoid asking only “Would you use a free app?”—that does not establish demand or willingness to maintain it.

The most important disconfirming question is whether a careful notification app is valuable without automatic checkout. If it is not, run the assisted-checkout feasibility spike before committing to the recommended MVP.

## Go-to-market sequence

1. Publish the independent source repository with clear scope, sample data, screenshots of our own UI, build steps, known limitations, license, security policy and changelog.
2. Recruit a small opt-in collector pilot through the founder's existing network and communities that allow project sharing. Prepare original announcement drafts; do not spam or automate community posting.
3. Publish measured alert quality and failures, supported sources, and how monitoring behaves during sleep. Invite reproducible bug reports with scrubbed diagnostics.
4. Offer a signed/notarized Mac download only after release gates pass. Distinguish source builds from supported signed builds.
5. Test optional paid monitoring after retention. Introduce Windows/mobile only when user demand and operating costs justify a second support surface.

Potential positioning to test: “A free collector watchlist that shows the evidence behind every alert.” Alternate: “Your collection goals, your budget, your decision.” Neither is a final brand or legal clearance.

## Naming and brand process

OpenTCG is the founder-chosen project name (2026-09-25). Before public launch, check existing apps/projects/domains and relevant trademark conflicts, then choose independently designed visual identity. Do not borrow Guppy's fish character, name, slogans, screen composition, or commercial imagery. A name search and appropriate review precede public launch; no domain purchase is needed for this pack.

## Operating risks and owners

| Risk | Early signal | Owner response |
|---|---|---|
| Retailer/data access unavailable | Access denied, unclear license, unstable HTML | Founder settles source rights; engineering disables unsupported connector |
| Alert fatigue | Low alert-to-open rate, repeated duplicates | Product improves matching, batching, freshness, and quiet hours |
| Security regression | New dependency advisory or widened permissions | Engineering patches/reviews; release owner blocks unsupported builds |
| Maintenance eats side-project time | Repeated connector breakage | Limit supported sources and support hours; pause expansion |
| “Free” loses money | High hosted check volume with low conversion | Keep local path useful; cap optional service work transparently |
| Spend ambiguity | Users cannot explain what a rule permits | Treat as blocking UX defect; do not enable purchasing |
| Trust overclaim | Marketing implies guaranteed stock or “malware-proof” | Replace with bounded, measured claims and public limitations |

## Founder decisions to make before the first implementation sprint

Confirm whether notification-only value is sufficient for the first release; choose initial category/source after the feasibility check; choose the weekly maintenance budget; select a license and name; choose whether optional paid hosting is desirable. Provisional answers are Mac-first, sealed TCG products, one authorized source, free local client, and no automatic purchasing in the first release.

These decisions do not block the research prototype and source-feasibility work already specified. They do block public claims, purchases, paid commitments, and a promise of full Guppy parity.
