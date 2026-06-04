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

CURATED = REPO / "products" / "better-business-web" / "portfolio" / "curated.json"
OUT_ROOT = REPO / "products" / "better-business-web" / "portfolio"
SITE_PUBLIC = REPO / "products" / "better-business-web" / "site" / "public"
SITE_DATA = REPO / "products" / "better-business-web" / "site" / "src" / "data" / "portfolio.json"
SHOOT = REPO / "scripts" / "web" / "shoot.mjs"
SCREENSHOT_DOCS = REPO / "docs" / "products" / "better-business-web" / "screenshots"
RECORDS = REPO / "state" / "prospects" / "records"
SITES = REPO / "state" / "prospects" / "sites"
PREVIEW_SITE_NAME = "bbw-portfolio"

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


def build_synthetic(demo: dict, *, deploy: bool, target: NetlifyDeployTarget | None, site) -> dict:
    """Publish a hand-authored demo (no real source business / place_id).

    The dist already lives at portfolio/<genre>/dist — no anonymization needed.
    Thumbnail comes from a fresh full-page screenshot of that dist.
    """
    genre = demo["genre_id"]
    slug = demo["slug"]
    portfolio_dist = OUT_ROOT / genre / "dist"
    if not (portfolio_dist / "index.html").is_file():
        raise FileNotFoundError(f"synthetic demo has no authored dist: {portfolio_dist}")

    public_work = SITE_PUBLIC / "work" / slug
    public_thumb = SITE_PUBLIC / "portfolio" / f"{slug}.webp"
    public_work.parent.mkdir(parents=True, exist_ok=True)
    copy_demo_tree(portfolio_dist, public_work)

    public_thumb.parent.mkdir(parents=True, exist_ok=True)
    make_thumb(screenshot_dist(portfolio_dist, slug), public_thumb)

    entry = {
        "genre_id": genre,
        "slug": slug,
        "name": demo["portfolio_name"],
        "type": demo["type"],
        "genre": slug,
        "place_id": "",
        "source_business": demo["portfolio_name"],
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


def build_one(demo: dict, *, deploy: bool, target: NetlifyDeployTarget | None, site) -> dict:
    if demo.get("synthetic"):
        return build_synthetic(demo, deploy=deploy, target=target, site=site)
    place_id = demo["place_id"]
    record_path = RECORDS / f"{place_id}.json"
    if not record_path.is_file():
        raise FileNotFoundError(f"missing record: {record_path}")
    record = json.loads(record_path.read_text(encoding="utf-8"))

    src = source_dist(place_id)
    if src is None:
        raise FileNotFoundError(f"no dist build for {place_id}")

    genre = demo["genre_id"]
    slug = demo["slug"]
    portfolio_dist = OUT_ROOT / genre / "dist"
    public_work = SITE_PUBLIC / "work" / slug
    public_thumb = SITE_PUBLIC / "portfolio" / f"{slug}.webp"

    copy_demo_tree(src, portfolio_dist)
    html_path = portfolio_dist / "index.html"
    html_path.write_text(anonymize_html(html_path.read_text(encoding="utf-8"), record, demo), encoding="utf-8")

    public_work.parent.mkdir(parents=True, exist_ok=True)
    copy_demo_tree(portfolio_dist, public_work)

    public_thumb.parent.mkdir(parents=True, exist_ok=True)
    # Thumbnail from the ANONYMIZED portfolio_dist, not the pre-anonymization
    # prospect screenshot — otherwise the public card would leak the real
    # business name, phone, and city. Crop top + downscale + WebP keeps it
    # ~100 KB crisp vs a multi-MB full-page PNG the browser downscales ~8x.
    make_thumb(screenshot_dist(portfolio_dist, slug), public_thumb)

    entry = {
        "genre_id": genre,
        "slug": slug,
        "name": demo["portfolio_name"],
        "type": demo["type"],
        "genre": slug,
        "place_id": place_id,
        "source_business": record.get("display_name", ""),
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
    ap.add_argument("--deploy", action="store_true", help="draft-deploy each demo to bbw-portfolio")
    args = ap.parse_args()

    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    demos = curated["demos"]

    target = NetlifyDeployTarget() if args.deploy else None
    site = target.ensure_site(PREVIEW_SITE_NAME) if target else None

    manifest = []
    for demo in demos:
        manifest.append(build_one(demo, deploy=args.deploy, target=target, site=site))

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_site_data(manifest)

    print(f"\n{len(manifest)} portfolio demo(s).")
    print(f"  manifest: {OUT_ROOT / 'manifest.json'}")
    print(f"  site data: {SITE_DATA.relative_to(REPO)}")
    print(f"  public work: {SITE_PUBLIC / 'work'}")


if __name__ == "__main__":
    main()
