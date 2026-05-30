"""Tests for the LLM-backed analyst — offline via a stub ChatModel.

A stub model lets us assert prompt construction and the strict JSON parsing
(fences, surrounding prose, insufficient-evidence, incomplete sets, clamping)
without any network or API key.
"""

from __future__ import annotations

from packages.discovery.analyst import (
    LLMSignalProvider,
    parse_signal_response,
)
from packages.schemas.opportunity import (
    SIGNAL_KEYS,
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    SourceRef,
)

FULL_SIGNALS = {key: 5 for key in SIGNAL_KEYS}


class StubModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str, float]] = []

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        self.calls.append((system, user, temperature))
        return self.response


def _record(*, evidence=True) -> OpportunityRecord:
    return OpportunityRecord(
        id="opp_1",
        title="Automate invoicing",
        problem="freelancers invoice by hand",
        audience="freelancers",
        source=SourceRef(connector="hackernews"),
        evidence=(
            [EvidenceLink(url="https://news.ycombinator.com/item?id=1", kind=EvidenceKind.REQUEST)]
            if evidence
            else []
        ),
    )


def _json(signals: dict) -> str:
    import json

    return json.dumps({"signals": signals})


def test_parses_clean_json() -> None:
    signals = parse_signal_response(_json({**FULL_SIGNALS, "buyer_intent": 8}))
    assert signals is not None
    assert signals.buyer_intent == 8.0


def test_parses_code_fenced_json() -> None:
    raw = f"```json\n{_json(FULL_SIGNALS)}\n```"
    assert parse_signal_response(raw) is not None


def test_parses_json_with_surrounding_prose() -> None:
    raw = f"Here is my assessment:\n{_json(FULL_SIGNALS)}\nHope that helps!"
    assert parse_signal_response(raw) is not None


def test_insufficient_evidence_returns_none() -> None:
    assert parse_signal_response('{"insufficient_evidence": true}') is None


def test_incomplete_signal_set_returns_none() -> None:
    partial = {key: 5 for key in SIGNAL_KEYS[:-1]}  # drop one key
    assert parse_signal_response(_json(partial)) is None


def test_non_numeric_value_returns_none() -> None:
    bad = {**FULL_SIGNALS, "risk": "high"}
    assert parse_signal_response(_json(bad)) is None


def test_bool_is_not_accepted_as_numeric() -> None:
    bad = {**FULL_SIGNALS, "risk": True}
    assert parse_signal_response(_json(bad)) is None


def test_values_are_clamped() -> None:
    signals = parse_signal_response(_json({**FULL_SIGNALS, "buyer_intent": 99, "risk": -4}))
    assert signals.buyer_intent == 10.0
    assert signals.risk == 0.0


def test_unparseable_returns_none() -> None:
    assert parse_signal_response("the model said no") is None


def test_provider_skips_model_call_without_evidence() -> None:
    model = StubModel(_json(FULL_SIGNALS))
    provider = LLMSignalProvider(model)
    assert provider(_record(evidence=False)) is None
    assert model.calls == []  # no point paying for a model call with no evidence


def test_provider_calls_model_and_returns_signals() -> None:
    model = StubModel(_json(FULL_SIGNALS))
    provider = LLMSignalProvider(model)
    signals = provider(_record())
    assert signals is not None
    assert len(model.calls) == 1
    system, user, temperature = model.calls[0]
    assert "INVERTED" in system  # risk-inversion reminder is in the rubric
    assert "freelancers" in user  # the record's audience reached the prompt
    assert temperature == 0.0


def test_provider_returns_none_on_insufficient() -> None:
    provider = LLMSignalProvider(StubModel('{"insufficient_evidence": true}'))
    assert provider(_record()) is None
