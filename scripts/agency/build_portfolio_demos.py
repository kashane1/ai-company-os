#!/usr/bin/env python3
"""Build portfolio demos for the Better Business Web landing page.

Picks one curated bespoke demo per major business genre, copies the local
dist-v2 build, anonymizes identifying business details, and publishes copies
under the BBW site at /work/<slug>/ with matching thumbnail screenshots.

    python scripts/agency/build_portfolio_demos.py
    python scripts/agency/build_portfolio_demos.py --deploy   # draft-deploy each demo

Source of truth for selections: products/better-business-web/portfolio/curated.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.deploy import NetlifyDeployTarget  # noqa: E402

sys.path.insert(0, str(REPO / "scripts" / "web"))
from make_thumb import make_thumb  # noqa: E402
from PIL import Image  # noqa: E402

CURATED = REPO / "products" / "better-business-web" / "portfolio" / "curated.json"
OUT_ROOT = REPO / "products" / "better-business-web" / "portfolio"
SITE_PUBLIC = REPO / "products" / "better-business-web" / "site" / "public"
SITE_DATA = REPO / "products" / "better-business-web" / "site" / "src" / "data" / "portfolio.json"
SHOOT = REPO / "scripts" / "web" / "shoot.mjs"
SCREENSHOT_DOCS = REPO / "docs" / "products" / "better-business-web" / "screenshots"
RECORDS = REPO / "state" / "prospects" / "records"
SITES = REPO / "state" / "prospects" / "sites"
PREVIEW_SITE_NAME = "bbw-portfolio"
# Mirror the ux-audit performance budget: any single published image must stay under
# this, or the launch checklist's `performance` category drops below its pass bar.
MAX_IMAGE_BYTES = 600_000

CONCEPT_NOTE = (
    "Concept demo — illustrative sample design by Better Business Web. "
    "Business details are fictional; layout and craft reflect real builds."
)


def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def _phone_variants(phone: str) -> list[str]:
    if not phone:
        return []
    d = _digits(phone)
    if len(d) == 11 and d.startswith("1"):
        d10 = d[1:]
    elif len(d) == 10:
        d10 = d
    else:
        d10 = d[-10:] if len(d) >= 10 else d
    variants = {phone.strip(), d, d10}
    if len(d10) == 10:
        variants.add(f"+1{d10}")
        variants.add(f"+1 {d10[:3]}-{d10[3:6]}-{d10[6:]}")
        variants.add(f"({d10[:3]}) {d10[3:6]}-{d10[6:]}")
        variants.add(f"{d10[:3]}-{d10[3:6]}-{d10[6:]}")
        variants.add(f"tel:+1{d10}")
        variants.add(f"tel:+1-{d10[:3]}-{d10[3:6]}-{d10[6:]}")
    return sorted(v for v in variants if v)


def _portfolio_phone_variants(phone: str) -> list[str]:
    d = _digits(phone)
    if len(d) != 10:
        return [phone]
    return [
        phone,
        f"({d[:3]}) {d[3:6]}-{d[6:]}",
        f"{d[:3]}-{d[3:6]}-{d[6:]}",
        f"tel:+1{d}",
    ]


def _name_variants(name: str) -> list[str]:
    out = {name.strip(), html.unescape(name.strip())}
    for v in list(out):
        out.add(v.replace("&", "&amp;"))
        out.add(v.replace("'", "'"))
        out.add(v.replace("'", "'"))
    parts = re.split(r"[\s&]+", html.unescape(name))
    if parts:
        out.add(parts[0])
    if len(parts) >= 2:
        out.add(" ".join(parts[:2]))
    return sorted(v for v in out if len(v) >= 3)


def _address_variants(address: str) -> list[str]:
    if not address:
        return []
    base = address.replace(", USA", "").strip()
    variants = {address, base, base.replace("#", " #")}
    if "," in base:
        variants.add(base.split(",")[0].strip())
    return sorted(v for v in variants if v)


def _city_label(city_id: str) -> str:
    return " ".join(part.capitalize() for part in city_id.replace("_", " ").split())


def _address_parts(address: str) -> dict[str, str]:
    base = address.replace(", USA", "").strip()
    parts = [p.strip() for p in base.split(",")]
    street = parts[0] if parts else base
    city = parts[1] if len(parts) > 1 else ""
    state_zip = parts[2] if len(parts) > 2 else ""
    state = state_zip.split()[0] if state_zip else ""
    postal = state_zip.split()[1] if len(state_zip.split()) > 1 else ""
    street_name = re.sub(r"^\d+\s*", "", street.split("#")[0]).strip()
    street_num = re.match(r"(\d+)", street)
    return {
        "full": base,
        "street": street,
        "street_name": street_name,
        "street_num": street_num.group(1) if street_num else "",
        "city": city,
        "state": state,
        "postal": postal,
    }


def _replacement_pairs(record: dict, demo: dict) -> list[tuple[str, str]]:
    real_name = str(record.get("display_name", ""))
    real = _address_parts(str(record.get("formatted_address", "")))
    real_phone = str(record.get("phone", ""))
    city_id = str(record.get("city_id", ""))
    city_label = _city_label(city_id)

    pf_name = demo["portfolio_name"]
    pf = _address_parts(demo["portfolio_address"])
    pf_phone = demo["portfolio_phone"]
    pf_area = demo.get("portfolio_area", pf["city"] or city_label)
    pf_short = demo.get("portfolio_short") or pf_name.split()[0]
    real_short = real_name.split()[0]
    pf_phone_vars = _portfolio_phone_variants(pf_phone)
    pf_tel = next((v for v in pf_phone_vars if v.startswith("tel:")), f"tel:+1{_digits(pf_phone)}")

    pairs: list[tuple[str, str]] = []
    for old in _name_variants(real_name):
        pairs.append((old, pf_name))
    if real_short and real_short.lower() != pf_short.lower():
        pairs.append((real_short, pf_short))

    for old in _address_variants(real["full"]):
        pairs.append((old, demo["portfolio_address"]))
    if real["street"]:
        pairs.append((real["street"], pf["street"]))
    if real["street_name"] and pf["street_name"]:
        pairs.append((real["street_name"], pf["street_name"]))
        pairs.append((real["street_name"].replace("Street", "St"), pf["street_name"].replace("Way", "St")))
        pairs.append((real["street_name"].replace("St", "Street"), pf["street_name"]))
    if real["street_num"] and pf["street_num"] and real["street_num"] != pf["street_num"]:
        pairs.append((real["street_num"], pf["street_num"]))
    if real["city"]:
        pairs.append((real["city"], pf_area))
    if real["state"] and pf["state"]:
        pairs.append((real["state"], pf["state"]))
    if real["postal"] and pf["postal"]:
        pairs.append((real["postal"], pf["postal"]))

    phone_old = _phone_variants(real_phone)
    for i, old in enumerate(phone_old):
        new = pf_phone_vars[min(i, len(pf_phone_vars) - 1)]
        if old.startswith("tel:"):
            new = pf_tel
        pairs.append((old, new))
    if city_label and city_label != pf_area:
        pairs.append((city_label, pf_area))
        pairs.append((city_id.replace("_", " "), pf_area.lower()))

    for extra in demo.get("extra_replacements", []):
        pairs.append((extra["from"], extra["to"]))

    mockup_url = str(record.get("mockup_url", ""))
    if mockup_url:
        pairs.append((mockup_url, f"/work/{demo['slug']}/"))

    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    # Drop empty/old strings and dedupe by old value.
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for old, new in pairs:
        if not old or old in seen:
            continue
        seen.add(old)
        out.append((old, new))
    return out


def anonymize_html(html_text: str, record: dict, demo: dict) -> str:
    out = html_text
    for old, new in _replacement_pairs(record, demo):
        out = out.replace(old, new)

    pf_query = demo["portfolio_address"].replace(" ", "+")
    out = re.sub(
        r'href="https://www\.google\.com/maps/search/\?[^"]+"',
        f'href="https://www.google.com/maps/search/?api=1&query={pf_query}"',
        out,
    )
    out = re.sub(
        r'src="https://maps\.google\.com/maps\?[^"]+"',
        f'src="https://maps.google.com/maps?q={pf_query}&output=embed"',
        out,
    )
    out = re.sub(
        r'title="Map to [^"]+"',
        f'title="Map to {demo["portfolio_name"]}"',
        out,
    )
    out = re.sub(
        r'content="https?://[^"]+/assets/',
        'content="assets/',
        out,
    )

    note = (
        f'<p class="concept-demo-note" style="margin-top:1rem;font-size:.85rem;opacity:.75">'
        f"{CONCEPT_NOTE}</p>"
    )
    if "concept-demo-note" not in out:
        out = out.replace("</footer>", f"{note}\n</footer>", 1)
    return out


def _rebase_root_relative(html_text: str) -> str:
    """Make root-absolute asset refs relative so a multi-file (Astro) dist works when
    served from a SUBPATH (/work/<slug>/), not just the domain root.

    Premium Astro builds emit absolute asset paths (``/_astro/...``, ``/img/...``);
    at /work/<slug>/ those resolve against the domain root and 404. Rewriting them to
    ``./_astro/...`` works both at a subpath and at the root (so a standalone draft
    deploy still works). Only asset paths are touched — the home link (``href="/"``)
    and external URLs (fonts) are left alone. No-op for self-contained demos.
    """
    out = html_text
    for prefix in ("_astro/", "img/", "assets/", "fonts/"):
        out = out.replace(f'="/{prefix}', f'="./{prefix}')
    return out


def _shrink_oversized_images(root: Path, *, max_bytes: int = MAX_IMAGE_BYTES) -> None:
    """Downscale any published image over the perf budget, FORMAT-PRESERVING so the
    HTML refs don't change. Image-model output (the premium demos' hero/support PNGs)
    ships far larger than its display size; the ux-audit perf gate caps any single
    image at 600KB, so an unshrunk one silently fails the launch checklist.
    """
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    for img_path in root.rglob("*"):
        if not (img_path.is_file() and img_path.suffix.lower() in exts):
            continue
        if img_path.stat().st_size <= max_bytes:
            continue
        try:
            im = Image.open(img_path)
            im.load()
        except Exception as exc:  # never let one bad image abort the build
            print(f"  ! could not shrink {img_path.name}: {exc}", file=sys.stderr)
            continue
        fmt = im.format or img_path.suffix.lstrip(".").upper().replace("JPG", "JPEG")
        for _ in range(8):  # ~0.85 linear/step → converges well under budget in a few
            if img_path.stat().st_size <= max_bytes:
                break
            w, h = im.size
            im = im.resize((max(1, int(w * 0.85)), max(1, int(h * 0.85))), Image.LANCZOS)
            save_kwargs: dict[str, object] = {"optimize": True}
            if fmt in ("JPEG", "WEBP"):
                save_kwargs["quality"] = 82
            im.save(img_path, format=fmt, **save_kwargs)
        print(f"    ↓ shrank {img_path.name} → {img_path.stat().st_size // 1024}KB ({im.size[0]}px)")


def source_dist(place_id: str) -> Path | None:
    site_dir = SITES / place_id
    for sub in ("dist-v2", "dist"):
        candidate = site_dir / sub
        if (candidate / "index.html").is_file():
            return candidate
    return None


def latest_screenshot(place_id: str) -> Path | None:
    shots = SITES / place_id / "screenshots"
    if not shots.is_dir():
        return None
    latest = shots / "*-latest.png"
    matches = sorted(shots.glob("*-latest.png"))
    return matches[0] if matches else None


def copy_demo_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def screenshot_dist(dist: Path, slug: str) -> Path:
    """Full-page screenshot of an authored dist via shoot.mjs.

    Saved into the BBW docs screenshots gallery (per house convention) and
    returned so the caller can derive a WebP thumbnail from it.
    """
    SCREENSHOT_DOCS.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["node", str(SHOOT), str(dist), str(SCREENSHOT_DOCS), f"/:{slug}"],
        check=True, cwd=REPO,
    )
    return SCREENSHOT_DOCS / f"{slug}.png"


def _publish_demo(
    demo: dict,
    portfolio_dist: Path,
    *,
    source_business: str,
    place_id: str,
    deploy: bool,
    target: NetlifyDeployTarget | None,
    site,
) -> dict:
    """Publish a (committed) portfolio dist into the BBW site: copy → rebase subpath
    asset paths → shrink oversized images to the perf budget → screenshot a thumbnail.
    """
    genre = demo["genre_id"]
    slug = demo["slug"]
    public_work = SITE_PUBLIC / "work" / slug
    public_thumb = SITE_PUBLIC / "portfolio" / f"{slug}.webp"

    public_work.parent.mkdir(parents=True, exist_ok=True)
    copy_demo_tree(portfolio_dist, public_work)
    # Served at /work/<slug>/ — rebase root-absolute asset paths so a multi-file
    # (Astro) build resolves at the subpath instead of 404ing.
    work_index = public_work / "index.html"
    if work_index.is_file():
        work_index.write_text(
            _rebase_root_relative(work_index.read_text(encoding="utf-8")), encoding="utf-8"
        )
    # Keep every published image under the ux-audit perf budget.
    _shrink_oversized_images(public_work)

    public_thumb.parent.mkdir(parents=True, exist_ok=True)
    # Thumbnail from the published dist (already anonymized for prospect demos) — never
    # a pre-anonymization prospect screenshot, which would leak real business details.
    make_thumb(screenshot_dist(portfolio_dist, slug), public_thumb)

    entry = {
        "genre_id": genre,
        "slug": slug,
        "name": demo["portfolio_name"],
        "type": demo["type"],
        "genre": slug,
        "place_id": place_id,
        "source_business": source_business,
        "dist": str(portfolio_dist),
        "url": f"/work/{slug}/",
        "thumbnail": f"/portfolio/{slug}.webp" if public_thumb.exists() else "",
    }
    if deploy and target and site:
        result = target.deploy(site, portfolio_dist, production=False)
        entry["deploy_url"] = result.url
        print(f"  ✓ {demo['portfolio_name']:28s} ({genre})  →  {result.url}")
    else:
        print(f"  ✓ {demo['portfolio_name']:28s} ({genre})  →  {public_work.relative_to(REPO)}")
    return entry


def build_synthetic(demo: dict, *, deploy: bool, target: NetlifyDeployTarget | None, site) -> dict:
    """Publish a hand-authored demo (no real source business / place_id). The dist
    already lives at portfolio/<genre>/dist — no source pull or anonymization."""
    genre = demo["genre_id"]
    portfolio_dist = OUT_ROOT / genre / "dist"
    if not (portfolio_dist / "index.html").is_file():
        raise FileNotFoundError(f"synthetic demo has no authored dist: {portfolio_dist}")
    return _publish_demo(
        demo, portfolio_dist, source_business=demo["portfolio_name"], place_id="",
        deploy=deploy, target=target, site=site,
    )


def build_one(
    demo: dict, *, deploy: bool, target: NetlifyDeployTarget | None, site, refresh: bool
) -> dict:
    if demo.get("synthetic"):
        return build_synthetic(demo, deploy=deploy, target=target, site=site)

    genre = demo["genre_id"]
    place_id = demo["place_id"]
    portfolio_dist = OUT_ROOT / genre / "dist"
    record_path = RECORDS / f"{place_id}.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}

    # The committed portfolio_dist is the source of truth. Only RE-PULL from the
    # volatile prospect build (state/prospects/sites/<id>/dist-v2 — gitignored, and
    # rewritten whenever that prospect is re-rendered for outreach) when explicitly
    # asked (--refresh) or when no committed dist exists yet. This stops a routine run
    # from silently overwriting a curated demo with a drifted prospect rebuild.
    need_pull = refresh or not (portfolio_dist / "index.html").is_file()
    if need_pull:
        src = source_dist(place_id)
        if src is None:
            if not (portfolio_dist / "index.html").is_file():
                raise FileNotFoundError(
                    f"no source dist for {place_id} and no committed portfolio dist at {portfolio_dist}"
                )
            print(f"  ! no source dist for {place_id}; reusing committed {portfolio_dist.relative_to(REPO)}")
        else:
            if not record:
                raise FileNotFoundError(f"missing record: {record_path}")
            copy_demo_tree(src, portfolio_dist)
            html_path = portfolio_dist / "index.html"
            html_path.write_text(
                anonymize_html(html_path.read_text(encoding="utf-8"), record, demo), encoding="utf-8"
            )

    source_business = record.get("display_name", "") if record else demo["portfolio_name"]
    return _publish_demo(
        demo, portfolio_dist, source_business=source_business, place_id=place_id,
        deploy=deploy, target=target, site=site,
    )


def write_site_data(manifest: list[dict]) -> None:
    payload = {
        "demos": [
            {
                "name": e["name"],
                "type": e["type"],
                "genre": e["genre"],
                "slug": e["slug"],
                "url": e["url"],
                "thumbnail": e["thumbnail"],
            }
            for e in manifest
        ]
    }
    SITE_DATA.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deploy", action="store_true", help="draft-deploy each built demo to bbw-portfolio")
    ap.add_argument(
        "--only",
        default="",
        help="comma-separated slugs to (re)build; every other demo is left exactly as "
        "committed and its existing manifest entry is carried forward",
    )
    ap.add_argument(
        "--refresh",
        action="store_true",
        help="re-pull non-synthetic demos from their prospect dist-v2 source. Default: "
        "reuse the committed portfolio dist, so a routine run never drifts a curated demo "
        "even if its prospect source was rebuilt for outreach.",
    )
    args = ap.parse_args()

    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    demos = curated["demos"]
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    manifest_path = OUT_ROOT / "manifest.json"
    existing: dict[str, dict] = {}
    if manifest_path.is_file():
        existing = {e["slug"]: e for e in json.loads(manifest_path.read_text(encoding="utf-8"))}

    target = NetlifyDeployTarget() if args.deploy else None
    site = target.ensure_site(PREVIEW_SITE_NAME) if target else None

    manifest = []
    for demo in demos:
        slug = demo["slug"]
        if only and slug not in only:
            if slug in existing:
                manifest.append(existing[slug])  # untouched — carry the entry forward
                print(f"  · {demo['portfolio_name']:28s} ({demo['genre_id']})  →  unchanged (not in --only)")
            else:
                print(f"  ! {slug}: not in --only and no existing manifest entry — skipped")
            continue
        manifest.append(
            build_one(demo, deploy=args.deploy, target=target, site=site, refresh=args.refresh)
        )

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_site_data(manifest)

    print(f"\n{len(manifest)} portfolio demo(s).")
    print(f"  manifest: {OUT_ROOT / 'manifest.json'}")
    print(f"  site data: {SITE_DATA.relative_to(REPO)}")
    print(f"  public work: {SITE_PUBLIC / 'work'}")


if __name__ == "__main__":
    main()
