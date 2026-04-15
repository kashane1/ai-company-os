# Everything Claude Code Gap Analysis for `ai-company-os`

Date: 2026-04-14

## Question

Can `ai-company-os` benefit from ideas in [`affaan-m/everything-claude-code`](https://github.com/affaan-m/everything-claude-code)? If so, what are the biggest gaps in this repo today, and is it worth referencing or copying that repo directly?

## Executive Take

Yes, this repo can benefit from `everything-claude-code` knowledge, but mostly at the **workflow and operator-ergonomics layer**, not at the **architecture or orchestration layer**.

My recommendation:

- **Do not reference the whole repo as a runtime dependency**
- **Do not bulk-copy its skills**
- **Do selectively port 4-6 high-value ideas** into this repo's canonical skill system
- **Do treat ECC as a pattern library**, not as a source of truth

The core reason is architectural fit. `ai-company-os` is explicitly a **platform with bounded workers and policy-owned orchestration** ([README.md](/Users/simons/ai-company-os/README.md:7), [AGENTS.md](/Users/simons/ai-company-os/AGENTS.md:11), [docs/operating-model.md](/Users/simons/ai-company-os/docs/operating-model.md:19)). ECC is optimized as an **agent-harness performance system** with a very broad surface of skills, rules, hooks, commands, and cross-harness packaging ([ECC README](https://github.com/affaan-m/everything-claude-code), observed 2026-04-14).

That means the overlap is real, but the abstraction level is different.

## What `ai-company-os` Already Does Better

This repo is already stronger than ECC in a few important ways:

- It has a much clearer platform/worker boundary and explicitly prevents Codex from becoming the system brain ([README.md](/Users/simons/ai-company-os/README.md:22), [docs/architecture.md](/Users/simons/ai-company-os/docs/architecture.md:17)).
- It has a canonical skill model with explicit inputs, outputs, edit boundaries, forbidden areas, validation steps, adapters, and fixture state ([skills/README.md](/Users/simons/ai-company-os/skills/README.md:7), [skills/spec.md](/Users/simons/ai-company-os/skills/spec.md:1), [skills/registry.yaml](/Users/simons/ai-company-os/skills/registry.yaml:5)).
- It already encodes lane-aware validation and testing policy in shared code, not just prompts ([README.md](/Users/simons/ai-company-os/README.md:215), [skills/canonical/shared/post-run-validation.md](/Users/simons/ai-company-os/skills/canonical/shared/post-run-validation.md:1)).

So this is not a case where ECC should replace the repo's current model. The useful question is where ECC has **higher-quality operational know-how** that this repo has not yet turned into productized workflows.

## Biggest Gaps Where ECC Knowledge Helps

### 1. Research-first execution is still underpowered here

This is the clearest gap.

`ai-company-os` has strong implementation and validation surfaces, but it does not yet have first-class canonical skills for:

- research before coding
- live documentation lookup
- repo onboarding / quick architecture reconnaissance
- operator-facing “find existing solution before building custom code” loops

ECC has mature examples of exactly these workflows:

- `search-first`
- `documentation-lookup`
- `codebase-onboarding`

Why this matters here:

- this repo explicitly wants to stay legible and avoid hidden prompt logic ([README.md](/Users/simons/ai-company-os/README.md:30))
- that goal gets easier if the supervisor/engineering lanes have reusable research procedures instead of ad hoc investigation
- there is already evidence in this repo that “search-first” thinking matters at the product layer, but it is not yet generalized as a reusable platform capability ([todos/003-pending-p2-lock-waterbody-search-contract.md](/Users/simons/ai-company-os/todos/003-pending-p2-lock-waterbody-search-contract.md:11))

Recommendation:

- Add canonical skills for `search-first`, `documentation-lookup`, and `repo-onboarding`
- Keep them narrow and policy-safe
- Route them through `supervisor` and `engineering`, not through global hooks

### 2. Skill operations and catalog hygiene are immature here

This repo has a clean canonical skill system, but it is still small and partially unverified:

- `21` registry entries total
- `8` marked `fixture_status: passing`
- `14` marked `fixture_status: missing`

Source: [skills/registry.yaml](/Users/simons/ai-company-os/skills/registry.yaml:1)

ECC has much stronger operational patterns for managing a large skill estate:

- `skill-stocktake`
- `context-budget`
- install manifests and install profiles
- surface audits and harness audits

Why this matters here:

- this repo is already growing across supervisor, engineering, iOS, App Store, and GTM lanes
- once more skills land, drift and bloat become real
- the repo already anticipates later additions like memory helpers and observability helpers ([docs/architecture.md](/Users/simons/ai-company-os/docs/architecture.md:112))

Recommendation:

- Port the **idea** of `skill-stocktake`, not the file as-is
- Port the **idea** of `context-budget`, adapted to this repo's runtime surfaces:
  - canonical skills
  - adapters
  - worker prompts / packets
  - tool schemas
  - policy overhead
- Defer any install-profile machinery until this repo actually needs external distribution

### 3. Session memory and continuous learning are mostly still future-state here

`ai-company-os` talks about persistent workers, durable state, and explicit runtime records ([README.md](/Users/simons/ai-company-os/README.md:7), [docs/architecture.md](/Users/simons/ai-company-os/docs/architecture.md:122)), but it does not yet have a mature loop for:

- extracting reusable learnings from task runs
- turning repeated patterns into reviewed skills
- automatically summarizing sessions into reusable memory objects

ECC is materially ahead here in concept coverage:

- continuous learning
- instinct extraction / evolution
- session state infrastructure
- hook-triggered summaries and observers

This is probably the single biggest conceptual opportunity, but also the easiest place to make a mistake.

Why not copy directly:

- ECC's design is harness-centric and hook-heavy
- this repo's architecture says the **platform** owns orchestration and persistence, not the tool harness ([AGENTS.md](/Users/simons/ai-company-os/AGENTS.md:13), [docs/operating-model.md](/Users/simons/ai-company-os/docs/operating-model.md:21))
- direct hook-driven behavior could smuggle important state transitions out of shared policy code

Recommendation:

- Borrow the pattern, not the implementation
- Build “continuous learning” as a **platform service** that consumes task runs and review artifacts from `state/checkpoints/platform/`
- Allow it to suggest new or updated skills, but require explicit review before promotion into `skills/canonical/`

### 4. Verification is good here, but still too narrow

This repo already has meaningful validation:

- post-run validation
- task-run records
- lane-aware tests-with-code enforcement
- approval scaffolding

Source: [skills/canonical/shared/post-run-validation.md](/Users/simons/ai-company-os/skills/canonical/shared/post-run-validation.md:1)

But ECC is stronger at the broader “operator quality loop” level:

- comprehensive verification workflows
- eval harness concepts
- repeated quality gates
- audit/repair surfaces for the harness itself

Current gap in `ai-company-os`:

- validation is strongest around engineering task execution
- weaker around ongoing harness health, skill quality, prompt/context bloat, and operator surfaces

Recommendation:

- Do not replace `post-run-validation`
- Add a higher-level `verification-loop` style skill for:
  - repo health checks
  - worker runtime health
  - changed-surface verification
  - pre-PR and pre-release “quality gate” sweeps

### 5. Cross-harness and install-surface strategy is a future opportunity, not an immediate need

ECC has a mature manifest/profile installation model and broad harness packaging across Claude Code, Codex, Cursor, OpenCode, Gemini, and more ([ECC README](https://github.com/affaan-m/everything-claude-code), [install components](https://github.com/affaan-m/everything-claude-code/tree/main/manifests)).

`ai-company-os` already has canonical/adapters separation ([skills/README.md](/Users/simons/ai-company-os/skills/README.md:43)), which is the right foundation.

But the repo is still explicitly in a lean control-plane phase ([README.md](/Users/simons/ai-company-os/README.md:176)). That means install profiles and massive harness packaging are likely premature.

Recommendation:

- Learn from ECC's manifest approach
- Do not build full install/profile machinery yet
- Revisit only when this repo needs:
  - external distribution
  - selective skill packs
  - multi-harness shipping as a product

## Is It Worth Referencing the Whole ECC Repo?

Mostly no.

Reasons:

1. **Surface area mismatch**
   ECC is huge. On 2026-04-14 I observed roughly `183` top-level skill directories in the cloned repo, while `ai-company-os` currently tracks `21` canonical skills.

2. **Architectural mismatch**
   ECC optimizes the harness. This repo optimizes the operating system and control plane.

3. **Bloat risk**
   Bulk-importing ECC-style skills would make it easier to reintroduce the exact “prompt bundle” failure mode this repo is trying to avoid ([README.md](/Users/simons/ai-company-os/README.md:34)).

4. **Governance mismatch**
   `ai-company-os` requires bounded edit areas, validation steps, adapter discipline, and fixture state. ECC skills are useful, but they are not already normalized to this repo's canonical schema.

5. **Catalog inconsistency risk**
   ECC's own public counts vary across surfaces. In one observed pass:
   - GitHub page showed `156k` stars and `1,405` commits on 2026-04-14
   - README “What's New” described `156 skills`
   - README quick-start text described `181 skills`
   - local clone scan showed about `183` skill directories

   That does not make the repo bad. It does mean the surface changes quickly and should not be blindly vendored.

## Is It Worth Copying Some Skills Directly?

Directly copying files is only worth it for a very small set, and even then I would treat them as **draft source material**, not production-ready imports.

### Best direct-port candidates

These are the most compatible with this repo's architecture:

1. `documentation-lookup`
2. `search-first`
3. `codebase-onboarding`
4. `skill-stocktake`
5. `context-budget`

Why these work:

- they are workflow-oriented
- they do not need to own orchestration
- they can be rewritten into canonical skill form with bounded inputs/outputs
- they strengthen the supervisor/engineering lanes without weakening platform boundaries

### Adapt heavily, do not copy literally

1. `continuous-learning`
2. `continuous-learning-v2`
3. hook runtime controls
4. install manifests / install profiles
5. multi-agent orchestration command surfaces

Why:

- these touch persistence, orchestration, runtime lifecycle, or global tool behavior
- in this repo, those responsibilities belong to platform code and shared policy, not imported skill text

### Do not copy unless a product need appears

- language-specific pattern packs unrelated to the current codebase
- broad operator/business domains outside the active lanes
- generic harness branding / marketplace / plugin packaging surfaces

## Recommended Adoption Plan

### Phase 1: Immediate high-value ports

Create new canonical skills inspired by ECC:

1. `documentation-lookup`
2. `search-first`
3. `repo-onboarding`

Expected payoff:

- better research quality before implementation
- fewer ad hoc doc lookups
- better task packets and decomposition inputs

### Phase 2: Skill estate hygiene

Create internal versions of:

1. `skill-stocktake`
2. `context-budget`

Expected payoff:

- cleaner skill growth
- earlier detection of prompt/runtime bloat
- better discipline as more lanes gain skills

### Phase 3: Platform-native learning loop

Design, do not copy:

1. task-run summarization
2. pattern extraction from completed runs
3. suggested skill creation from repeated successful flows
4. review gate before any promoted skill enters `skills/canonical/`

Expected payoff:

- durable learning without surrendering orchestration to the harness

## Bottom Line

`ai-company-os` should absolutely learn from `everything-claude-code`, but it should do so **surgically**.

Best use of ECC:

- mine it for workflow patterns
- port a small number of high-leverage research and skill-ops ideas
- borrow concepts around verification and learning

Worst use of ECC:

- copy the whole repo
- vendor its full skill catalog
- adopt hook-heavy behavior that bypasses this repo's policy and control-plane boundaries

If we want a simple decision:

- **Reference selectively:** yes
- **Copy a few skills as draft source material:** yes
- **Adopt the whole repo or treat it as a dependency:** no

## Sources

- Local architecture and skill system:
  - [README.md](/Users/simons/ai-company-os/README.md:7)
  - [docs/architecture.md](/Users/simons/ai-company-os/docs/architecture.md:17)
  - [docs/operating-model.md](/Users/simons/ai-company-os/docs/operating-model.md:19)
  - [skills/README.md](/Users/simons/ai-company-os/skills/README.md:7)
  - [skills/spec.md](/Users/simons/ai-company-os/skills/spec.md:1)
  - [skills/registry.yaml](/Users/simons/ai-company-os/skills/registry.yaml:1)
  - [skills/canonical/shared/post-run-validation.md](/Users/simons/ai-company-os/skills/canonical/shared/post-run-validation.md:1)
- External reference:
  - [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code)

---

## Appendix — 2026-04-15 (ECC Gap Recommendations plan closed)

The four open recommendations from this gap analysis are now closed
by [docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md](/Users/simons/ai-company-os/docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md).

| § | Recommendation                | Status         | How                                                                                         |
| - | ----------------------------- | -------------- | ------------------------------------------------------------------------------------------- |
| 1 | Research-first execution      | **closed**     | Three canonical agentic skills shipped in Phase 1: `search-first`, `documentation-lookup`, `repo-onboarding`. Trigger phrases added to CLAUDE.md with a binding disambiguation rule. |
| 2 | Skill-estate hygiene          | **closed**     | Two canonical validators shipped in Phase 2: `skill-stocktake` (3 MVP drift types) and `context-budget` (report-only v1, no thresholds). Seven new primitives under `packages/tools/primitives/` including `_safe_paths`, `_serialization`, `_state_writer`, `_contracts`, `followup_issue_writer`, `registry_drift`, `context_budget`. Loader refactored to import the adapter-path guard from primitives (dependency inversion). |
| 3 | Continuous learning           | (prior closure)| Closed by [Hermes Phase 3](/Users/simons/ai-company-os/docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md) (`worker-skill-evolution`, PR #8, commit `1ce62bb`). |
| 4 | Verification loop             | **closed**     | One canonical agentic skill shipped in Phase 3: `verification-loop`. Composes reconciliation + skill-stocktake + changed-surface into a 5-state severity aggregator (`{info, warn, fail, error, skipped}`) with `pass` / `soft_fail` / `hard_fail` verdict. Two entry points: runner primitive (advisory, never raises) + policy wrapper (raises `VERIFICATION_LOOP_HARD_FAIL` for CI). |
| 5 | Install-surface strategy      | **deferred**   | Formally deferred in [docs/adr/2026-04-15-ecc-skill-decisions.md](/Users/simons/ai-company-os/docs/adr/2026-04-15-ecc-skill-decisions.md) §A with four explicit trip-wire conditions. Any PR reintroducing install-profile / manifest / marketplace machinery must first supersede §A with evidence that a trip-wire has fired. |

### Phase 4 baseline metrics

- Registry: **26 canonical skill entries** (22 pre-existing + 3 Phase 1 + 2 Phase 2 + 1 Phase 3 – `content-performance-review` removed earlier).
- Stocktake drift: **1 item**, tagged as `known_drift` (`post-run-validation` registry `path:` vs actual dir; pre-existing debt).
- Verification-loop verdict on the live repo: **`pass`**.
- Context-budget tokenizer: **`char_count_fallback`** (tiktoken not installed in this env; `o200k_base` preferred when available).
- Context-budget top 3 skills by token total: `gtm-artifact-refresh`, `niche-research-brief`, `codex-claude-handoff`.
- Per-lane token totals: `gtm` 16,664 · `supervisor` 13,664 · `engineering` 9,512 · `any` 9,269 · `ios` 2,952 · `appstore` 2,378.
- System-prompt lane (CLAUDE.md + project-skill pointers): **5,054 tokens**. MCP instruction blocks not yet included (deferred to v2 with a TODO per todo 014).

Baseline artifacts:
- [state/health/skill-estate/2026-04-15-stocktake.json](/Users/simons/ai-company-os/state/health/skill-estate/2026-04-15-stocktake.json)
- [state/health/skill-estate/2026-04-15-context-budget.json](/Users/simons/ai-company-os/state/health/skill-estate/2026-04-15-context-budget.json)
- [state/health/skill-estate/2026-04-15-ecc-gap-baseline.json](/Users/simons/ai-company-os/state/health/skill-estate/2026-04-15-ecc-gap-baseline.json) (composite)
- [state/artifacts/verification-loop/2026-04-15-ecc-gap-baseline/report.json](/Users/simons/ai-company-os/state/artifacts/verification-loop/2026-04-15-ecc-gap-baseline/report.json)
