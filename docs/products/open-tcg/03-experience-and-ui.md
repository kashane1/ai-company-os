# Experience and UI specification

Original proposed design, 2026-09-20. The reference app was inspected through its visible interface; this document specifies our own organization, wording, and behavior. It contains no vendor screenshots or copied visual assets.

## Design direction

Build a focused Mac utility with a readable item list and an evidence inspector. Keep navigation shallow: **Watchlist**, **Inbox**, **Activity**, and **Settings**. Discovery belongs in an Add flow or a later Explore view. Trading-card art is optional and shown only when appropriately licensed; a text-first interface should remain complete.

Use native window behavior, a resizable sidebar, system typography, generous line height, light/dark modes, and a quiet neutral palette with one action color. Use explicit labels as well as icons. Avoid celebratory urgency, countdown pressure, hidden destructive gestures, and a gamified spending score. Prototype at 1024×700 and test at 200% text size before adding decorative motion.

## Primary screen, proposed wireframe

```text
┌ OpenTCG ───────────────────────────────────────────────────────────────┐
│ Watchlist          │ My watches            [+ Add item]   [Pause all] │
│ Inbox       2      │ Search…      Source ▾    State ▾                  │
│ Activity           ├───────────────────────────┬──────────────────────┤
│                    │ Item / variant           │ Selected item        │
│ Settings           │ Target · last seen 2m    │ Notify only          │
│                    │ $34 item · tax unknown   │ Item target $35      │
│                    │ In stock · matches       │                      │
│                    │                           │ Evidence             │
│                    │ Another wanted item      │ Seller: retailer     │
│                    │ Source unavailable       │ Observed 14:02       │
│                    │ Last check 28m ago       │ Source: permitted API│
│                    │                           │ Shipping: unknown    │
│ Monitoring paused  │                           │ [Open retailer]      │
│ while Mac asleep   │                           │ [Pause this watch]   │
└────────────────────┴───────────────────────────┴──────────────────────┘
```

The example is synthetic. It demonstrates hierarchy, not a claim of live Target access.

## First-run flow

1. Explain what the app does in two sentences. Show “Works locally while this Mac is awake” and the current data-source limitations.
2. Offer “Try a sample” or “Add a watch.” Sample content is clearly labeled and generates no external traffic.
3. Enter a supported product URL, search the permitted catalog, or add manually. Show the proposed exact identity and variant. A general URL is never treated as permission to run code or crawl a whole site.
4. Choose sources, region, desired quantity, and item-price target. Display whether shipping and tax are known. Defaults: quantity one, Notify only.
5. Preview an example alert and request notification permission only when enabling notifications.
6. Show first check state and a link to its evidence. No credential wall or upgrade interstitial.

## Critical flows

| Flow | Successful behavior | Important failure behavior |
|---|---|---|
| Add product link | Match exact variant and seller; preview then save | Unsupported retailer gives a manual-watch option; no implied live coverage |
| Price threshold hit | One inbox item with observation and reason | Stale, missing price, wrong variant, marketplace seller, or unknown stock does not become a confident deal |
| Open retailer | Open verified HTTPS link in the user's browser after click | Unexpected redirect or invalid URL shows a warning state; never opens arbitrary local schemes |
| Pause all | Stop new checks/actions and mark all affected watches | In-flight network reads can complete but cannot trigger a new action; any later purchase mode must explain already-submitted operations |
| Sleep and resume | Timeline records gap; resumes with bounded scheduling | No “watching continuously” claim; overdue checks stagger and deduplicate |
| Source breaks | Show cause, last reliable observation, and next retry | Stale cached values cannot masquerade as current stock |
| Export data | Preview fields and destination; portable file | Secrets, tokens, browser cookies, diagnostic dumps excluded |
| Delete local data | Preview scope and a reversible/export path when possible | Explain separate browser/cloud data if those optional features exist |
| Future assistance | Show immutable cart proposal and specific authority | Changed price, seller, quantity, shipping, or total invalidates approval |
| Future order timeout | Clearly say “Outcome unknown; checking order status” | No automatic resubmission that may duplicate a purchase |

## The evidence inspector

Required sections: **Your rule**, **Latest observation**, **Why you were notified**, **Source health**, and **Recent activity**. Separate facts from estimates and user-entered values. Let the user inspect a compact event payload with personal data removed, but keep debugging jargon out of the normal flow.

Example original copy:

> Available at the selected retailer when checked 2 minutes ago. The item price meets your $35 target. Tax and shipping are not yet known. Stock may change before checkout.

> This source has not returned a successful check for 28 minutes. The last observation is shown for reference. Alerts are paused until fresh data returns.

> Your Mac was asleep from 11:40 to 12:15. Local watches did not run during that time.

## Authority and money controls

Future interaction modes must have distinct labels and icons: Notify → Prepare cart → Confirm purchase → Scheduled authority. Do not use one ambiguous “Start mission” button for all four.

A purchase authority screen must show exact product and variant, allowed retailer/seller, quantity, all-in total ceiling, cumulative budget, valid-until time, whether substitution is allowed (default no), and how to stop. “Remember this choice” cannot silently expand its scope. Notification thresholds never double as checkout approval.

Unknown final fees block automatic submission. A fixed shipping buffer is not a substitute for a verified total. A successful button click is not proof of a completed order.

## Settings structure

- **Sources:** enabled connectors, destinations, intervals, health, supported capabilities, last verification date.
- **Notifications:** permission status, quiet hours, sound, cooldown, test notification using local sample data.
- **Data:** local storage, retention, export/import, delete controls, encryption/recovery explanation.
- **Privacy:** telemetry off by default, inspectable diagnostic preview, no automatic screenshot upload.
- **Updates:** version, supported runtime status, release notes, trusted channel, install timing. Never update mid-purchase.
- **Accessibility:** system appearance, density if needed, reduced motion inherited from OS.

## Visual and usability acceptance

All controls have descriptive accessible names; status changes announce without stealing focus. Table and card modes share the same information. Large product names wrap; no amount, error, or source timestamp is hidden behind a tooltip. Date/time reflects the user's locale and timezone, with absolute time available. Empty, loading, permission-denied, source-blocked, offline, and partial-data states have designed screens.

Measure before claiming superiority: time to create a first watch, ability to identify stale evidence, notification relevance, support confusion, task completion with keyboard/VoiceOver, idle memory/CPU, and wake recovery. Guppy's interface establishes ideas worth studying; it does not provide a benchmark we have already beaten.

## Prototype test script

Give five participants synthetic tasks: add the correct product variant; notice a marketplace seller mismatch; distinguish $35 item price from $42 total; find a sleep gap; pause every watch; export a watchlist; handle a denied source; explain what Notify permits. Observe without coaching. Four of five should complete each essential task. Any misunderstanding about spending authority is a blocking design defect.
