# simulator-driven-polish — Codex adapter

> Source of truth: `skills/canonical/simulator-driven-polish/skill.md`.
> This adapter translates the canonical polish loop into Codex runtime
> behavior. Do not duplicate product-specific polish logic here.

## Codex startup contract

Before running the loop, Codex must surface and confirm the canonical inputs:

- `product_id` and `products/<product-id>-ios/`
- Xcode scheme, verified with `xcodebuild -list -project <path>`
- Simulator device + iOS, selected from `xcrun simctl list devices available`
- mode: `fix-list`, `freeform-polish`, `reference-match`, or `vision-driven`
- mode payload, if any
- slug for `docs/products/<product-id>/polish-<YYYY-MM-DD>-<slug>.md`
- iteration cap
- `final_check`

If the working tree is dirty, stop and ask before beginning. Do not silently
fold unrelated user edits into the polish run.

## Runtime translation

Use shell commands for simulator work:

```bash
xcodebuild -list -project products/<product-id>-ios/<Project>.xcodeproj
xcrun simctl list devices available
xcodebuild -project products/<product-id>-ios/<Project>.xcodeproj \
  -scheme <scheme> \
  -destination 'platform=iOS Simulator,name=<device>' \
  build
xcrun simctl boot <device>
xcrun simctl install <device> <app-path>
xcrun simctl launch --console <device> <bundle-id>
```

Use the product's launch seed harness for deterministic state, such as
`LIFECLOCK_UI_TEST_SCENARIO`, `LIFECLOCK_SEED_TONE`,
`LIFECLOCK_FIXED_DATE`, or a product-equivalent env var.

## Observation order

Prefer the cheapest deterministic signal first:

1. Existing UITest or recon harness that dumps an accessibility tree.
2. `XCUIApplication().debugDescription` from a focused recon test.
3. `xcrun simctl io <device> screenshot <path>` when the tree is insufficient.
4. Computer Use only for gestures or the final user-style checkpoint.

Screenshots captured for the loop belong under
`products/<product-id>-ios/.polish/goldens/`. When a screenshot changes, record
whether the diff was intended in the session log. If a screen not touched by
the current fix changes, treat it as a regression suspect and classify it
before proceeding.

## Editing and asks

Use `apply_patch` for manual source edits. Keep changes inside:

- `products/<product-id>-ios/**`
- `docs/products/<product-id>/**`

Never edit `packages/policies/`, `state/`, other products, or `vision.md`
`## Decided constraints`.

When the canonical skill calls for `AskUserQuestion`, present a numbered list
in chat and wait for the operator's answer. Batch Feature and Vision-question
asks at cycle close. Do not ask one-off questions during the iteration unless
a precondition or stop condition blocks the run.

## Commits and logs

If the operator authorized an editing polish run, Codex may create one commit
per logical fix. The commit rule is one commit per logical fix:

- `fix(<product>): <one-line>`
- `feat(<product>): <one-line>`
- `chore(<product>): a11y id for <element>`
- `docs(<product>): <one-line>`

Each commit must be preceded by a passing build for the target simulator.
Append one iteration line to
`docs/products/<product-id>/polish-<YYYY-MM-DD>-<slug>.md` after each fix.

If a driven element lacks a stable `accessibilityIdentifier`, add one in source
and commit it separately when it is not already part of the logical fix.

## Computer Use final checkpoint

Use Computer Use only when `final_check=true`, when `vision-driven` mode makes
it mandatory, or when a gesture cannot be expressed by the accessibility tree.
Before every Computer Use action, fetch the latest app state and confirm the
frontmost app/window is the intended Simulator target. Do not send, delete,
purchase, archive, deploy, or submit anything.

## Memory replacement

Codex has no durable assistant-memory primitive in this repo. When the
canonical skill says to write memory, record the convention in the session log
and propose a `vision.md` or product-doc update for operator approval. Codex may
append `## Open Questions`; it must never edit `## Decided constraints`.

## Verification

Before declaring done:

- run the changed-surface build/test command that matches the files touched
- confirm touched goldens are intentional
- check `git diff --stat`
- emit the PR-ready summary from the session log
- report any outstanding batched asks
