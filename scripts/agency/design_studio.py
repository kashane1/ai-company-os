#!/usr/bin/env python3
"""Design Studio orchestration — make the premium-design contract usable.

`packages/web/design_studio.py` is the pure contract (packets + visual review).
This script is the operator-facing plumbing that runs the **premium track** for a
single chosen build: it persists an art-direction packet, captures desktop/mobile
screenshots, ingests rubric scores, and writes a visual-review report — all under
that build's own hub.

The premium track is opt-in. A build joins it only when a packet is written here;
cold-outreach demos that never call this script are completely unaffected.

USAGE
-----
  python scripts/agency/design_studio.py packet  --target <dir> --spec <spec.json|->
  python scripts/agency/design_studio.py shoot   --target <dir> --dist <distDir>
  python scripts/agency/design_studio.py review  --target <dir> --scores <scores.json|->
  python scripts/agency/design_studio.py status  --target <dir>

`<dir>` is the build hub — e.g. `state/prospects/sites/<place_id>/` (path B) or
`products/<slug>-site/` (path C). Artifacts land in `<dir>/design-studio/`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.design_studio import (  # noqa: E402
    DesignReference,
    DesignStudioPacket,
    ReferenceTranslation,
    VisualReviewReport,
    VisualScore,
    WebsiteDesignRequest,
    build_design_studio_packet,
    review_visual_quality,
)

SHOOT = REPO / "scripts" / "web" / "shoot.mjs"

# Width presets for the two required screenshot viewports.
VIEWPORTS = {"desktop": 1440, "mobile": 390}


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
def studio_dir(target: str | Path) -> Path:
    """The premium-track artifact directory inside a build hub."""

    return Path(target) / "design-studio"


def _screenshots_dir(target: str | Path) -> Path:
    return studio_dir(target) / "screenshots"


# --------------------------------------------------------------------------- #
# Packet
# --------------------------------------------------------------------------- #
def request_from_spec(spec: dict) -> WebsiteDesignRequest:
    """Build a `WebsiteDesignRequest` from a plain spec dict."""

    references = [
        DesignReference(
            title=str(ref["title"]),
            url=str(ref.get("url", "")),
            source_type=str(ref.get("source_type", "reference")),
            takeaways=list(ref.get("takeaways", [])),
        )
        for ref in spec.get("references", [])
    ]
    return WebsiteDesignRequest(
        site_name=str(spec["site_name"]),
        business_category=str(spec["business_category"]),
        audience=str(spec["audience"]),
        goal=str(spec["goal"]),
        evidence=list(spec.get("evidence", [])),
        visual_assets=list(spec.get("visual_assets", [])),
        references=references,
        imagery_mode=str(spec.get("imagery_mode", "evidence-led")),
        concept_statement=str(spec.get("concept_statement", "")),
        concept_palette=str(spec.get("concept_palette", "")),
        concept_type=str(spec.get("concept_type", "")),
    )


def write_packet(target: str | Path, request: WebsiteDesignRequest) -> Path:
    """Persist the packet as JSON + a human-readable brief; return the JSON path."""

    packet = build_design_studio_packet(request)
    out = studio_dir(target)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "packet.json"
    json_path.write_text(json.dumps(packet.to_dict(), indent=2) + "\n")
    (out / "packet.md").write_text(render_packet_md(packet))
    return json_path


def load_packet(target: str | Path) -> DesignStudioPacket:
    """Reconstruct the persisted packet from its JSON artifact."""

    payload = json.loads((studio_dir(target) / "packet.json").read_text())
    references = [DesignReference(**ref) for ref in payload.get("references", [])]
    translations = [
        ReferenceTranslation(**item)
        for item in payload.get("reference_translations", [])
    ]
    return DesignStudioPacket(
        site_name=payload["site_name"],
        business_category=payload["business_category"],
        audience=payload["audience"],
        goal=payload["goal"],
        concept_statement=payload["concept_statement"],
        archetype=payload["archetype"],
        palette_strategy=payload["palette_strategy"],
        type_direction=payload["type_direction"],
        imagery_plan=list(payload["imagery_plan"]),
        motion_plan=list(payload["motion_plan"]),
        reference_translations=translations,
        copy_constraints=list(payload["copy_constraints"]),
        required_build_phases=list(payload["required_build_phases"]),
        required_screenshots=list(payload["required_screenshots"]),
        references=references,
        visual_qa=payload["visual_qa"],
    )


def render_packet_md(packet: DesignStudioPacket) -> str:
    """A readable art-direction brief for the human/agent doing the build."""

    lines = [
        f"# Design Studio packet — {packet.site_name}",
        "",
        f"**Concept:** {packet.concept_statement}",
        f"**Archetype:** {packet.archetype}",
        f"**Audience:** {packet.audience}",
        f"**Goal:** {packet.goal}",
        "",
        "## Direction",
        f"- **Palette:** {packet.palette_strategy}",
        f"- **Type:** {packet.type_direction}",
        "",
        "## Imagery plan",
        *[f"- {item}" for item in packet.imagery_plan],
        "",
        "## Motion plan",
        *[f"- {item}" for item in packet.motion_plan],
        "",
        "## Reference translations (translate, never copy)",
    ]
    for item in packet.reference_translations:
        lines.append(f"- **{item.reference_title}** — _{item.observed_pattern}_")
        lines.append(f"  → {item.application}")
    lines += [
        "",
        "## Copy constraints",
        *[f"- {item}" for item in packet.copy_constraints],
        "",
        "## Visual QA bar (must pass after screenshots)",
        f"- overall ≥ {packet.visual_qa['minimum_overall']}/100",
        f"- every category ≥ {packet.visual_qa['category_floor']}/5",
        f"- critical categories: {', '.join(packet.visual_qa['critical_categories'])}",
        f"- required screenshots: {', '.join(packet.required_screenshots)}",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Screenshots
# --------------------------------------------------------------------------- #
def shoot_commands(dist: str | Path, target: str | Path, *, frames: int = 0) -> list[dict]:
    """The desktop + mobile capture commands for `scripts/web/shoot.mjs`.

    Returned as structured dicts so callers (and tests) can inspect them before
    anything shells out to a browser. ``frames`` > 0 adds a motion-capture pass to
    the desktop command (`<name>.frameK.png`), so the judge can see scroll
    choreography the reduced-motion static shot can't.
    """

    out_dir = _screenshots_dir(target)
    commands: list[dict] = []
    for name, width in VIEWPORTS.items():
        argv = [
            "node",
            str(SHOOT),
            str(dist),
            str(out_dir),
            f"/:{name}",
            "--width",
            str(width),
        ]
        if frames > 0 and name == "desktop":
            argv += ["--frames", str(frames)]
        commands.append({"name": name, "width": width, "argv": argv})
    return commands


def capture_screenshots(dist: str | Path, target: str | Path, *, frames: int = 0) -> list[Path]:
    """Run the capture commands; return the PNG paths that now exist."""

    _screenshots_dir(target).mkdir(parents=True, exist_ok=True)
    for cmd in shoot_commands(dist, target, frames=frames):
        subprocess.run(cmd["argv"], check=True, cwd=REPO)
    return [
        _screenshots_dir(target) / f"{name}.png"
        for name in VIEWPORTS
        if (_screenshots_dir(target) / f"{name}.png").exists()
    ]


def frame_paths(target: str | Path, *, name: str = "desktop") -> list[str]:
    """Ordered motion scroll-frame PNGs captured under the screenshots dir."""

    shots = _screenshots_dir(target)
    out: list[str] = []
    k = 1
    while (shots / f"{name}.frame{k}.png").exists():
        out.append(str(shots / f"{name}.frame{k}.png"))
        k += 1
    return out


def _screenshot_map(target: str | Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in VIEWPORTS:
        path = _screenshots_dir(target) / f"{name}.png"
        if path.exists():
            out[name] = str(path)
    return out


# --------------------------------------------------------------------------- #
# Review
# --------------------------------------------------------------------------- #
def scores_from_payload(payload: list[dict]) -> list[VisualScore]:
    """Turn rubric output (`scores.json`) into `VisualScore` objects."""

    return [
        VisualScore(
            category=str(item["category"]),
            score=int(item["score"]),
            note=str(item.get("note", "")),
        )
        for item in payload
    ]


def run_review(target: str | Path, scores: list[VisualScore]) -> VisualReviewReport:
    """Score the captured screenshots and persist the visual-review report."""

    report = review_visual_quality(
        scores=scores,
        screenshots=_screenshot_map(target),
    )
    out = studio_dir(target)
    out.mkdir(parents=True, exist_ok=True)
    (out / "visual-review.json").write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    (out / "review.md").write_text(render_review_md(report))
    return report


def render_review_md(report: VisualReviewReport) -> str:
    verdict = "PASS" if report.passed else "FAIL"
    lines = [
        f"# Visual review — {verdict} ({report.overall}/100)",
        "",
        "## Scores",
        *[f"- **{s.category}**: {s.score}/5 — {s.note}" for s in report.scores],
    ]
    if report.failure_codes:
        lines += ["", "## Failures", *[f"- `{code}`" for code in report.failure_codes]]
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #
def studio_status(target: str | Path) -> dict:
    """Summarize which premium-track artifacts exist and the current verdict."""

    has_packet = (studio_dir(target) / "packet.json").exists()
    screenshots = {
        name: (_screenshots_dir(target) / f"{name}.png").exists() for name in VIEWPORTS
    }
    review_path = studio_dir(target) / "visual-review.json"
    reviewed = review_path.exists()
    passed = False
    if reviewed:
        passed = bool(json.loads(review_path.read_text()).get("passed", False))
    return {
        "target": str(target),
        "has_packet": has_packet,
        "screenshots": screenshots,
        "reviewed": reviewed,
        "passed": passed,
    }


def premium_ready(target: str | Path) -> bool:
    """Opt-in deploy guard.

    A build that has joined the premium track (a packet exists) is only ready
    once its visual review passes. A build with no packet — every cold-outreach
    demo — is unaffected and always returns True.
    """

    from packages.web.imagery import imagery_cleared

    status = studio_status(target)
    if not status["has_packet"]:
        return True
    if not status["passed"]:
        return False
    # A premium build also can't ship with uncleared generated imagery on it.
    return imagery_cleared(studio_dir(target) / "imagery" / "manifest.json")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _read_json_arg(value: str) -> object:
    if value == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(value).read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Design Studio premium-track runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p_packet = sub.add_parser("packet", help="build + persist the art-direction packet")
    p_packet.add_argument("--target", required=True)
    p_packet.add_argument("--spec", required=True, help="spec JSON path or '-' for stdin")

    p_shoot = sub.add_parser("shoot", help="capture desktop + mobile screenshots")
    p_shoot.add_argument("--target", required=True)
    p_shoot.add_argument("--dist", required=True, help="built site dir to screenshot")

    p_review = sub.add_parser("review", help="score screenshots and write the report")
    p_review.add_argument("--target", required=True)
    p_review.add_argument("--scores", required=True, help="scores JSON path or '-'")

    p_status = sub.add_parser("status", help="show premium-track artifacts + verdict")
    p_status.add_argument("--target", required=True)

    p_guard = sub.add_parser(
        "guard", help="exit non-zero if a premium build has not passed review"
    )
    p_guard.add_argument("--target", required=True)

    args = parser.parse_args(argv)

    if args.command == "packet":
        request = request_from_spec(_read_json_arg(args.spec))  # type: ignore[arg-type]
        path = write_packet(args.target, request)
        print(f"✓ packet → {path}")
        return 0

    if args.command == "shoot":
        paths = capture_screenshots(args.dist, args.target)
        for path in paths:
            print(f"✓ screenshot → {path}")
        return 0 if len(paths) == len(VIEWPORTS) else 1

    if args.command == "review":
        scores = scores_from_payload(_read_json_arg(args.scores))  # type: ignore[arg-type]
        report = run_review(args.target, scores)
        verdict = "PASS" if report.passed else "FAIL"
        print(f"{verdict} — {report.overall}/100")
        for code in report.failure_codes:
            print(f"  ✗ {code}")
        return 0 if report.passed else 1

    if args.command == "status":
        print(json.dumps(studio_status(args.target), indent=2))
        return 0

    if args.command == "guard":
        ready = premium_ready(args.target)
        print("ready" if ready else "BLOCKED — premium build has not passed review")
        return 0 if ready else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
