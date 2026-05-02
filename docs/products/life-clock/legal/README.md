# Life Clock Legal — Hosting Instructions

These markdown files are the **source** for the public privacy policy and terms-of-use pages that Life Clock links to from `PaywallSheet.swift` and the App Store Connect listing.

They need a stable, public URL. The cheapest correct way to host them is GitHub Pages, free.

## Setup (one-time, ~10 minutes)

### 1. Create a public GitHub repo

Suggested name: `life-clock-legal` (under your personal or org account).

```bash
# from this directory:
cp privacy-policy.md /tmp/life-clock-legal/privacy-policy.md
cp terms-of-use.md /tmp/life-clock-legal/terms-of-use.md
cp README.md /tmp/life-clock-legal/README.md
# create a tiny index.html that redirects to privacy-policy
```

Or just upload the three markdown files to a new public repo via the GitHub web UI.

### 2. Enable GitHub Pages

In the repo settings:

- Settings → Pages
- Source: **Deploy from a branch**
- Branch: **main**, folder: **/ (root)**
- Save

GitHub will build the site and tell you the URL. It looks like:

```
https://<your-github-username>.github.io/life-clock-legal/
```

The privacy policy will be reachable at:

```
https://<your-github-username>.github.io/life-clock-legal/privacy-policy
```

(GitHub Pages with the default Jekyll theme renders `.md` files as HTML and drops the extension.)

### 3. Replace the placeholders in the markdown

Both files have `[REPLACE WITH ...]` markers for legal entity name, support email, and governing-law jurisdiction. Update those before publishing.

### 4. Wire the URLs into the app

The current app already points to the GitHub Pages URLs in:

- `products/life-clock-ios/Sources/Services/LifeClockConfiguration.swift`

If the legal site ever moves, update `privacyPolicyURL`, `termsOfUseURL`, and `supportURL` there.

### 5. Submit those URLs to App Store Connect

When you create the app in ASC, the App Information page asks for:

- **Privacy Policy URL** (required for all apps)
- **Subscription EULA URL** (optional; we use Apple's standard EULA but link our terms page additionally)

Paste the GitHub Pages URLs there.

## Why GitHub Pages

- Free, no server to run.
- Edits are version-controlled (so any change to the policy has a public history Apple reviewers can audit).
- Renders Markdown to HTML automatically.
- Custom domain optional (`legal.lifeclock.app` if you ever buy the domain).
- No cookies, no analytics by default — matching the privacy-first posture.

## When the policy changes

1. Edit the markdown in this `docs/products/life-clock/legal/` folder.
2. Commit and push to the *legal* repo (not just this monorepo).
3. The "Last updated" date at the top of the file updates automatically when you edit it (manually — there's no script).
4. If the change is **material** (collecting new data, sharing with new third parties, etc.), surface an in-app notice. Today's app has no such mechanism; one would need to be added.
