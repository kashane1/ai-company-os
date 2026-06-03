# Automated Gather Protocol (Checkpoint A)

How the agent gathers a business's data automatically — what's fully automated,
what's partial, and the anti-bot/pacing rules. Proven on King Auto Repair
(2026-06). Feeds the `[AGENT]` half of `_scaffold/01-gather-packet.md`.

## Source matrix — what's automatable

| Source | Method | Login? | Status | Yields |
|---|---|---|---|---|
| **Google Place Details** | Places API (`fetch_profile`) + Photos API | no (API key) | ✅ full | facts, hours, payments, 5 reviews, 10 photos |
| **Yelp** | Chrome MCP (real browser) → `get_page_text` | **no** | ✅ full | owner "About", full service list, amenities, **all reviews + owner replies**, highlights, price range, neighborhood |
| **Booking** (Fresha/Booksy/…) | WebFetch or Chrome MCP | no | ✅ good | service list (verify owner-managed!) |
| **Facebook** | Chrome MCP → `get_page_text` | partial | ⚠️ public-only | tagline/Intro, address, phone, email, price range, follower count, **a few public posts** — full feed/photos need the operator's logged-in FB session |
| **Instagram** | Chrome MCP | likely required | ⚠️ untested | expect a login wall; full portfolio needs the operator's session |
| **Photos for the site** | Google API (auto) + human pick from IG/owner | — | hybrid | Google photos auto; best curation stays human |

**Bottom line:** Google + Yelp + booking = fully automatable today and already
richer than a manual pass. FB gives public basics even behind its login wall; FB/
IG *full* content needs the operator to be logged into those sites in the browser
(their choice — the agent never enters credentials).

## Anti-bot / pacing rules (binding)

- **Use the operator's own connected Chrome** (`list_connected_browsers` →
  `select_browser`). Real, logged-in, human profile — not a headless scraper.
- **One business per page load.** Don't fan out rapid requests at one site.
- **Pace every page:** navigate → `wait` 3–4s → **screenshot to check for a
  captcha/bot wall** → only then read. If a captcha appears, **stop** and flag for
  the human; never attempt to solve it.
- **Human-like interaction** for collapsed content: `find` the expander →
  `scroll_to` → `wait` → click → `wait` → re-read. No machine-gun clicking.
- **Read-only.** Never post, react, submit, or enter credentials. Don't try to
  bypass a login wall — read what the public DOM exposes and move on.
- Prefer `get_page_text` (one clean extraction) over many screenshots.

## Yelp recipe (the highest-value source)

1. Get the Yelp URL (often already in `web_verify_url`).
2. Navigate → wait → screenshot (captcha check) → `get_page_text` (captures
   reviews + About + highlights + hours + amenities in one shot).
3. Expand collapsed sections for completeness: **"See N More"** (services),
   **"N More Attributes"** (amenities), **"Read more"** (About) — `find` → click →
   re-read.
4. Capture **owner replies** and **negative reviews** — they're the richest
   guardrail material (e.g. King: a "no-warranty / provide-your-own-parts then
   blame the parts" theme from 1★ reviews → don't claim a warranty).

## Output

Agent writes findings into `01-gather-packet.md` `[AGENT]` blocks — now including
Yelp and FB-public, not just Google. The human still owns: best-photo curation,
IG/FB *full* content (if logged in), and the brand/taste judgment.

## Running it

This is an agent protocol over the Chrome MCP (interactive, not a headless
script — that's the point). It can run as a per-business sub-agent: each gets its
own tab (`tabs_create_mcp`), drives only that tab, and writes its packet. Keep
the pacing rules even when parallelized — they protect the operator's accounts.
