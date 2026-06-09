"""Tests for the premium build keystone (design engine v3 — Phase 1).

The v2 loop never closed because there was no real `BuildStep` and the premium
scaffold was never instantiated. These tests lock the keystone that fixes both:

* :func:`apply_brief` makes the revision *parametric* — a failed category actually
  changes the next build (archetype / palette / imagery / concept), not a no-op.
* :func:`build_premium_site` instantiates the **premium** stack (the path that was
  passed nowhere), synthesizes the theme, and composes art-directed blocks.
* :func:`run_premium_loop` drives the whole thing through the tested orchestrator,
  with a real (brief-consuming) build and per-iteration checkpointing — no Node,
  browser, or API key needed (runner/capture/judge are injected fakes).
"""

from __future__ import annotations

from packages.web.blocks_composer import plan_composition
from packages.web.design_loop import RevisionBrief
from packages.web.design_studio import (
    VisualScore,
    WebsiteDesignRequest,
    build_design_studio_packet,
)
from packages.web.design_system import synthesize_design_system
from packages.web.premium_build import apply_brief, build_premium_site, run_premium_loop


def _packet(category: str = "auto repair", concept_palette: str = ""):
    return build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="TrueLine",
            business_category=category,
            audience="local drivers",
            goal="book more service appointments",
            evidence=["20 years in business", "ASE-certified technicians"],
            concept_palette=concept_palette,
        )
    )


def _scores(values: dict[str, int]) -> list[VisualScore]:
    return [VisualScore(cat, v, "note") for cat, v in values.items()]


WEAK = {
    "visual_thesis": 2, "hero_impact": 3, "imagery_art_direction": 2,
    "typography": 3, "layout_composition": 3, "copy_specificity": 4,
}
STRONG = {
    "visual_thesis": 5, "hero_impact": 5, "imagery_art_direction": 4,
    "typography": 4, "layout_composition": 4, "copy_specificity": 5,
}


# --------------------------------------------------------------------------- #
# apply_brief — revision is real
# --------------------------------------------------------------------------- #
def test_apply_brief_noop_when_nothing_failed() -> None:
    packet = _packet()
    brief = RevisionBrief(failing_categories=[], notes={}, overall=80)
    assert apply_brief(packet, brief) is packet


def test_apply_brief_rotates_archetype_on_structural_fail() -> None:
    packet = _packet()  # "auto repair" → classic-custom
    brief = RevisionBrief(failing_categories=["layout_composition"], notes={}, overall=50)
    revised = apply_brief(packet, brief, attempt=0)
    assert revised.archetype != packet.archetype
    # The change is structural, not cosmetic: the composed block plan differs.
    assert plan_composition(revised).to_dict() != plan_composition(packet).to_dict()


def test_apply_brief_rotates_palette_on_imagery_fail() -> None:
    packet = _packet()
    brief = RevisionBrief(failing_categories=["imagery_art_direction"], notes={}, overall=50)
    revised = apply_brief(packet, brief, attempt=1)
    assert revised.concept_palette.startswith("#")
    # A palette change re-themes the synthesized role tokens.
    assert synthesize_design_system(revised).roles != synthesize_design_system(packet).roles


def test_apply_brief_escalates_with_attempt() -> None:
    packet = _packet()
    brief = RevisionBrief(failing_categories=["hero_impact"], notes={}, overall=50)
    first = apply_brief(packet, brief, attempt=0).concept_palette
    second = apply_brief(packet, brief, attempt=1).concept_palette
    assert first != second  # successive revisions explore different hues


# --------------------------------------------------------------------------- #
# build_premium_site — the premium path that was never wired
# --------------------------------------------------------------------------- #
def test_build_premium_site_composes_premium_stack(tmp_path) -> None:
    packet = _packet("plumbing")  # service-area-cinematic (dark, cinematic)
    calls: list[list[str]] = []

    def runner(args, cwd):
        calls.append(list(args))
        return (0, "ok", "")

    project = tmp_path / "site"
    result = build_premium_site(packet, project, runner=runner)

    assert result.succeeded
    # The PREMIUM template was instantiated (its block components exist).
    assert (project / "src" / "blocks" / "CinematicHero.astro").exists()
    # The theme layer is the synthesized token set, not the baseline.
    css = (project / "src" / "styles" / "design-system.css").read_text()
    assert "--accent" in css and "--display-font" in css
    # The page is composed from blocks, not the {{TOKEN}} scaffold baseline.
    index = (project / "src" / "pages" / "index.astro").read_text()
    assert "CinematicHero" in index
    assert "{{SITE_NAME}}" not in index
    # The real build steps ran (through the injected runner).
    assert ["npm", "ci"] in calls and ["npm", "run", "build"] in calls


def test_build_premium_site_can_skip_npm(tmp_path) -> None:
    packet = _packet("nail salon")
    project = tmp_path / "site"
    result = build_premium_site(packet, project, run_build=False)
    assert result.succeeded
    assert (project / "src" / "pages" / "index.astro").exists()
    assert result.dist_dir == project / "dist"


# --------------------------------------------------------------------------- #
# run_premium_loop — the loop closes end to end (with fakes)
# --------------------------------------------------------------------------- #
def test_run_premium_loop_closes_and_checkpoints(tmp_path) -> None:
    packet = _packet("plumbing")

    def runner(args, cwd):
        return (0, "", "")

    seq = [_scores(WEAK), _scores(STRONG)]  # fail once → revise → pass
    counter = [0]

    def judge(_shots):
        s = seq[min(counter[0], len(seq) - 1)]
        counter[0] += 1
        return s

    def capture():
        return {"desktop": "d.png", "mobile": "m.png"}

    project = tmp_path / "site"
    result = run_premium_loop(
        packet,
        project,
        runner=runner,
        capture=capture,
        judge=judge,
        target=tmp_path,
        max_iters=4,
    )

    assert result.passed is True
    assert result.needs_signoff is True  # never auto-ships
    assert len(result.iterations) == 2
    # Checkpoint trail: one loop-log line per iteration + the best review persisted.
    log = (tmp_path / "design-studio" / "loop-log.jsonl").read_text().strip().splitlines()
    assert len(log) == 2
    assert (tmp_path / "design-studio" / "visual-review.json").exists()


def test_run_premium_loop_halts_to_best_when_build_cannot_pass(tmp_path) -> None:
    packet = _packet("auto repair")

    def runner(args, cwd):
        return (0, "", "")

    def judge(_shots):
        return _scores(WEAK)  # the deterministic thin build never clears the gate

    def capture():
        return {"desktop": "d.png", "mobile": "m.png"}

    result = run_premium_loop(
        packet,
        tmp_path / "site",
        runner=runner,
        capture=capture,
        judge=judge,
        target=tmp_path,
        max_iters=5,
        no_improve_patience=2,
    )
    # It halts (plateau) and surfaces the best build rather than spinning forever.
    assert result.passed is False
    assert result.halted_reason == "plateau"
    assert result.best is not None
