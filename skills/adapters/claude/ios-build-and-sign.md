# ios-build-and-sign — Claude adapter

> Thin pointer. Source of truth: `skills/canonical/products/catchbook/ios-build-and-sign.md`.

## Claude's slice

Claude **does not invoke fastlane**. The Codex adapter owns the build
path. Claude's job is to:

1. Read the build record at `state/checkpoints/platform/builds/<product_id>-<build_number>.json`.
2. Validate the signing identity matches the product config in `infra/products.json`.
3. Surface failures with concrete next-step guidance.

Keeping the build path single-tier (Codex only) prevents drift between
two parallel "build" implementations.

## Validation checks

Given a build record, confirm:

- [ ] `binary_path` resolves to a real file
- [ ] `build_validated == true`
- [ ] `code_sign_identity` matches `infra/products.json:<product>.signing.certificate_id` (or its CN)
- [ ] `provisioning_profile` matches `infra/products.json:<product>.signing.provisioning_profile_name`
- [ ] `build_number` is greater than the last entry in `state/checkpoints/platform/releases/<product>-*.json`

If any check fails, do NOT trigger a re-build from this adapter — surface the failure.

## Surfacing failures

For each failure mode, emit a single clear next-step:

| Failure | Next step to surface |
|---|---|
| `certificate_expired` (despite renewal attempt) | "Cert renewal failed. Run `fastlane match` interactively or rotate via Apple Developer console." |
| `provisioning_profile_mismatch` | "Profile bundle id != product bundle id. Re-generate the profile in Apple Developer." |
| `build_number_regression` | "Bump build number in the source's Info.plist before re-archiving." |
| `codesign_verify_failed` | "Codesign rejected the binary. Most common cause: keychain locked. Run `security unlock-keychain` and retry." |
| `unsafe_product_config` | "Required field missing in `infra/products.json`. Add `<field>` and re-run." |

## Forbidden

- Do NOT invoke fastlane, xcodebuild, or any build tool. That is the Codex adapter's slice.
- Do NOT modify the build record. Read-only.
- Do NOT advance `status` beyond what's already in the record.
