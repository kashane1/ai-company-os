# Discovery Compliance

The discovery layer reaches out to the open web, so it carries compliance weight
the rest of the platform does not. This doc covers the controls specific to
**crawling and sourcing**. Money, sends, and deploys are already governed by the
platform's approval policy (`docs/approval-policy.md`, `packages/policies/`); the
discovery gates route into those, they do not replace them.

> This describes engineering and operational controls. It is **not legal
> advice.** For anything involving personal data, paid outreach at scale, or
> regulated sectors, get advice from a qualified professional in the relevant
> jurisdiction before going live.

## Crawling & sourcing (enforced in code)

- **Respect `robots.txt`.** `packages/discovery/connectors/robots.py` checks
  robots before any HTML fetch and caches the result per host. Disallowed paths
  are not crawled. On a hard fetch error it **fails closed** (does not crawl).
- **Rate limit per domain.** `rate_limiter.py` is a token bucket with
  exponential backoff; connectors share one limiter per source and back off on
  429/503. Hammering a host gets your IP range blocked and ends the loop.
- **Prefer official APIs.** The shipped connectors (Hacker News, GitHub) use
  documented endpoints within quota — no HTML scraping. Set a source
  `enabled: false` in `config/sources.yaml` if its only viable access is
  ToS-violating scraping. That is a scorecard hard gate, not a low score.
- **Identify yourself honestly.** Every request sends a real `User-Agent`
  (`config/sources.yaml` → `defaults.user_agent`). Do not spoof or use
  anti-detection browsing to evade access controls — out of scope for this
  system.
- **Attribute every signal.** `RawSignal.url` is mandatory and never stripped;
  the inbox keeps provenance on every piece of evidence. Store links and short
  factual quotes, not wholesale copies of others' content.
- **No paywall / login / anti-bot circumvention.** Connectors never touch
  authenticated or protected content.

## Bulk crawls are gated

A connector refuses a `bulk=True` fetch on its own (`CompliancePolicyError`).
A large crawl beyond normal per-domain limits must go through the platform's
approval gate with a vetted, throttled plan — same human-in-the-loop pattern as
spend and deploys.

## Personal data

- **Minimize.** Collect only what the use case needs. Flag opportunities that
  touch PII with the `pii` compliance flag; regulated data (`regulated-data`) is
  a hard block pending a named owner.
- **Retention.** Expire stored signals per your retention policy; don't hoard.
- **Special categories.** Health, financial, biometric, children's data →
  blocked pending a named compliance owner and a documented basis.

## Outreach (when validation involves sending)

Validation experiments that send (cold outreach, email waitlists) inherit the
platform's existing outreach controls: anti-spam compliance (sender identity, a
physical address, working unsubscribe), a permanent suppression list, volume
gates, and per-platform rules. The discovery layer's job is to *flag* that an
experiment sends; the compliance reviewer and the approval gate decide.

## Pre-launch checklist (discovery)

- [ ] `robots.txt` + per-domain rate limits enforced and tested.
- [ ] Only `enabled` sources crawl; disabled sources stay off.
- [ ] Provenance stored on every signal.
- [ ] Bulk crawls go through the approval gate, never a heartbeat.
- [ ] PII / regulated-data flags route to a named owner before advancing.
