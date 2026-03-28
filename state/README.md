# State

Everything under `state/` is runtime-owned, not source-owned.

Use it for:

- cloned repos
- task worktrees
- generated artifacts
- checkpoints
- logs
- cache and retrieved context
- file-backed platform records during the scaffold phase

Do not commit real runtime contents here.
