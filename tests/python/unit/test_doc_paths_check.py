from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("reference", "expected_exit"),
    [("build/", 0), ("packages/missing.py", 1), ("build/missing-report.json", 1)],
)
def test_doc_paths_distinguishes_generated_directory_from_missing_source(
    tmp_path: Path, reference: str, expected_exit: int,
) -> None:
    """A pristine clone has no reports yet; missing source still fails."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for relative in ("README.md", "CLAUDE.md", "AGENTS.md", "docs/README.md", "docs/skills-index.md"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Fixture\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(f"Output: `{reference}`\n", encoding="utf-8")
    script = Path(__file__).resolve().parents[3] / "scripts/ci/check_doc_paths.sh"
    result = subprocess.run(["bash", str(script)], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert not (tmp_path / "build").exists()
