# Typography Spec — Life Clock

> **Status:** Canonical product policy. The 2026-05-12 premium-feel audit flagged `typography-drift` as an unresolved gap (Prompt 1) — many surfaces mix Dynamic Type semantic tokens with absolute system sizes without a clear rule. This spec defines when each is appropriate and locks the small set of allowed absolute-size exceptions.

## One-line rule

**Default to semantic Dynamic Type tokens. Use absolute system sizes only for numeric-display roles** — the headline delta, the wrap-up signed-minute readout, the dial number. Everything else (titles, body, captions, buttons, labels) uses `.font(.title)`, `.font(.headline)`, `.font(.subheadline)`, `.font(.body)`, `.font(.callout)`, `.font(.caption)`, `.font(.caption2)`, `.font(.footnote)`.

## Why

Dynamic Type is the iOS-native accessibility contract. A user who increases their system text size expects every label, title, and body string in the app to scale. Absolute sizes break that contract — they're frozen, which is fine for stylized readouts (the Today delta is a *figure* more than a *label*) but wrong for anything the user reads as text.

## The numeric-display exception (binding — role-based size families)

Numeric figures (signed-minute deltas, healthspan years, override input values, projection headlines, splash icons) are permitted to use `.font(.system(size:weight:design:))` with absolute sizes — they're visual figures, not text. They use a small set of **role families**, not arbitrary sizes:

| Role | Canonical size(s) | Weight | Design | Used by |
|---|---|---|---|---|
| **Hero numeric** | 56 → 52 → 36 → 28 fallback chain via `ViewThatFits` | `.semibold` | `.rounded` | Healthspan dial center (Future tab headline, Engine reveal, Lead-in reactive slider demo) |
| **Display numeric** | 44 | `.semibold` | `.rounded` | Today + WrapUp signed-minutes |
| **Section numeric** | 40 → 36 → 28 → 22 fallback via `ViewThatFits` | `.semibold` | `.rounded` | History weekly net, History yesterday delta, InstallSummarySection, Day detail metric |
| **Inline numeric** | 32 | `.semibold` | `.rounded` | Override input field, archetype reveal label |
| **Compact numeric** | 22 | `.semibold` | `.rounded` | Day-row delta, History compact rows |
| **Icon glyph (functional)** | 32 | `.regular` | (none) | `EmptyStateView` icon |
| **Icon glyph (splash)** | 48 | (none) | (none) | Lead-in / data-collection screen splash icon |

The convention is:

- `.semibold` weight + `.rounded` design for every numeric figure (the brand's display register).
- Plain weight + no design override for icon-glyph roles.
- Use `ViewThatFits(in: .horizontal)` to chain hero / section numeric sizes so the figure gracefully degrades on narrow widths.

Any new absolute-size site **must map to an existing role family**. Inventing a new size = `typography-drift` audit prompt; resolve by picking the closest role.

## Allowed Dynamic Type tokens

The full set in use today, ranked from largest to smallest:

- `.largeTitle.bold()` — once-per-flow page headers (use sparingly; most pages use `.title.bold()` instead)
- `.title.bold()` / `.title2.bold()` / `.title3` — section + screen titles
- `.headline` / `.headline.monospacedDigit()` — primary labels, action button copy
- `.subheadline` / `.subheadline.monospacedDigit()` / `.subheadline.weight(.semibold)` — secondary labels
- `.body` / `.body.bold()` — long-form copy, narrative paragraphs
- `.callout` — heading-adjacent emphasis (the wrap-up body line uses this)
- `.footnote` / `.footnote.weight(.semibold)` — fine print, disclaimers
- `.caption` / `.caption.weight(.semibold)` / `.caption.monospacedDigit()` / `.caption.bold()` — table cells, chip labels, the "auto-renews" line
- `.caption2` — micro-text (App Review-required fine print, `.tertiary` foreground)

### Monospaced digits

Use `.monospacedDigit()` whenever a number sits next to other numbers in a column or whenever the number animates (the heading delta, paywall price column, day-detail rows). Non-mono digits jitter when their proportional widths shift between e.g. "10" → "12".

### Weights and color

Weight modifiers (`.weight(.semibold)`, `.bold()`) are the only secondary attribute used on tokens. Color is set via `.foregroundStyle(.primary | .secondary | .tertiary)` and palette tokens (`DesignTokens.Palette.positive / negative / elevated`) — never hard-coded `Color(.systemGray)` etc.

## Anti-patterns (binding refusals)

- **Do not use `.font(.system(size:))` for label text** — that's a typography-drift violation.
- **Do not pile multiple Dynamic Type tokens** on the same line ("title for the number, body for the unit"). The line picks one token; if numeric emphasis is needed, use `.headline.monospacedDigit()` or graduate to the numeric-display exception.
- **Do not use absolute pixel font sizes** outside the table above. If you think you need one, file a vision-question.
- **Do not use serif fonts.** The numeric display is `.rounded` for the on-brand display register; everything else is the system default sans.
- **Do not nest `.font(...)` inside a `Text + Text` composite** without verifying it works under Dynamic Type. SwiftUI composes attributed strings well, but mixed-size `Text` runs can break extra-large accessibility sizes.

## Cross-references

- Premium-bar: [`premium-bar.md`](premium-bar.md) § "Typography"
- Brand guidelines: [`brand-guidelines.md`](brand-guidelines.md) (NB: that doc was a pre-rename snapshot — typography content here supersedes anything inconsistent there)
- Audit prompt: `premium-feel-backlog-2026-05-12-standard.md` Prompt 1 (`typography-drift`)

## Validation

A surface is typography-aligned when ALL of the following hold:

1. Every `.font(...)` modifier uses either (a) a Dynamic Type semantic token or (b) one of the six approved absolute-size numeric-display roles.
2. No call site uses raw `Color(.systemGray)` / hex colors for text — every color goes through `.foregroundStyle(...)` with a semantic key.
3. Animated or column-aligned numbers use `.monospacedDigit()`.
4. The surface renders correctly at the largest accessibility text size (`UIContentSizeCategory.accessibilityExtraExtraExtraLarge`) without truncation, overlap, or hidden controls.

When (1)–(4) hold across all shipped surfaces, the premium-readiness `typography-drift` count is zero.
