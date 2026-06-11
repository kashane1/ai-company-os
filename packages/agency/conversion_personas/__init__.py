from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


PACK_ROOT = Path(__file__).resolve().parent


class PersonaPackError(ValueError):
    pass


@dataclass(frozen=True)
class ConversionPersona:
    persona_id: str
    vertical: str
    dossier: str
    trust_signals: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    review_prompt: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, object], *, vertical: str) -> "ConversionPersona":
        return cls(
            persona_id=str(payload["persona_id"]),
            vertical=str(payload.get("vertical", vertical)),
            dossier=str(payload["dossier"]),
            trust_signals=[str(item) for item in list(payload.get("trust_signals", []))],
            objections=[str(item) for item in list(payload.get("objections", []))],
            review_prompt=str(payload["review_prompt"]),
        )


@dataclass(frozen=True)
class PersonaPack:
    vertical: str
    personas: list[ConversionPersona]


@dataclass(frozen=True)
class VerticalModifier:
    modifier_id: str
    verticals: list[str]
    objections: list[str]
    trust_signals: list[str]
    decision_triggers: list[str]
    compliance_notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "VerticalModifier":
        return cls(
            modifier_id=str(payload["modifier_id"]),
            verticals=[str(item) for item in list(payload.get("verticals", []))],
            objections=[str(item) for item in list(payload.get("objections", []))],
            trust_signals=[str(item) for item in list(payload.get("trust_signals", []))],
            decision_triggers=[
                str(item) for item in list(payload.get("decision_triggers", []))
            ],
            compliance_notes=[
                str(item) for item in list(payload.get("compliance_notes", []))
            ],
        )


@dataclass(frozen=True)
class AudiencePanel:
    vertical: str
    modifier: VerticalModifier
    personas: list[ConversionPersona]


def load_persona_pack(vertical: str, *, root: Path | None = None) -> PersonaPack:
    pack_root = root or PACK_ROOT
    path = pack_root / f"{vertical}.yaml"
    if not path.exists():
        raise PersonaPackError(f"missing persona pack: {vertical}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pack_vertical = str(payload.get("vertical", vertical))
    personas = [
        ConversionPersona.from_dict(dict(item), vertical=pack_vertical)
        for item in list(payload.get("personas", []))
    ]
    _validate_personas(personas)
    return PersonaPack(vertical=pack_vertical, personas=personas)


def load_audience_panel(vertical: str, *, root: Path | None = None) -> AudiencePanel:
    pack_root = root or PACK_ROOT
    core = load_persona_pack("core", root=pack_root)
    modifier = _modifier_for(vertical, root=pack_root)
    personas = list(core.personas)
    vertical_path = pack_root / f"{vertical}.yaml"
    if vertical_path.exists() and vertical != "core":
        personas.extend(load_persona_pack(vertical, root=pack_root).personas)
    _validate_personas(personas)
    return AudiencePanel(vertical=vertical, modifier=modifier, personas=personas)


def _modifier_for(vertical: str, *, root: Path) -> VerticalModifier:
    path = root / "modifiers.yaml"
    if not path.exists():
        raise PersonaPackError("missing modifiers.yaml")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    modifiers = [
        VerticalModifier.from_dict(dict(item))
        for item in list(payload.get("modifiers", []))
    ]
    for modifier in modifiers:
        if vertical == modifier.modifier_id or vertical in modifier.verticals:
            _validate_modifier(modifier)
            return modifier
    raise PersonaPackError(f"missing vertical modifier: {vertical}")


def _validate_personas(personas: list[ConversionPersona]) -> None:
    seen: set[str] = set()
    for persona in personas:
        if persona.persona_id in seen:
            raise PersonaPackError(f"duplicate persona_id: {persona.persona_id}")
        seen.add(persona.persona_id)
        if not persona.dossier:
            raise PersonaPackError(f"persona {persona.persona_id}: dossier required")
        if not persona.trust_signals:
            raise PersonaPackError(f"persona {persona.persona_id}: trust_signals required")
        if not persona.objections:
            raise PersonaPackError(f"persona {persona.persona_id}: objections required")
        if not persona.review_prompt:
            raise PersonaPackError(f"persona {persona.persona_id}: review_prompt required")


def _validate_modifier(modifier: VerticalModifier) -> None:
    if not modifier.verticals:
        raise PersonaPackError(f"modifier {modifier.modifier_id}: verticals required")
    if not modifier.objections:
        raise PersonaPackError(f"modifier {modifier.modifier_id}: objections required")
    if not modifier.trust_signals:
        raise PersonaPackError(f"modifier {modifier.modifier_id}: trust_signals required")
    if not modifier.decision_triggers:
        raise PersonaPackError(
            f"modifier {modifier.modifier_id}: decision_triggers required"
        )
