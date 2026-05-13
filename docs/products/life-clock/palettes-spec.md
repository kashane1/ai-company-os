# Palettes Spec — Life Clock

> **Status:** Canonical product policy. The three named palettes (`default-navy / aurora-cool / sunset-warm`) are user-selectable in Profile and ratcheted via `UserProfile.paletteId`. This spec defines the constants, the orange-not-red invariant, and the heartbeat-red exception. Sister to `brand-guidelines.md` (which carried the original color exploration but is partly superseded).
>
> Implementation: [`Sources/Shared/LifeClockPalette.swift`](../../../products/life-clock-ios/Sources/Shared/LifeClockPalette.swift) (palette enum + accent colors) + [`Sources/Shared/DesignTokens.swift`](../../../products/life-clock-ios/Sources/Shared/DesignTokens.swift) (`Palette` semantic tokens).

## One-line rule

**Three named palettes provide the accent color. Semantic colors (`surface / elevated / positive / negative / muted`) live in `DesignTokens.Palette` and are palette-independent. Negative is muted orange — never alarming red — with one explicit exception: the mascot's ECG heartbeat.**

## The three palettes

| Palette ID | Display name | Accent color | Use |
|---|---|---|---|
| `defaultNavy` ("default-navy") | Default Navy | RGB(0.137, 0.282, 0.612) | Default; carries the icon's blue chrome |
| `auroraCool` ("aurora-cool") | Aurora Cool | RGB(0.231, 0.357, 0.749) | Cool variant; lighter blue |
| `sunsetWarm` ("sunset-warm") | Sunset Warm | RGB(0.85, 0.42, 0.20) | Warm variant — **light-mode contrast borderline; track in follow-up** |

The palette ID rawValue is stable across releases (used as `UserProfile.paletteId` SwiftData persistence). Renaming = breaking SwiftData migration.

## Semantic color tokens (binding — palette-independent)

`DesignTokens.Palette` exposes the semantic tokens every surface should use:

| Token | Color | Used for |
|---|---|---|
| `surface` | `Color(.systemBackground)` | Page backgrounds |
| `elevated` | `Color(.secondarySystemBackground)` | Cards, sheets, raised affordances |
| `positive` | `Color.green.opacity(0.85)` | Time-earned signed deltas; positive drivers |
| `negative` | `Color.orange` | Time-lost signed deltas; negative drivers (**muted, never alarming red**) |
| `muted` | `Color.secondary` | Disabled state, secondary copy |

**Never** use `Color.red` for negative deltas. The orange-not-red invariant is explicit in `LifeClockPalette.swift`'s top-of-file comment and ratcheted to vision.

## The heartbeat-red exception (binding)

`LifeClockPalette.heartbeatRed` is RGB(0.86, 0.18, 0.18) — true red. It is the **only** sanctioned use of red in the app:

- It's an identity mark (the mascot's ECG), not a status indicator.
- Direction (gain vs. loss) is conveyed by clock-hand motion, not heartbeat color.
- Centralized in `LifeClockPalette.swift` so reviewers see the rationale before "fixing" the literal.

Adding any other red use = vision-question. The invariant matters because alarming red on a healthspan app reads as "you're dying," which is the framing the entire product avoids.

## When palettes apply

The user-selected palette drives:

- `accentColor` (the `Color.accentColor` global, set in `LifeClockApp.scene` via `.tint(palette.accent)`)
- `tint(...)` on accent-tinted glyphs (sparkle icons, info badges)
- Chart's primary series stroke color on `TrajectoryChart`

The user-selected palette does NOT drive:

- Semantic tokens (`positive / negative / muted / surface / elevated`) — these stay constant
- The heartbeat — stays red
- Tone-mode colors — tone is non-visual

## Anti-patterns (binding refusals)

- **Do not hardcode hex colors in views.** Use the semantic token or the palette accent.
- **Do not use Color.red.** Heartbeat is the only exception.
- **Do not introduce a fourth palette without a vision-question.** Three is the curated set; a fourth dilutes the brand identity.
- **Do not change palette rawValues.** SwiftData migration breaker.
- **Do not let the user mix palettes.** One palette at a time. A "tinted positive / sunset negative" combo would be visually incoherent.

## Outstanding (tracked)

- Sunset Warm light-mode contrast is borderline (per `LifeClockPalette.swift` source comment). Color-contrast follow-up tracked in a polish session.
- `brand-guidelines.md` predates this spec and carries some stale "Memento Mori" tone-mode references — operator decision: archive, refresh, or supersede entirely with this spec + `microcopy-spec.md` + `accessibility-spec.md`.

## Cross-references

- Implementation: [`Sources/Shared/LifeClockPalette.swift`](../../../products/life-clock-ios/Sources/Shared/LifeClockPalette.swift), [`Sources/Shared/DesignTokens.swift`](../../../products/life-clock-ios/Sources/Shared/DesignTokens.swift)
- Profile picker: [`Sources/Features/Profile/ProfileView.swift`](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift) § Appearance section
- Privacy disclosure (palette is stored on-device): [`legal/privacy-policy.md`](legal/privacy-policy.md)
- A11y contrast: [`accessibility-spec.md`](accessibility-spec.md)
- Brand history: [`brand-guidelines.md`](brand-guidelines.md) (NB: partially superseded)

## Validation

The palette system is on-spec when ALL of the following hold:

1. Three palettes exist with stable rawValues.
2. Semantic tokens (`positive / negative / muted / surface / elevated`) are palette-independent.
3. `Color.red` appears only in `LifeClockPalette.heartbeatRed`.
4. No view hardcodes hex colors; every color flows through a semantic token or `palette.accent`.
5. The user's palette choice persists via `UserProfile.paletteId`.
6. Sunset Warm contrast is tracked (acknowledged borderline; not blocking).
