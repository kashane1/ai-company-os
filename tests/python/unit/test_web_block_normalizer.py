"""Tests for the block normalizer (raw design -> tokenized Astro block).

The model is injected (a fake ChatModel), so these run with no key. They lock: the
.astro is extracted from a fenced reply, the tokenization guard flags raw Tailwind /
hardcoded values, and the repair loop re-prompts once when the first rewrite isn't
clean.
"""

from __future__ import annotations

from packages.web.block_normalizer import (
    NormalizedBlock,
    extract_astro,
    normalize_block,
    tokenization_issues,
)

CLEAN_ASTRO = """---
const { data } = Astro.props;
---
<section class="section" style="background:var(--color-canvas);padding:var(--space-l)">
  <h2 style="font-family:var(--display-font)">{data.headline}</h2>
</section>
"""

RAW_TAILWIND = """<section class="bg-indigo-600 p-8 text-white">
  <h2 class="text-4xl font-bold">Hero</h2>
</section>
"""


class FakeModel:
    """A ChatModel that returns queued replies and records the prompts it saw."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        self.calls.append((system, user))
        return self._replies.pop(0)


# --------------------------------------------------------------------------- #
# guards
# --------------------------------------------------------------------------- #
def test_extract_astro_strips_fences() -> None:
    assert extract_astro(f"sure!\n```astro\n{CLEAN_ASTRO}```\nhope that helps") == CLEAN_ASTRO.strip()


def test_tokenization_issues_clean_block() -> None:
    assert tokenization_issues(CLEAN_ASTRO) == []


def test_tokenization_issues_flags_raw_tailwind_and_missing_props() -> None:
    issues = tokenization_issues(RAW_TAILWIND)
    assert any("Tailwind" in i for i in issues)
    assert any("Astro.props" in i for i in issues)


def test_tokenization_issues_flags_hardcoded_color_and_px() -> None:
    astro = "---\nconst { data } = Astro.props;\n---\n<h2 style='color:#ff0044;font-size:42px'>x</h2>"
    issues = tokenization_issues(astro)
    assert any("hex" in i for i in issues)
    assert any("px font-size" in i for i in issues)


# --------------------------------------------------------------------------- #
# normalize_block
# --------------------------------------------------------------------------- #
def test_normalize_returns_clean_block_in_one_pass() -> None:
    model = FakeModel([f"```astro\n{CLEAN_ASTRO}```"])
    result = normalize_block(RAW_TAILWIND, slot="hero", component="GenHero", model=model)
    assert isinstance(result, NormalizedBlock)
    assert result.component == "GenHero"
    assert result.issues == ()
    assert len(model.calls) == 1
    # the raw design + slot were handed to the model
    assert "RAW DESIGN" in model.calls[0][1]
    assert "hero" in model.calls[0][1]


def test_normalize_repairs_once_when_first_output_is_dirty() -> None:
    # first reply is still Tailwind; repair pass returns a clean block
    model = FakeModel([f"```astro\n{RAW_TAILWIND}```", f"```astro\n{CLEAN_ASTRO}```"])
    result = normalize_block(RAW_TAILWIND, slot="hero", component="GenHero", model=model)
    assert result.issues == ()
    assert len(model.calls) == 2
    # the repair prompt names the problems to fix
    assert "fix ALL of them" in model.calls[1][1]


def test_normalize_reports_residual_issues_when_repair_fails() -> None:
    model = FakeModel([f"```astro\n{RAW_TAILWIND}```", f"```astro\n{RAW_TAILWIND}```"])
    result = normalize_block(RAW_TAILWIND, slot="hero", component="GenHero", model=model)
    assert result.issues  # still dirty -> surfaced, not hidden
