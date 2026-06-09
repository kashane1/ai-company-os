"""Tests for the deterministic composition/overlap gate.

These lock the geometry rules the vision judge structurally can't enforce: no two
full-bleed photo sections stacked, no section/text overlaps, no horizontal scroll.
"""

from __future__ import annotations

from packages.web.composition_gate import composition_defects, high_severity


def _sec(i, top, bottom, *, full=False, imgs=None, texts=None):
    return {
        "i": i, "cls": f"s{i}", "top": top, "bottom": bottom, "left": 0, "right": 1440,
        "w": 1440, "h": bottom - top, "fullBleed": full,
        "imgs": imgs or ([{"top": top, "bottom": bottom, "left": 0, "right": 1440}] if full else []),
        "texts": texts or [],
    }


def _geo(sections, **kw):
    return {"viewportWidth": 1440, "scrollWidth": 1440, "clientWidth": 1440,
            "hasHorizontalScroll": False, "sections": sections, **kw}


def test_clean_layout_has_no_defects() -> None:
    # hero (full-bleed) -> contained editorial -> full-bleed band -> cta: no stacking.
    geo = _geo([
        _sec(0, 0, 700, full=True),
        _sec(1, 700, 1100, full=False),
        _sec(2, 1100, 1700, full=True),
        _sec(3, 1700, 2100, full=False),
    ])
    assert composition_defects(geo) == []


def test_stacked_fullbleed_is_flagged_high() -> None:
    geo = _geo([
        _sec(0, 0, 700, full=True),
        _sec(1, 700, 1300, full=True),   # full-bleed directly after a full-bleed hero
        _sec(2, 1300, 1700, full=False),
    ])
    d = composition_defects(geo)
    assert any(x["type"] == "stacked_fullbleed" for x in d)
    assert high_severity(d)


def test_section_overlap_is_flagged_high() -> None:
    geo = _geo([
        _sec(0, 0, 720, full=False),
        _sec(1, 680, 1100, full=False),  # starts 40px before section 0 ends
    ])
    d = composition_defects(geo)
    assert any(x["type"] == "section_overlap" for x in d)


def test_text_over_foreign_section_image_is_flagged() -> None:
    # A text element in section 1 whose rect lands on section 0's image.
    geo = _geo([
        _sec(0, 0, 700, full=True, imgs=[{"top": 0, "bottom": 760, "left": 0, "right": 1440}]),
        _sec(1, 700, 1100, full=False,
             texts=[{"tag": "H2", "top": 710, "bottom": 750, "left": 80, "right": 600}]),
    ])
    d = composition_defects(geo)
    assert any(x["type"] == "text_foreign_image_overlap" for x in d)


def test_horizontal_overflow_flagged_medium() -> None:
    geo = _geo([_sec(0, 0, 700)], hasHorizontalScroll=True, scrollWidth=1600, clientWidth=1440)
    d = composition_defects(geo)
    assert any(x["type"] == "horizontal_overflow" and x["severity"] == "medium" for x in d)
    assert not high_severity(d)  # overflow alone shouldn't hard-fail


def test_same_section_text_over_its_own_image_is_fine() -> None:
    # The intentional pattern: a hero card's text over the hero's own full-bleed image.
    geo = _geo([
        _sec(0, 0, 700, full=True, imgs=[{"top": 0, "bottom": 700, "left": 0, "right": 1440}],
             texts=[{"tag": "H1", "top": 120, "bottom": 200, "left": 80, "right": 700}]),
        _sec(1, 700, 1100, full=False),
    ])
    assert composition_defects(geo) == []
