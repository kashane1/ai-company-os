"""Phase 2.3 — tests for packages/tools/product_artifacts/gtm_chain.py."""

from __future__ import annotations

from pathlib import Path

from packages.tools.product_artifacts.gtm_chain import (
    MIN_BACKLOG_ITEMS,
    PERFORMANCE_LOG_HEADER,
    REQUIRED_FILES,
    validate_gtm_chain,
)


def _write_minimal_chain(gtm_dir: Path) -> None:
    gtm_dir.mkdir(parents=True, exist_ok=True)
    (gtm_dir / "voice.md").write_text("voice\n")
    (gtm_dir / "campaign-calendar.md").write_text("cal\n")
    backlog = "\n".join(f"{i}. item" for i in range(1, MIN_BACKLOG_ITEMS + 1))
    (gtm_dir / "content-backlog.md").write_text(backlog + "\n")
    (gtm_dir / "hook-library.md").write_text("- hook\n")
    (gtm_dir / "hashtag-strategy.md").write_text("tags\n")
    (gtm_dir / "performance-log.md").write_text(PERFORMANCE_LOG_HEADER + "\n")


def test_happy_path(tmp_path):
    product_dir = tmp_path / "docs" / "products" / "catchbook" / "gtm"
    _write_minimal_chain(product_dir)
    result = validate_gtm_chain("catchbook", tmp_path)
    assert result.ok, result
    assert result.backlog_count == MIN_BACKLOG_ITEMS


def test_missing_file_fails(tmp_path):
    product_dir = tmp_path / "docs" / "products" / "catchbook" / "gtm"
    _write_minimal_chain(product_dir)
    (product_dir / "voice.md").unlink()
    result = validate_gtm_chain("catchbook", tmp_path)
    assert not result.ok
    assert "voice.md" in result.missing


def test_short_backlog_fails(tmp_path):
    product_dir = tmp_path / "docs" / "products" / "catchbook" / "gtm"
    _write_minimal_chain(product_dir)
    (product_dir / "content-backlog.md").write_text("1. one\n2. two\n")
    result = validate_gtm_chain("catchbook", tmp_path)
    assert not result.ok
    assert any("content-backlog" in f for f in result.failures)


def test_real_catchbook_chain_valid():
    """The real catchbook artifacts created in Phase 2.3 should validate."""
    repo = Path(__file__).resolve().parents[3]
    result = validate_gtm_chain("catchbook", repo)
    assert result.ok, result
    assert set(REQUIRED_FILES).isdisjoint(result.missing)
