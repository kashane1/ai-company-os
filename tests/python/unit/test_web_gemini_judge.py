"""Tests for the Gemini-vision judge (design engine Phase 6 / v3).

The live API call needs a key, but the PARSER contract — extracting valid 0-5
category scores from the model's reply, tolerating code fences/prose, and rejecting
incomplete responses — must hold deterministically. v3 also locks: rubric-anchor
injection into the prompt, and the N-sample median that damps single-call variance.
"""

from __future__ import annotations

import json

import pytest

from packages.web.design_studio import RUBRIC_CATEGORIES, VisualScore
from packages.web.gemini_judge import _prompt, median_scores, parse_judge_response


def _full_json(scores: dict[str, int] | None = None) -> str:
    scores = scores or {c: 4 for c in RUBRIC_CATEGORIES}
    return json.dumps([{"category": c, "score": s, "note": "n"} for c, s in scores.items()])


def test_parses_clean_json_array() -> None:
    values = {**{c: 4 for c in RUBRIC_CATEGORIES}, "hero_impact": 5}
    scores = parse_judge_response(_full_json(values))
    assert {s.category for s in scores} == set(RUBRIC_CATEGORIES)
    assert next(s for s in scores if s.category == "hero_impact").score == 5


def test_tolerates_code_fences_and_prose() -> None:
    wrapped = "Here are my scores:\n```json\n" + _full_json() + "\n```\nHope that helps."
    scores = parse_judge_response(wrapped)
    assert len(scores) == len(RUBRIC_CATEGORIES)


def test_rejects_response_missing_categories() -> None:
    partial = '[{"category":"visual_thesis","score":4,"note":"x"}]'
    with pytest.raises(ValueError, match="omitted categories"):
        parse_judge_response(partial)


def test_rejects_non_json() -> None:
    with pytest.raises(ValueError, match="no JSON array"):
        parse_judge_response("I cannot score this.")


def test_out_of_range_score_is_rejected_by_visualscore() -> None:
    bad = _full_json({**{c: 4 for c in RUBRIC_CATEGORIES}, "typography": 9})
    with pytest.raises(ValueError):
        parse_judge_response(bad)


def test_rubric_includes_motion_and_anti_tell_dimensions() -> None:
    # v3 added the dimensions the v2 judge was blind to.
    for dim in ("motion_quality", "signature_moment", "conversion_strength", "ai_house_style"):
        assert dim in RUBRIC_CATEGORIES


def test_prompt_injects_the_repo_rubric_anchors() -> None:
    # The judge must grade against the repo's rubric, not its own taste — so the
    # rubric file's anchors are embedded in the prompt.
    prompt = _prompt()
    assert "RUBRIC" in prompt
    assert "ai_house_style" in prompt
    assert "five-figure" in prompt.lower()
    # A distinctive anchor phrase from visual_rubric.md should be present.
    assert "scroll choreography" in prompt.lower() or "scroll frame" in prompt.lower()


def test_median_scores_takes_per_category_median() -> None:
    def sample(values: dict[str, int]) -> list[VisualScore]:
        base = {c: 4 for c in RUBRIC_CATEGORIES}
        base.update(values)
        return [VisualScore(c, s, "n") for c, s in base.items()]

    runs = [sample({"hero_impact": 2}), sample({"hero_impact": 4}), sample({"hero_impact": 5})]
    merged = {s.category: s.score for s in median_scores(runs)}
    assert merged["hero_impact"] == 4  # median of 2,4,5
    assert merged["typography"] == 4  # all 4
    assert {s.category for s in median_scores(runs)} == set(RUBRIC_CATEGORIES)


def test_extract_json_array_is_tolerant() -> None:
    from packages.web.gemini_judge import _extract_json_array

    assert _extract_json_array('prose [{"type":"overlap"}] more') == [{"type": "overlap"}]
    assert _extract_json_array("no array here") is None
    assert _extract_json_array("[broken json") is None


def test_high_severity_defects_filters() -> None:
    from packages.web.gemini_judge import high_severity_defects

    defects = [
        {"type": "overlap", "severity": "high"},
        {"type": "minor", "severity": "low"},
    ]
    assert high_severity_defects(defects) == [{"type": "overlap", "severity": "high"}]


def test_one_judgment_retries_past_a_malformed_response(monkeypatch) -> None:
    # The model sometimes returns invalid JSON (an unescaped quote in a note); one bad
    # response must not crash the loop — retry re-samples valid JSON.
    import packages.web.gemini_judge as gj

    bad = '[{"category":"visual_thesis","score":4,"note":"he said "hi""}]'  # invalid JSON
    good = _full_json()
    responses = iter([bad, good])
    monkeypatch.setattr(gj, "_call_gemini", lambda parts, key: next(responses))
    scores = gj._one_judgment([], "key", attempts=3)
    assert {s.category for s in scores} == set(RUBRIC_CATEGORIES)


def test_one_judgment_raises_after_exhausting_retries(monkeypatch) -> None:
    import packages.web.gemini_judge as gj
    import pytest as _pytest

    monkeypatch.setattr(gj, "_call_gemini", lambda parts, key: "not json at all")
    with _pytest.raises(ValueError, match="unparseable"):
        gj._one_judgment([], "key", attempts=2)


def test_inspect_defects_fails_open_without_key(monkeypatch) -> None:
    import packages.web.gemini_judge as gj

    monkeypatch.setattr(gj, "get_api_key", lambda _: None)
    assert gj.inspect_defects({"desktop": "/x.png"}) == []
