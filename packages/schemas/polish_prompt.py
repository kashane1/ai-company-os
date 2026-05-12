"""Polish-prompt schema — the producer-consumer contract for backlog skills.

Audit skills (``simulator-polish-recon``, ``premium-feel-audit``,
``pro-value-audit``, future siblings) emit backlog files containing prompts
in a fixed 9-field shape. ``simulator-driven-polish`` consumes those prompts
unchanged.

This module exports the field set used by producer fixtures'
``required_input_fields`` group label and by
``tests/python/unit/test_polish_prompt_schema.py``.

Drift mitigation: ``shared/recon-scaffolding.md`` documents the same nine
fields in prose. The markdown is *documentation*; this module is *contract*.
If they ever disagree, this module wins.

See ``docs/plans/2026-05-12-feat-premium-and-pro-value-audit-skills-plan.md``
deepening review §6 for the architecture rationale.
"""

from __future__ import annotations


#: Ordered tuple of the nine binding field names every emitted polish
#: prompt must carry. Order matches the canonical per-prompt template in
#: ``skills/canonical/shared/recon-scaffolding.md``.
POLISH_PROMPT_FIELDS: tuple[str, ...] = (
    "Tier",
    "Evidence",
    "Idea",
    "Surfaces",
    "Fixture knobs",
    "Prior context",
    "Success criteria",
    "Iteration cap",
    "Final computer-use checkpoint",
)


#: Modes the consumer (``simulator-driven-polish``) accepts.
#: A prompt's ``Tier`` value drives consumer behaviour; ``Mode`` lives
#: alongside the prompt block as the mode the *producer* recommends.
POLISH_PROMPT_MODES: tuple[str, ...] = (
    "fix-list",
    "freeform-polish",
    "reference-match",
    "vision-driven",
)
