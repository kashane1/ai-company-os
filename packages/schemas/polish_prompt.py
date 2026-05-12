"""Polish-prompt schema — the producer-consumer contract for backlog skills.

Audit skills (``simulator-polish-recon``, ``premium-feel-audit``,
``pro-value-audit``, future siblings) emit backlog files containing prompts
in a fixed 9-field shape. ``simulator-driven-polish`` consumes those prompts
unchanged. This module is the **mechanical** contract surface: producer
fixtures assert that the canonical body lists every field in
``POLISH_PROMPT_FIELDS``, and the consumer adapter cites this module so
edits to the schema fail loudly rather than silently.

Drift mitigation: ``shared/recon-scaffolding.md`` documents the same nine
fields in prose. The markdown is *documentation*; this module is *contract*.
If they ever disagree, this module wins.

See ``docs/plans/2026-05-12-feat-premium-and-pro-value-audit-skills-plan.md``
deepening review §6 for the architecture rationale.
"""

from __future__ import annotations

from dataclasses import dataclass


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


@dataclass(frozen=True)
class PolishPrompt:
    """Typed representation of an emitted polish-backlog prompt.

    The audit skills produce these as markdown blocks (one per backlog
    entry); the consumer reads them as markdown. This dataclass exists so
    that tests, fixtures, and future runtime parsers share one source of
    truth on the field set.

    Fields use snake_case for Python ergonomics; the canonical markdown
    template uses Title Case with spaces (see ``POLISH_PROMPT_FIELDS``).
    """

    tier: str
    evidence: str
    idea: str
    surfaces: str
    fixture_knobs: str
    prior_context: str
    success_criteria: str
    iteration_cap: int
    final_computer_use_checkpoint: str  # "yes" | "no" + one-line reason

    def to_markdown(self) -> str:
        """Render the prompt in the canonical 9-field markdown template."""
        return (
            f"> **Tier:** {self.tier}\n>\n"
            f"> **Evidence:** {self.evidence}\n>\n"
            f"> **Idea:** {self.idea}\n>\n"
            f"> **Surfaces:** {self.surfaces}\n>\n"
            f"> **Fixture knobs:** {self.fixture_knobs}\n>\n"
            f"> **Prior context:** {self.prior_context}\n>\n"
            f"> **Success criteria:** {self.success_criteria}\n>\n"
            f"> **Iteration cap:** {self.iteration_cap}\n>\n"
            f"> **Final computer-use checkpoint:** "
            f"{self.final_computer_use_checkpoint}"
        )
