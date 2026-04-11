# Document Review Skill (compound-engineering)

Source: https://github.com/EveryInc/compound-engineering-plugin (plugins/compound-engineering/skills/document-review and plugins/compound-engineering/agents/document-review).

This is a reference copy for Claude to load when hardening planning, requirements, or design documents. Kashane has confirmed this skill should be applied at all times when reviewing plans.

## When to invoke

Any time the user asks to review, harden, critique, stress-test, red-team, or validate a plan, requirements document, or design doc. Do not invoke for code diffs (that is `ce:review` territory), short notes, or conversational Q&A.

## Workflow

1. **Load** the document fully. Ask which document if ambiguous.
2. **Classify** requirements vs. plan. Detect activation signals:
   - Product strategy or prioritization → product-lens
   - UI/UX, flows, interaction patterns → design-lens
   - Auth, APIs, PII, secrets, trust boundaries → security-lens
   - 8+ requirements or multiple priority tiers → scope-guardian
   - 5+ requirements with rationale, high stakes, new abstractions → adversarial
   - Coherence and feasibility always run.
3. **Dispatch personas in parallel.** Each produces findings with a confidence score (0.00-1.00) and a severity band (P0 blocker, P1 high, P2 medium, P3 low). Suppress below 0.50, except P0 which can go to 0.50 minimum.
4. **Deduplicate.** When two personas flag the same issue, merge and bump confidence by +0.10.
5. **Synthesize** into a findings table grouped by severity.
6. **Harden** the document in place if asked. Add a review-log section listing which findings were addressed and how.
7. **Protected artifacts**: never delete sections of `docs/brainstorms/`, `docs/plans/`, or `docs/solutions/`. Edit or annotate.

## Personas

### coherence-reviewer — internal consistency
- Contradictions between sections.
- Terminology drift.
- Structural/dependency issues (step B references something defined only after).
- Genuine ambiguity (multiple valid interpretations producing different implementations).
- Broken references (links, file paths, task IDs).
Out of scope: style, taste, completeness.

### feasibility-reviewer — buildability and brownfield reality
- Existing assets acknowledged vs. greenfield assumption.
- Architecture alignment with the stack.
- Data flow paths: happy / nil / empty / error for every integration.
- Dependencies named (external and implicit).
- Performance math where latency matters.
- Migration concreteness (rollback, compat, ordering, volumes).
- Engineer-ready specificity (can someone start tomorrow?).
Out of scope: style, test design, code taste, theoretical scalability.

### adversarial-document-reviewer — is the plan *right*?
Five techniques:
1. Premise challenge — does the problem-solution match?
2. Assumption surfacing — environmental, behavioral, scale, temporal.
3. Decision stress-test — when does each major decision become wrong?
4. Simplification pressure — is this as simple as feasible?
5. Alternative blindness — what "build vs. use" is omitted?
Depth: quick (<1000 words, <5 reqs, max 3 findings); standard (medium); deep (>3000 words, high-stakes).

### scope-guardian-reviewer — right-sized and every abstraction earns its keep
1. What already exists? Minimum change set. >8 files or >2 new abstractions needs a proportional goal.
2. Scope-goal alignment: orphan scope, unserved goals, indirect scope built for hypothetical futures.
3. Complexity challenge: new abstractions, custom-vs-existing, framework-ahead-of-need, configuration without consumers.
4. Priority dependency: upward dependencies (P0 on P2), priority inflation, independent deliverability.
5. Completeness principle: with AI-assisted implementation, complete solutions are typically worth the small extra cost for error handling and edge cases.
Doesn't flag: product strategy, missing requirements, security, UX, feasibility.

### security-lens-reviewer — attack surface and trust boundaries
- Attack surface gaps.
- Auth/authorization assumptions.
- Data protection (PII, secrets, credentials).
- Third-party trust boundaries.
- Secrets management and credential flow.
- Top 3 threat scenarios for the proposed design.

### product-lens-reviewer — building the right thing
1. Premise challenge — right problem? Direct impact or proxy? Evidence of pain? Failure-despite-shipping?
2. Strategic consequences — trajectory, identity, adoption, opportunity cost, compounding.
3. Implementation alternatives — 80/20 options when concrete simpler paths exist.
4. Goal-requirement alignment — orphan requirements, unserved goals.
5. Prioritization coherence — do priority tiers match stated goals?
Threshold: 0.60+. Does not comment on implementation detail, security, design, or internal consistency.

### design-lens-reviewer — missing design decisions (not visual taste)
Rate each applicable dimension 0-10, flag 7 or below:
- Information architecture.
- Interaction state coverage (loading, empty, error, success, partial).
- User flow completeness (entry, happy path, edges, exit).
- Responsive / accessibility.
- Unresolved design decisions (TBDs, vague descriptions).
AI slop check: 3-column grids, purple/blue gradients, uniform border-radius, "modern and clean" as the only direction.
Skip entirely if the document has no UI/UX surface.

## Output format

```
## Review Findings
### P0 (blockers)
- [persona] title — conf 0.XX
  Quote: "..."
  Issue: ...
  Fix: ...
### P1 (high)
...
### P2 (medium)
...
### Deferred / below threshold
- brief mentions only
```

## Citation

Adapted from the compound-engineering plugin by Every Inc.
