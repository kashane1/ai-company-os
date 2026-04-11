# Skill: aso-keyword-refresh

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Weekly ASO keyword refresh. Reads the current App Store metadata and a
keyword-rank snapshot from App Store Connect, returns a diff plus a
recommendation. Does not touch metadata directly. If the recommended diff
exceeds `refresh_threshold`, files a `APPSTORE_METADATA_DRAFT` strategic
task instead of applying the change.

## Contract

Inputs: `metadata_md` (text), `rank_snapshot` (list of `{keyword, rank}`),
`refresh_threshold` (default 0.2).

Outputs: `diff_md` (str), `recommendation` (enum: `apply`, `file_strategic_task`,
`no_change`), `rationale` (str).

## Non-goals

- Never publishes to App Store Connect.
- Never edits `docs/products/<product>/app-store/metadata.md`.
