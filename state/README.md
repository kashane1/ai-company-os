# State

Everything under `state/` is runtime-owned, not source-owned.

Do not commit real runtime contents here. Subdirectories are created
lazily on first write by the code that owns them.

## Directory glossary

| Subdir                                 | Writer                    | Purpose                                                                               | Lifecycle                              |
| -------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------- |
| `state/repos/`                         | platform git tools        | Cloned upstream repos for workers.                                                    | Retained until manual purge.           |
| `state/worktrees/`                     | platform git tools        | Per-task git worktrees.                                                               | Cleaned up on task completion.         |
| `state/artifacts/`                     | workers + skills          | Per-run output (diffs, reports, generated files). One subdir per skill or run-id.     | Retained per writer convention.        |
| `state/artifacts/verification-loop/`   | `verification-loop` skill | Per-run `VerificationLoopReport` JSON + per-sub-check output. One dir per `run-id`.   | Retain last 30 per retention policy.   |
| `state/checkpoints/`                   | platform task runner      | Task-run checkpoint and replay data.                                                  | Retained per runner convention.        |
| `state/logs/`                          | all platform components   | Append-only JSONL logs.                                                               | Rotated per log writer.                |
| `state/cache/`                         | retrievers + context      | Retrieved context, embeddings, tool-call caches.                                      | Cache-eviction per writer.             |
| `state/benchmarks/`                    | benchmarking scripts      | Point-in-time performance measurements. Wallclock / throughput / cost snapshots.      | Retain last 30.                        |
| `state/health/`                        | CI + operators            | Recurring platform-health snapshots. Trend comparison data.                           | Retain last 30.                        |
| `state/health/skill-estate/`           | CI + operators            | `StocktakeReport` + `ContextBudgetReport` baselines from `skill-stocktake` / `context-budget`. | Retain last 30.                   |
| `state/followups/`                     | agents + operators        | Typed `FollowupEntry` YAML files from `followup_issue_writer.py` — drift items and other issues captured for deferred resolution. | Retain until resolved, then archive to `state/archive/followups/<yyyy>/`. |
| `state/last30days_social_report/`      | `last30days` skill        | Cached social-research payloads.                                                      | Cache TTL per skill.                   |

## Semantic categories

Three state-directory semantic categories are recognized repo-wide:

- **`state/health/`** — recurring snapshots of platform state for
  trend comparison (drift counts, lane token budgets, verification
  verdicts). Retention: keep last N = 30.
- **`state/benchmarks/`** — performance measurements (wallclock,
  throughput, cost). Retention: keep last N = 30.
- **`state/artifacts/`** — per-run output (reports, diffs, generated
  files) with one subdirectory per run-id. Retention: per writer
  convention.

Governance rules for `state/health/` and `state/artifacts/verification-loop/`
are recorded in
[docs/adr/2026-04-15-ecc-skill-decisions.md](/docs/adr/2026-04-15-ecc-skill-decisions.md)
§C and §D.

## Writer conventions

- New subdirectories MUST be added to this glossary in the same PR
  that introduces their writer.
- Atomic JSON writes go through
  `packages/tools/primitives/_state_writer.py:atomic_write_json`
  (landed in Phase 2a of the ECC Gap Recommendations plan).
- CODEOWNERS on `state/health/**` is required before Phase 4 baseline
  runs land.
