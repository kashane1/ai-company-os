# UX / accessibility rules (curated, high-severity)

Curated from UI UX Pro Max `ux-guidelines.csv` (MIT — see `ATTRIBUTION.md`),
filtered to the high-severity rules that apply to a static landing page. These
back the QA checklist (`_scaffold/04-qa-checklist.md`) and the contrast gate in
`packages/web/validation.py`.

## Accessibility (High)
- **Color contrast — text:** ≥ **4.5:1** for normal text, ≥ **3:1** for large
  text (≥ 24px, or ≥ 18.66px bold). Check `--text`/`--bg` and any text-on-color
  (CTA label on accent). Enforced in code by `check_contrast`.
- **Non-text contrast:** UI components, icons, focus rings, and borders that
  carry meaning ≥ **3:1** against adjacent colors.
- **Alt text:** every meaningful `<img>` has descriptive `alt`; decorative images
  use `alt=""`. (Already enforced by `check_accessibility`.)
- **Keyboard + focus:** every interactive element is reachable by Tab and shows a
  visible focus state. Don't remove outlines without a replacement ring.
- **Accessible names:** links/buttons have text or an `aria-label`. (Enforced.)
- **One `<h1>`, logical heading order.** (Enforced.)
- **`<html lang>` and a `<title>`.** (Enforced.)

## Touch (High / Medium)
- **Tap targets ≥ 44×44px** with adequate spacing — applies to nav links, CTA
  buttons, and form controls on mobile.

## Forms (High)
- Every input has an associated `<label>` (visible or visually-hidden).
- Use appropriate `type`/`autocomplete` (`type=email`, `autocomplete=email`).
- Validate inline; don't rely on color alone to signal errors.

## Responsive / Animation (High)
- `width=device-width` viewport meta present. (Enforced by `check_responsive`.)
- Honor `prefers-reduced-motion`: gate every animation behind it.

## Single primary CTA
- One **primary** CTA per viewport/section; repeat the same action top and
  bottom rather than competing buttons. (Authoring rule — eyeball in QA, not a
  code gate; a uniform button style makes this hard to police automatically.)
