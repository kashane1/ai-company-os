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
