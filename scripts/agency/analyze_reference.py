#!/usr/bin/env python3
"""Reference analyzer CLI — Phase 5 of the design engine.

Persists a structured read of an inspiration shot and folds it into a build spec
as concrete parameters (palette, type ratio, density, grid, motion cues) — instead
of hand-fed prose takeaways.

The *vision* (looking at the Dribbble/Awwwards shot) is an agent capability: an
agent reads the image and emits the params JSON; this CLI is the dumb primitive
that validates + persists + applies them, keeping Phase 5 parity-consistent with
the rest of the lane.

  analyze_reference.py record --params <params.json|-> --out <reference-params.json>
  analyze_reference.py apply  --params <reference-params.json> --spec <spec.json|-> [--out OUT]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.reference_params import ReferenceParams, apply_to_spec  # noqa: E402


def _read_json(value: str) -> object:
    return json.loads(sys.stdin.read()) if value == "-" else json.loads(Path(value).read_text())


def cmd_record(params: dict, out: str) -> int:
    ref = ReferenceParams.from_dict(params)  # validates
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(ref.to_dict(), indent=2) + "\n")
    print(f"✓ reference params → {out}")
    return 0


def cmd_apply(params_path: str, spec: dict, out: str | None) -> int:
    ref = ReferenceParams.from_dict(json.loads(Path(params_path).read_text()))
    merged = apply_to_spec(ref, spec)
    text = json.dumps(merged, indent=2) + "\n"
    if out:
        Path(out).write_text(text)
        print(f"✓ spec with reference applied → {out}")
    else:
        sys.stdout.write(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reference analyzer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_rec = sub.add_parser("record", help="validate + persist agent-supplied params")
    p_rec.add_argument("--params", required=True, help="params JSON path or '-'")
    p_rec.add_argument("--out", required=True)

    p_app = sub.add_parser("apply", help="fold reference params into a build spec")
    p_app.add_argument("--params", required=True, help="reference-params.json path")
    p_app.add_argument("--spec", required=True, help="spec JSON path or '-'")
    p_app.add_argument("--out", default=None)

    args = parser.parse_args(argv)
    if args.command == "record":
        return cmd_record(_read_json(args.params), args.out)  # type: ignore[arg-type]
    if args.command == "apply":
        return cmd_apply(args.params, _read_json(args.spec), args.out)  # type: ignore[arg-type]
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
