# Failure Modes — iOS Lane

Phase 1.4. See `engineering-lane.md` for the column convention.

| Condition | Detection | Recovery | failure_code | Who resolves |
|---|---|---|---|---|
| xcodebuild not installed | `scripts/preflight_xcode.sh` | Lane `blocked:xcodebuild_missing` | `xcodebuild_missing` | Founder installs Xcode |
| xcodegen not installed | preflight_xcode.sh | Lane `blocked:xcodegen_missing` | `xcodegen_missing` | Founder installs xcodegen |
| project.yml regeneration failure | preflight or worker pre-build step | Task `failed` with stderr tail | `xcodegen_generate_failed` | iOS worker or founder |
| xcodebuild compile failure | Worker captures build log | Task `failed`, log path in `artifacts[]` | `xcodebuild_compile_failed` | iOS worker |
| xcodebuild timeout | Worker hard timeout (default 20m) | Task re-queued once | `xcodebuild_timeout` | iOS worker |
| Simulator boot failure | `xcrun simctl boot` non-zero | Task `failed`; worker resets device state | `simulator_boot_failed` | iOS worker |
| Code-signing profile missing | xcodebuild error classified | Lane `blocked:signing_profile_missing`; briefing alerts | `signing_profile_missing` | Founder |
| Swift Package resolution failure | `xcodebuild -resolvePackageDependencies` error | Task `failed`, retried once | `spm_resolution_failed` | iOS worker |
| Simulator disk full | simctl returns ENOSPC-equivalent | Worker pauses lane | `simulator_disk_full` | Founder |
| App Store submission attempted without approval | `packages/policies/release_readiness.py` gate | `PolicyViolation` | `app_store_submission_approval_missing` | Founder |
| IPA upload credentials missing | Secrets helper returns None for Keychain P0 | Lane `blocked:ios_submission_credentials_missing` | `ios_submission_credentials_missing` | Founder (Keychain fix) |

Environmental rows (`xcodebuild_missing`, `xcodegen_missing`,
`signing_profile_missing`, `simulator_disk_full`,
`ios_submission_credentials_missing`) use
`no_test_reason_code=environmental_only`. All others must have an integration
test under `tests/python/integration/`.
