#!/usr/bin/env python3
"""Quality-loop CLI — Phase 6 of the design engine.

The independent-judge half an operator/agent drives between builds:

  design_loop.py judge     --target <dir>            score screenshots with Gemini → scores.json
  design_loop.py calibrate --gold <gold.json>        re-score the gold set; halt on judge drift

Builder≠judge: the build is done by the agent/composer (Claude); `judge` scores
with Gemini vision (a different model family), writing `scores.json` that
`design_studio.py review` then gates on. A pass never auto-ships — the founder
signs off. The full programmatic loop lives in `packages.web.design_loop`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.design_loop import GoldSample, calibrate  # noqa: E402
from packages.web.gemini_judge import gemini_vision_judge  # noqa: E402


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

    p_judge = sub.add_parser("judge", help="score the build's screenshots with Gemini")
    p_judge.add_argument("--target", required=True)
    p_judge.add_argument("--out", default=None)

    p_cal = sub.add_parser("calibrate", help="re-score the gold set; halt on drift")
    p_cal.add_argument("--gold", required=True)

    args = parser.parse_args(argv)
    if args.command == "judge":
        return cmd_judge(args.target, args.out)
    if args.command == "calibrate":
        return cmd_calibrate(args.gold)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
