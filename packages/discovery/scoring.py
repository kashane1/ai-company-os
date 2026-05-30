"""Opportunity scoring — the math behind the scorecard.

Pure functions, no I/O — easy to test and to call from any worker. The weights
come from ``config/scoring.yaml`` (passed in, never hardcoded, so the monthly
retune in ``docs/founder/discovery-evals.md`` actually takes effect).

This module deliberately holds only the *numbers*. The *decision* — does an
opportunity advance to validation? — lives in
``packages/policies/discovery_gates.py`` because, per the repo's architecture
rules, policy is owned by ``packages/policies/``, not by tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from packages.schemas.opportunity import SIGNAL_KEYS, OpportunitySignals

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - pyyaml is a declared dependency
    yaml = None  # type: ignore


DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "scoring.yaml"


@dataclass(frozen=True)
class Thresholds:
    min_score_to_validate: float = 65.0
    min_confidence_to_validate: float = 0.6
    min_distribution_score: float = 1.0


@dataclass(frozen=True)
class HardGates:
    reject_if_risk_at_or_below: float = 2.0
    block_compliance_flags: tuple[str, ...] = ("tos-risk", "regulated-data")


@dataclass(frozen=True)
class ConfidenceModel:
    target_evidence: int = 5
    diversity_bonus: bool = True


@dataclass(frozen=True)
class ScoringConfig:
    weights: dict[str, float] = field(default_factory=dict)
    thresholds: Thresholds = field(default_factory=Thresholds)
    hard_gates: HardGates = field(default_factory=HardGates)
    confidence: ConfidenceModel = field(default_factory=ConfidenceModel)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_scoring_config(path: Path | None = None) -> ScoringConfig:
    """Load ``scoring.yaml`` into a typed config. Falls back to defaults for any
    missing section so a partial file still produces a usable config."""
    if yaml is None:  # pragma: no cover - guarded import
        raise RuntimeError("pyyaml is required to load scoring config")
    raw = yaml.safe_load(Path(path or DEFAULT_CONFIG_PATH).read_text()) or {}

    thresholds_raw = raw.get("thresholds", {}) or {}
    hard_raw = raw.get("hard_gates", {}) or {}
    conf_raw = raw.get("confidence", {}) or {}

    return ScoringConfig(
        weights={key: float(value) for key, value in (raw.get("weights", {}) or {}).items()},
        thresholds=Thresholds(
            min_score_to_validate=float(thresholds_raw.get("min_score_to_validate", 65)),
            min_confidence_to_validate=float(thresholds_raw.get("min_confidence_to_validate", 0.6)),
            min_distribution_score=float(thresholds_raw.get("min_distribution_score", 1)),
        ),
        hard_gates=HardGates(
            reject_if_risk_at_or_below=float(hard_raw.get("reject_if_risk_at_or_below", 2)),
            block_compliance_flags=tuple(
                str(flag) for flag in hard_raw.get("block_compliance_flags", []) or []
            ),
        ),
        confidence=ConfidenceModel(
            target_evidence=int(conf_raw.get("target_evidence", 5)),
            diversity_bonus=bool(conf_raw.get("diversity_bonus", True)),
        ),
    )


def compute_score(signals: OpportunitySignals, weights: dict[str, float]) -> float:
    """Weighted, normalized 0..100 score. Signals outside 0..10 are clamped."""
    weighted = 0.0
    total_weight = 0.0
    signal_map = signals.to_dict()
    for key in SIGNAL_KEYS:
        weight = float(weights.get(key, 0.0))
        value = _clamp(float(signal_map.get(key, 0.0) or 0.0), 0.0, 10.0)
        weighted += weight * value
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return (weighted / total_weight) * 10.0  # signals are 0..10, *10 -> 0..100


def compute_confidence(
    evidence_links: int,
    distinct_sources: int,
    model: ConfidenceModel,
) -> float:
    """Confidence from evidence count and source diversity.

    confidence = min(1, evidence_links / target) * diversity_factor

    diversity_factor rewards multiple distinct platforms (0.7 with one source,
    up to 1.0). A high score with one source is a hypothesis, not a fact.
    """
    base = _clamp(evidence_links / max(1, model.target_evidence), 0.0, 1.0)
    if not model.diversity_bonus:
        return round(base, 4)
    diversity_factor = _clamp(0.7 + 0.15 * (distinct_sources - 1), 0.7, 1.0)
    return round(_clamp(base * diversity_factor, 0.0, 1.0), 4)
