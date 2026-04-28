---
id: ios-build-and-sign
name: iOS Build and Sign
purpose: Produce a signed, validated iOS binary ready for TestFlight or App Store upload. Captures the build + sign workflow as an explicit contract — what was previously a procedural black box in `apps/worker-ios` becomes reviewable.
owner_agent: ios
target_runtimes: [claude, codex]
stage: active
inputs:
  - product_id (string) — from infra/products.json
  - build_configuration (enum: release | debug) — defaults to release
  - certificate_id (string, optional) — defaults to product config
outputs:
  - binary_path (string) — absolute path to the signed .ipa
  - code_sign_identity (string) — the certificate common name actually used
  - provisioning_profile (string) — name of the profile baked into the binary
  - build_number (int or string) — CFBundleVersion of the produced binary
  - build_validated (bool) — true only if every validation step passed
allowed_edit_boundaries:
  - state/artifacts/ios/builds/
  - state/checkpoints/platform/builds/
forbidden_areas:
  - products/ (source code is read-only during build)
  - packages/policies/ (policy is read-only input)
  - infra/ (signing config is read-only input)
dependencies:
  - infra/products.json must declare the product with a valid `source_path`
  - fastlane (or equivalent) is installed and configured for the product
  - signing certificate and provisioning profile exist and are not expired
validation_steps:
  - binary exists at the declared path
  - `codesign --verify --verbose <binary>` succeeds
  - `code_sign_identity` matches the requested `certificate_id` (or the product default)
  - `build_number` is greater than the last submitted build (App Store regression check)
  - no debug flags or test configurations are baked into a release configuration
handoff_contract:
  what_is_handed_off: signed binary path + signing-state record
  handed_to: ios-to-appstore-handoff (downstream skill consumes the binary path and signing record)
claude_adaptation_notes: |
  Claude does not invoke fastlane directly. Claude reads the artifact
  emitted by the Codex run, validates the signing identity matches the
  product config, and surfaces failures with concrete next-step
  guidance (renew cert, rotate profile, bump build number). When the
  binary is missing or unsigned, Claude does NOT attempt to re-run
  the build — that path is owned by the Codex adapter to keep the
  build path single-tier.
codex_adaptation_notes: |
  Codex owns the actual fastlane invocation (or `xcodebuild archive`
  fallback). Codex parses fastlane stdout for `binary_path`,
  `code_sign_identity`, `provisioning_profile`, and `build_number`.
  On certificate-expired failure, Codex retries once after triggering
  `fastlane match` for renewal. On a second failure, surface the error
  with the captured stderr — do NOT loop further. The retry budget is
  one renewal attempt per build invocation.
---

## Instructions

### 1. Load product config

Read `infra/products.json` and locate the entry for `product_id`. Required fields:
- `source_path` — typically `products/<product>-ios/`
- `bundle_id` — for signing-identity validation
- `signing.certificate_id` — default certificate
- `signing.provisioning_profile_name` — default profile

If any required field is missing, halt and emit `unsafe_product_config` — do not proceed with assumed defaults.

### 2. Verify signing prerequisites

Before invoking the build:
- Certificate exists in the keychain and is not expired (codex adapter: `security find-identity -v -p codesigning`).
- Provisioning profile exists and matches the bundle id.
- Build number bumps cleanly — fetch the last submitted build from `state/checkpoints/platform/releases/` and compute `build_number = max(local, submitted) + 1`.

If a prerequisite fails, emit a typed failure (see `## Failure modes`) and stop. The build is not attempted with broken signing state.

### 3. Invoke the build

Codex adapter runs the actual archive. Two supported invocations:
- Preferred: `fastlane build_release` (or `fastlane build_debug` per `build_configuration`) — the product's fastlane lane orchestrates archive + sign.
- Fallback: `xcodebuild -workspace <ws> -scheme <scheme> -configuration <cfg> -archivePath <out> archive` followed by `xcodebuild -exportArchive`.

Capture stdout to `state/artifacts/ios/builds/<product_id>/<build_number>/build.log`. The log path is part of the build record and must be referenced by downstream tools.

### 4. Parse the artifact

After a successful invocation, locate:
- `.ipa` file at the path declared by fastlane / xcodebuild output
- `code_sign_identity` from the export options or `codesign -dv` output
- `provisioning_profile` from the embedded `embedded.mobileprovision`
- `build_number` from `Info.plist:CFBundleVersion`

Each value MUST be parseable from the actual artifact, not from the input parameters. Trusting input over artifact is a known signing-mismatch trap.

### 5. Validate

Run `codesign --verify --deep --strict <binary_path>`. Must exit 0. Any failure is a hard stop — do not emit `build_validated: true`.

Run a sanity check that the produced `code_sign_identity` matches what was requested. Mismatch indicates the keychain returned a different identity than expected (common when multiple certs share a CN).

Run a build-number regression check against `state/checkpoints/platform/releases/`. If a release with `build_number ≥ produced` already exists, halt — Apple will reject the upload.

### 6. Emit the build record

Write to `state/checkpoints/platform/builds/<product_id>-<build_number>.json`:

```yaml
product_id: <product_id>
build_configuration: release | debug
build_number: <int>
binary_path: <absolute path>
code_sign_identity: <CN of cert used>
provisioning_profile: <name>
build_log_path: state/artifacts/ios/builds/<product_id>/<build_number>/build.log
build_validated: true
built_at: <ISO 8601 UTC>
```

This record is the handoff input to `ios-to-appstore-handoff`. Do NOT advance status beyond `build_validated: true` here — TestFlight upload is a separate skill.

## Failure modes

- **certificate_expired** — codesign cert past its valid range. Codex adapter retries once via `fastlane match` (cert-renewal lane). Second failure halts with the captured `security find-identity` output.
- **provisioning_profile_mismatch** — the profile bundle id does not match the product's `bundle_id`. Halt; do NOT attempt to regenerate. Surface to the operator with the parsed mismatch.
- **build_number_regression** — produced number ≤ last submitted. Halt before the upload step. The fix is bumping the local source's build number, which this skill never does on its own.
- **codesign_verify_failed** — `codesign --verify` non-zero. Halt; emit `build_validated: false`. Common cause: stale entitlements, mismatched profile, or a broken keychain unlock state.
- **fastlane_unavailable** — fastlane not installed or product has no Fastfile. Fall back to `xcodebuild`. Document the fallback in the build log so reviewers can see which path ran.
- **unsafe_product_config** — required fields missing in `infra/products.json`. Halt before any side effect.

## Worked example

For Catchbook v1.0.0, build 42:

```
inputs:
  product_id: catchbook
  build_configuration: release
  # certificate_id omitted — uses product default

outputs:
  binary_path: state/artifacts/ios/builds/catchbook/42/Catchbook.ipa
  code_sign_identity: "Apple Distribution: Kashane Singh (TEAMID)"
  provisioning_profile: Catchbook AppStore
  build_number: 42
  build_validated: true

build record:
  state/checkpoints/platform/builds/catchbook-42.json
```

A typical failure (cert expired):

```
verdict: failed
failure_code: certificate_expired
attempted_renewal: true
renewal_outcome: succeeded
build_validated: false  # second attempt still failed for unrelated reason
log_excerpt: |
  ❌ codesign returned 1: errSecInternalComponent
  💡 Run: security unlock-keychain -p <pwd> ~/Library/Keychains/login.keychain
```

## References

- fastlane match: https://docs.fastlane.tools/actions/match/
- Apple `codesign(1)`: https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Procedures/Procedures.html
- Build number guidance: https://developer.apple.com/library/archive/qa/qa1827/_index.html
- Sibling skill: `skills/canonical/handoffs/ios-to-appstore-handoff.md` (downstream consumer of the build record)
- Product config: `infra/products.json`
