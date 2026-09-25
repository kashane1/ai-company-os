# Reliability decisions and their limits

The useful part of building this system has been deciding how to inspect
agent output and recover when a step fails. These examples distinguish code
and tests from procedures that still depend on an operator or agent following
them.

## Preserve the previous record when a write fails

[PostMortemStore.save](../packages/db/postmortem_store.py) writes a temporary
file and replaces the destination with `os.replace`. The
[failure-injection test](../tests/python/integration/test_audit_artifact_crash_safety.py)
checks that a serialization error preserves the previous record and removes
the temporary file. This is evidence for that failure case, not a blanket
power-loss or concurrent-writer durability guarantee.

## Validate the fields that cross a parsing boundary

[TaskRun.from_dict](../packages/schemas/task_run.py) converts worker lane,
classification, and status through enums. The
[typed-surface tests](../tests/python/unit/test_typed_tool_surface.py) cover
unknown enum values and missing required fields. Direct dataclass construction
and type annotations do not provide complete runtime validation; several
fields are coerced and some policy values remain strings.

## Test the approval mechanism independently of its illustration

The [offline demo](../scripts/demo/run_demo.py) constructs sample approval
records. It does not demonstrate authorization. The
[token integration tests](../tests/python/integration/test_approval_tokens.py)
exercise signature rejection, expiry, single-use tokens, and local endpoint
state changes instead.

The API assumes a trusted local environment. P0 actions require a second
confirmation with the same token/device; the name “second factor” in code does
not imply independent MFA. This is a bounded local mechanism, not a complete
security boundary for an internet-facing service.

## Define when an iteration should stop

The [simulator polish skill](../skills/canonical/simulator-driven-polish/skill.md)
sets decision tiers, recurrence limits, and a build-failure stop condition.
These make operator expectations explicit. They are agent instructions; the
skill itself does not prove automatic enforcement or successful golden-image
comparison on every run. Review a
[recorded session](products/life-clock/polish-2026-05-05.md) alongside the procedure.

## Keep development fixtures behind a build boundary

[LifeClockLaunchConfiguration.swift](../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift)
uses `#if DEBUG` for its environment-based fixtures and supplies production
defaults in Release. The
[configuration tests](../products/life-clock-ios/Tests/LifeClockLaunchConfigurationTests.swift)
show expected fixture behavior. This is evidence about this configuration
surface, not a claim that every test hook throughout the product was audited.

## Scope redaction and retention precisely

[PostMortem](../packages/schemas/postmortem.py) applies redaction to selected
fields, including notes, excerpts, remediation text, and fixture paths. Other
fields and raw worker stdout/stderr are not covered by that statement; this
is not proof that all artifacts or Git history are free of secrets.

[Postmortem retention policy](../packages/policies/postmortem_retention.py)
controls visibility and stale-record checks. Its time window is not automatic
deletion of all runtime artifacts. Likewise, loading a serialized task-run
record is not the same as replaying the original agent execution.

For runnable verification and the scope of each check, use the
[evaluator walkthrough](EVALUATOR-WALKTHROUGH.md).
