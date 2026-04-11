# App Review Demo Instructions: Catchbook v1.0

Instructions for Apple App Store reviewers. Copy this into App Store Connect → App Review Information → Review Notes.

---

## How to Test Catchbook

This app stores all data locally on-device using SwiftData. There are no accounts, no login, and no server communication. Location access is used only to tag fishing spots and is stored locally. Photo library access is used to attach catch photos. Weather data is fetched from Apple's WeatherKit and stored locally — no third-party services involved. The app works fully offline (weather enrichment is optional and graceful).

### Quick Test Flow (2 minutes)

1. **Launch the app** — you'll land on the Home tab with an empty state
2. **Go to Log tab** — tap "Add Waterbody" and create one (e.g., name: "Test Lake", type: Lake)
3. **Start a trip** — select the waterbody, optionally add a spot, tap "Start Trip"
4. **Observe conditions** — weather data should populate (temperature, wind, cloud cover) if device has network; if offline, conditions show "Weather data unavailable" and trip starts normally
5. **Log a catch** — enter species (e.g., "Bass"), optionally add weight, lure, photo
6. **End the trip** — tap End Trip, observe the summary (duration, catch count, conditions)
7. **View history** — go to Trips tab to see the completed trip
8. **Check spot detail** — go to Spots tab, tap the spot/waterbody to see accumulated history
9. **Export share card** — from a catch detail, tap Share to generate a privacy-safe catch card (location is hidden by default)

### Demo Account

Not applicable — no accounts, no login, no server.

### Special Permissions

- **Location (When In Use):** Used to tag fishing spots with GPS coordinates. Stored locally only. App works without location access — falls back to saved waterbody/spot coordinates.
- **Photo Library:** Used to optionally attach catch photos. App works without photo access — catch logging is never blocked by photo denial.
- **WeatherKit:** Fetches current weather conditions on trip start. Data stored locally. Works gracefully offline — weather fields stay empty and core logging continues.

### Network Usage

The only network call is to Apple WeatherKit for current weather conditions. No other network calls are made. No data is sent to external servers. No analytics, crash reporting, or telemetry of any kind.

### Content

All content is user-generated and private. There is no social feed, no public profiles, no shared content. The only sharing mechanism is a manual export of a privacy-safe catch card that omits location data by default.
