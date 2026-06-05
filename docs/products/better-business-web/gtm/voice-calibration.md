# Better Business Web — Voice Calibration

Evidence that `voice.md` produces on-voice bbw copy. Three real sections from the
live marketing site (`products/better-business-web/site/src/components/LandingBody.astro`),
each shown three ways: the **generic-AI draft** a model produces with no voice
guide (the failure mode), the **on-voice** version, and **why** — tied to the
voice pillars and banned list.

Verdict: the live copy already scores well against the voice (it leads with the
preview, stays first-person and plain). These rewrites tighten it a notch and,
more importantly, show the voice discriminating slop from on-voice — the same
discrimination `copy-review` automates.

**Founder sign-off (on-voice?):** ☐ Kashane — _________

---

## 1. Hero

**Generic-AI draft (what to avoid):**
> Unlock your business's full potential with a cutting-edge, bespoke website that
> elevates your brand and drives conversions across every device.

Banned/slop hits: *unlock, cutting-edge, bespoke, elevate, drives conversions*; zero
specifics; no risk-reduction.

**On-voice (live copy — kept):**
> A better website for your business — previewed before you pay.
> I build clean, modern websites for small businesses. You'll get a real preview
> link first — see exactly how your new site looks before paying a cent.

Why: leads with the preview (risk-reducing pillar), first person, plain, concrete
("a cent", "preview link"); em-dashes within budget.

---

## 2. Problem

**Generic-AI draft (what to avoid):**
> In today's competitive landscape, a robust online presence is essential. Don't
> get left behind — transform how customers discover your business.

Banned/slop hits: *"In today's competitive landscape", robust, transform*; "don't get
left behind" is fear-hype; says nothing specific.

**On-voice (live copy — kept):**
> Customers look you up before they call. No website, an outdated one, or only a
> social page — and they quietly move on to the next business.

Why: concrete behavior (they look you up, they move on), constructive not
catastrophizing (never "your business is failing"), plain.

---

## 3. Package A card

**Generic-AI draft (what to avoid):**
> Empower your brand with our comprehensive, end-to-end presence solution —
> everything you need to leverage a seamless digital experience.

Banned/slop hits: *empower, comprehensive/end-to-end, leverage, seamless*; tech-as-product
framing; no outcome; "our" from a studio of one.

**On-voice (live copy — lightly tightened):**
> Look professional online. I handle the website and the annoying tech so you
> don't have to.

Why: outcome first ("look professional"), first person, names the real pain ("the
annoying tech"), no jargon. The live card reads *"Website + the annoying tech
handled."* — this tightening makes it a full sentence in the founder's voice.
Note: package copy is **catalog-synced** — apply this in
`packages/agency/catalog.yaml`, not `packages.json` (plan D5).
