---
status: pending
priority: p3
issue_id: "061"
tags: [code-review, agent-native, repo-wide-debt, audit-fork]
dependencies: []
---

# Problem Statement

Two MAJOR agent-native gaps surfaced during this PR's review, but both are pre-existing across the recon-family (simulator-polish-recon shipped them on 2026-05-10 in commit b70b1a6) rather than introduced by the audit-sibling fork. They're tracked here as repo-wide follow-ups, not blockers for this PR.

## Findings

- **agent-native-reviewer (MAJOR 1 — memory-pass portability):** "The path `~/.claude/projects/-Users-simons-ai-company-os/memory/` is Claude-Code-on-this-Mac-specific. It is **not** a worker-context path (workers run from `apps/` with their own cwd and may not share `$HOME`), and the slugified `-Users-simons-…` segment will not exist on any other machine or CI."

- **agent-native-reviewer (MAJOR 2 — file-based chaining):** "The handoff is file-based-only. An agent cannot run `premium-feel-audit` → `simulator-driven-polish` in one shot without a human in the loop. Add a documented `--from-backlog <path>` mode on `simulator-driven-polish`, or have the audits emit a machine-readable `backlog.yaml` keyed by `polish_prompt.PolishPrompt` next to the markdown."

## Proposed Solutions

### Option 1: Two-PR follow-up plan

**Follow-up PR A:** Move operator memory into the repo at `state/operator-memory/` and update every recon-family skill body to read from there. Backward-compat: if `~/.claude/projects/.../memory/` exists, copy entries into `state/operator-memory/` once; afterward the repo path is canonical.

**Follow-up PR B:** Add a machine-readable backlog emission. Each audit emits both `<focus>-backlog-<date>.md` (human-readable) AND `<focus>-backlog-<date>.yaml` (machine-readable, keyed by the schema). `simulator-driven-polish` adds a `--from-backlog <yaml-path>` mode that consumes prompts programmatically.

Pros: closes both MAJOR gaps; makes the recon family truly agent-portable
Cons: each is a real piece of work; would touch every recon-family skill
Effort: Medium-Large per PR
Risk: Medium (touches operator-memory semantics which the user relies on)

### Option 2: Document the limitations, defer the fix

Add a "Portability limitations" section to `skills/WIRING.md` documenting the two issues with their workarounds (operator manually copies memory to other machines; agent-to-agent chain requires human paste). Track follow-up via a single repo-wide debt item.

Pros: cheapest; doesn't risk breaking the current Claude-Code-on-this-Mac flow
Cons: doesn't actually fix anything
Effort: Trivial
Risk: None

## Recommended Action

**Option 2 now, Option 1 when the user starts running these audits from a non-Claude-Code agent.** Today the only consumer of these audits is the operator in Claude Code on this machine. The portability concerns become real when (a) a worker daemon starts running audits autonomously, or (b) the operator picks up a second machine. Neither is happening today.

## Technical Details

- Files affected (Option 2):
  - `skills/WIRING.md` (new "Portability limitations" section)
- Files affected (Option 1, future PRs):
  - `state/operator-memory/` (new directory, with migration)
  - Every recon-family adapter and canonical body that reads memory
  - `skills/canonical/simulator-driven-polish/skill.md` (new --from-backlog mode)
  - Every audit-skill canonical body (emit yaml alongside md)

## Acceptance Criteria (Option 2)

- [ ] `skills/WIRING.md` documents both portability limitations
- [ ] Each recon-family adapter's "memory directory missing" failure-mode language is verified to gracefully degrade

## Work Log

(empty)
