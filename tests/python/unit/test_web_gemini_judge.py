"""Tests for the Gemini-vision judge response parser (design engine Phase 6).

The live API call needs a key, but the PARSER contract — extracting valid
0-5 category scores from the model's reply, tolerating code fences/prose, and
rejecting incomplete responses — must hold deterministically.
"""

from __future__ import annotations

import pytest

from packages.web.gemini_judge import RUBRIC_CATEGORIES, parse_judge_response

_FULL = (
    '[{"category":"visual_thesis","score":4,"note":"clear concept"},'
    '{"category":"hero_impact","score":5,"note":"strong"},'
    '{"category":"imagery_art_direction","score":4,"note":"cohesive"},'
    '{"category":"typography","score":4,"note":"distinctive"},'
    '{"category":"layout_composition","score":4,"note":"varied"},'
    '{"category":"copy_specificity","score":5,"note":"grounded"}]'
)


def test_parses_clean_json_array() -> None:
    scores = parse_judge_response(_FULL)
    assert {s.category for s in scores} == set(RUBRIC_CATEGORIES)
    assert next(s for s in scores if s.category == "hero_impact").score == 5


def test_tolerates_code_fences_and_prose() -> None:
    wrapped = "Here are my scores:\n```json\n" + _FULL + "\n```\nHope that helps."
    scores = parse_judge_response(wrapped)
    assert len(scores) == 6


def test_rejects_response_missing_categories() -> None:
    partial = '[{"category":"visual_thesis","score":4,"note":"x"}]'
    with pytest.raises(ValueError, match="omitted categories"):
        parse_judge_response(partial)


def test_rejects_non_json() -> None:
    with pytest.raises(ValueError, match="no JSON array"):
        parse_judge_response("I cannot score this.")


def test_out_of_range_score_is_rejected_by_visualscore() -> None:
    bad = _FULL.replace('"score":4,"note":"clear concept"', '"score":9,"note":"x"')
    with pytest.raises(ValueError):
        parse_judge_response(bad)
