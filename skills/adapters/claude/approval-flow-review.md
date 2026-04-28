# approval-flow-review — Claude adapter

> Thin pointer. Source of truth: `skills/canonical/shared/approval-flow-review.md`.
>
> **Status: deferred.** Registered ahead of activation; not yet invoked.

## When to invoke

Trigger phrase (per `CLAUDE.md`): "review this approval request" / "audit the approval flow".

Use when the operator hands you an approval-request envelope and asks
whether it's well-formed and policy-compliant *before* the founder is
asked to look at it.

## How to invoke

Read the approval request, walk the canonical body's 4 steps:
1. Parse + structurally validate.
2. Match against `packages/policies/approvals.py`.
3. Bucket the verdict.
4. Emit `state/artifacts/approvals/reviews/<request_id>.json`.

Return the `ApprovalReviewVerdict` shape (verdict, reason,
preconditions_missing, policy_rules_referenced).

## Boundaries

- **Read-only against policy.** Never propose changes to `packages/policies/`.
- **Read-only against the approval store.** Mutations go through `approval-token-audit`, not this skill.
- **Never default to `approved` on error.** Any uncertainty → `needs_clarification` or `escalate_to_founder`. Failing open is forbidden.
