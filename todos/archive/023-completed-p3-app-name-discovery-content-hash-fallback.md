---
status: completed
priority: p3
issue_id: "023"
tags: [code-review, skills, yagni, app-name-discovery]
dependencies: [022]
---

# Problem Statement

`skill.md` Failure modes section specifies a SHA-256 content-hash fallback when the product directory is not in a git repo. The repo's product dirs all live under `docs/products/` in this git tree — the fallback path will never fire in practice.

## Findings

Code-simplicity-reviewer:
> "`content_hash` git-fallback is speculative — most runs will be in-repo. Cut until someone hits it."

## Proposed Solutions

### Option 1: Remove the fallback (recommended)

If `git rev-parse HEAD` fails, abort with a clear error: "skill must be invoked inside a git repo." Don't invent a parallel reproducibility scheme.

Pros: simpler. One reproducibility path, not two.
Cons: future caller running the skill outside git needs to set up a repo first. Negligible.

### Option 2: Keep as documented contingency

Pros: belt-and-suspenders. Cons: dead code.

## Acceptance Criteria

- [ ] Failure modes section no longer mentions content-hash fallback.
- [ ] Output-template no longer references `content_hash`.
- [ ] Adapter no longer references the fallback.
- [ ] Pytest still passes.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/15
