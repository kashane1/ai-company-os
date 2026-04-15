---
id: context-budget
name: Context Budget
purpose: Count approximate tokens across every adapter file, canonical body, and project-skill pointer, bucket totals by owner_agent lane, and produce a per-lane report with the top N largest skills.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: validator
---

# Skill: context-budget

Kind: validator
Owner: supervisor
Runtimes: claude

## Purpose

Per-lane prompt bloat is invisible until a worker's context window
starts evicting content. This skill measures the token totals per
`owner_agent` lane and per skill so the operator can see which lane
is trending toward bloat.

**First-landing scope (per deepening finding #4 and OpenTelemetry
GenAI "attribute don't aggregate" convention):** report numbers,
not verdicts. No thresholds. No `over_threshold_lanes`. No
`packages/policies/context_budget.py`. The baseline run produces
real numbers and a future PR sets caps if and when an incident
motivates a specific threshold.

## When to invoke

- CI on every push (via pytest integration in the existing unit-test
  run).
- `verification-loop` as a sub-check (deferred — added when
  thresholds exist).
- Operator via trigger phrases: "check the context budget", "how
  bloated are the skill lanes", "which lane is trending toward
  prompt bloat".

## Contract

Inputs (via the validator `run()` payload):

- `registry_path`: Path | None — override for synthetic tests.

Outputs:

- `verdict`: always `"pass"` in v1 (report-only, no thresholds).
- `report`: ContextBudgetReport as JSON-safe dict with fields:
  - `tokenizer`: `"tiktoken:o200k_base"` or `"char_count_fallback"`
  - `tokenizer_version`: str
  - `lanes`: list of `{lane, total_tokens, skill_count}` sorted
    descending by token count
  - `top_largest`: list of `{skill_id, lane, canonical_tokens,
    adapter_tokens, project_skill_tokens, total_tokens}` — top 10
  - `system_prompt`: breakdown of CLAUDE.md + project-skill pointers
    + (deferred) MCP instruction blocks
  - `notes`: list of strings documenting measurement caveats

## Token counting

The primitive counts via `tiktoken.o200k_base` when the package is
available; otherwise it falls back to `len(text) // 4`. The
`tiktoken` import is lazy (inside `count_tokens()`) per the
primitives convention test that forbids module-level I/O. The
encoder is cached via `functools.lru_cache` on a lazy factory so
warm calls amortize the ~100-200 ms cold-start cost.

**`o200k_base` is a closer proxy to Claude's tokenizer than
`cl100k_base`** on contemporary English/code. The char-count
fallback is conservative and reliably under-counts punctuation-dense
code. Comparisons across tokenizer versions should flag the bump;
the baseline JSON records which tokenizer ran.

## System-prompt lane

A special `system_prompt` lane sums:

- `CLAUDE.md` — the primary system prompt file.
- Every active `.claude/skills/*.md` project-skill pointer.
- (Deferred to v2) MCP instruction blocks from `.mcp.json` and
  `settings.json` — surfaced as a TODO note in every v1 report.

Measured as a distinct lane from the `supervisor`/`engineering`/etc.
adapter lanes so system-prompt bloat is visible separately.

## Procedure

1. Load the registry via direct YAML parse.
2. For each entry, count tokens in the canonical body, every
   adapter file, and the project-skill pointer (if present). Every
   path resolves via `_safe_paths.safe_join()`.
3. Bucket per-skill totals by `owner_agent`.
4. Compute top-N largest skills by total tokens.
5. Measure the system_prompt lane (CLAUDE.md + project-skill
   pointers).
6. Assemble a `ContextBudgetReport` with tokenizer metadata + notes.
7. Serialize via `dataclasses.asdict(..., dict_factory=json_safe_factory)`.
8. Return `{verdict: "pass", report}`.

## Boundaries and failure modes

- **Read-only.** Counts file sizes and token approximations; never
  writes source.
- **Lazy tiktoken import.** Module-level compile / import of heavy
  deps is forbidden by the primitives convention test.
- **No thresholds in v1.** A lane being "huge" is not a failure in
  the v1 landing. The operator reads the report, not the verdict.
- **Performance.** < 400 ms warm / < 1000 ms cold on the live
  registry.
- **Thread safety.** `tiktoken.Encoding.encode()` is treated as
  thread-safe based on community usage but the upstream README
  doesn't document it. Revisit before CI enables parallel test
  runners.

## References

- Plan: `docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md` Phase 2b.
- Primitive: `packages/tools/primitives/context_budget.py`.
- Reader: `packages/tools/primitives/context_budget_reader.py`.
- Framework docs research on o200k_base vs cl100k_base (2026-04-15).
