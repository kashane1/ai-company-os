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
from packages.web.design_loop import BudgetGuard, GoldSample, calibrate  # noqa: E402
from packages.web.design_studio import build_design_studio_packet  # noqa: E402
from packages.web.gemini_judge import gemini_vision_judge  # noqa: E402
from packages.web.premium_build import run_premium_loop  # noqa: E402


def _studio(target: str | Path) -> Path:
    return Path(target) / "design-studio"


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
) -> int:
    """The autonomous premium loop: build → shoot → judge → revise → repeat."""

    from scripts.agency.design_studio import (  # local import (script module)
        capture_screenshots,
        request_from_spec,
        studio_dir,
    )

    packet = build_design_studio_packet(request_from_spec(spec))  # type: ignore[arg-type]
    project_dir = Path(target) / "site"
    dist_dir = project_dir / "dist"

    def capture() -> dict[str, str]:
        capture_screenshots(dist_dir, target)
        shots_dir = studio_dir(target) / "screenshots"
        return {
            name: str(shots_dir / f"{name}.png")
            for name in ("desktop", "mobile")
            if (shots_dir / f"{name}.png").exists()
        }

    budget = BudgetGuard(max_seconds=max_seconds) if max_seconds else None
    result = run_premium_loop(
        packet,
        project_dir,
        runner=subprocess_runner(),
        capture=capture,
        judge=gemini_vision_judge,
        target=Path(target),
        max_iters=max_iters,
        no_improve_patience=no_improve_patience,
        budget=budget,
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

    p_judge = sub.add_parser("judge", help="score the build's screenshots with Gemini")
    p_judge.add_argument("--target", required=True)
    p_judge.add_argument("--out", default=None)

    p_cal = sub.add_parser("calibrate", help="re-score the gold set; halt on drift")
    p_cal.add_argument("--gold", required=True)

    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run(
            args.target,
            _read_json_arg(args.spec),
            max_iters=args.max_iters,
            max_seconds=args.max_seconds,
            no_improve_patience=args.no_improve_patience,
        )
    if args.command == "judge":
        return cmd_judge(args.target, args.out)
    if args.command == "calibrate":
        return cmd_calibrate(args.gold)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
