#!/usr/bin/env python3
"""Block studio — author the block library (design engine, authoring lane).

The autonomous fleet loop *searches* the block library; this CLI is how the library
*grows*. It runs the tournament: render each candidate block in isolation, judge it
with the same independent Gemini judge the loop uses, and admit the survivors — each
as an un-cleared generated block that a founder must clear before it can ship.

  block_studio.py gen        --slot hero --archetype <a> --brief "..." [--generator claude|stitch] [--n 3] --out <dir>
  block_studio.py tournament --candidates <dir> --target <dir> [--keep 6] [--admit]
  block_studio.py figma-tokens (--file <key> | --manual <tokens.json>) --out <dir>
  block_studio.py clear      --target <dir> --id <block-id> --by <name>
  block_studio.py list       --target <dir>

A candidates dir holds one ``<Component>.astro`` per candidate plus a
``candidates.json`` describing them ([{id, component, slot, source, license,
archetype_affinity}]). Rendering needs `npm` + Chromium; judging needs
`GEMINI_API_KEY`. The orchestration core is unit-tested with fakes in
`tests/python/unit/test_web_block_tournament.py` — this is the live wrapper.

External generators (Stitch) write candidate dirs via `block_studio.py gen`
(Phase 4); this command is generator-agnostic — it judges whatever astro it's given.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.block_harness import harness_index_astro  # noqa: E402
from packages.web.block_library import BlockLibrary  # noqa: E402
from packages.web.block_tournament import (  # noqa: E402
    BlockCandidate,
    CandidateResult,
    admit,
    tournament,
)
from packages.web.build import subprocess_runner, build_site  # noqa: E402
from packages.web.gemini_judge import gemini_vision_judge  # noqa: E402

_SCAFFOLD = REPO / "packages" / "web" / "scaffold" / "astro-premium"


def library_path(target: str | Path) -> Path:
    return Path(target) / "block-library" / "manifest.json"


def _load_library(target: str | Path) -> BlockLibrary:
    path = library_path(target)
    return BlockLibrary.load(path) if path.exists() else BlockLibrary()


def _load_candidates(candidates_dir: Path) -> list[BlockCandidate]:
    meta = json.loads((candidates_dir / "candidates.json").read_text())
    out: list[BlockCandidate] = []
    for m in meta:
        astro = (candidates_dir / f"{m['component']}.astro").read_text()
        out.append(
            BlockCandidate(
                id=m["id"],
                slot=m["slot"],
                component=m["component"],
                source=m["source"],
                astro=astro,
                archetype_affinity=tuple(m.get("archetype_affinity", [])),
                license=m.get("license", ""),
                prompt=m.get("prompt", ""),
            )
        )
    return out


def _ensure_harness(target: Path) -> Path:
    """A built-once copy of the premium scaffold we re-render per candidate."""

    harness = target / "harness"
    if not harness.exists():
        shutil.copytree(_SCAFFOLD, harness)
        (harness / "src" / "blocks" / "generated").mkdir(parents=True, exist_ok=True)
    return harness


def _render(harness: Path, target: Path):
    """Make a render() closure that builds + shoots one candidate → screenshots."""

    from scripts.agency.design_studio import capture_screenshots, studio_dir

    runner = subprocess_runner()
    generated = harness / "src" / "blocks" / "generated"

    def render(candidate: BlockCandidate) -> dict:
        (generated / f"{candidate.component}.astro").write_text(candidate.astro)
        (harness / "src" / "pages" / "index.astro").write_text(harness_index_astro(candidate))
        result = build_site(harness, runner=runner)
        if result.exit_code != 0:
            raise RuntimeError(f"build failed for {candidate.component}: {result.stderr[:300]}")
        shot_target = target / "renders" / candidate.id
        capture_screenshots(result.dist_dir, shot_target)
        shots_dir = studio_dir(shot_target) / "screenshots"
        return {
            name: str(shots_dir / f"{name}.png")
            for name in ("desktop", "mobile")
            if (shots_dir / f"{name}.png").exists()
        }

    return render


def _judge(shots: dict) -> list:
    # samples=1 to keep the gate cheap during authoring (the full loop uses 2).
    return gemini_vision_judge(shots, samples=1)


def _result_row(r: CandidateResult) -> dict:
    return {
        "id": r.candidate.id,
        "component": r.candidate.component,
        "slot": r.candidate.slot,
        "source": r.candidate.source,
        "overall": r.overall,
        "passed": r.passed,
        "reasons": r.reasons,
        "scores": [s.to_dict() for s in r.scores],
    }


def cmd_tournament(candidates_dir: str, target: str, *, keep: int, do_admit: bool) -> int:
    candidates = _load_candidates(Path(candidates_dir))
    if not candidates:
        print("no candidates found", file=sys.stderr)
        return 1
    harness = _ensure_harness(Path(target))
    result = tournament(
        candidates, render=_render(harness, Path(target)), judge=_judge, keep=keep
    )
    report = {
        "ranked": [_result_row(r) for r in result.ranked],
        "admitted": [r.candidate.id for r in result.admitted],
    }
    report_path = Path(target) / "block-library" / "tournament.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    for r in result.ranked:
        mark = "✓ admit" if r in result.admitted else ("· pass" if r.passed else "✗ fail")
        print(f"  {mark}  {r.candidate.component:24} {r.overall:5}  {'; '.join(r.reasons)}")
    print(f"→ {report_path}")

    if do_admit and result.admitted:
        _admit_into_library(Path(target), candidates, result.admitted)
    elif result.admitted:
        print(f"  {len(result.admitted)} pass — re-run with --admit (or `admit`) to record them")
    return 0


def _admit_into_library(target: Path, candidates, admitted) -> None:
    """Record passers in the library + stash their .astro under state for later staging."""

    # The wall clock is read only here (the pure layer stays deterministic).
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    library = _load_library(target)
    admit(library, admitted, admitted_at=stamp)
    library.save(library_path(target))
    blocks_dir = target / "block-library" / "blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)
    by_id = {c.id: c for c in candidates}
    for r in admitted:
        c = by_id[r.candidate.id]
        (blocks_dir / f"{c.component}.astro").write_text(c.astro)
    print(f"✓ admitted {len(admitted)} block(s) (un-cleared) → {library_path(target)}")
    print("  clear one with: block_studio.py clear --target "
          f"{target} --id <id> --by <name>")


def cmd_gen(
    *, slot: str, archetype: str, brief: str, generator: str, n: int, out: str
) -> int:
    """Generate raw block designs, normalize each to tokenized Astro, write a
    candidate dir ready for `tournament`. External keys are touched only here."""

    from packages.tools.llm.client import OpenRouterClient
    from packages.web.block_generators import GenerationRequest, claude_generator, stitch_generator
    from packages.web.block_harness import sample_data_for
    from packages.web.block_normalizer import normalize_block

    # The slot's canonical data shape — so a generated block reads the same `data`
    # fields the harness and the real composer supply (not an invented shape).
    data_shape = json.dumps(sample_data_for(slot))

    model = OpenRouterClient()
    if generator == "claude":
        gen = claude_generator(model)
    elif generator == "stitch":
        import httpx

        from packages.web.block_generators import StitchClient

        client = StitchClient()
        gen = stitch_generator(client.call_tool, fetch=lambda u: httpx.get(u, timeout=60).text)
    else:
        print(f"unknown generator {generator}", file=sys.stderr)
        return 2

    raws = gen(GenerationRequest(slot=slot, archetype=archetype, brief=brief, n=n))
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = []
    cap = slot.capitalize()
    for i, raw in enumerate(raws, start=1):
        component = f"{raw.source.capitalize()}{cap}{i}"
        norm = normalize_block(
            raw.markup, slot=slot, component=component, model=model, data_shape=data_shape
        )
        (out_dir / f"{component}.astro").write_text(norm.astro)
        meta.append(
            {
                "id": f"{raw.source}:{slot}-{i}",
                "component": component,
                "slot": slot,
                "source": raw.source,
                "license": raw.license,
                "archetype_affinity": [archetype],
                "prompt": raw.prompt,
                "tokenization_issues": list(norm.issues),
            }
        )
        flag = "clean" if not norm.issues else f"{len(norm.issues)} token issue(s)"
        print(f"  • {component:18} ({raw.source}, {flag})")
    (out_dir / "candidates.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"✓ {len(meta)} candidate(s) → {out_dir}")
    print(f"  next: block_studio.py tournament --candidates {out_dir} --target <hub> --admit")
    return 0


def cmd_figma_tokens(*, file_key: str | None, manual: str | None, out: str) -> int:
    """Emit brand tokens.json + tokens.css for a premium, brand-locked build.

    Reads Figma Variables when available; falls back to a hand-authored tokens.json
    (Variables REST is Enterprise-gated, so the fallback is the free-account path)."""

    from packages.web.figma_tokens import (
        FigmaClient,
        FigmaError,
        load_manual_tokens,
        variables_to_tokens,
        write_tokens,
    )

    if manual:
        tokens = load_manual_tokens(Path(manual))
        print(f"• {len(tokens)} token(s) from manual {manual}")
    elif file_key:
        try:
            payload = FigmaClient().local_variables(file_key)
        except FigmaError as exc:
            print(f"✗ {exc}", file=sys.stderr)
            print("  → author a tokens.json and re-run with --manual <tokens.json>", file=sys.stderr)
            return 1
        tokens = variables_to_tokens(payload)
        print(f"• {len(tokens)} token(s) from Figma file {file_key}")
    else:
        print("need --file <key> or --manual <tokens.json>", file=sys.stderr)
        return 2

    json_path, css_path = write_tokens(tokens, Path(out))
    print(f"✓ {json_path}\n✓ {css_path}")
    print("  premium builds layer tokens.css over design-system.css to brand-lock.")
    return 0


def cmd_clear(target: str, block_id: str, by: str) -> int:
    library = _load_library(target)
    hit = next((e for e in library.entries if e.id == block_id), None)
    if hit is None:
        print(f"no block {block_id} in {library_path(target)}", file=sys.stderr)
        return 1
    from dataclasses import replace

    library.entries = [
        replace(e, cleared=True) if e.id == block_id else e for e in library.entries
    ]
    library.save(library_path(target))
    print(f"✓ cleared {block_id} (by {by}) — now eligible for builds")
    return 0


def cmd_metrics(target: str, *, tier: str) -> int:
    """Report whether the library actually widened the search space + diversity."""

    from packages.web.library_metrics import library_report

    library = _load_library(target)
    report = library_report(library, tier=tier)
    out = Path(target) / "block-library" / "metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"search-space width ({tier}): {report['search_space_width']}  "
          f"({report['blocks_cleared']}/{report['blocks_total']} blocks cleared)")
    for slot, n in report["slot_coverage"].items():
        print(f"  {slot:9} {n} option(s)")
    print(f"→ {out}")
    return 0


def cmd_list(target: str) -> int:
    library = _load_library(target)
    if not library.entries:
        print("(empty library)")
        return 0
    for e in library.entries:
        flag = "cleared" if e.cleared else "UNCLEARED"
        print(f"  {e.id:28} {e.slot:9} {e.source:7} score={e.judge_score:<5} {flag}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block studio — grow the block library")
    sub = parser.add_subparsers(dest="command", required=True)

    p_t = sub.add_parser("tournament", help="render + judge candidates; admit survivors")
    p_t.add_argument("--candidates", required=True, help="dir with <Component>.astro + candidates.json")
    p_t.add_argument("--target", required=True, help="authoring hub dir (library + renders under it)")
    p_t.add_argument("--keep", type=int, default=6)
    p_t.add_argument("--admit", action="store_true", help="record passers into the library")

    p_g = sub.add_parser("gen", help="generate + normalize candidate blocks (touches keys)")
    p_g.add_argument("--slot", required=True, choices=("hero", "split", "bento", "process", "fullbleed", "cta"))
    p_g.add_argument("--archetype", required=True)
    p_g.add_argument("--brief", required=True, help="what the block should express")
    p_g.add_argument("--generator", default="claude", choices=("claude", "stitch"))
    p_g.add_argument("--n", type=int, default=3)
    p_g.add_argument("--out", required=True, help="candidate dir to write")

    p_f = sub.add_parser("figma-tokens", help="emit brand tokens.json+css (Figma or manual)")
    p_f.add_argument("--file", default=None, help="Figma file key (Variables REST; Enterprise)")
    p_f.add_argument("--manual", default=None, help="hand-authored tokens.json (free-tier fallback)")
    p_f.add_argument("--out", required=True, help="output dir for tokens.json + tokens.css")

    p_c = sub.add_parser("clear", help="founder clearance — make an admitted block shippable")
    p_c.add_argument("--target", required=True)
    p_c.add_argument("--id", required=True)
    p_c.add_argument("--by", required=True)

    p_m = sub.add_parser("metrics", help="report search-space width + diversity")
    p_m.add_argument("--target", required=True)
    p_m.add_argument("--tier", default="fleet", choices=("fleet", "premium"))

    p_l = sub.add_parser("list", help="list the library")
    p_l.add_argument("--target", required=True)

    args = parser.parse_args(argv)
    if args.command == "tournament":
        return cmd_tournament(args.candidates, args.target, keep=args.keep, do_admit=args.admit)
    if args.command == "gen":
        return cmd_gen(
            slot=args.slot,
            archetype=args.archetype,
            brief=args.brief,
            generator=args.generator,
            n=args.n,
            out=args.out,
        )
    if args.command == "figma-tokens":
        return cmd_figma_tokens(file_key=args.file, manual=args.manual, out=args.out)
    if args.command == "clear":
        return cmd_clear(args.target, args.id, args.by)
    if args.command == "metrics":
        return cmd_metrics(args.target, tier=args.tier)
    if args.command == "list":
        return cmd_list(args.target)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
