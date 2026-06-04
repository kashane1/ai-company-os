# Genre → palette reference (curated)

Curated from UI UX Pro Max `colors.csv` (MIT — see `ATTRIBUTION.md`), remapped
from SaaS "Product Type" keys onto our local-SMB genres. Each row gives a
**primary / secondary / accent (CTA)** triad plus the text-on-color and a
light background/foreground/border. `On *` columns are the source's
WCAG-checked text colors — lift them, don't recompute.

> **Precedence:** for bespoke prospect demos, derive the palette from the
> business's OWN visual cues first (storefront, signage, logo, photos). Use this
> table only as a fallback or when cues are weak. For paid client Astro sites,
> these are sensible defaults; the owner's real brand colors win when known.
>
> The machine-readable form of this table lives in
> `packages/web/palette.py::GENRE_PALETTES`; keep the two in sync.

| Genre | Primary | On primary | Secondary | Accent (CTA) | On accent | Light BG | FG (text) | Border | Source Product Type / note |
|---|---|---|---|---|---|---|---|---|---|
| auto_repair | `#1E293B` | `#FFFFFF` | `#334155` | `#DC2626` | `#FFFFFF` | `#F8FAFC` | `#0F172A` | `#E2E8F0` | Automotive/Car Dealership |
| garage_door | `#1E40AF` | `#FFFFFF` | `#3B82F6` | `#EA580C` | `#FFFFFF` | `#EFF6FF` | `#1E3A8A` | `#BFDBFE` | Home Services |
| plumber | `#1E40AF` | `#FFFFFF` | `#3B82F6` | `#EA580C` | `#FFFFFF` | `#EFF6FF` | `#1E3A8A` | `#BFDBFE` | Home Services |
| electrician | `#1E40AF` | `#FFFFFF` | `#3B82F6` | `#F59E0B` | `#0F172A` | `#EFF6FF` | `#1E3A8A` | `#BFDBFE` | Home Services (accent → amber for "electric") |
| roofer | `#64748B` | `#FFFFFF` | `#94A3B8` | `#EA580C` | `#FFFFFF` | `#F8FAFC` | `#334155` | `#E2E8F0` | Construction/Architecture |
| landscaper | `#15803D` | `#FFFFFF` | `#22C55E` | `#D97706` | `#FFFFFF` | `#F0FDF4` | `#14532D` | `#BBF7D0` | Florist/Plant Shop (accent → gold; source pink unfit) |
| house_cleaning | `#059669` | `#FFFFFF` | `#10B981` | `#EA580C` | `#FFFFFF` | `#ECFDF5` | `#064E3B` | `#A7F3D0` | Hyperlocal Services |
| barber_shop | `#1E293B` | `#FFFFFF` | `#334155` | `#DC2626` | `#FFFFFF` | `#F8FAFC` | `#0F172A` | `#E2E8F0` | Automotive (barber-pole red on near-black; source Beauty pink unfit) |
| beauty_salon | `#EC4899` | `#FFFFFF` | `#F9A8D4` | `#8B5CF6` | `#FFFFFF` | `#FDF2F8` | `#831843` | `#FBCFE8` | Beauty/Spa/Wellness |
| nail_salon | `#EC4899` | `#FFFFFF` | `#F9A8D4` | `#8B5CF6` | `#FFFFFF` | `#FDF2F8` | `#831843` | `#FBCFE8` | Beauty/Spa/Wellness |
| massage_therapy | `#7C3AED` | `#FFFFFF` | `#8B5CF6` | `#059669` | `#FFFFFF` | `#FAF5FF` | `#0F172A` | `#EFE7FC` | Meditation & Mindfulness |
| dog_groomer | `#0D9488` | `#FFFFFF` | `#14B8A6` | `#EA580C` | `#FFFFFF` | `#F0FDFA` | `#134E4A` | `#99F6E4` | Veterinary Clinic |
| bakery | `#92400E` | `#FFFFFF` | `#B45309` | `#E8557A` | `#FFFFFF` | `#FEF3C7` | `#78350F` | `#FDE68A` | Bakery/Cafe (accent → berry; source accent == primary) |
| coffee_shop | `#92400E` | `#FFFFFF` | `#B45309` | `#C9472F` | `#FFFFFF` | `#FEF3C7` | `#78350F` | `#FDE68A` | Bakery/Cafe (accent → terracotta) |
| restaurant | `#DC2626` | `#FFFFFF` | `#F87171` | `#A16207` | `#FFFFFF` | `#FEF2F2` | `#450A0A` | `#FECACA` | Restaurant/Food Service |
| yoga_studio | `#6B7280` | `#FFFFFF` | `#78716C` | `#0891B2` | `#FFFFFF` | `#F5F5F0` | `#0F172A` | `#EDEEEF` | Yoga & Stretching Guide |
| tutoring | `#0D9488` | `#FFFFFF` | `#2DD4BF` | `#EA580C` | `#FFFFFF` | `#F0FDFA` | `#134E4A` | `#5EEAD4` | Online Course/E-learning |
| music_lessons | `#DC2626` | `#FFFFFF` | `#9A3412` | `#D97706` | `#FFFFFF` | `#FFFBEB` | `#0F172A` | `#FAE4E4` | Music Instrument Learning |
| accountant | `#0F172A` | `#FFFFFF` | `#1E3A8A` | `#A16207` | `#FFFFFF` | `#F8FAFC` | `#020617` | `#E2E8F0` | Banking/Traditional Finance |
| notary | `#1E3A8A` | `#FFFFFF` | `#1E40AF` | `#B45309` | `#FFFFFF` | `#F8FAFC` | `#0F172A` | `#CBD5E1` | Legal Services |

**Usage notes**
- The **60/30/10** rule: primary ≈ 60% (surfaces, headers), secondary ≈ 30%
  (supporting blocks), accent ≈ 10% (CTAs, links, highlights only).
- Keep the accent for the primary CTA; don't paint large areas with it.
- A few accents were overridden where the source category's accent didn't fit
  the trade (electrician, landscaper, barber, bakery, coffee) — noted inline.
- For genres absent here, synthesize with
  `packages/web/palette.py::derive_palette()` (HSL split-complement, WCAG-gated).
