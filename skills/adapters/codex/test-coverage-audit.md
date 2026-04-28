# test-coverage-audit — Codex adapter

> Thin pointer. Source of truth: `skills/canonical/shared/test-coverage-audit.md`.
>
> **Status: deferred.** Registered ahead of coverage tooling configuration.

## Codex's slice

Codex owns **tool invocation**: run `coverage` / `xccov`, parse output,
write the structured report to `state/artifacts/coverage/<branch>/`.

Claude's slice is proposing tests. Do not duplicate that here.

## Invocation

Python lane:
```bash
coverage run -m pytest tests/python/
coverage json -o state/artifacts/coverage/<branch>/python.json
```

iOS lane:
```bash
xcodebuild test \
  -workspace products/<product>-ios/Catchbook.xcworkspace \
  -scheme Catchbook \
  -enableCodeCoverage YES \
  -resultBundlePath state/artifacts/coverage/<branch>/ios-result.xcresult

xccov view --json state/artifacts/coverage/<branch>/ios-result.xcresult \
  > state/artifacts/coverage/<branch>/ios.json
```

## Parsing output

Required fields in the structured report (per lane):

- `targetCoverage` (overall fraction)
- `files[].path` + `files[].lineCoverage`

Aggregate per-file coverage across the changed-files list. Compute:
- Lane percent: weighted average over changed files in that lane.
- Overall percent: weighted average across all changed logic-bearing files.

Write the report to `state/artifacts/coverage/<branch>/<lane>.json`. Claude's adapter consumes it.

## Forbidden

- Do NOT propose tests. That's Claude's slice.
- Do NOT modify `tests/`. The skill is read-only against existing tests.
- Do NOT default to `meets_policy` if tooling fails — emit `coverage_tool_unavailable`.
