# ios-build-and-sign — Codex adapter

> Thin pointer. Source of truth: `skills/canonical/products/catchbook/ios-build-and-sign.md`.

## Codex's slice

Codex owns the **invocation path** — runs fastlane (or xcodebuild
fallback), parses output, retries on cert renewal, and writes the
build record.

Claude's slice is artifact validation. Do not duplicate that here.

## Invocation pattern

```bash
# Preferred:
fastlane --env release build_release

# Fallback when fastlane is unavailable:
xcodebuild -workspace <ws> -scheme <scheme> \
  -configuration Release \
  -archivePath state/artifacts/ios/builds/<product>/<build>/archive.xcarchive \
  archive

xcodebuild -exportArchive \
  -archivePath state/artifacts/ios/builds/<product>/<build>/archive.xcarchive \
  -exportOptionsPlist <product>/ExportOptions.plist \
  -exportPath state/artifacts/ios/builds/<product>/<build>/
```

Capture both stdout and stderr to
`state/artifacts/ios/builds/<product_id>/<build_number>/build.log`.

## Retry policy

**One renewal attempt per build invocation.** If `codesign` fails with
`errSecInternalComponent` or fastlane reports a cert expiry, run
`fastlane match` (renewal lane) once and retry the build. A second
failure is a hard stop — surface the captured stderr to the operator.
Do NOT loop further; cert state needs human review at that point.

## Parsing fastlane output

Required fields, all parsed from the actual artifact (NOT from input):

| Field | Source |
|---|---|
| `binary_path` | `IPA_OUTPUT_PATH` from fastlane env, or the path printed by `xcodebuild -exportArchive` |
| `code_sign_identity` | `codesign -dv <binary>` stderr → `Authority=<CN>` line |
| `provisioning_profile` | Read `embedded.mobileprovision` inside the .ipa via `security cms -D -i` |
| `build_number` | `Info.plist:CFBundleVersion` inside the .ipa |

Trusting the input parameters over the artifact is a known
signing-mismatch trap (the keychain may return a different cert than
the one the operator named).

## Forbidden

- Do NOT modify source under `products/`. Build is a read-only operation against source.
- Do NOT advance `status` beyond `build_validated: true`. TestFlight upload is `ios-to-appstore-handoff`'s job.
- Do NOT loop more than one renewal attempt — see Retry policy above.
