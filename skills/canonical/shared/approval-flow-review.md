---
id: approval-flow-review
name: Approval Flow Review
purpose: Pre-validate an approval request against `packages/policies/approvals.py` so malformed or policy-violating requests get filtered before the founder sees them. Reduces approval-spam without weakening the gate.
owner_agent: supervisor
target_runtimes: [claude]
stage: deferred
inputs:
  - approval_request envelope (action, actor, context, risk_level)
  - policy_config_path (defaults to packages/policies/approvals.py — read-only)
outputs:
  - ApprovalReviewVerdict
    - verdict (enum: approved | needs_clarification | escalate_to_founder)
    - reason (string)
    - preconditions_missing (list of strings)
    - policy_rules_referenced (list of PolicyViolationCode names)
allowed_edit_boundaries:
  - state/artifacts/approvals/reviews/
forbidden_areas:
  - packages/policies/ (read-only input — never edited by this skill)
  - state/checkpoints/platform/approvals/ (canonical approval store; mutations go through approval-token-audit)
dependencies:
  - packages/policies/approvals.py exists and is readable
  - the approval request envelope conforms to ApprovalRecord shape (packages/schemas/approval.py)
validation_steps:
  - verdict is one of the three enumerated values
  - reason is non-empty
  - preconditions_missing is exhaustive (every check that failed is named)
  - policy_rules_referenced names real PolicyViolationCode members
handoff_contract:
  what_is_handed_off: ApprovalReviewVerdict + the original request
  handed_to: founder (when verdict == escalate_to_founder), supervisor (when verdict == approved or needs_clarification)
claude_adaptation_notes: |
  Claude is the right runtime for this — the structural pre-checks are
  mechanical (well-formedness, required fields) but the verdict bucket
  (needs_clarification vs escalate_to_founder) needs reading context
  the policy file alone can't capture. Stay strictly read-only against
  the policy file. Never propose policy changes from this skill — that
  is a separate workflow.
---

> **stage: deferred** — registered ahead of activation. Until a real
> call site exists (proposed: a control-plane hook that runs every
> approval request through this skill before adding it to the founder
> queue), this skill is contract-frozen but not invoked. Activate by
> moving `stage: active` in the registry once the call site lands.

## Instructions

### 1. Parse the approval request

The request envelope must contain (per `packages/schemas/approval.py:ApprovalRecord`):

- `id` (string)
- `action` (string — what is being requested, e.g. "merge to main", "rotate API key")
- `actor` (string — which worker / lane / human is asking)
- `context` (string — free-form rationale)
- `risk_level` (enum: low | medium | high)
- `created_at` (ISO 8601)

If any required field is missing or malformed, set:
- `verdict: needs_clarification`
- `reason: "missing required field <name>"`
- `preconditions_missing: [<name>]`

Do NOT escalate malformed requests to the founder. Send them back to the actor.

### 2. Match against policy

Read `packages/policies/approvals.py`. For each rule that applies to
the requested `action` + `actor` + `risk_level` combination:

- Confirm the request meets the rule's preconditions.
- Capture every rule consulted in `policy_rules_referenced` using the
  `PolicyViolationCode` enum member name (e.g. `APPROVAL_NOT_GRANTED`).

Rules that don't apply are not listed. The list is "rules consulted,"
not "rules in the file."

### 3. Bucket the verdict

| Verdict | When |
|---|---|
| `approved` | All preconditions met; risk is `low` AND policy says no human approval required (e.g. `requires_human_approval(task) == False`). |
| `needs_clarification` | Request is malformed, ambiguous, or missing context the policy demands. The actor — not the founder — fixes this. |
| `escalate_to_founder` | Policy demands human approval (e.g. `requires_human_approval == True`), the request is well-formed, and no clarification can substitute for human judgment. |

The `escalate_to_founder` bucket is the **only** path that surfaces the
request to the founder. Every other verdict short-circuits.

### 4. Emit the verdict

Write to `state/artifacts/approvals/reviews/<request_id>.json`:

```yaml
request_id: <id>
verdict: approved | needs_clarification | escalate_to_founder
reason: <short string>
preconditions_missing: [list]
policy_rules_referenced: [list of PolicyViolationCode names]
reviewed_at: <ISO 8601>
```

Return the same shape as `ApprovalReviewVerdict` to the caller.

## Failure modes

- **policy_unavailable** — `packages/policies/approvals.py` cannot be read. Halt; emit `verdict: needs_clarification` with `reason: "policy file unavailable"`. Never default to approval.
- **schema_drift** — request envelope is missing a field that recently became required. Emit `verdict: needs_clarification` naming the drifted field. Do NOT guess defaults.
- **ambiguous_action** — the action string doesn't match any policy rule. Emit `verdict: escalate_to_founder` with `reason: "no policy rule matches"` — better to surface than silently approve.
- **conflicting_rules** — two rules give different verdicts on the same request. Emit `verdict: escalate_to_founder` with both rules in `policy_rules_referenced`. Never resolve conflicts in the skill — that's policy authorship, not review.

## Worked example

Deferred — populate when the first call site exists. Tracked at
`docs/plans/2026-04-27-feat-three-new-skills-pack-plan.md`.

## References

- `packages/policies/approvals.py` — the policy this skill consults.
- `packages/schemas/approval.py` — `ApprovalRecord` shape.
- `packages/schemas/approval.py` — `PolicyViolationCode` enum.
- Sibling skill: `skills/canonical/approval-token-audit/skill.md` — runs AFTER approval is granted to verify token integrity.
