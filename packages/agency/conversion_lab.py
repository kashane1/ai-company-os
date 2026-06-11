from __future__ import annotations

from pathlib import Path

from packages.agency.conversion_personas import ConversionPersona
from packages.schemas.conversion_lab import ConversionLabInput, ConversionLabReport


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None noted"]


def render_report_markdown(report: ConversionLabReport) -> str:
    lines = [
        f"# Conversion Lab Report: {report.product_id}",
        "",
        "## Executive Summary",
        "",
        f"Vertical: {report.vertical}",
        "",
        f"Confidence: {report.confidence_label}",
        "",
        "## Scorecard",
        "",
        "| Area | Score |",
        "|---|---:|",
        f"| Clarity | {report.scorecard.clarity} |",
        f"| Trust | {report.scorecard.trust} |",
        f"| Offer strength | {report.scorecard.offer_strength} |",
        f"| Friction | {report.scorecard.friction} |",
        f"| Local relevance | {report.scorecard.local_relevance} |",
        f"| Conversion action | {report.scorecard.conversion_action} |",
        "",
        "## Top Conversion Blockers",
        "",
        *_bullets(report.top_blockers),
        "",
        "## Top Trust Gaps",
        "",
        *_bullets(report.top_trust_gaps),
        "",
        "## Persona Feedback",
    ]
    for review in report.persona_reviews:
        lines.extend(
            [
                "",
                f"### {review.persona_id}",
                "",
                f"Likely action: {review.likely_action}",
                "",
                f"Confidence: {review.confidence}",
                "",
                "Clarity notes:",
                *_bullets(review.clarity_notes),
                "",
                "Objections:",
                *_bullets(review.objections),
                "",
                "Trust gaps:",
                *_bullets(review.trust_gaps),
                "",
                "Useful rewrites:",
                *_bullets(review.useful_rewrites),
            ]
        )
    lines.extend(["", "## Recommended Rewrites"])
    for section, copy in report.recommended_rewrites.items():
        lines.extend(["", f"### {section}", "", copy])
    lines.extend(
        [
            "",
            "## Confidence And Caveats",
            "",
            "This is a synthetic-audience preflight report. It can surface likely conversion issues, but it does not replace live analytics, real customer interviews, or controlled ad experiments.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: ConversionLabReport, *, root: Path, run_id: str) -> Path:
    out_dir = root / "state" / "clients" / report.product_id / "conversion_lab" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "REPORT.md"
    out.write_text(render_report_markdown(report), encoding="utf-8")
    return out


def render_prompts_markdown(input_payload: ConversionLabInput, prompts: list[str]) -> str:
    lines = [
        f"# Conversion Lab Prompts: {input_payload.product_id}",
        "",
        f"Vertical: {input_payload.vertical}",
        f"Target action: {input_payload.target_action.value}",
        f"URL: {input_payload.url}",
        "",
    ]
    for index, prompt in enumerate(prompts, start=1):
        lines.extend([f"## Prompt {index}", "", prompt.strip(), ""])
    return "\n".join(lines)


def build_persona_review_prompt(
    *,
    persona: ConversionPersona,
    input_payload: ConversionLabInput,
) -> str:
    known_objections = "\n".join(f"- {item}" for item in input_payload.known_objections)
    objections = known_objections or "- None provided"
    trust_signals = "\n".join(f"- {item}" for item in persona.trust_signals)
    persona_objections = "\n".join(f"- {item}" for item in persona.objections)
    return f"""Embody the following buyer persona for exploratory conversion review.

This is a synthetic simulation, not a real customer interview.

Persona ID: {persona.persona_id}
Persona vertical: {persona.vertical}

Persona dossier:
{persona.dossier}

Persona trust signals:
{trust_signals}

Persona objections:
{persona_objections}

Business vertical: {input_payload.vertical}
Target action: {input_payload.target_action.value}
URL: {input_payload.url}

Known objections from the operator:
{objections}

Page copy:
{input_payload.page_copy}

Persona-specific review instruction:
{persona.review_prompt}

Return JSON with exactly these keys:
- persona_id
- likely_action
- clarity_notes
- objections
- trust_gaps
- useful_rewrites
- confidence
"""
