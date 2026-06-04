# Operator Ads Playbook

Package C includes Google Search ads management, but agents only draft. The
operator owns account connection, client budget confirmation, and go-live approval.

## Scope

- Default channel: Google Search ads.
- Meta ads: quote/add-on only.
- Spend: billed through the client's ad account.
- Agent work: keywords, negative keywords, ad copy, geo proposal, and launch checklist.
- Operator work: connect account, confirm payment owner, set budget, approve go-live.

## Before First Campaign

1. Confirm `google_ads` is present in `client.services[]`.
2. Confirm `ADS.md` has approved geo targeting.
3. Confirm the client owns or authorizes the ad account and payment method.
4. Confirm daily/monthly budget cap in writing.
5. Create canonical `ad_campaign_go_live` approval with the campaign draft artifact.

## Budget Rules

- Start small: prefer a daily cap the owner can tolerate for 14 days.
- Never let an agent change budget without `ad_budget_change` approval.
- Refuse national targeting for local SMBs unless the client explicitly sells nationally.
- Document every budget change in `ADS.md`.

## Draft Checklist

- Campaign objective: calls/forms/bookings.
- Geo target matches signed intake or `ADS.md`.
- Keywords are service-specific.
- Negative keywords include jobs, DIY, free, course, salary, template.
- Ads point to the relevant page.
- No claims the business cannot substantiate.

## Go-Live

Do not launch until:

- `ad_campaign_go_live` approval is granted.
- Budget cap is visible in the ad platform.
- Landing page/contact form has passed launch checks.
- Client understands spend is separate from the retainer.

## Monthly Review

Report owner-friendly numbers:

- leads/forms/bookings when available
- spend
- obvious wasted-search terms
- one recommended action

Avoid jargon-first reporting. The owner cares whether the ads created useful work.
