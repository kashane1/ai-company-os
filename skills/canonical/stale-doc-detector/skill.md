---
id: stale-doc-detector
name: Stale Doc Detector
purpose: Detect common documentation drift — broken repo-relative paths and obvious stale product-name patterns — in the docs an agent reads first, and classify each finding so the operator knows what to do.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: agentic
allowed_edit_boundaries:
  - state/artifacts/stale-doc-detector/
forbidden_areas:
  - packages/
  - apps/
  - products/
  - docs/
  - skills/canonical/
  - skills/adapters/
  - skills/registry.yaml
  - .claude/skills/
  - state/
---

# Skill: stale-doc-detector

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

Documentation drift is the most common way a fresh agent gets misled.
Examples already seen in this repo: stale `fishing-logbook-ios` paths
that survived a product rename, illustrative shorthand inside backticks
that read as broken refs, runtime-only paths flagged as broken.

This skill is the agent-driven wrapper around the lightweight script
`scripts/ci/check_doc_paths.sh`. The script does the mechanical
extraction and existence check. This skill adds:

1. **classification** of each finding — fix now, allowlist, founder
   decision, or ignore as non-path text
2. **stale product-name detection** that the path checker can't see
   (e.g. legacy product slugs inside Swift code samples,
   reverse-DNS identifiers, prose that names a renamed product)

The skill does NOT inspect product source. It reads only the docs an
agent reads first.

## When to invoke

Trigger phrases: "scan for stale doc refs", "doc-path audit", "find
doc drift", "check the docs for broken paths", "audit the entry docs
for drift".

Do NOT invoke this skill for:

- Open-ended exploratory search (use `Explore`).
- Per-skill registry drift (use `skill-stocktake`).
- Pre-PR comprehensive verification (use `verification-loop`; it
  should call this skill as a sub-check).

If two trigger phrases could match, ask the operator.

## Contract

Inputs:

- `doc_paths`: list[str] | None — when None, defaults to the same set
  `scripts/ci/check_doc_paths.sh` scans:
    - `README.md`
    - `CLAUDE.md`
    - `AGENTS.md`
    - `docs/README.md`
    - `docs/skills-index.md`
- `product_ids`: list[str] | None — when None, derived from
  `infra/products.json`. Used to detect legacy product slugs in prose
  and code samples.
- `legacy_slug_hints`: list[str] = `["fishing-logbook"]` — known
  legacy slugs that the audit should flag in any doc inside the
  configured paths.

Outputs (a structured report):

- `verdict`: `"pass" | "fail"` — pass when no `fix_now` findings.
- `path_findings`: list of `{doc, token, classification, reason}`
  from the path-existence check.
- `name_findings`: list of `{doc, line, slug, classification, reason}`
  from the legacy-slug heuristic.
- `helper_exit_code`: int — exit code of
  `scripts/ci/check_doc_paths.sh`.
- `report_path`: str — path under
  `state/artifacts/stale-doc-detector/<run-id>/report.md`.

Classification values (per finding):

- `fix_now` — broken repo-relative path or legacy slug in a normal
  doc context; the agent should fix it.
- `allowlist` — runtime-only path documented as a convention (e.g.
  `state/checkpoints/platform/`); should be added to the script's
  `RUNTIME_ALLOWED` list rather than fixed in the doc.
- `founder_decision` — finding requires founder input (e.g. a
  product-rename that touches a bundle identifier; a code sample
  string whose change might affect a real product).
- `ignore` — false positive (illustrative shorthand, regex match
  inside a URL fragment, etc.).

## Procedure

1. **Run the helper script.** Invoke
   `scripts/ci/check_doc_paths.sh`. Capture stdout, stderr, exit
   code. The script emits one line per broken reference of the form:
   `<doc> -> <token>`.

2. **Classify each path finding.** For each `<doc, token>` from the
   script output:
   - If `token` matches a known runtime-only path documented in
     `state/README.md` and is referenced as a *convention* (not a
     real file), classify `allowlist`.
   - If `token` is inside backticks and is illustrative shorthand
     (e.g. `catchbook-ios/` when the full path is `products/catchbook-ios/`),
     classify `fix_now` with a one-line proposed correction.
   - Otherwise, classify `fix_now`.

3. **Scan for legacy slugs.** For each doc in `doc_paths` plus
   `docs/ios-conventions.md`, grep for every entry in
   `legacy_slug_hints`. For each hit:
   - If the surrounding context is a path (e.g. `products/<slug>-ios/`),
     classify `fix_now` and propose the current product id (from
     `infra/products.json`) as the replacement.
   - If the surrounding context is a bundle/subsystem identifier or
     a code sample where the identifier might be load-bearing for a
     real product, classify `founder_decision`.
   - If the surrounding context is clearly historical prose (a
     paragraph that documents a past name), classify `ignore`.

4. **Assemble report.** Write the structured report to
   `state/artifacts/stale-doc-detector/<run-id>/report.md`.
   `<run-id>` is the UTC timestamp of the run.

5. **Verdict.** `pass` if every finding is `allowlist`, `founder_decision`,
   or `ignore`. `fail` if any finding is `fix_now`.

## Examples

### Example — clean repo

```
input: {}
→ helper_exit_code: 0
→ path_findings: []
→ name_findings: []
→ verdict: "pass"
```

### Example — broken path + runtime-only convention

```
helper output:
  README.md -> state/checkpoints/platform/
  docs/README.md -> ../REPO_MAP.md   (note: would not appear after batch 1; illustrative)

→ path_findings: [
    {doc: "README.md", token: "state/checkpoints/platform/",
     classification: "allowlist",
     reason: "runtime-only convention; add to RUNTIME_ALLOWED"},
  ]
→ verdict: "pass"  (only allowlist findings)
```

### Example — legacy slug in code sample

```
docs/ios-conventions.md line 19: subsystem: "com.ai-company-os.fishing-logbook"

→ name_findings: [
    {doc: "docs/ios-conventions.md", line: 19, slug: "fishing-logbook",
     classification: "founder_decision",
     reason: "bundle/subsystem identifier; replacement may affect real product code"},
  ]
→ verdict: "fail"
```

## Boundaries and failure modes

- **Read-only outside `state/artifacts/stale-doc-detector/`.**
  Never edits docs, even when the classification is `fix_now`. The
  operator (or the next skill in the chain) does the edit.
- **No product source inspection.** Do not open Swift, `.pbxproj`,
  or any file under `products/`.
- **Bounded scan surface.** Default is exactly the five docs the
  helper script already scans, plus `docs/ios-conventions.md` for
  the legacy-slug heuristic. Expanding the surface requires a
  separate change to both this skill and the helper script in the
  same commit.
- **Helper is the source of truth for path existence.** This skill
  does not re-implement the path check; it interprets the helper's
  output.
- **No external calls.** Filesystem and the helper script only.

## References

- Helper script: `scripts/ci/check_doc_paths.sh` (Anti-drift batch 1).
- Sibling skills: `agent-preflight`, `handoff-write`, `verification-loop`.
- Operating doc: `docs/preflight-for-agents.md`.
