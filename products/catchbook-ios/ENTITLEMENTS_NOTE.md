# Entitlements Evaluation

Evaluated: 2026-04-08
Updated: 2026-04-09

## Current Status

Catchbook.entitlements exists with one entitlement: WeatherKit.

## Current Entitlements

| Entitlement | Key | Reason |
|-------------|-----|--------|
| WeatherKit | `com.apple.developer.weatherkit` | Live weather enrichment on trip start (temperature, wind, cloud cover, precipitation). Added 2026-04-09. |

## Current Permissions (Info.plist)

The app uses these system capabilities, all handled via Info.plist declarations:

- Core Location (when-in-use) — NSLocationWhenInUseUsageDescription
- Photo Library read — NSPhotoLibraryUsageDescription
- Photo Library write — NSPhotoLibraryAddUsageDescription
- Custom UTType export — UTExportedTypeDeclarations

## What Would Require Additional Entitlements

If the app adds any of these features, add to Catchbook.entitlements:

- iCloud/CloudKit sync → com.apple.developer.icloud-container-identifiers, com.apple.developer.icloud-services
- Push notifications → aps-environment
- App Groups (widget data sharing) → com.apple.security.application-groups
- HealthKit → com.apple.developer.healthkit
- Apple Pay → com.apple.developer.in-app-payments

## WeatherKit Setup Note

WeatherKit also requires enabling the capability in the Apple Developer Portal:
1. Go to Certificates, Identifiers & Profiles → Identifiers
2. Select the App ID (`io.aicompanyos.products.fishinglogbook`)
3. Enable "WeatherKit" under Capabilities
4. This must be done when setting up code signing (before building)

The Apple Developer Program includes 500,000 WeatherKit API calls per month at no extra cost.
