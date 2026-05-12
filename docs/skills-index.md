# Skills Index

Full catalog of Claude project skills and their trigger phrases. CLAUDE.md keeps only a pointer to this file so the always-loaded context stays small. Read this when you need to know what skills exist or which trigger phrase routes where.

## Disambiguation rule (binding)

If multiple trigger phrases could apply to a user's message, Claude MUST ask which skill to invoke rather than guess. Do not silently route to the first match.

### Four-way carve-out: audit/backlog/polish family

The recon-family of audit skills (`simulator-polish-recon`, `premium-feel-audit`, `pro-value-audit`) and the editing skill `simulator-driven-polish` have overlapping trigger phrases. When a user's prompt is ambiguous between these four, ASK rather than guess. The intent split:

- **"what regressed / what's incomplete / what's left before submission"** → `simulator-polish-recon` (remedial discovery; observer is prior coverage)
- **"make it feel premium / elevate the app / find premium gaps / what would 10x this"** → `premium-feel-audit` (elevation discovery; observer is `premium-bar.md`)
- **"audit Pro value / where is Pro thin / audit the paywall / make Pro stand out"** → `pro-value-audit` (monetization audit; observer is `pro-value-rule.md` + `MONETIZATION.md`)
- **"polish the app / let's fix things live / drive the simulator / match this reference"** → `simulator-driven-polish` (editing, in-session — consumes prompts emitted by any of the three audit skills above)

If the prompt is bare ("audit the app" / "improve the app" / "make it better"), surface the four options and ask before routing.

## Available Claude project skills

- **product-artifact-chain** — validate/extend the founder-to-spec artifact chain
- **codex-claude-handoff** — transfer work between Codex and Claude
- **ios-ui-polish-review** — review iOS code for UI polish and platform conventions
- **ios-to-appstore-handoff** — prepare handoff from iOS build to App Store release
- **supervisor-goal-decomposition** — decompose founder goals into structured worker tasks
- **app-store-positioning-pack** — generate App Store positioning outputs from product artifacts
- **app-name-discovery** — generate a 4×6 register×archetype matrix of candidate app names from the founder pack, with hard gates and an archetype-spread shortlist of 5
- **niche-research-brief** — research a product niche and produce a scored, classified research brief with persistent memory
- **gtm-artifact-refresh** — consume a research brief and refresh all GTM artifacts with archetype mix balance
- **content-factory** — generate finished slide images from authored backlog items (Gemini backgrounds + Pillow text overlay)
- **content-scheduler** — push generated slides to Postiz as draft posts for human review
- **content-performance-review** — (planned) analyze content performance and propose improvements to hooks, archetype weights, and platform strategy
- **search-first** — look for existing code/patterns before building custom; produces a reuse | extend | custom recommendation
- **documentation-lookup** — look up library/framework docs via Context7 with a 3-call-per-question budget and allowlisted WebFetch fallback
- **repo-onboarding** — produce a bounded structured brief (architecture, key files, conventions, footguns) for a repo area
- **skill-stocktake** — structural audit of the skill registry, canonical files, project-skill pointers, and CLAUDE.md trigger phrases
- **context-budget** — per-lane token totals across adapters, canonical bodies, and project-skill pointers (v1 reports numbers, not verdicts)
- **verification-loop** — pre-PR / pre-release quality-gate sweep composing reconciliation + stocktake + changed-surface into a single verdict
- **verification-loop-runtime** — runtime-evidence half of the verification-loop split; owns the `stale_postmortems` sub-check (operator hygiene, not registry drift)
- **ios-build-and-sign** — produce a signed, validated iOS binary ready for TestFlight (Codex runs fastlane; Claude validates the artifact)
- **ios-simulator-ux-audit** — run a repeatable simulator-driven UX audit on an iOS product, capture findings with evidence, and leave behind reusable docs and test hooks
- **simulator-driven-polish** — drive the iOS app live in Simulator, identify gaps with explicit decision authority (Polish/Stretch/Feature/Vision-question), fix in tight commits, and surface only the decisions that need the operator. Modes: fix-list, freeform-polish, reference-match, vision-driven. See `docs/skills/simulator-driven-polish-guide.md` for the full operator guide.
- **simulator-polish-recon** — **remedial** discovery counterpart to `simulator-driven-polish`. Read-only audit; observer is prior polish coverage (diff-against-recent-work). Emits a backlog focused on regressions, drift, and submission gaps. Sibling of `premium-feel-audit` and `pro-value-audit`. Depths: quick (≤20), standard (≤40, default), deep (≤60). Minimum 10 prompts.
- **premium-feel-audit** — **elevation** discovery counterpart to `simulator-driven-polish`. Read-only audit; observer is `docs/products/<product-id>/premium-bar.md`. Emits a backlog focused on motion / haptics / typography / transitions / empty-state / loading / lighting / microcopy coherence. Sibling of `simulator-polish-recon`. Use when the operator wants to elevate, not remediate.
- **pro-value-audit** — **monetization** discovery counterpart to `simulator-driven-polish`. Read-only audit; observer is `docs/products/<product-id>/pro-value-rule.md` (operationalizes MONETIZATION.md's Free/Pro rule). Emits a backlog focused on Pro discoverability, justification, perceived depth, friction-to-trial, upsell moments, trust signals, and value-claim accuracy. Trust-gaps and Free/Pro-rule violations escalate to submission-blocker tier.
- **approval-flow-review** *(deferred)* — pre-validate an approval request against `packages/policies/approvals.py` before it reaches the founder queue
- **test-coverage-audit** *(deferred)* — audit a worktree diff against the coverage policy in `packages/policies/testing.py` before commit

## Trigger phrases → skills

When the user's message matches one of these patterns (including paraphrases), read and follow the named skill's Claude adapter before doing anything else.

- "hand this to codex" / "dispatch to codex" / "delegate to codex" / "queue a task for codex" / "find tasks for codex" / "have codex fix X" / "send this to codex" / "run this through codex" → `skills/adapters/claude/codex-claude-handoff.md` (local dispatch, on-device worker)
- "use codex cloud" / "dispatch via codex cloud" / "queue this on codex cloud" / "open a PR via codex cloud" → `docs/codex-cloud-dispatch.md` (Chrome-MCP-driven chatgpt.com/codex/cloud → PR against `staging`)
- "decompose this goal" / "break this down into tasks" / "turn this into worker tasks" → `skills/adapters/claude/supervisor-goal-decomposition.md`
- "validate the artifact chain" / "check product artifacts" → `skills/adapters/claude/product-artifact-chain.md`
- "review the iOS code" / "polish review" → `skills/adapters/claude/ios-ui-polish-review.md`
- "prep the app store handoff" / "cut a release" → `skills/adapters/claude/ios-to-appstore-handoff.md`
- "generate app store copy" / "positioning pack" → `skills/adapters/claude/app-store-positioning-pack.md`
- "find a name for this app" / "name this product" / "run name discovery" / "explore app names" → `skills/adapters/claude/app-name-discovery.md`
- "research the niche" / "run niche research" / "research this audience" / "build a research brief" / "what does this audience care about" → `skills/adapters/claude/niche-research-brief.md`
- "refresh the GTM artifacts" / "update the content backlog" / "propagate the research" / "refresh content from brief" / "balance the content mix" → `skills/adapters/claude/gtm-artifact-refresh.md`
- "create content" / "generate slides" / "make posts" / "run the content factory" / "generate images for the backlog" → `skills/adapters/claude/content-factory.md`
- "schedule posts" / "push to postiz" / "send to drafts" / "schedule content" / "queue drafts" → `skills/adapters/claude/content-scheduler.md`
- "search first" / "find existing solution" / "is there already a way to do this" / "look before you build" → `skills/adapters/claude/search-first.md`
- "look up the docs" / "pull the framework docs" / "check the SDK reference" / "what's the current API for" → `skills/adapters/claude/documentation-lookup.md`
- "onboard me to this area" / "give me the lay of the land" / "what's in this part of the repo" / "quick brief on <area>" → `skills/adapters/claude/repo-onboarding.md`
- "audit the skill estate" / "run a skill stocktake" / "check for orphan skills" / "find drift in the skill registry" → `skills/adapters/claude/skill-stocktake.md`
- "check the context budget" / "how bloated are the skill lanes" / "which lane is trending toward prompt bloat" → `skills/adapters/claude/context-budget.md`
- "run the verification loop" / "pre-PR sweep" / "check if this is ready to merge" / "run all the quality gates" → `skills/adapters/claude/verification-loop.md`
- "check stale postmortems" / "audit operator hygiene" / "run the runtime verification loop" → `skills/canonical/verification-loop-runtime/skill.md`
- "build the iOS app" / "sign the build" / "archive and sign" / "produce a TestFlight-ready binary" → `skills/adapters/claude/ios-build-and-sign.md`
- "audit the UX in simulator" / "run a simulator UX audit" / "do an iOS UX audit" / "run a UX pass on the iOS app" → `skills/adapters/claude/ios-simulator-ux-audit.md`
- "polish the app" / "polish loop" / "iterate on the iOS app" / "run the polish loop" / "drive the simulator and improve the app" / "dogfood the app" / "fix this list of issues in the app" / "match this reference in the app" / "do a vision pass on the app" / "run a vision-driven session" → `skills/adapters/claude/simulator-driven-polish.md` (editing — confirm mode before starting; if the operator wants review-only, route to `ios-simulator-ux-audit` instead)
- "audit the app for regressions" / "audit the app for drift" / "audit the app for submission gaps" / "polish recon" / "recon the app" / "find me prompts to run" / "generate polish prompts" / "what regressed" / "what's incomplete" / "what's left before submission" / "audit before polishing" → `skills/adapters/claude/simulator-polish-recon.md` (read-only **remedial** discovery — emits a backlog of polish prompts; consumer is `simulator-driven-polish`. For elevation framing use `premium-feel-audit`; for monetization framing use `pro-value-audit`.)
- "make it feel premium" / "make the app feel more premium" / "elevate the app" / "premium audit" / "premium-feel audit" / "premium-feel backlog" / "find premium gaps" / "what would 10x this" / "compare to the premium bar" / "what would make this feel premium" → `skills/adapters/claude/premium-feel-audit.md` (read-only **elevation** discovery — emits a backlog of motion / haptics / typography / transitions / empty-state / loading / lighting / microcopy prompts scored against `premium-bar.md`; consumer is `simulator-driven-polish`. Refuses if `premium-bar.md` is missing — operator authors the rubric.)
- "audit Pro value" / "make Pro stand out" / "where is Pro thin" / "Pro feels weak" / "audit the paywall" / "audit Pro discoverability" / "pro-value audit" / "pro-value backlog" / "audit monetization" / "is Pro delivering value" → `skills/adapters/claude/pro-value-audit.md` (read-only **monetization** discovery — emits a backlog of Pro-discoverability / justification / depth / trust / value-claim prompts scored against `pro-value-rule.md` + `MONETIZATION.md`; consumer is `simulator-driven-polish`. Trust-gap and Free/Pro-rule-violation findings escalate to submission-blocker tier.)

<!-- approval-flow-review and test-coverage-audit trigger phrases deferred until each skill activates (stage: active in registry). Adding them now would route users to frozen no-op contracts. -->

Following the adapter is not optional — the protocols exist because they encode boundaries, pre-flight checks, and failure modes that aren't obvious from the user's request alone.
