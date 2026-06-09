"""Design Studio contract for premium web builds.

The regular web gate answers "does this site build and meet baseline UX?" This
module answers the missing upstream question: "does this build have enough art
direction to be worth showing as custom work?"

The code is deliberately pure and small. It creates structured packets for the
build lane and structured review reports after screenshot capture; humans read
markdown, workers and tests consume these dataclasses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from packages.schemas.task_run import ValidationCheck

REQUIRED_BUILD_PHASES = [
    "evidence",
    "reference-translation",
    "creative-direction",
    "imagery",
    "build",
    "screenshot-review",
    "technical-gates",
]

REQUIRED_SCREENSHOTS = ["desktop", "mobile"]
VISUAL_MIN_OVERALL = 80
VISUAL_SCORE_FLOOR = 4

CRITICAL_CATEGORIES = {
    "visual_thesis": "design_studio_no_visual_thesis",
    "hero_impact": "design_studio_weak_hero",
    "imagery_art_direction": "design_studio_weak_imagery",
}


@dataclass(frozen=True)
class DesignReference:
    """A design inspiration source and the patterns worth translating."""

    title: str
    url: str
    source_type: str
    takeaways: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WebsiteDesignRequest:
    """Input for the Design Studio pass."""

    site_name: str
    business_category: str
    audience: str
    goal: str
    evidence: list[str] = field(default_factory=list)
    visual_assets: list[str] = field(default_factory=list)
    references: list[DesignReference] = field(default_factory=list)
    imagery_mode: str = "evidence-led"
    # The one genuinely human (or agent) input — the one-line creative concept
    # that everything serves. When supplied it overrides the derived statement;
    # when empty the packet falls back to an evidence-derived line.
    concept_statement: str = ""
    concept_palette: str = ""
    concept_type: str = ""


@dataclass(frozen=True)
class ReferenceTranslation:
    """One reference pattern translated into a build-safe local rule."""

    reference_title: str
    observed_pattern: str
    application: str
    rule: str = "Translate, do not copy the reference."

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesignStudioPacket:
    """The structured art-direction artifact a web build consumes."""

    site_name: str
    business_category: str
    audience: str
    goal: str
    concept_statement: str
    archetype: str
    palette_strategy: str
    type_direction: str
    imagery_plan: list[str]
    motion_plan: list[str]
    reference_translations: list[ReferenceTranslation]
    copy_constraints: list[str]
    required_build_phases: list[str]
    required_screenshots: list[str]
    references: list[DesignReference] = field(default_factory=list)
    # Real business evidence carried through as the composer's content source.
    evidence: list[str] = field(default_factory=list)
    # Raw concept cues carried through for the design-system synthesizer.
    concept_palette: str = ""
    concept_type: str = ""
    visual_qa: dict[str, object] = field(
        default_factory=lambda: {
            "minimum_overall": VISUAL_MIN_OVERALL,
            "category_floor": VISUAL_SCORE_FLOOR,
            "critical_categories": sorted(CRITICAL_CATEGORIES),
        }
    )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["references"] = [ref.to_dict() for ref in self.references]
        payload["reference_translations"] = [
            item.to_dict() for item in self.reference_translations
        ]
        return payload


@dataclass(frozen=True)
class VisualScore:
    """A 0-5 score for one visual-quality dimension."""

    category: str
    score: int
    note: str

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 5:
            raise ValueError("visual score must be between 0 and 5")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class VisualReviewReport:
    """Screenshot-backed visual quality report."""

    overall: int
    passed: bool
    checks: list[ValidationCheck]
    failure_codes: list[str]
    scores: list[VisualScore]
    screenshots: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "overall": self.overall,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "failure_codes": list(self.failure_codes),
            "scores": [score.to_dict() for score in self.scores],
            "screenshots": dict(self.screenshots),
        }


def build_design_studio_packet(request: WebsiteDesignRequest) -> DesignStudioPacket:
    """Create the art-direction packet for a website build."""

    archetype = _archetype_for(request.business_category)
    # A supplied concept is the human/agent's call and always wins; otherwise
    # derive a serviceable line from evidence so the packet is never empty.
    if request.concept_statement.strip():
        concept = request.concept_statement.strip()
    else:
        evidence_signal = _primary_signal(request.evidence, request.goal)
        concept = (
            f"{request.site_name} should feel like {evidence_signal}: a "
            f"{request.business_category} site for {request.audience}."
        )

    return DesignStudioPacket(
        site_name=request.site_name,
        business_category=request.business_category,
        audience=request.audience,
        goal=request.goal,
        concept_statement=concept,
        archetype=archetype,
        palette_strategy=_palette_strategy(request),
        type_direction=_type_direction(archetype),
        imagery_plan=_imagery_plan(request, archetype),
        motion_plan=_motion_plan(),
        reference_translations=_translate_references(request.references, archetype),
        copy_constraints=[
            "Copy only from evidence and approved owner input.",
            "No fabricated testimonials, trust logos, awards, or superlatives.",
            "Claims that cannot be sourced are cut, not softened.",
        ],
        required_build_phases=list(REQUIRED_BUILD_PHASES),
        required_screenshots=list(REQUIRED_SCREENSHOTS),
        references=list(request.references),
        evidence=list(request.evidence),
        concept_palette=request.concept_palette,
        concept_type=request.concept_type,
    )


def review_visual_quality(
    *,
    scores: list[VisualScore],
    screenshots: dict[str, str],
    minimum_overall: int = VISUAL_MIN_OVERALL,
    category_floor: int = VISUAL_SCORE_FLOOR,
) -> VisualReviewReport:
    """Score the premium design layer after screenshots are captured."""

    failure_codes: list[str] = []
    checks: list[ValidationCheck] = []

    if not scores:
        failure_codes.append("design_studio_missing_scores")
        overall = 0
    else:
        overall = round(sum(score.score for score in scores) / len(scores) * 20)

    by_category = {score.category: score for score in scores}
    for screenshot in REQUIRED_SCREENSHOTS:
        if not screenshots.get(screenshot):
            failure_codes.append(f"design_studio_missing_{screenshot}_screenshot")

    for category, code in CRITICAL_CATEGORIES.items():
        score = by_category.get(category)
        if score is None or score.score < category_floor:
            failure_codes.append(code)

    low_categories = [
        score.category for score in scores if score.score < category_floor
    ]
    if low_categories:
        failure_codes.append("design_studio_low_category_score")

    if overall < minimum_overall:
        failure_codes.append("design_studio_low_overall_score")

    failure_codes = _dedupe(failure_codes)
    passed = not failure_codes
    details = (
        f"visual quality score {overall}/100 with required screenshots"
        if passed
        else f"visual quality score {overall}/100; failures: {', '.join(failure_codes)}"
    )
    checks.append(
        ValidationCheck(
            name="design-studio-visual-quality",
            passed=passed,
            details=details,
            code=None if passed else failure_codes[0],
        )
    )
    checks.append(
        ValidationCheck(
            name="design-studio-screenshots",
            passed=all(screenshots.get(item) for item in REQUIRED_SCREENSHOTS),
            details="desktop and mobile screenshots captured"
            if all(screenshots.get(item) for item in REQUIRED_SCREENSHOTS)
            else "missing required screenshot(s)",
            code=None
            if all(screenshots.get(item) for item in REQUIRED_SCREENSHOTS)
            else "design_studio_missing_screenshot",
        )
    )

    return VisualReviewReport(
        overall=overall,
        passed=passed,
        checks=checks,
        failure_codes=failure_codes,
        scores=list(scores),
        screenshots=dict(screenshots),
    )


def _archetype_for(category: str) -> str:
    c = category.lower()
    if any(term in c for term in ("plumb", "roof", "electric", "hvac", "clean", "landscap")):
        return "service-area-cinematic"
    if any(term in c for term in ("nail", "salon", "barber", "groom", "bakery")):
        return "gallery-led"
    if any(term in c for term in ("coffee", "restaurant", "cafe")):
        return "editorial-visit"
    if any(term in c for term in ("saas", "software", "app", "platform")):
        return "product-led"
    return "classic-custom"


def _primary_signal(evidence: list[str], fallback: str) -> str:
    for item in evidence:
        stripped = item.strip()
        if stripped:
            return stripped
    return fallback.strip() or "a specific, evidence-led promise"


def _palette_strategy(request: WebsiteDesignRequest) -> str:
    asset_hint = (
        ", ".join(request.visual_assets[:2])
        if request.visual_assets
        else "available evidence"
    )
    return (
        "derive from evidence first; use "
        f"{asset_hint} for dominant canvas and one sharp accent; "
        "reference palettes are fallback only"
    )


def _type_direction(archetype: str) -> str:
    if archetype == "service-area-cinematic":
        return (
            "distinctive display face plus clean body; "
            "consider editorial serif + precise mono labels"
        )
    if archetype == "gallery-led":
        return "distinctive display face plus clean body; elegant or tactile display type"
    if archetype == "editorial-visit":
        return (
            "distinctive display face plus clean body; "
            "warm editorial pacing and readable long copy"
        )
    if archetype == "product-led":
        return (
            "distinctive display face plus clean body; "
            "restrained SaaS type with sharp numeric rhythm"
        )
    return "distinctive display face plus clean body; choose by the business concept"


def _imagery_plan(request: WebsiteDesignRequest, archetype: str) -> list[str]:
    base = [
        "hero image must express the concept before any copy is read",
        "supporting image set must share one crop, color, and lighting logic",
    ]
    if request.imagery_mode == "concept-led":
        base.insert(
            1,
            "generate or commission a cohesive concept-led hero and gallery "
            "when owned assets are weak",
        )
    elif request.visual_assets:
        base.insert(1, "curate owned/real photos before using generated or stock imagery")
    else:
        base.insert(1, "create an art-directed imagery brief before build starts")

    if archetype == "service-area-cinematic":
        base.append(
            "show proof of work, service area trust, and process instead of a storefront visit"
        )
    elif archetype == "gallery-led":
        base.append("lead with a varied gallery or bento layout, not uniform cards")
    return base


def _motion_plan() -> list[str]:
    return [
        "stagger hero reveal from eyebrow to headline to CTA",
        "use reduced-motion gated scroll reveals for section entrances",
        "add small CTA and card interactions that do not resize layout",
    ]


def _translate_references(
    references: list[DesignReference],
    archetype: str,
) -> list[ReferenceTranslation]:
    translations: list[ReferenceTranslation] = []
    for ref in references:
        pattern = ref.takeaways[0] if ref.takeaways else ref.title
        application = _application_for_pattern(pattern, archetype)
        translations.append(
            ReferenceTranslation(
                reference_title=ref.title,
                observed_pattern=pattern,
                application=application,
            )
        )
    return translations


def _application_for_pattern(pattern: str, archetype: str) -> str:
    p = pattern.lower()
    if "device" in p or "frame" in p:
        return f"Use a framed proof artifact when it supports the {archetype} concept."
    if "typography" in p:
        return f"Use stronger type contrast and editorial hierarchy for the {archetype} concept."
    if "canvas" in p or "accent" in p:
        return (
            "Limit the palette to one dominant canvas and one memorable accent "
            f"for the {archetype} concept."
        )
    if "scene" in p or "hero" in p:
        return f"Make the hero a composed scene tied to the {archetype} concept."
    return f"Translate the pattern into a business-specific choice for the {archetype} concept."


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
