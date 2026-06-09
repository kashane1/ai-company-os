"""Premium build keystone — the missing builder that closes the design loop.

The design engine v2 shipped a correct convergence *orchestrator*
(`packages.web.design_loop.run_design_loop`) but never a real `BuildStep` to drive
it, and the premium scaffold (`scaffold/astro-premium`) was never instantiated by
any production code. This module is that keystone:

* :func:`build_premium_site` — synthesize tokens → scaffold the **premium** stack →
  compose art-directed blocks → build. This is the path that was missing; it makes
  `synthesize_design_system`, the `astro-premium` template, and the block composer
  all reachable in one call.
* :func:`apply_brief` — turn a failed review's :class:`RevisionBrief` into a
  *parametric* packet revision (archetype / palette / imagery / concept deltas), so
  the loop's revision is real — the next build genuinely differs — not the no-op the
  old tests faked.
* :func:`run_premium_loop` — wire build + capture + judge into the tested
  orchestrator with checkpointing (`loop-log.jsonl`). The build leg is deterministic
  here (the thin v3 Phase-1 builder); later phases hand the build leg to a Claude
  sub-agent for richer copy/imagery while keeping this same control flow.

Build (npm) and capture (browser) and judge (Gemini) are all **injected**, so the
whole loop is unit-testable without Node, a browser, or an API key.
"""

from __future__ import annotations

import colorsys
import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

from packages.web.blocks_composer import plan_composition, render_index_astro
from packages.web.build import BuildResult, CommandRunner, build_site, subprocess_runner
from packages.web.design_loop import (
    BudgetGuard,
    Iteration,
    LoopResult,
    run_design_loop,
)
from packages.web.design_studio import VISUAL_SCORE_FLOOR, DesignStudioPacket
from packages.web.design_system import synthesize_design_system
from packages.web.palette import parse_color
from packages.web.scaffold import (
    PREMIUM_TEMPLATE,
    default_context,
    scaffold_site,
)

# Capture maps screenshots -> paths (same shape the judge + review_visual_quality
# consume). Injected so the loop runs without a browser in tests.
Capture = Callable[[], dict[str, str]]

# The order the revision lever rotates archetypes through when a *structural*
# category fails. A rotation (not a fixed swap) so repeated failures keep exploring
# instead of bouncing between two skeletons.
_ARCHETYPE_ROTATION = [
    "service-area-cinematic",
    "gallery-led",
    "editorial-visit",
    "product-led",
    "classic-custom",
]

# Failing categories that a *structural* lever (archetype rotation) can address vs.
# a *palette* lever (hue rotation). Two categories are intentionally unhandled by a
# parametric lever in the thin Phase-1 builder, so a fail is surfaced, not faked:
# `copy_specificity` (real conversion copy is the agent build-leg's job, v3 Phase 4)
# and `imagery_art_direction` beyond its palette nudge (art-directed imagery is wired
# into blocks in v3 Phase 3). A palette rotation is the honest lever we have today for
# an imagery/hero/thesis fail.
_STRUCTURAL_CATEGORIES = {"hero_impact", "typography", "layout_composition", "visual_thesis"}
_PALETTE_CATEGORIES = {"hero_impact", "imagery_art_direction", "visual_thesis"}

_DEFAULT_SEED_HEX = "#1e3a5f"
_INTENSIFIERS = ["Boldly", "Singularly", "Unmistakably", "Decisively"]


# --------------------------------------------------------------------------- #
# Parametric revision — the brief actually changes the next build.
# --------------------------------------------------------------------------- #
def apply_brief(
    packet: DesignStudioPacket,
    brief: "object",
    *,
    attempt: int = 0,
) -> DesignStudioPacket:
    """Return a revised packet that addresses ``brief``'s failing categories.

    ``brief`` is a :class:`packages.web.design_loop.RevisionBrief`. The revision is
    *parametric*: it rotates the archetype (changes type/motion/blocks), rotates the
    palette seed hue, flips imagery to concept-led, and/or sharpens the concept —
    each keyed to which categories failed. ``attempt`` escalates the rotation so a
    repeated revision from the same base keeps exploring rather than repeating.

    A no-op brief (nothing actionable failed) returns the packet unchanged, so the
    caller/loop can detect a structural plateau honestly.
    """

    failing = set(getattr(brief, "failing_categories", []) or [])
    if not failing:
        return packet

    changes: dict[str, object] = {}

    if failing & _STRUCTURAL_CATEGORIES:
        rotated = _rotate_archetype(packet.archetype, attempt)
        if rotated != packet.archetype:
            changes["archetype"] = rotated

    if failing & _PALETTE_CATEGORIES:
        seed = _rotate_hue(_seed_of(packet), 47.0 * (attempt + 1))
        changes["concept_palette"] = seed

    if "visual_thesis" in failing:
        changes["concept_statement"] = _sharpen(packet.concept_statement, attempt)

    if not changes:
        return packet
    return dataclasses.replace(packet, **changes)


def _rotate_archetype(current: str, attempt: int) -> str:
    if current in _ARCHETYPE_ROTATION:
        base = _ARCHETYPE_ROTATION.index(current)
    else:
        base = _ARCHETYPE_ROTATION.index("classic-custom")
    return _ARCHETYPE_ROTATION[(base + 1 + attempt) % len(_ARCHETYPE_ROTATION)]


def _seed_of(packet: DesignStudioPacket) -> str:
    cue = packet.concept_palette.strip()
    if cue.startswith("#"):
        try:
            parse_color(cue)
            return cue
        except ValueError:
            pass
    return _DEFAULT_SEED_HEX


def _rotate_hue(hex_color: str, degrees: float) -> str:
    r, g, b = parse_color(hex_color)
    h, light, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    h = (h + degrees / 360.0) % 1.0
    # Keep saturation/lightness in a premium-leaning band so a rotated seed is still
    # a usable brand color, not neon or mud.
    s = min(0.85, max(0.35, s))
    light = min(0.55, max(0.30, light))
    nr, ng, nb = colorsys.hls_to_rgb(h, light, s)
    return "#{:02x}{:02x}{:02x}".format(round(nr * 255), round(ng * 255), round(nb * 255))


def _sharpen(concept: str, attempt: int) -> str:
    word = _INTENSIFIERS[attempt % len(_INTENSIFIERS)]
    stripped = concept.strip()
    # Don't stack intensifiers across rounds — replace any prior one.
    for prior in _INTENSIFIERS:
        if stripped.startswith(prior + " "):
            stripped = stripped[len(prior) + 1 :]
            break
    head = stripped[:1].lower() + stripped[1:] if stripped else "a singular idea"
    return f"{word} {head}"


# --------------------------------------------------------------------------- #
# The build — the premium path that was never wired.
# --------------------------------------------------------------------------- #
def build_premium_site(
    packet: DesignStudioPacket,
    project_dir: Path,
    *,
    runner: CommandRunner | None = None,
    run_build: bool = True,
    template: str = PREMIUM_TEMPLATE,
) -> BuildResult:
    """Materialize + build a premium site from a packet.

    Steps: synthesize role tokens → scaffold the premium stack → overwrite the
    theme layer with the synthesized tokens → compose art-directed blocks into
    ``index.astro`` → ``npm ci && npm run build``. Returns the :class:`BuildResult`.

    ``runner`` is injected (defaults to a real subprocess runner); pass a fake to
    test the composition without Node. ``run_build=False`` materializes the project
    but skips the npm build (useful for inspecting the generated source).
    """

    project_dir = Path(project_dir)
    design = synthesize_design_system(packet)
    context = default_context(
        packet.site_name,
        tagline=_tagline(packet),
        audience=packet.audience,
    )
    scaffold_site(project_dir, context, template=template)

    # Overwrite the two files synthesis + composition own (the scaffold ships
    # presentable baselines; here we replace them with this build's craft).
    (project_dir / "src" / "styles" / "design-system.css").write_text(
        design.to_css(), encoding="utf-8"
    )
    composition = plan_composition(packet)
    (project_dir / "src" / "pages" / "index.astro").write_text(
        render_index_astro(
            composition,
            tagline=context["TAGLINE"],
            meta_description=context["META_DESCRIPTION"],
            year=context["YEAR"],
        ),
        encoding="utf-8",
    )

    if not run_build:
        return BuildResult(exit_code=0, stdout="", stderr="", dist_dir=project_dir / "dist")
    return build_site(project_dir, runner=runner or subprocess_runner())


def _tagline(packet: DesignStudioPacket) -> str:
    concept = packet.concept_statement.split(";")[0].split(".")[0].strip()
    tagline = concept or packet.goal.strip() or packet.business_category.title()
    return tagline[:70]


# --------------------------------------------------------------------------- #
# The loop — wire the keystone into the tested orchestrator + checkpoint.
# --------------------------------------------------------------------------- #
def run_premium_loop(
    packet: DesignStudioPacket,
    project_dir: Path,
    *,
    runner: CommandRunner,
    capture: Capture,
    judge: Callable[[dict[str, str]], list],
    target: Path | None = None,
    max_iters: int = 4,
    no_improve_patience: int | None = 2,
    budget: BudgetGuard | None = None,
) -> LoopResult:
    """Drive build → capture → judge → revise to a pass (or halt-to-best).

    The build leg is :func:`build_premium_site` with :func:`apply_brief` applied on
    every revision (so the brief is real); ``capture`` and ``judge`` are injected
    (browser + independent Gemini in production, fakes in tests). Each iteration is
    checkpointed to ``<target>/design-studio/loop-log.jsonl``; the best iteration's
    review is persisted on exit. A build failure raises → the orchestrator degrades
    to the best build so far. Never auto-ships: a pass returns ``needs_signoff``.
    """

    project_dir = Path(project_dir)
    target_dir = Path(target) if target is not None else project_dir.parent
    studio = target_dir / "design-studio"
    log_path = studio / "loop-log.jsonl"

    def build(index: int, brief: object | None) -> None:
        revised = packet if brief is None else apply_brief(packet, brief, attempt=index)
        result = build_premium_site(revised, project_dir, runner=runner)
        if not result.succeeded:
            raise RuntimeError(
                f"premium build failed (exit {result.exit_code}): {result.stderr[:200]}"
            )

    def on_progress(iteration: Iteration) -> None:
        _append_log(
            log_path,
            {
                "index": iteration.index,
                "overall": iteration.overall,
                "passed": iteration.passed,
                "failing_categories": [
                    s.category for s in iteration.report.scores if s.score < VISUAL_SCORE_FLOOR
                ],
            },
        )

    result = run_design_loop(
        build=build,
        capture=capture,
        judge=judge,
        max_iters=max_iters,
        no_improve_patience=no_improve_patience,
        budget=budget,
        on_progress=on_progress,
    )

    if result.best is not None:
        studio.mkdir(parents=True, exist_ok=True)
        (studio / "visual-review.json").write_text(
            json.dumps(result.best.report.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
    return result


def _append_log(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
