# Agency compliance templates

Per-client compliance artifacts for services that contact **end customers**
(review SMS, follow-up automation). Copy into each client workspace at promotion
or before enabling `reviews` / `follow_up_automation`.

| File | Purpose |
|------|---------|
| [`COMPLIANCE-template.md`](COMPLIANCE-template.md) | Workspace checklist: what’s allowed, what’s on file, gates |
| [`review-sms-consent-addendum.md`](review-sms-consent-addendum.md) | Signable addendum for TCPA-style review-request SMS |

**Rule:** do not enable live review SMS until the addendum is signed and stored at
`docs/products/<slug>-site/compliance/review-sms-consent-signed.pdf` (or `.md` with
signature block filled).

Scaffolded automatically by `packages/agency/templates.scaffold_client_workspace`
(see retainer ops plan Phase 8.0).
