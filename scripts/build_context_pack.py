#!/usr/bin/env python3
"""Build a curated ChatGPT-project context pack from the repo's canonical docs.

The ChatGPT "ai-company-os" project can hold up to 40 source files; raw code goes
stale and can't be run there, so the high-value set is the repo's own "read-first"
orienting docs + a freshly-generated snapshot of what actually exists *now*. This
assembles that curated set (numbered for read order, flattened names so ChatGPT shows
them clearly) plus an auto-written STATE-OF-THE-REPO.md, into a folder you drag-drop
into the project. Re-run anytime to refresh.

    python scripts/build_context_pack.py            # -> ~/Downloads/ai-company-os-context-pack/
    python scripts/build_context_pack.py --out DIR  # custom destination
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# (order-prefix, destination filename, source path relative to repo). Missing sources
# are skipped with a warning — the pack still builds. Numbered so ChatGPT (and you)
# see a logical read order; 00 is the fresh snapshot, generated below.
CURATED: list[tuple[str, str, str]] = [
    # Spine — what the project is + where everything lives.
    ("01", "CLAUDE.md", "CLAUDE.md"),
    ("02", "REPO_MAP.md", "REPO_MAP.md"),
    ("03", "AGENTS.md", "AGENTS.md"),
    ("04", "README.md", "README.md"),
    # Operating model — how the agents + skills work.
    ("10", "agent-model.md", "docs/agent-model.md"),
    ("11", "preflight-for-agents.md", "docs/preflight-for-agents.md"),
    ("12", "operating-model.md", "docs/operating-model.md"),
    ("13", "skills-index.md", "docs/skills-index.md"),
    ("14", "skills-WIRING.md", "skills/WIRING.md"),
    ("15", "large-doc-standard.md", "docs/large-doc-standard.md"),
    ("16", "approval-policy.md", "docs/approval-policy.md"),
    # The live lanes / products.
    ("20", "demo-site-build-playbook.md", "docs/demo-site-build-playbook.md"),
    ("21", "waas-prospecting-lane.md", "docs/waas-prospecting-lane.md"),
    ("22", "appstore-lane.md", "docs/appstore-lane.md"),
    ("23", "ios-lane.md", "docs/ios-lane.md"),
    # Design engine + the BBW product.
    ("30", "bbw-LANDING_PAGE_PLAN.md", "docs/products/better-business-web/LANDING_PAGE_PLAN.md"),
    ("31", "design-engine-v3-plan.md",
     "docs/plans/2026-06-08-feat-design-engine-v3-premium-loop-plan.md"),
    ("32", "concept-led-imagery-playbook.md",
     "docs/products/better-business-web/concept-led-imagery-playbook.md"),
    # Voice / GTM.
    ("40", "bbw-voice.md", "docs/products/better-business-web/gtm/voice.md"),
    ("41", "demo-voice-framework.md",
     "docs/products/better-business-web/gtm/demo-voice-framework.md"),
    ("42", "go-to-market-build-plan-v3.md", "docs/go-to-market-build-plan-v3.md"),
]


def _git(args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return ""


def _demos() -> list[dict]:
    path = REPO / "products" / "better-business-web" / "portfolio" / "curated.json"
    try:
        return json.loads(path.read_text())["demos"]
    except Exception:
        return []


def _state_doc(stamp: str) -> str:
    """A current snapshot — the highest-value file, since ChatGPT can't browse the repo."""
    log = _git(["log", "-25", "--pretty=format:- %ad %s", "--date=short"])
    head = _git(["rev-parse", "--short", "HEAD"])
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    demos = _demos()
    demo_lines = "\n".join(
        f"  {i + 1}. **{d.get('portfolio_name', d['slug'])}** ({d.get('type', '?')}) "
        f"— /work/{d['slug']}/" + ("  · synthetic (hand-authored)" if d.get("synthetic") else "")
        for i, d in enumerate(demos)
    ) or "  (none found)"

    return f"""# STATE OF THE REPO — ai-company-os

> Auto-generated snapshot for the ChatGPT project. Re-run
> `python scripts/build_context_pack.py` to refresh. The repo is the source of truth;
> this file is a point-in-time summary so ChatGPT reasons off current reality, not the
> May-2026 founding docs.

**Generated:** {stamp}
**Git:** branch `{branch}` @ `{head}`

## What this is
`ai-company-os` is a local-first platform for running an AI-driven software business
from an always-on Mac. It is no longer a plan — it is a working codebase with several
operational lanes and a live product. Orientation order: `CLAUDE.md` → `REPO_MAP.md`
(the five-zone model + where files go) → `docs/agent-model.md` → `docs/skills-index.md`.

## Lanes / products that exist now
- **Better Business Web (BBW)** — the agency's own funnel + portfolio, **live at
  https://better-business-web.netlify.app** (Astro site, deployed via
  `scripts/web/deploy_bbw.py`). It hosts a portfolio of demo sites at `/work/<slug>/`.
- **WaaS prospecting / demo lane** — bespoke per-prospect demo sites (gather → brief →
  build → craft pass → operator-gated deploy). See `demo-site-build-playbook.md`.
- **Design engine (v3)** — an autonomous build→capture→judge→revise loop that produces
  premium Astro sites. Builder ≠ judge: Claude/composer builds; a Gemini vision judge
  scores a 12-dimension rubric; an adversarial defect inspector + a **deterministic
  composition gate** (DOM geometry, no model) catch defects. Entrypoint:
  `scripts/agency/design_loop.py` (`run` / `judge` / `composition`). Build-only (no
  judge): `packages/web/premium_build.py`. Portfolio publish: \
  `scripts/agency/build_portfolio_demos.py` (`--only` / `--refresh`).
- **App Store lane** and **iOS lane** — see `appstore-lane.md`, `ios-lane.md`.

## Portfolio demos currently live ({len(demos)})
{demo_lines}

Demos 1–8 are anonymized real-prospect builds; the premium design-engine builds
(med spa, fish tacos) are marked synthetic.

## Design-engine specifics (current)
- Premium Astro scaffold: blocks (CinematicHero, EditorialSplit, BentoGallery,
  FullBleedMedia, StickyProcess, ClosingCta) + GSAP/Lenis motion + role-token theme.
- Palette synthesizer with WCAG-AA gating, **explicit-accent** + **imagery-direction**
  controls for reference-guided art direction.
- Gates: duplicate-section, adversarial defect inspector, and the deterministic
  composition gate (stacked full-bleed / section overlap / text-over-foreign-image /
  horizontal overflow).

## Known constraints / gotchas
- **Imagery API is currently blocked**: Gemini (Nano Banana Pro) returns 429
  "prepayment credits depleted." Both imagery generation and the vision judge need it.
  ChatGPT-in-browser (Instant model, self-contained prompts — not the Thinking model,
  no live-URL references) is a working alternative image source.
- **Founder-gated dirs** (need explicit approval): `packages/policies/`,
  `packages/schemas/`, `skills/canonical/`, `skills/registry.yaml`. `state/` is
  runtime-only (gitignored), never source of truth.
- Skill logic lives in `skills/canonical/` + `skills/adapters/`; `.claude/skills/*`
  are thin pointers (see `skills/WIRING.md`).

## Recent activity (last 25 commits)
{log}
"""


def _index_doc(copied: list[str], missing: list[str], stamp: str) -> str:
    listing = "\n".join(f"- `{n}`" for n in copied)
    miss = ("\n\n**Skipped (not found at build time):**\n" + "\n".join(f"- `{m}`" for m in missing)) if missing else ""
    return f"""# Context pack — ai-company-os ({stamp})

Curated, current source files for the ChatGPT **ai-company-os** project. Drag the whole
folder into the project's Sources (replace the stale May-2026 set). Read order is the
numeric prefix; **start with `00-STATE-OF-THE-REPO.md`**.

Quality over quantity — this is the repo's "read-first" spine + the live lanes/products
+ a fresh state snapshot, not raw code (code changes constantly and can't run in
ChatGPT). Refresh anytime with `python scripts/build_context_pack.py`.

## Files
{listing}{miss}
"""


def build(out_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pack = out_root / "ai-company-os-context-pack"
    if pack.exists():
        shutil.rmtree(pack)
    pack.mkdir(parents=True)

    copied: list[str] = []
    missing: list[str] = []

    state_name = "00-STATE-OF-THE-REPO.md"
    (pack / state_name).write_text(_state_doc(stamp), encoding="utf-8")
    copied.append(state_name)

    for order, dest, rel in CURATED:
        src = REPO / rel
        name = f"{order}-{dest}"
        if src.is_file():
            shutil.copyfile(src, pack / name)
            copied.append(name)
        else:
            missing.append(f"{name}  (from {rel})")

    (pack / "99-PACK-INDEX.md").write_text(_index_doc(copied, missing, stamp), encoding="utf-8")
    copied.append("99-PACK-INDEX.md")

    # Also zip it for easy upload.
    zip_path = out_root / "ai-company-os-context-pack.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(pack.iterdir()):
            zf.write(f, f"ai-company-os-context-pack/{f.name}")

    print(f"✓ context pack → {pack}  ({len(copied)} files)")
    print(f"✓ zip          → {zip_path}")
    if missing:
        print("! skipped (not found):")
        for m in missing:
            print(f"    {m}")
    return pack


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out", default=str(Path.home() / "Downloads"),
        help="destination dir (default: ~/Downloads)",
    )
    args = ap.parse_args()
    out_root = Path(args.out).expanduser()
    out_root.mkdir(parents=True, exist_ok=True)
    build(out_root)


if __name__ == "__main__":
    main()
