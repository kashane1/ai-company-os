# Task Packet: Trust, Safety, And Moderation Primitives Planning

## Packet ID

`after-plans-supervisor-002`

## Lane

`supervisor`

## Risk

`high`

## Approval

No approval needed for planning. Any later policy or release action that changes external behavior may require approval.

## Tests

Not required for this planning packet.

## Objective

Finalize the minimum launch trust model so iOS implementation and App Store preparation do not proceed on vague assumptions.

## Inputs

- `../TRUST_SAFETY_GUARDRAILS.md`
- `../DATA_MODEL.md`
- `../APP_STORE_POSITIONING.md`
- `../OPEN_QUESTIONS.md`

## Scope

- choose launch eligibility posture
- finalize v1 visibility modes
- finalize report reasons and moderation actions
- define block behavior across feed, plan detail, and invites
- define the moderation operating path for founder-led launch

## Out Of Scope

- fully built moderation tooling
- background enforcement automation
- community management suite

## Deliverables

- locked trust model decisions
- UI-facing requirements for report and block flows
- App Review support notes
- explicit follow-on tasks for iOS and App Store lanes

## Constraints

- do not drift into anonymous or random-chat posture
- keep shared context ahead of public discovery
- keep the initial moderation model realistic for a small launch team

## Exit Criteria

- age and eligibility stance is chosen
- visibility modes are final enough for implementation
- report and block semantics are unambiguous
- App Store positioning can accurately describe the trust posture

## Resume Point

Start with the three hardest choices: eligibility policy, visibility modes, and what happens when one user blocks another.
