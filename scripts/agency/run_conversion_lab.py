#!/usr/bin/env python3
"""Prepare and render manual Conversion Lab runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.conversion_lab import (  # noqa: E402
    build_persona_review_prompt,
    render_prompts_markdown,
    write_report,
)
from packages.agency.conversion_personas import load_persona_pack  # noqa: E402
from packages.schemas.conversion_lab import (  # noqa: E402
    ConversionAction,
    ConversionLabInput,
    ConversionLabReport,
)


def _run_dir(root: Path, product_id: str, run_id: str) -> Path:
    return root / "state" / "clients" / product_id / "conversion_lab" / run_id


def _prepare(args: argparse.Namespace) -> int:
    page_copy = args.page_copy_file.read_text(encoding="utf-8")
    input_payload = ConversionLabInput(
        product_id=args.product_id,
        vertical=args.vertical,
        target_action=ConversionAction(args.target_action),
        url=args.url,
        page_copy=page_copy,
        known_objections=list(args.known_objection or []),
    )
    pack = load_persona_pack(args.vertical)
    prompts = [
        build_persona_review_prompt(persona=persona, input_payload=input_payload)
        for persona in pack.personas
    ]

    out_dir = _run_dir(args.root, args.product_id, args.run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "INPUT.json").write_text(
        json.dumps(input_payload.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "PROMPTS.md").write_text(
        render_prompts_markdown(input_payload, prompts),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run_dir": str(out_dir),
                "input": str(out_dir / "INPUT.json"),
                "prompts": str(out_dir / "PROMPTS.md"),
            },
            indent=2,
        )
    )
    return 0


def _render(args: argparse.Namespace) -> int:
    payload = json.loads(args.reviews_json.read_text(encoding="utf-8"))
    report = ConversionLabReport.from_dict(payload)
    if report.product_id != args.product_id:
        print(
            f"ERROR: reviews product_id {report.product_id!r} does not match {args.product_id!r}",
            file=sys.stderr,
        )
        return 1
    path = write_report(report, root=args.root, run_id=args.run_id)
    print(json.dumps({"report": str(path)}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="write INPUT.json and PROMPTS.md")
    prepare.add_argument("--root", type=Path, default=REPO)
    prepare.add_argument("--product-id", required=True)
    prepare.add_argument("--vertical", required=True)
    prepare.add_argument("--target-action", required=True, choices=[a.value for a in ConversionAction])
    prepare.add_argument("--url", default="")
    prepare.add_argument("--page-copy-file", required=True, type=Path)
    prepare.add_argument("--known-objection", action="append")
    prepare.add_argument("--run-id", required=True)
    prepare.set_defaults(func=_prepare)

    render = sub.add_parser("render", help="render REPORT.md from review JSON")
    render.add_argument("--root", type=Path, default=REPO)
    render.add_argument("--product-id", required=True)
    render.add_argument("--run-id", required=True)
    render.add_argument("--reviews-json", required=True, type=Path)
    render.set_defaults(func=_render)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
