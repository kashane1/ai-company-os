"""Mood-board generator — palette + type + 6–9 on-brief images on one page.

A mood board is two artifacts at once: the **internal build brief** that drives a
site, and a **client-facing sales artifact** you can send to a prospect to sell the
vision *before* building the full site. It's assembled from a genre kit
(``packages.web.art_direction``) — which can stand alone (sell the vision from the
recipe + exemplars) or be layered over a real build's imagery (richer, on-brief).

This module is the pure, testable core: a ``MoodBoard`` value + a self-contained HTML
renderer + the priority-layered image picker. The CLI
(``scripts/agency/moodboard.py``) does the disk/preview/deploy plumbing.

Reuse, not reinvention:
  - palette + WCAG badges  -> ``packages.web.palette`` (contrast_ratio/passes_aa/best_text_on)
  - the ``{{TOKEN}}`` guard -> ``packages.web.scaffold.unfilled_tokens``
  - kit recipe + palette    -> ``packages.web.art_direction``
  - exemplar provenance     -> ``packages.web.imagery`` (ImageryManifest)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.web.imagery import ImageAsset, ImageryManifest
from packages.web.palette import Palette, contrast_ratio, passes_aa
from packages.web.scaffold import unfilled_tokens


# --------------------------------------------------------------------------- #
# Typography vibes — hand-mirror of design_reference/font_pairings.md.
# Keep in sync (same pattern as palette.GENRE_PALETTES mirroring palettes.md).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FontVibe:
    vibe: str
    display: str
    display_weights: tuple[int, ...]
    body: str
    body_weights: tuple[int, ...]


_SERIF = {"Playfair Display", "Cormorant Garamond", "Fraunces", "Lora", "Spectral", "Newsreader"}

FONT_VIBES: dict[str, FontVibe] = {
    "industrial": FontVibe("industrial", "Oswald", (500, 600, 700), "Inter", (400, 500, 600)),
    "trades": FontVibe("trades", "Archivo", (600, 700, 800), "Inter", (400, 500, 600)),
    "vintage": FontVibe("vintage", "Oswald", (600, 700), "Inter", (400, 500)),
    "elegant": FontVibe("elegant", "Playfair Display", (500, 600, 700), "Inter", (400, 500)),
    "elegant-alt": FontVibe(
        "elegant-alt", "Cormorant Garamond", (500, 600, 700), "Mulish", (400, 500, 600)
    ),
    "warm": FontVibe("warm", "Fraunces", (400, 500, 600, 700), "Nunito", (400, 600, 700)),
    "warm-alt": FontVibe("warm-alt", "Lora", (500, 600, 700), "Inter", (400, 500)),
    "playful": FontVibe("playful", "Fredoka", (500, 600, 700), "Nunito", (400, 600)),
    "calm": FontVibe("calm", "Spectral", (400, 500, 600), "Inter", (400, 500)),
    "friendly": FontVibe("friendly", "Poppins", (500, 600, 700), "Inter", (400, 500)),
    "friendly-alt": FontVibe("friendly-alt", "Manrope", (600, 700, 800), "Inter", (400, 500)),
    "professional": FontVibe("professional", "Sora", (600, 700), "Inter", (400, 500)),
    "professional-alt": FontVibe("professional-alt", "Spectral", (500, 600), "Inter", (400, 500)),
}
DEFAULT_VIBE = "friendly-alt"  # general SMB, modern


def fonts_for_vibe(vibe: str) -> FontVibe:
    """The font pairing for ``vibe`` (a font_pairings.md vibe), or a sane default."""

    return FONT_VIBES.get((vibe or "").strip().lower(), FONT_VIBES[DEFAULT_VIBE])


def _font_kind(family: str) -> str:
    return "serif" if family in _SERIF else "sans-serif"


def _google_fonts_url(font: FontVibe) -> str:
    def fam(name: str, weights: tuple[int, ...]) -> str:
        return f"family={name.replace(' ', '+')}:wght@{';'.join(str(w) for w in weights)}"

    return (
        "https://fonts.googleapis.com/css2?"
        + fam(font.display, font.display_weights)
        + "&"
        + fam(font.body, font.body_weights)
        + "&display=swap"
    )


# --------------------------------------------------------------------------- #
# Image selection — priority-layered merge by id
# --------------------------------------------------------------------------- #
def collect_images(
    *manifests: ImageryManifest, want: int = 9, selected_only: bool = True
) -> list[ImageAsset]:
    """Merge assets across manifests, **business-first**, deduped by id, capped at ``want``.

    Pass the real build's manifest first and the kit's exemplar manifest second: real
    on-brief shots take priority, kit exemplars fill the grid toward ``want``. Dedupe is
    by ``id`` so a business ``hero`` shadows the kit's ``hero``.
    """

    seen: set[str] = set()
    out: list[ImageAsset] = []
    for manifest in manifests:
        for asset in manifest.assets:
            if selected_only and not asset.selected:
                continue
            if asset.id in seen:
                continue
            seen.add(asset.id)
            out.append(asset)
            if len(out) >= want:
                return out
    return out


# --------------------------------------------------------------------------- #
# Board model + renderer
# --------------------------------------------------------------------------- #
@dataclass
class MoodBoard:
    """Everything the one-page board renders. ``images`` are web paths (e.g.
    ``assets/hero.webp``); the CLI stages the files and fills these in."""

    business_name: str
    kit_name: str
    concept_statement: str
    palette: Palette
    font: FontVibe
    images: list[str] = field(default_factory=list)
    direction_notes: list[str] = field(default_factory=list)


def _swatch(label: str, color: str, on_color: str) -> str:
    ratio = contrast_ratio(on_color, color)
    aa = "AA" if passes_aa(on_color, color) else "·"
    return (
        f'<div class="sw" style="background:{color};color:{on_color}">'
        f'<span class="sw-role">{label}</span>'
        f'<span class="sw-hex">{color.upper()}</span>'
        f'<span class="sw-aa">{aa} {ratio:.1f}:1</span>'
        f"</div>"
    )


def _image_cell(src: str, i: int) -> str:
    cls = "img hero" if i == 0 else "img"
    return f'<figure class="{cls}"><img src="{src}" alt="" loading="lazy"></figure>'


def render_moodboard_html(board: MoodBoard) -> str:
    """Render a self-contained, single-file HTML mood board (inlined CSS).

    Guarded by ``unfilled_tokens`` so no ``{{TOKEN}}`` ever ships to a client.
    """

    p = board.palette
    f = board.font
    vars_css = (
        ":root{"
        f"--brand:{p.primary};--on-brand:{p.on_primary};--secondary:{p.secondary};"
        f"--accent:{p.accent};--on-accent:{p.on_accent};--bg:{p.bg};--fg:{p.fg};--border:{p.border};"
        f"--display:'{f.display}',{_font_kind(f.display)};--body:'{f.body}',{_font_kind(f.body)};"
        "}"
    )
    static_css = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font-family:var(--body);line-height:1.55;
  -webkit-font-smoothing:antialiased;padding:clamp(1.5rem,5vw,4rem)}
.wrap{max-width:1100px;margin:0 auto}
.kicker{font-size:.72rem;letter-spacing:.22em;text-transform:uppercase;color:var(--brand);font-weight:600}
h1{font-family:var(--display);font-weight:600;font-size:clamp(2rem,6vw,3.6rem);line-height:1.05;
  letter-spacing:-.01em;margin:.5rem 0 .4rem;color:var(--brand)}
.biz{font-size:1.05rem;color:var(--fg);opacity:.7}
section{margin-top:clamp(2rem,5vw,3.5rem)}
.label{font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;opacity:.55;font-weight:600;
  border-bottom:1px solid var(--border);padding-bottom:.5rem;margin-bottom:1rem}
.swatches{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.75rem}
.sw{border-radius:14px;padding:1rem;min-height:104px;display:flex;flex-direction:column;
  justify-content:space-between;border:1px solid rgba(0,0,0,.06);
  box-shadow:0 1px 2px rgba(0,0,0,.04)}
.sw-role{font-size:.7rem;letter-spacing:.16em;text-transform:uppercase;opacity:.85;font-weight:600}
.sw-hex{font-size:1.05rem;font-weight:600;font-variant-numeric:tabular-nums}
.sw-aa{font-size:.7rem;opacity:.8;font-variant-numeric:tabular-nums}
.type{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;align-items:start}
@media(max-width:640px){.type{grid-template-columns:1fr}}
.specimen{border:1px solid var(--border);border-radius:14px;padding:1.5rem;background:#fff}
.specimen .big{font-family:var(--display);font-size:3.2rem;line-height:1;color:var(--brand)}
.specimen .fam{font-size:.8rem;letter-spacing:.04em;opacity:.6;margin-top:.5rem}
.specimen .body-spec{font-family:var(--body);margin-top:.75rem;opacity:.85}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.75rem}
.img{margin:0;border-radius:14px;overflow:hidden;aspect-ratio:1/1;background:var(--secondary)}
.img.hero{grid-column:span 2;aspect-ratio:16/10}
@media(max-width:640px){.img.hero{grid-column:span 1;aspect-ratio:4/3}}
.img img{width:100%;height:100%;object-fit:cover;display:block}
.notes{list-style:none;display:grid;gap:.6rem}
.notes li{padding-left:1.1rem;position:relative;opacity:.85}
.notes li::before{content:"";position:absolute;left:0;top:.62em;width:.45rem;height:.45rem;
  border-radius:50%;background:var(--accent)}
.foot{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--border);
  font-size:.75rem;opacity:.5}
"""
    swatches = "".join(
        [
            _swatch("Primary", p.primary, p.on_primary),
            _swatch("Secondary", p.secondary, p.on_primary),
            _swatch("Accent", p.accent, p.on_accent),
            _swatch("Surface", p.bg, p.fg),
        ]
    )
    images_html = (
        "".join(_image_cell(src, i) for i, src in enumerate(board.images))
        if board.images
        else '<p style="opacity:.55">Recipe-only kit — imagery is harvested from real builds.</p>'
    )
    notes_html = "".join(f"<li>{n}</li>" for n in board.direction_notes)
    body = f"""
<div class="wrap">
  <header>
    <div class="kicker">{board.kit_name} · brand direction</div>
    <h1>{board.concept_statement}</h1>
    <div class="biz">{board.business_name}</div>
  </header>
  <section>
    <div class="label">Palette</div>
    <div class="swatches">{swatches}</div>
  </section>
  <section>
    <div class="label">Type</div>
    <div class="type">
      <div class="specimen">
        <div class="big">Aa</div>
        <div class="fam">{f.display} — display</div>
        <div class="body-spec">{board.concept_statement}</div>
      </div>
      <div class="specimen">
        <div class="big" style="font-family:var(--body);font-weight:400">Aa</div>
        <div class="fam">{f.body} — body</div>
        <div class="body-spec">Real, specific copy in calm, plain language.
          Numbers stay tabular: open 7 days · (555) 012-3456.</div>
      </div>
    </div>
  </section>
  <section>
    <div class="label">Imagery</div>
    <div class="grid">{images_html}</div>
  </section>
  <section>
    <div class="label">Direction</div>
    <ul class="notes">{notes_html}</ul>
  </section>
  <div class="foot">Brand mood board · generated from the {board.kit_name} art-direction kit.</div>
</div>
"""
    html = (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{board.business_name} — brand mood board</title>"
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<link rel="stylesheet" href="{_google_fonts_url(f)}">'
        f"<style>{vars_css}{static_css}</style></head><body>{body}</body></html>\n"
    )
    leaked = unfilled_tokens(html)
    if leaked:
        raise ValueError(f"mood board has unfilled tokens: {leaked}")
    return html


def moodboard_from_kit(
    kit,
    *,
    business_name: str,
    images: list[str],
    concept_statement: str = "",
    extra_notes: tuple[str, ...] = (),
) -> MoodBoard:
    """Assemble a ``MoodBoard`` from a ``GenreKit`` (+ staged image web paths).

    Imported lazily-friendly: takes the kit by duck type to avoid a hard import cycle
    with ``art_direction`` (which does not import this module).
    """

    from packages.web.art_direction import kit_palette

    recipe = kit.recipe
    notes = list(recipe.composition_rules)
    if recipe.imagery_direction:
        notes.append(recipe.imagery_direction)
    notes.extend(extra_notes)
    return MoodBoard(
        business_name=business_name,
        kit_name=recipe.display_name,
        concept_statement=concept_statement or recipe.concept_statement,
        palette=kit_palette(kit),
        font=fonts_for_vibe(recipe.type_vibe),
        images=list(images),
        direction_notes=notes,
    )
