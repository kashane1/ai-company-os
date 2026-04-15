---
title: packages/tools/primitives/ Subpackage Convention
date: 2026-04-14
status: accepted
supersedes: (none)
related:
  - docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md
  - docs/adr/2026-04-14-canonical-skill-layout.md
---

# `packages/tools/primitives/` Subpackage Convention

## Status

**Accepted** (2026-04-14, Phase 0.5e).

## Context

`packages/tools/` today mixes two categories of modules:

1. **Subsystem call-outs** — modules that wrap an external system
   (Claude, Codex, git worktrees, the skill registry). Examples:
   `claude_tools/`, `codex_tools/`, `worktrees.py`, `skills/`.

2. **Agent-callable primitives** — stateless, side-effect-free
   functions with typed return values that ANY worker or canonical
   skill can import and call. Phase 0.5c/0.5d/Phase 4/5/6 all add
   primitives of this shape: `dispatch_health_reader`, `kill_switches`,
   `approvals`, `peer_runtimes`.

Without a convention, these two categories would accumulate side-by-side
under the flat `packages/tools/` namespace and the boundary between
"wrapper of external system" and "primitive for agent composition"
would erode. A grep for "kill switches" would turn up
`packages/tools/kill_switches.py` sitting next to
`packages/tools/codex_tools/`, with no obvious distinction.

## Decision

**Every agent-callable primitive lives under `packages/tools/primitives/`.**

The layout:

```
packages/tools/
├── claude_tools/        # subsystem call-out (Claude SDK integration)
├── codex_tools/         # subsystem call-out
├── skills/              # subsystem call-out (registry + loader)
├── worktrees.py         # subsystem call-out (git worktree wrapper)
├── acp/                 # Phase 4 — subsystem call-out (ACP SDK wrapper)
├── providers/           # Phase 6 — subsystem call-out (provider overlay)
├── dispatch_health.py   # cross-cutting writer (emits JSONL events)
└── primitives/          # THIS ADR — agent-callable primitives
    ├── __init__.py
    ├── dispatch_health_reader.py    # Phase 0.5e (cross-cutting observability)
    ├── kill_switches.py             # Phase 3
    ├── approvals.py                 # Phase 5
    └── peer_runtimes.py             # Phase 4
```

## Convention rules

Every module under `packages/tools/primitives/` MUST:

1. **Be stateless at module level.** No mutable global state, no module-
   level initialization that touches the filesystem, network, or
   environment variables.

2. **Have side-effect-free imports.** `import packages.tools.primitives.foo`
   must NOT spawn threads, open sockets, read config files, or trigger
   any other work. A primitive is loaded lazily when its functions are
   called, not at import time.

3. **Return typed values.** Every public function returns a frozen
   dataclass, a Protocol instance, or a primitive Python type
   (str, int, bool, tuple of those). No dicts-of-anything, no dynamic
   attribute bags. Typed returns are the contract callers depend on.

4. **Contain no orchestration.** Each public function is a single
   operation — read a switch, summarize health events, request one
   approval. Functions that loop over tasks or call other primitives
   in sequence belong in workers, not primitives.

## Convention test

A new test at `tests/python/unit/test_primitives_conventions.py` walks
`packages/tools/primitives/` and asserts:

- No module contains a class instantiation at module level (other than
  frozen dataclass DEFINITIONS, which are class statements but don't
  instantiate anything).
- No module imports `subprocess`, `socket`, `urllib`, `requests`, or
  any other network/subprocess entry point at module level.
- No module writes to the filesystem at module level.
- Every public function (non-underscore prefix) has a type annotation
  on its return value.

The test fails CI on any primitive that violates the rules, forcing
new primitives to follow the convention or explicitly change the ADR.

## Rationale

- **The mental model stays clean.** When a reviewer sees
  `packages/tools/primitives/foo.py`, they know immediately that
  it's callable from anywhere with zero setup cost.

- **Agent-native parity is enforced by the import graph.** Phase 3's
  skill-self-evolution canonical skill reads task outcomes through
  `primitives/dispatch_health_reader.py` so the skill contract is
  portable across runtimes (Claude, Codex, ACP) — the skill doesn't
  care about file paths or stream buffers, just the typed primitive.

- **Refactors are contained.** Moving a module INTO `primitives/`
  later requires proving it passes the convention test. Moving a
  module OUT of `primitives/` is an explicit signal that it's grown
  state or orchestration responsibilities.

## Consequences

### Immediate

- Phase 0.5e creates the `packages/tools/primitives/` directory with
  an `__init__.py` placeholder and the `test_primitives_conventions.py`
  convention test.
- Phase 3/4/5 primitive modules (listed in the layout above) land
  under `primitives/` instead of flat.

### Forward

- Any subsystem call-out that accidentally grows primitive-shaped
  helpers should extract them into `primitives/` rather than pollute
  its own namespace.
- Reviewers treat `primitives/` as the canonical place to look for
  "can I call this from my skill / worker / script?" answers.

## References

- Plan section: Cross-Cutting Enhancements X4a and X6 in
  `docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md`.
- Pattern consistency review (deepening pass) flagged the flat
  `packages/tools/*.py` primitives as an accumulating grab-bag risk.
