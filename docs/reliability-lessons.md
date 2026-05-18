# What building an unattended agent system taught me about reliability

I direct a fleet of AI coding agents that build and ship real apps. The
interesting engineering was never the model calls. It was everything
required to *leave the thing running and still trust the result*. A few
lessons, each tied to something concrete in this repo.

## 1. "It produced output" is not "it succeeded"

An agent will happily report success while leaving a half-written file
behind. So writes that matter are atomic: `PostMortemStore.save`
(`packages/db/postmortem_store.py`) writes to a temp file and `os.replace`s
it into place, cleaning the temp file on any exception. A transient failure
mid-write leaves the *previous* good record intact — never a corrupt one.
This is proven, not asserted:
`tests/python/integration/test_audit_artifact_crash_safety.py`.

The general lesson: durability boundaries belong at the lowest layer that
writes, and they need a test that actually injects the failure.

## 2. Reject bad state at the boundary, not three steps later

A malformed task contract that fails deep in a run is expensive to debug
and easy to misattribute. The domain schemas in `packages/schemas/` are
enum-constrained typed records: an unknown worker lane or an invalid
classification *cannot construct*. The failure happens at parse time with a
clear error, not after an agent has done half a unit of irreversible work.
See `tests/python/unit/test_typed_tool_surface.py`.

## 3. Autonomy has to be explicit and tiered, or it is just hope

The simulator-driven-polish loop
(`skills/canonical/simulator-driven-polish/skill.md`) classifies every
finding into Polish / Stretch / Feature / Vision-question, and only the
first two are auto-applied. Irreversible product decisions are always
escalated, and asks are batched so the human reviews a coherent set, not a
stream of interruptions. "The agent decides when to ask" fails; "the system
encodes what class of thing always requires a human" holds.

## 4. Loops need a stop condition that isn't success

Most agent failure in practice is not a crash — it is thrashing. Two rules
do most of the work: the **two-recurrence rule** (same finding survives two
fix attempts → stop and escalate) and the **build-fail gate** (two
consecutive build failures → stop). Cheap to implement, and they convert
"ran forever producing noise" into "stopped and asked a human."

## 5. Regression detection has to be automatic, because attention isn't

When an agent fixes screen A it can quietly break screen B. Golden
screenshots (`products/<product>-ios/.polish/goldens/`) mean a diff on an
untouched screen is *flagged*, not noticed-if-lucky. The reliability win is
removing the human from the detection path and keeping them only in the
decision path.

## 6. Safety surfaces must not exist in the artifact you ship

The deterministic seed harness
(`products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift`)
lets the loop jump to any UI state — and every probe is `#if DEBUG`. The
fixture surface is physically absent from the App Store binary. A test hook
that ships is a vulnerability; the boundary belongs in the build, not in a
code review checklist.

## 7. Redact at the schema, not at the log line

`PostMortem.__post_init__` (`packages/schemas/postmortem.py`) redacts every
free-text field on construction, and path fields strip `/Users/<name>/`.
Redaction at the call site is something you forget once; redaction at the
type is something you cannot forget.

## The through-line

Every one of these is the same move: take a property you would otherwise
have to *remember to check*, and make it structurally true — atomic writes,
boundary validation, tiered autonomy, hard stop conditions, automatic
regression flags, build-time safety boundaries, redaction at the type. That
is what made it safe to stop watching it run, and it is the same discipline
that makes any production system trustworthy.
