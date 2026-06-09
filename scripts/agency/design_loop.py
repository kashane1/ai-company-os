#!/usr/bin/env python3
"""Quality-loop CLI — design engine v3.

The autonomous premium loop and the independent-judge primitives:

  design_loop.py run       --target <dir> --spec <spec.json|->   build→judge→revise→repeat
  design_loop.py judge     --target <dir>            score screenshots with Gemini → scores.json
  design_loop.py calibrate --gold <gold.json>        re-score the gold set; halt on judge drift

`run` is the one command the founder asked for: it drives build (the premium
keystone) → shoot → JUDGE → parametric revise → repeat, autonomously, until the
visual gate passes or it halts to the best build (iteration cap / plateau / budget).
Builder≠judge: the build is Claude/composer; `judge` scores with Gemini vision (a
different model family). A pass never auto-ships — the founder signs off. The loop
needs `npm` (build) and `GEMINI_API_KEY` (judge) for a live run; the control flow
itself is unit-tested with fakes in `tests/python/unit/test_web_premium_build.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.build import subprocess_runner  # noqa: E402
from packages.web.composition_gate import composition_defects  # noqa: E402
from packages.web.design_loop import BudgetGuard, GoldSample, calibrate  # noqa: E402
from packages.web.design_studio import VisualScore, build_design_studio_packet  # noqa: E402
from packages.web.gemini_judge import (  # noqa: E402
    gemini_vision_judge,
    high_severity_defects,
    inspect_defects,
)
from packages.web.premium_build import run_premium_loop  # noqa: E402


def _studio(target: str | Path) -> Path:
    return Path(target) / "design-studio"


def _geometry_defects(geo_file: Path) -> list[dict]:
    """Classify the DOM geometry snapshot into composition defects (fail-open)."""
    try:
        if geo_file.exists():
            return composition_defects(json.loads(geo_file.read_text()))
    except Exception as exc:  # the gate's own error must never abort a build
        print(f"! composition gate skipped: {exc}", file=sys.stderr)
    return []


def cmd_composition(target: str) -> int:
    """Deterministic composition gate ONLY — DOM geometry, no Gemini. Captures a
    geometry snapshot of the built site and reports composition defects (stacked
    full-bleed sections, section/text overlaps, horizontal overflow)."""
    from scripts.agency.design_studio import capture_screenshots, geometry_path

    dist_dir = Path(target) / "site" / "dist"
    if not (dist_dir / "index.html").exists():
        print(f"no built site at {dist_dir} — build first", file=sys.stderr)
        return 1
    capture_screenshots(dist_dir, target, frames=4)  # frames>0 triggers the geometry pass
    defects = _geometry_defects(geometry_path(target))
    _studio(target).mkdir(parents=True, exist_ok=True)
    (_studio(target) / "composition.json").write_text(json.dumps(defects, indent=2) + "\n")
    highs = [d for d in defects if d.get("severity") == "high"]
    if defects:
        for d in defects:
            print(f"  [{d['severity']}] {d['type']} @ {d['where']}: {d['detail']}")
    else:
        print("✓ no composition defects")
    print(f"  → {_studio(target) / 'composition.json'}")
    return 1 if highs else 0


def cmd_judge(target: str, out: str | None) -> int:
    shots_dir = _studio(target) / "screenshots"
    screenshots = {
        name: str(shots_dir / f"{name}.png")
        for name in ("desktop", "mobile")
        if (shots_dir / f"{name}.png").exists()
    }
    if not screenshots:
        print("no screenshots to judge — run design_studio.py shoot first", file=sys.stderr)
        return 1
    scores = gemini_vision_judge(screenshots)
    payload = [s.to_dict() for s in scores]
    out_path = Path(out) if out else _studio(target) / "scores.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    overall = round(sum(s.score for s in scores) / len(scores) * 20)
    print(f"✓ judged (Gemini) → {out_path}  [{overall}/100]")
    print("  next: design_studio.py review "
          f"--target {target} --scores {out_path}")
    return 0


def _read_json_arg(value: str) -> object:
    if value == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(value).read_text())


def cmd_run(
    target: str,
    spec: object,
    *,
    max_iters: int,
    max_seconds: float | None,
    no_improve_patience: int | None,
    imagery: bool = True,
    min_overall: int | None = None,
) -> int:
    """The autonomous premium loop: build → shoot → judge → revise → repeat."""

    from scripts.agency.design_studio import (  # local import (script module)
        capture_screenshots,
        frame_paths,
        geometry_path,
        request_from_spec,
        studio_dir,
    )

    packet = build_design_studio_packet(request_from_spec(spec))  # type: ignore[arg-type]
    project_dir = Path(target) / "site"
    dist_dir = project_dir / "dist"
    motion_frames = 4  # scroll-frame captures so the judge can see motion
    judge_samples = 2  # median across N judge calls to damp variance on the gate

    # Imagery leg: generate a concept-led set ONCE up front (reused across iterations)
    # so the loop is self-sufficient and `imagery_art_direction` can actually clear.
    # Skipped if a manifest already exists (cheap re-runs) or --no-imagery.
    if imagery:
        manifest_path = studio_dir(target) / "imagery" / "manifest.json"
        if manifest_path.exists():
            print(f"• reusing existing imagery manifest → {manifest_path}")
        else:
            from packages.tools.content_tools.gemini_images import (
                GEMINI_IMAGE_MODEL_PRO,
                generate_image,
            )
            from packages.web.imagery import generate_imagery_set

            def _gen(prompt: str, aspect_ratio: str, seed: int):
                return generate_image(
                    prompt, aspect_ratio=aspect_ratio, model=GEMINI_IMAGE_MODEL_PRO, seed=seed
                )

            print("• generating concept-led imagery (Gemini Pro)…")
            try:
                generate_imagery_set(packet, manifest_path.parent, generate=_gen)
                print("✓ imagery generated + auto-curated")
            except Exception as exc:  # never let imagery failure abort the build
                print(f"! imagery generation failed ({exc}); building without it", file=sys.stderr)

    def capture() -> dict[str, str]:
        capture_screenshots(dist_dir, target, frames=motion_frames)
        shots_dir = studio_dir(target) / "screenshots"
        shots = {
            name: str(shots_dir / f"{name}.png")
            for name in ("desktop", "mobile")
            if (shots_dir / f"{name}.png").exists()
        }
        # Carry motion frames alongside the stills under frame* keys; the judge
        # closure splits them out, and review_visual_quality ignores extra keys.
        for i, fp in enumerate(frame_paths(target), start=1):
            shots[f"frame{i}"] = fp
        return shots

    def judge(shots: dict[str, str]) -> list:
        stills = {k: v for k, v in shots.items() if k in ("desktop", "mobile")}
        frames = [v for k, v in sorted(shots.items()) if k.startswith("frame")]
        scores = gemini_vision_judge(stills, frames=frames, samples=judge_samples)
        # Adversarial defect lens (separate from the taste judge). A high-severity
        # defect (illegible text over a photo, overlap, broken layout, repeat) FAILS
        # the build by capping the structural categories below the floor — the taste
        # score can't rescue a real defect.
        defects = inspect_defects(stills, frames=frames)
        # Deterministic composition gate (DOM geometry — no model). Catches what the
        # vision judge structurally can't: stacked full-bleed sections, section/text
        # overlaps, horizontal overflow. Merged first so it shares the same gate.
        defects = _geometry_defects(geometry_path(target)) + defects
        # Always record the current defects (empty list on a clean build) so the file
        # never goes stale and reflects the latest iteration.
        (studio_dir(target)).mkdir(parents=True, exist_ok=True)
        (studio_dir(target) / "defects.json").write_text(json.dumps(defects, indent=2) + "\n")
        highs = high_severity_defects(defects)
        if highs:
            note = "DEFECT — " + "; ".join(f"{d['type']}: {d['detail']}" for d in highs)[:140]
            kinds = ", ".join(d["type"] for d in highs)
            print(f"  ✗ {len(highs)} high-severity defect(s): {kinds}")
            scores = [
                VisualScore(s.category, min(2, s.score), note)
                if s.category in ("layout_composition", "ai_house_style")
                else s
                for s in scores
            ]
        return scores

    budget = BudgetGuard(max_seconds=max_seconds) if max_seconds else None
    result = run_premium_loop(
        packet,
        project_dir,
        runner=subprocess_runner(),
        capture=capture,
        judge=judge,
        target=Path(target),
        max_iters=max_iters,
        no_improve_patience=no_improve_patience,
        budget=budget,
        min_overall=min_overall,
    )

    best = result.best
    overall = best.overall if best else 0
    if result.passed:
        print(f"PASS — {overall}/100 in {len(result.iterations)} iteration(s).")
        print("  → needs founder sign-off before any client ship (loop never auto-ships).")
    else:
        reason = result.halted_reason or "no-pass"
        print(f"NO PASS — halted: {reason}. Best build: {overall}/100.")
    print(f"  log:    {studio_dir_path(target) / 'loop-log.jsonl'}")
    print(f"  review: {studio_dir_path(target) / 'visual-review.json'}")
    print(f"  site:   {project_dir}")
    return 0 if result.passed else 1


def studio_dir_path(target: str | Path) -> Path:
    return _studio(target)


def cmd_calibrate(gold_path: str) -> int:
    gold = [
        GoldSample(id=g["id"], screenshots=g["screenshots"], expected=g["expected"])
        for g in json.loads(Path(gold_path).read_text())
    ]
    report = calibrate(gemini_vision_judge, gold)
    if report.drifted:
        print("DRIFT — judge miscalibrated:\n  " + "\n  ".join(report.mismatches))
        return 1
    print(f"calibrated — judge classifies all {len(gold)} gold samples correctly")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Design quality loop (independent judge)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="autonomous loop: build→judge→revise until pass or halt")
    p_run.add_argument("--target", required=True, help="build hub dir (artifacts under <dir>/)")
    p_run.add_argument("--spec", required=True, help="design spec JSON path or '-' for stdin")
    p_run.add_argument("--max-iters", type=int, default=4, help="hard iteration cap (default 4)")
    p_run.add_argument(
        "--max-seconds", type=float, default=None, help="wall-clock budget for the run"
    )
    p_run.add_argument(
        "--no-improve-patience",
        type=int,
        default=2,
        help="halt after N rounds with no gain over the best build (plateau; default 2)",
    )
    p_run.add_argument(
        "--no-imagery",
        action="store_true",
        help="skip concept-led imagery generation (build without photography)",
    )
    p_run.add_argument(
        "--min-overall",
        type=int,
        default=None,
        help="raise the pass bar above 80 (e.g. 95) to keep revising past 'good enough'",
    )

    p_judge = sub.add_parser("judge", help="score the build's screenshots with Gemini")
    p_judge.add_argument("--target", required=True)
    p_judge.add_argument("--out", default=None)

    p_cal = sub.add_parser("calibrate", help="re-score the gold set; halt on drift")
    p_cal.add_argument("--gold", required=True)

    p_comp = sub.add_parser(
        "composition", help="deterministic composition/overlap gate (DOM geometry, no Gemini)"
    )
    p_comp.add_argument("--target", required=True, help="build hub dir (expects <dir>/site/dist)")

    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run(
            args.target,
            _read_json_arg(args.spec),
            max_iters=args.max_iters,
            max_seconds=args.max_seconds,
            no_improve_patience=args.no_improve_patience,
            imagery=not args.no_imagery,
            min_overall=args.min_overall,
        )
    if args.command == "judge":
        return cmd_judge(args.target, args.out)
    if args.command == "calibrate":
        return cmd_calibrate(args.gold)
    if args.command == "composition":
        return cmd_composition(args.target)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
