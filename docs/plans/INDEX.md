# Plans index

Per-feature implementation plans generated before execution. Each plan
captures intent, scope, and structure for a specific change. Plans are
run/spec output — skim, don't read top-to-bottom (see
[docs/README.md](../README.md)).

## Convention for new plans

Filename:

```
docs/plans/YYYY-MM-DD-<slug>-plan.md
```

Optional disambiguation prefix for same-day plans: `YYYY-MM-DD-NNN-<slug>-plan.md`
where `NNN` is a zero-padded counter.

Recommended frontmatter (YAML at the top of the plan file):

```yaml
---
status: open | done | abandoned
change_id: short-stable-id
related_brainstorm: docs/brainstorms/...
related_task: state/checkpoints/platform/tasks/<task-id>.json   # if applicable
owner: <name>
last_reviewed: YYYY-MM-DD
---
```

Status meaning:

- `open` — work has not landed yet
- `done` — the plan's scope has shipped (referenced by a merged change or release)
- `abandoned` — plan was superseded, deferred indefinitely, or rejected

Status transitions happen by editing the frontmatter, not by renaming
the file. Filenames are immutable once committed so links stay stable.

## Current plans

All entries below are marked `unverified` because this index was built
from filenames only. A future pass should open each plan, read its
frontmatter or opening section, and set the real status.

| File | Date | Slug | Status | Notes |
|---|---|---|---|---|
| [2026-04-12-feat-catchbook-angler-ux-parity-plan.md](2026-04-12-feat-catchbook-angler-ux-parity-plan.md) | 2026-04-12 | feat-catchbook-angler-ux-parity | unverified | product-scoped (catchbook) |
| [2026-04-12-feat-catchbook-competitive-gap-plan.md](2026-04-12-feat-catchbook-competitive-gap-plan.md) | 2026-04-12 | feat-catchbook-competitive-gap | unverified | product-scoped (catchbook) |
| [2026-04-12-feat-content-pipeline-skills-plan.md](2026-04-12-feat-content-pipeline-skills-plan.md) | 2026-04-12 | feat-content-pipeline-skills | unverified | platform / skills |
| [2026-04-13-feat-gtm-multi-platform-content-engine-plan.md](2026-04-13-feat-gtm-multi-platform-content-engine-plan.md) | 2026-04-13 | feat-gtm-multi-platform-content-engine | unverified | platform / GTM |
| [2026-04-13-refactor-catchbook-optional-waterbody-plan.md](2026-04-13-refactor-catchbook-optional-waterbody-plan.md) | 2026-04-13 | refactor-catchbook-optional-waterbody | unverified | product-scoped (catchbook) |
| [2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md](2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md) | 2026-04-14 | feat-hermes-inspired-platform-upgrade | unverified | platform |
| [2026-04-15-feat-ecc-gap-recommendations-plan.md](2026-04-15-feat-ecc-gap-recommendations-plan.md) | 2026-04-15 | feat-ecc-gap-recommendations | unverified | platform / skills |
| [2026-04-15-macos-keychain-approval-signing-migration.md](2026-04-15-macos-keychain-approval-signing-migration.md) | 2026-04-15 | macos-keychain-approval-signing-migration | unverified | platform / approvals |
| [2026-04-20-001-feat-catchbook-app-store-submission-automation-plan.md](2026-04-20-001-feat-catchbook-app-store-submission-automation-plan.md) | 2026-04-20 | feat-catchbook-app-store-submission-automation | unverified | product-scoped (catchbook) |
| [2026-04-27-001-feat-after-plans-context-model-refactor-plan.md](2026-04-27-001-feat-after-plans-context-model-refactor-plan.md) | 2026-04-27 | feat-after-plans-context-model-refactor | unverified | product-scoped (after-plans) |
| [2026-04-27-002-feat-life-clock-ios-mvp-skeleton-plan.md](2026-04-27-002-feat-life-clock-ios-mvp-skeleton-plan.md) | 2026-04-27 | feat-life-clock-ios-mvp-skeleton | unverified | product-scoped (life-clock) |
| [2026-04-27-feat-postmortem-schema-and-adaptive-feedback-loop-plan.md](2026-04-27-feat-postmortem-schema-and-adaptive-feedback-loop-plan.md) | 2026-04-27 | feat-postmortem-schema-and-adaptive-feedback-loop | unverified | platform / schemas |
| [2026-04-27-feat-skill-completeness-pack-plan.md](2026-04-27-feat-skill-completeness-pack-plan.md) | 2026-04-27 | feat-skill-completeness-pack | unverified | platform / skills |
| [2026-04-27-feat-three-new-skills-pack-plan.md](2026-04-27-feat-three-new-skills-pack-plan.md) | 2026-04-27 | feat-three-new-skills-pack | unverified | platform / skills |
| [2026-04-28-001-feat-life-clock-live-healthkit-plan.md](2026-04-28-001-feat-life-clock-live-healthkit-plan.md) | 2026-04-28 | feat-life-clock-live-healthkit | unverified | product-scoped (life-clock) |
| [2026-04-28-002-feat-life-clock-persistence-plan.md](2026-04-28-002-feat-life-clock-persistence-plan.md) | 2026-04-28 | feat-life-clock-persistence | unverified | product-scoped (life-clock) |
| [2026-04-28-003-feat-life-clock-storekit-paywall-plan.md](2026-04-28-003-feat-life-clock-storekit-paywall-plan.md) | 2026-04-28 | feat-life-clock-storekit-paywall | unverified | product-scoped (life-clock) |
| [2026-04-28-feat-app-name-discovery-skill-plan.md](2026-04-28-feat-app-name-discovery-skill-plan.md) | 2026-04-28 | feat-app-name-discovery-skill | unverified | platform / skills |
| [2026-04-29-001-feat-life-clock-palette-picker-plan.md](2026-04-29-001-feat-life-clock-palette-picker-plan.md) | 2026-04-29 | feat-life-clock-palette-picker | unverified | product-scoped (life-clock) |
| [2026-04-29-fix-after-plans-dark-mode-and-create-plan-ux-plan.md](2026-04-29-fix-after-plans-dark-mode-and-create-plan-ux-plan.md) | 2026-04-29 | fix-after-plans-dark-mode-and-create-plan-ux | unverified | product-scoped (after-plans) |
| [2026-04-30-001-feat-life-clock-daily-reminder-plan.md](2026-04-30-001-feat-life-clock-daily-reminder-plan.md) | 2026-04-30 | feat-life-clock-daily-reminder | unverified | product-scoped (life-clock) |
| [2026-04-30-001-refactor-ux-audit-cleanup-plan.md](2026-04-30-001-refactor-ux-audit-cleanup-plan.md) | 2026-04-30 | refactor-ux-audit-cleanup | unverified | platform / skills |
| [2026-04-30-feat-history-wrapups-and-overrides-plan.md](2026-04-30-feat-history-wrapups-and-overrides-plan.md) | 2026-04-30 | feat-history-wrapups-and-overrides | unverified | platform / product (likely life-clock) |
| [2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md](2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md) | 2026-05-01 | feat-life-clock-reveal-onboarding-anchor-dial | unverified | product-scoped (life-clock) |
| [2026-05-01-refactor-history-feature-hardening-pass-plan.md](2026-05-01-refactor-history-feature-hardening-pass-plan.md) | 2026-05-01 | refactor-history-feature-hardening-pass | unverified | product-scoped (likely life-clock) |
| [2026-05-01-refactor-life-clock-tab-consolidation-plan.md](2026-05-01-refactor-life-clock-tab-consolidation-plan.md) | 2026-05-01 | refactor-life-clock-tab-consolidation | unverified | product-scoped (life-clock) |
| [2026-05-02-feat-life-clock-diet-rhythm-and-copy-pass-plan.md](2026-05-02-feat-life-clock-diet-rhythm-and-copy-pass-plan.md) | 2026-05-02 | feat-life-clock-diet-rhythm-and-copy-pass | unverified | product-scoped (life-clock) |
| [2026-05-02-feat-life-clock-mascot-animated-primitive-plan.md](2026-05-02-feat-life-clock-mascot-animated-primitive-plan.md) | 2026-05-02 | feat-life-clock-mascot-animated-primitive | unverified | product-scoped (life-clock) |
| [2026-05-03-feat-life-clock-onboarding-polish-pass-plan.md](2026-05-03-feat-life-clock-onboarding-polish-pass-plan.md) | 2026-05-03 | feat-life-clock-onboarding-polish-pass | unverified | product-scoped (life-clock) |
| [2026-05-08-feat-quest-pool-affinity-engine-plan.md](2026-05-08-feat-quest-pool-affinity-engine-plan.md) | 2026-05-08 | feat-quest-pool-affinity-engine | unverified | product-scoped (likely life-clock) |
| [2026-05-08-feat-quest-pool-phase-3-engines-plan.md](2026-05-08-feat-quest-pool-phase-3-engines-plan.md) | 2026-05-08 | feat-quest-pool-phase-3-engines | unverified | product-scoped |
| [2026-05-08-feat-quest-pool-phase-3cd-wiring-plan.md](2026-05-08-feat-quest-pool-phase-3cd-wiring-plan.md) | 2026-05-08 | feat-quest-pool-phase-3cd-wiring | unverified | product-scoped |
| [2026-05-08-feat-quest-pool-phase-4-and-5-plan.md](2026-05-08-feat-quest-pool-phase-4-and-5-plan.md) | 2026-05-08 | feat-quest-pool-phase-4-and-5 | unverified | product-scoped |
| [2026-05-08-feat-quest-pool-phase-4-and-5-prompt.md](2026-05-08-feat-quest-pool-phase-4-and-5-prompt.md) | 2026-05-08 | feat-quest-pool-phase-4-and-5-prompt | unverified | not a plan — a paired prompt file |
| [2026-05-08-feat-quest-pool-phase-4a-activity-plan.md](2026-05-08-feat-quest-pool-phase-4a-activity-plan.md) | 2026-05-08 | feat-quest-pool-phase-4a-activity | unverified | product-scoped |
| [2026-05-09-feat-life-clock-quest-completion-payoff-plan.md](2026-05-09-feat-life-clock-quest-completion-payoff-plan.md) | 2026-05-09 | feat-life-clock-quest-completion-payoff | unverified | product-scoped (life-clock) |
| [2026-05-11-feat-future-tab-history-summary-plan.md](2026-05-11-feat-future-tab-history-summary-plan.md) | 2026-05-11 | feat-future-tab-history-summary | unverified | product-scoped |
| [2026-05-12-feat-premium-and-pro-value-audit-skills-plan.md](2026-05-12-feat-premium-and-pro-value-audit-skills-plan.md) | 2026-05-12 | feat-premium-and-pro-value-audit-skills | unverified | platform / skills |

Totals: 38 plan files.

## Pending verification work

A follow-up pass should:

1. Open each plan and confirm the `status` (open / done / abandoned).
2. Wire `change_id`, `related_brainstorm`, and `related_task` where they
   exist.
3. Move plans whose work clearly shipped into a `docs/plans/archive/<year>/`
   subdirectory if the founder wants long-term archival isolated from
   active planning.
4. Add a brief one-line description column once plans are read.

This index intentionally avoids fabricating status. `unverified` is the
honest signal.
