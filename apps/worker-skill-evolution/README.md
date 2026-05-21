# worker-skill-evolution

The privilege-gated skill-self-evolution carrier. Runs a proposed
skill change through policy, stages the artifact, and requests a
signed human approval. It is a carrier process, not a code author.

## Owns

- claiming skill-evolution tasks from the control plane
- reading the proposal sidecar at
  `state/checkpoints/platform/skill_evolution_proposals/<task_id>.json`
- running `check_evolution_allowed` policy against the proposed diff
- acquiring a per-skill-id lock so two proposals cannot race
- staging the proposal artifact dir under
  `state/artifacts/skill-evolution/<proposal_id>/`
- requesting an HMAC magic-link approval and polling for its outcome
- honoring the skill-evolution kill switch

## Does not own

- drafting the actual diff — the caller supplies `diff_paths` and the
  proposed-diff blob in the sidecar
- `gh pr create` / `git push` — this is "Option B": the proposal
  lives on disk as a signed artifact, and a reviewer cherry-picks it
  in a separate human-authored PR
- applying skills directly without policy clearance and approval
- approval policy itself

## Entrypoint

[main.py](main.py) — a thin claim loop. On `approved`, it writes an
`applied.flag` marker to the artifact dir; on `rejected`, it
quarantines the artifact; on poll deadline, it blocks the task and
leaves the artifact staged.

## Boundaries

- **Kill switch:** the worker checks `state/flags/skill_evolution_frozen`
  before every claim and stops a running proposal cleanly when it is
  set.
- Evolution policy lives in `packages/policies/skill_evolution.py`;
  this worker never bypasses it. A policy rejection surfaces as a
  `FAILED` task with the violation code — nothing is staged.

## Validation

Python lane — `./scripts/test_python.sh`.

## Related docs

- [docs/runbooks/skill-evolution-revert.md](../../docs/runbooks/skill-evolution-revert.md)
- [docs/agent-model.md](../../docs/agent-model.md)
- [docs/approval-policy.md](../../docs/approval-policy.md)
- [approval-reviewer](../approval-reviewer/) — the human-side CLI that
  signs or rejects these proposals
