# Task Packet: iOS MVP Shell And Core-Loop Planning

## Packet ID

`after-plans-ios-001`

## Lane

`ios`

## Risk

`medium`

## Approval

Not required for shell planning or local implementation.

## Tests

When code work begins, tests are required under `products/after-plans-ios/Tests/` for logic-bearing additions.

## Objective

Bootstrap a compile-safe SwiftUI shell that encodes the screen map, navigation model, service protocols, and trust-aware state model without implementing the full product.

## Inputs

- `../MVP_SPEC.md`
- `../SCREEN_MAP.md`
- `../DATA_MODEL.md`
- `../IOS_ARCHITECTURE.md`
- `../TRUST_SAFETY_GUARDRAILS.md`

## Scope

- create project structure
- add app shell and navigation scaffolding
- define placeholder features and service protocols
- encode lifecycle, visibility, and participation enums
- add initial tests for logic-bearing state types

## Out Of Scope

- live backend integrations
- rich messaging
- full ranking engine
- App Store assets

## Deliverables

- `products/after-plans-ios/README.md` updated for implementation state
- `project.yml` if XcodeGen is used
- minimal SwiftUI app target
- placeholder feature folders aligned to the screen map
- test target wiring

## Constraints

- stay compile-safe
- do not build a half-finished social app
- no chat tab
- no public discovery surface
- keep visibility and safety states explicit in the shell

## Exit Criteria

- the app boots into a shell aligned with the screen map
- create-plan, feed, plan-detail, and safety placeholders exist
- service protocols and state enums are defined
- lane-matching tests exist for logic-bearing code

## Resume Point

Begin with `products/after-plans-ios/project.yml`, the root `App` target, and the screen-map-driven navigation shell before any feature logic.
