# Client Intake

**Kind:** agentic · **Owner:** web · **Runtimes:** claude, codex

Capture a local-SMB client's business details into a structured
`ClientIntake`, then produce the `CLIENT_BRIEF.md` and a localized site context
so the website scaffold can be generated. The first step of the agency
client-delivery flow (Agency layer, Phase 4).

## When to use

- A prospect has been promoted to a `client-site` engagement (see
  `prospect-to-client`) and you need to gather the details to build the site.
- The operator says "intake this client", "capture the business details",
  "start the client brief".

## Inputs

- Business name, service category (plumbing / med spa / barber / …), city.
- Services offered, hours, phone, ideal customer, photos, reviews, competitors.
- **Access block (collect up front — the #1 lever against back-and-forth):**
  domain registrar / DNS access, **GBP access added as a Manager** (not owner),
  existing hosting / CMS / analytics logins if migrating.
- **Single named approver** (name + email) for the preview-review — one decision
  maker, not a committee.
- **Brand kit:** logo (vector preferred), colors/fonts, and the **exact NAP**
  (name / address / phone, no abbreviations — feeds GBP verification).

> Capture the access block + named approver in `CLIENT_BRIEF.md` even though the
> `ClientIntake` dataclass doesn't persist them yet — extending the dataclass to
> store them is a tracked follow-up (must respect the strict typed-loader pattern;
> see the go-live readiness plan's Implementation Notes).

## Procedure

1. **Capture** the fields into `packages.agency.intake.ClientIntake` and call
   `.validate()` (business name, service category, and city are required).
2. **Render the brief** with `packages.agency.intake.render_brief(intake)` and
   write it to `docs/products/<slug>-site/CLIENT_BRIEF.md` (overwrites the Phase 3
   stub).
3. **Build the site context** with `intake.to_site_context()` — this reuses
   `packages.web.scaffold.local_business_context`, so the existing Astro template
   renders a local-business site. Hand off to `landing-page-build` (do not fork a
   new scaffold).
4. **Stop before deploy.** Intake + scaffold produce a buildable site; launching
   it is the separate, gated `launch-checklist` step.

## Outputs

- `docs/products/<slug>-site/CLIENT_BRIEF.md`
- a scaffold token context ready for `scaffold_site`

## Forbidden areas

- Does not deploy, does not send any client communication, does not edit policy
  or schema files.
