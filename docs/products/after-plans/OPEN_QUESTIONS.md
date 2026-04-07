# Open Questions: After Plans

These questions are intentionally unresolved after the ingestion pass. They should guide the next lane decisions rather than be buried in ad hoc prompts.

## Product And Policy

1. What is the launch eligibility posture: 18+ only, 17+, or a mixed model with stronger youth safeguards?
2. How much identity proof is required in v1 beyond first name, photo, and lightweight context cues?
3. Which shared-context anchors ship first: manually selected context, imported event/share link, geofenced nearby context, or some combination?
4. What is the minimum set of plan visibility modes for v1: same context only, invite-only, known people only, and friends-of-participants?
5. Does v1 allow any in-app text beyond structured actions, or should the product hand off to iMessage once a plan confirms?

## iOS And Service Shape

6. Is the first implementation pass best served by mocked service contracts inside the iOS shell, or should it include a real thin backend contract immediately?
7. Which creation mode should be the default composer entry: exact plan, default option, or open intent?
8. What location granularity is needed for relevance without creating a public map posture or over-requesting permission?
9. What is the minimum venue suggestion source for v1, if any?

## Trust And Safety

10. What report categories and moderation actions are the minimum launch set for App Review confidence?
11. How should blocked users affect plan visibility, join requests, and shared history surfaces?
12. What abuse-response expectation can realistically be supported in a founder-led launch?

## GTM And Launch

13. Which seeded contexts should launch first: campus, hobby meetups, recurring communities, or city social scenes?
14. Is the first launch geography single-city, single-campus, or a handful of manually seeded communities?
15. What counts as a valid signal that organizer or community premium is warranted later?
