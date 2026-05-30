"""Analyst layer — turning an evidenced opportunity into the twelve signals.

Scoring the twelve signals is the one genuinely *analytical* step in the loop.
This repo is agent-driven (the platform provides typed I/O; an agent does the
judgement), so the production analyst is an **agent session** that reads an
``OpportunityRecord`` and writes an ``OpportunitySignals`` — it plugs in through
the ``SignalProvider`` callable the scoring pass already accepts. There is no
hardcoded model call here, by design.

For runs without an agent in the loop (demos, smoke tests, a cheap first pass
before a human review), ``HeuristicSignalProvider`` derives a **coarse, fully
deterministic** estimate from the evidence already attached to the record. It is
explicitly a baseline, not a substitute for analyst judgement: treat its output
as a hypothesis to confirm, never as a reason to skip the human gate.
"""

from __future__ import annotations

import json
import re

from packages.discovery.connectors._pain import looks_like_pain
from packages.schemas.opportunity import (
    SIGNAL_KEYS,
    ComplianceFlag,
    EvidenceKind,
    OpportunityRecord,
    OpportunitySignals,
)
from packages.tools.llm.client import ChatModel


def _clamp(value: float) -> float:
    return max(0.0, min(10.0, value))


def heuristic_signals(record: OpportunityRecord) -> OpportunitySignals | None:
    """A deterministic, coarse first-pass scoring from the record's evidence.

    Returns ``None`` when there is no evidence to reason from — the honest answer
    is "send it back for research", not a guessed score.
    """
    evidence = record.evidence
    if not evidence:
        return None

    kinds = {link.kind for link in evidence}

    def has(kind: EvidenceKind) -> bool:
        return kind in kinds

    evidence_count = len(evidence)
    distinct = max(1, record.distinct_sources())
    text = f"{record.title} {record.problem}".lower()
    flags = set(record.compliance_flags)

    # risk is inverted (10 = low risk). Hard-blocking flags drive it low so the
    # scorecard's hard gate trips instead of silently passing.
    if ComplianceFlag.TOS_RISK in flags or ComplianceFlag.REGULATED_DATA in flags:
        risk = 2.0
    elif ComplianceFlag.PII in flags or ComplianceFlag.SCRAPING_REQUIRED in flags:
        risk = 5.0
    elif ComplianceFlag.NEEDS_REVIEW in flags:
        risk = 6.0
    else:
        risk = 8.0

    pays = has(EvidenceKind.WILLINGNESS_TO_PAY)
    complaint = has(EvidenceKind.COMPLAINT)
    workaround = has(EvidenceKind.WORKAROUND)
    return OpportunitySignals(
        search_volume=_clamp(3 + evidence_count),
        buyer_intent=_clamp(4 + 2 * has(EvidenceKind.REQUEST) + 2 * pays),
        urgency=_clamp(3 + 2 * complaint + workaround + looks_like_pain(text)),
        willingness_to_pay=_clamp(3 + 3 * pays + has(EvidenceKind.REVIEW)),
        competition_weakness=_clamp(5 + 2 * has(EvidenceKind.COMPETITOR)),
        community_pain=_clamp(3 + 2 * distinct),
        repeated_workflow=_clamp(4 + 3 * has(EvidenceKind.WORKAROUND) + ("manual" in text)),
        # Distribution and the build/margin signals can't be inferred from a
        # signal alone — leave neutral mid-values for an analyst to refine. Kept
        # >= 1 so a draft doesn't auto-trip the no-distribution hard gate before
        # anyone has looked at it.
        distribution_path=4.0,
        expected_margin=6.0,
        build_feasibility=6.0,
        defensibility=3.0,
        risk=risk,
    )


class HeuristicSignalProvider:
    """A ``SignalProvider`` implementation wrapping :func:`heuristic_signals`.

    Use it to make the scoring pass runnable end to end without an agent:

        ScoringPass(inbox, signal_provider=HeuristicSignalProvider()).run()
    """

    def __call__(self, record: OpportunityRecord) -> OpportunitySignals | None:
        return heuristic_signals(record)


# ── LLM-backed analyst (E1) ─────────────────────────────────────────────────────
#
# The production analyst: hand the model the evidence and ask it to score the
# twelve signals. The contract with the model is deliberately strict and
# machine-checkable so a free-text model produces structured, parseable output.
#
# JSON contract the model must follow:
#   {"signals": {"search_volume": 0-10, ..., "risk": 0-10}}
#   or, when there isn't enough evidence to score honestly:
#   {"insufficient_evidence": true}
#
# Heuristics / guardrails encoded here:
#   * temperature 0 — we want a calibrated judgement, not creativity.
#   * `risk` is INVERTED (10 = low risk); the prompt repeats this because it is
#     the most common scoring mistake.
#   * STRICT parsing — every one of the twelve keys must be present and numeric,
#     or we return None and let the wedge go back for another pass. A partial
#     score (e.g. a silently-missing distribution_path defaulting to 0) would
#     trip hard gates for the wrong reason, so "incomplete == no score".
#   * values are clamped to 0..10 defensively even though the prompt asks for it.
#   * no evidence => we don't even call the model (cheaper, and honest).
#   * the provider never raises on bad model output — it returns None, because
#     its contract is ``OpportunityRecord -> OpportunitySignals | None``. Hard
#     transport errors from the model client still propagate (see ModelError).

SIGNAL_SYSTEM_PROMPT = """\
You are a market analyst scoring a product opportunity against a fixed scorecard.
Score each of the TWELVE signals from 0 to 10 (10 = strongest evidence). Be
calibrated and honest: a 7 means strong evidence, not optimism.

Signals (use these exact keys):
- search_volume: 0 = nobody searches; 10 = high, growing search demand.
- buyer_intent: 0 = curiosity only; 10 = searching with wallet out ("pricing", "alternative to").
- urgency: 0 = nice-to-have someday; 10 = painful now, people hacking workarounds today.
- willingness_to_pay: 0 = expect it free; 10 = already paying for inferior tools.
- competition_weakness: 0 = strong, loved incumbents; 10 = incumbents exist but users complain.
- community_pain: 0 = quiet; 10 = repeated, specific complaints across communities.
- repeated_workflow: 0 = one-off; 10 = a recurring manual task many people do.
- distribution_path: 0 = no obvious channel; 10 = a clear, allowed channel reachable cheaply.
- expected_margin: 0 = thin/heavy ops; 10 = software-like margins.
- build_feasibility: 0 = needs a moonshot; 10 = buildable MVP in days-weeks.
- defensibility: 0 = trivially cloned; 10 = data/integration/distribution moat possible.
- risk: INVERTED. 10 = clean/low regulatory & ToS risk; 0 = high risk. Do NOT flip this.

Rules:
- Base every score ONLY on the evidence provided. Do not invent facts.
- If the evidence is too thin to score honestly, return {"insufficient_evidence": true}.
- Otherwise return STRICT JSON, no prose, no markdown fences:
  {"signals": {"search_volume": <int>, ... all twelve keys ...}}
"""


def _build_user_prompt(record: OpportunityRecord) -> str:
    lines = [
        f"Title: {record.title}",
        f"Problem: {record.problem}",
        f"Audience: {record.audience}",
    ]
    if record.compliance_flags:
        lines.append("Compliance flags: " + ", ".join(f.value for f in record.compliance_flags))
    if record.competitors:
        lines.append("Competitors:")
        for competitor in record.competitors:
            detail = ", ".join(p for p in (competitor.pricing, competitor.weakness) if p)
            lines.append(f"  - {competitor.name}" + (f" ({detail})" if detail else ""))
    lines.append("Evidence:")
    for link in record.evidence:
        quote = link.quote or ""
        lines.append(f"  - [{link.kind.value}] {quote} <{link.url}>")
    return "\n".join(lines)


def _extract_json(text: str) -> dict | None:
    """Best-effort: parse the model output as JSON, tolerating code fences and
    surrounding prose by falling back to the first balanced {...} object."""
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(stripped[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def parse_signal_response(raw: str) -> OpportunitySignals | None:
    """Parse a model response into signals, or None if it can't be scored.

    None is returned for: an explicit ``insufficient_evidence`` flag, unparseable
    output, or an incomplete signal set (any of the twelve keys missing or
    non-numeric). See the module heuristics note for why incomplete == no score.
    """
    obj = _extract_json(raw)
    if obj is None or obj.get("insufficient_evidence") is True:
        return None
    signal_obj = obj.get("signals", obj)
    if not isinstance(signal_obj, dict):
        return None
    values: dict[str, float] = {}
    for key in SIGNAL_KEYS:
        value = signal_obj.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None  # incomplete or wrong-typed => don't score on a guess
        values[key] = _clamp(float(value))
    return OpportunitySignals(**values)


class LLMSignalProvider:
    """A ``SignalProvider`` that scores the twelve signals with a chat model.

        provider = LLMSignalProvider(OpenRouterClient())
        ScoringPass(inbox, signal_provider=provider).run()

    Returns None (so the scoring pass leaves the wedge in the inbox) when there
    is no evidence, when the model signals insufficient evidence, or when the
    response can't be parsed into a complete signal set.
    """

    def __init__(self, model: ChatModel, *, temperature: float = 0.0) -> None:
        self._model = model
        self._temperature = temperature

    def __call__(self, record: OpportunityRecord) -> OpportunitySignals | None:
        if not record.evidence:
            return None
        raw = self._model.complete(
            SIGNAL_SYSTEM_PROMPT, _build_user_prompt(record), temperature=self._temperature
        )
        return parse_signal_response(raw)
