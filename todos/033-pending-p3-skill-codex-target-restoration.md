---
status: pending
priority: p3
issue_id: "033"
tags: [code-review, skills, codex, infrastructure]
dependencies: []
---

# Problem Statement

`ios-simulator-ux-audit` was previously declared with `target_runtimes: [claude, codex]`. When it graduated to `stage: active` in commit acefe50, the runtime list was narrowed to `[claude]` only (registry.yaml:137 and skills/canonical/ios-simulator-ux-audit/skill.md:6) because no codex adapter exists yet. The narrowing is correct — declaring a runtime without an adapter is a lie — but the architecture review surfaced the risk that the deferred codex adapter quietly disappears from the backlog.

This todo tracks the restoration so it doesn't drift further.

## Findings

- `skills/registry.yaml:134-137` — inline comment already names the acceptance criterion ("Add `codex` back to target_runtimes once skills/adapters/codex/ios-simulator-ux-audit.md exists"). That is the right marker but lives only in YAML.
- `skills/canonical/ios-simulator-ux-audit/skill.md:6` — `target_runtimes: [claude]` with no note about deferral.
- No codex adapter file under `skills/adapters/codex/`.
- The skill itself is iOS-Simulator-driven and assumes XcodeBuildMCP-style tooling — codex-cloud parity is not free; the codex adapter would have to either reach an iOS Simulator or be redefined as a non-simulator audit.

## Proposed Solutions

**A. Write the codex adapter** — translate the canonical skill for codex's runtime, verify against a real life-clock build, then add `codex` back to `target_runtimes` in both registry and canonical.
- Pros: closes the loop; restores parity.
- Cons: requires the codex runtime to actually have iOS Simulator access (it currently doesn't, on most setups).
- Effort: Medium-Large.

**B. Document codex as out of scope** — add a `runtime_notes:` field to the canonical front-matter explaining why codex is deferred, and update the registry comment to point at it. Mark in registry as a permanent claude-only skill.
- Pros: honest; no false TODO debt.
- Cons: gives up on agent-native parity for this skill.
- Effort: Small.

**C. Leave the registry comment as the marker, do nothing more** (current state).
- Pros: zero change.
- Cons: risks drift if registry is restructured.
- Effort: Zero.

## Recommended Action

Defer until codex actually has iOS Simulator access. At that point: option A. Until then, option B is acceptable if the deferral starts to feel permanent.

## Acceptance Criteria

- [ ] `skills/adapters/codex/ios-simulator-ux-audit.md` exists OR canonical front-matter explicitly documents codex deferral.
- [ ] `target_runtimes` list in registry.yaml and canonical skill.md agree.
- [ ] If adapter ships: `tests/python/unit/test_ios_simulator_ux_audit_fixtures.py` extended to cover the codex translation.

## Resources

- `skills/registry.yaml:130-149` — current registry entry
- `skills/canonical/ios-simulator-ux-audit/skill.md` — canonical
- `skills/WIRING.md` — convention for canonical/adapter/project-skill split
- PR #17 review (architecture-strategist) — surfaced this on 2026-04-30
