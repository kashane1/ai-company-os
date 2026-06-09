"""Block normalizer — raw harvested design → a tokenized Astro block.

External tools (Stitch) and raw LLM output arrive as hardcoded HTML/Tailwind with
their own colors, spacing, and fonts. That output cannot drop into the premium stack:
it ignores the synthesized design system and trips the rubric's `ai_house_style`
penalty. This module is the adapter — it rewrites a raw design into an Astro block
that (a) takes the slot's single `data` prop and (b) styles itself purely from the
design-system CSS custom properties — so the synthesizer's palette/type still drive
it and it composes like a builtin.

Claude does the rewrite (via the repo's `ChatModel`), injected so this is testable
without a key. `tokenization_issues()` is a cheap, deterministic guard: it flags
hardcoded colors / px sizes / Tailwind classes that should be tokens, so the
normalizer can repair-loop and the golden test can detect a flattened adapter
without a live judge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from packages.tools.llm.client import ChatModel

# The contract every normalized block must satisfy. Kept terse and imperative.
_SYSTEM = """You convert a raw web UI design into ONE Astro block component for a \
premium, hand-built site. Output ONLY the .astro file in a single ```astro code block.

Hard rules:
- It is a FRAGMENT: a single <section> (or <header>/<article>), NO <html>/<head>/<body>.
- It takes exactly one prop: in the frontmatter `const { data } = Astro.props;` and \
reads its fields (see the slot's data shape). Never invent new top-level props.
- Style ONLY with the design system's CSS custom properties and global.css utility \
classes. Use var(--color-*), var(--space-*), var(--step-*)/var(--display-font) etc. \
NEVER hardcode hex/rgb colors, NEVER hardcode px font-sizes, NEVER use Tailwind/utility \
CSS frameworks or `class="...bg- text- p-4..."` utility strings.
- Translate the raw design's STRUCTURE and idea — do not copy its literal colors, \
fonts, or copy. Rebuild it on our tokens.
- Accessible (semantic tags, alt text from data) and responsive (no fixed pixel widths).
"""

_FENCE = re.compile(r"```(?:astro|html)?\s*(.*?)```", re.DOTALL)
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_RGB_FUNC = re.compile(r"\brgba?\(", re.IGNORECASE)  # rgb( / rgba(
_PX_FONT = re.compile(r"font-size\s*:\s*\d+(\.\d+)?px", re.IGNORECASE)
_TAILWIND = re.compile(
    r'class\s*=\s*"[^"]*\b('
    r"bg-[a-z]|text-(?:xs|sm|base|lg|xl|\d)|p[xytrbl]?-\d|m[xytrbl]?-\d|"
    r"flex|grid-cols-\d|rounded-|shadow-|gap-\d|w-\d|h-\d"
    r')[^"]*"',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NormalizedBlock:
    component: str
    astro: str
    issues: tuple[str, ...] = ()


def extract_astro(text: str) -> str:
    """Pull the .astro source out of a model reply (tolerating fences/prose)."""

    match = _FENCE.search(text)
    return (match.group(1) if match else text).strip()


def tokenization_issues(astro: str) -> list[str]:
    """Hardcoded values that should be design-system tokens (empty = clean).

    A deterministic proxy for "did the adapter actually tokenize?" — used to repair
    the normalizer and to catch a flattened rewrite without spending a judge call.
    """

    issues: list[str] = []
    if _HEX.search(astro):
        issues.append("hardcoded hex color (use var(--color-*))")
    if _RGB_FUNC.search(astro):
        issues.append("hardcoded rgb()/rgba() color (use var(--color-*))")
    if _PX_FONT.search(astro):
        issues.append("hardcoded px font-size (use var(--step-*))")
    if _TAILWIND.search(astro):
        issues.append("Tailwind/utility class strings (use tokenized CSS)")
    if "Astro.props" not in astro:
        issues.append("does not read Astro.props (must take a single `data` prop)")
    return issues


def normalize_block(
    raw: str,
    *,
    slot: str,
    component: str,
    model: ChatModel,
    design_system: str = "",
    data_shape: str = "",
    repair: bool = True,
) -> NormalizedBlock:
    """Rewrite a raw design into a tokenized Astro block for ``slot``.

    If the first rewrite still has tokenization issues and ``repair`` is set, the
    issues are fed back for one corrective pass — small, bounded, and key-cheap.
    """

    user = (
        f"Target slot: {slot}\nAstro component name: {component}\n"
        f"Slot data shape (the fields `data` will have):\n{data_shape or '(use sensible fields)'}\n\n"
        f"Available design tokens (CSS custom properties):\n{design_system or '(standard --color-*, --space-*, --step-*, --display-font, --body-font)'}\n\n"
        f"RAW DESIGN to translate (rebuild it on our tokens — do not copy its literals):\n{raw}"
    )
    astro = extract_astro(model.complete(_SYSTEM, user))
    issues = tokenization_issues(astro)
    if issues and repair:
        repair_user = (
            f"{user}\n\nYour previous output had these problems — fix ALL of them and "
            f"return the corrected .astro only:\n- " + "\n- ".join(issues)
            + f"\n\nPrevious output:\n```astro\n{astro}\n```"
        )
        astro = extract_astro(model.complete(_SYSTEM, repair_user))
        issues = tokenization_issues(astro)
    return NormalizedBlock(component=component, astro=astro, issues=tuple(issues))
