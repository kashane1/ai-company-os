---
summary: Every doc over 400 lines must open with a TL;DR so an agent can decide
  in one screen whether to read on. Enforced by the token-efficiency CI gate.
---

# Large-doc standard (TL;DR-first)

> **TL;DR:** Any Markdown doc longer than **400 lines** must start with a TL;DR —
> a frontmatter `summary:`/`tldr:` field, a `> ` blockquote under the H1, or a
> `## TL;DR` / `## Summary` heading near the top. The token-efficiency CI gate
> (`scripts/ci/token_efficiency_check.py`) enforces this on new docs. Existing
> docs are grandfathered, so this is a ratchet you can't backslide on, not a
> mass rewrite.

## Why

Agents pay tokens to read a doc before they know if it's relevant. A one-screen
TL;DR at the top lets them decide to read on or skip — turning a 2,000-line plan
from a forced full read into a cheap triage. This is the single highest-leverage
habit for keeping the repo cheap to operate in as it grows.

## The rule

A tracked `*.md` over `TLDR_THRESHOLD` (400) lines must contain **one** of:

1. **Frontmatter summary** (preferred for plans/specs that already use YAML):

   ```yaml
   ---
   title: ...
   status: ...
   summary: One or two sentences: what this doc is and what decision/outcome it drives.
   ---
   ```

2. **Blockquote TL;DR** directly under the H1 (preferred for prose):

   ```markdown
   # My Big Plan

   > **TL;DR:** What this is, the one decision it makes, and the bottom line.
   ```

3. **A `## TL;DR` or `## Summary` heading** within the first ~15 lines of body.

`INDEX.md` files and generator-stamped files are exempt (they are already
summaries).

## How it's enforced (so it sticks)

- **CI gate:** `scripts/ci/token_efficiency_check.py` runs in
  `.github/workflows/tests.yml` (`token-efficiency` job). A new >400-line doc
  without a TL;DR fails the build.
- **Local:** `make tokens-check` runs the same gate against your working tree —
  it sees uncommitted new docs too, so you catch it before pushing.
- **Ratchet, not a wall:** pre-existing offenders are listed in
  `scripts/ci/token_efficiency_baseline.txt` and ignored. The list can only
  shrink in spirit — **do not add new entries.** Give new docs a TL;DR instead.
  If you intentionally accept an existing doc as-is, run
  `python3 scripts/ci/token_efficiency_check.py --update-baseline`.

## Authoring checklist

- [ ] Will this doc exceed ~400 lines? Add a TL;DR up front.
- [ ] Does the TL;DR state *what it is* and *the bottom line / decision*?
- [ ] If it lives in an indexed directory, run `make doc-index` so the
      directory `INDEX.md` picks up the new summary.

## Related

- [docs/README.md](README.md) — the docs map and per-directory indexes.
- `scripts/docs/gen_doc_index.py` — pulls each doc's summary into its directory
  index (it reads the same `summary:` / blockquote this standard requires).
