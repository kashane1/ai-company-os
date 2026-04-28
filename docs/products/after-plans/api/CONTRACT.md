# After Plans — Backend Contract

Status: draft v1
Owner: After Plans iOS lane
Audience: any client (iOS Swift, Android Kotlin, Web TypeScript) and any backend implementor.

## Purpose

This contract is the **source of truth** for the After Plans data model and the operations clients perform against the backend. Each platform translates these shapes into native types but does not invent new ones. When the contract changes, this document changes first.

The contract is intentionally backend-neutral. The reference backend is Supabase (Postgres + RLS + Realtime + Edge Functions), but the protocol shapes do not name it.

## Design principles

1. **Server-authoritative state.** All lifecycle transitions, visibility decisions, and ranking happen on the backend. Clients never compute their own version of who-can-see-what.
2. **Idempotent mutating actions.** A client retrying `join` or `confirm` after a flaky network must never double-record. The backend deduplicates by (planID, userID, action).
3. **Explicit error taxonomy.** Every operation can fail in a small, named set of ways that clients can render meaningfully.
4. **Realtime is additive.** Every realtime event has a corresponding "fetch latest" REST shape. Clients that miss events recover by re-fetching.
5. **No PII beyond what the user types.** No location, no contacts, no device identifiers used for cross-app tracking. Identity is "first name + a few context cues" until the user explicitly adds more.

## Identifier conventions

| Type | Format | Notes |
| --- | --- | --- |
| `UserID` | UUID v4 | Stable per identity, not per device. |
| `PlanID` | UUID v4 | |
| `ContextID` | UUID v4 | |
| `InviteID` | UUID v4 | |
| `ReportID` | UUID v4 | |
| `InviteCode` | URL-safe base64, 12+ chars | Used in `afterplans://join/<code>` and shareable links. Distinct from `PlanID` so plans can rotate codes without breaking past links. |

## Core entities

### `UserProfile`

```
{
  "id": UserID,
  "first_name": string,            // user-typed, ≤ 24 chars
  "descriptor": string,            // "Verified phone · ceramics regular" — composed
  "visibility_default": PlanVisibility,
  "trust_headline": string         // server-composed; never user-typed
}
```

### `ContextOption`

```
{
  "id": ContextID,
  "type": "class_session" | "community" | "meetup" | "event" | "venue",
  "title": string,
  "venue_name": string,
  "ended_at_label": string,        // human-rendered; e.g. "Ended 12 min ago"
  "proximity_label": string,       // human-rendered; "3 min away"
  "trust_note": string             // why this context is bounded
}
```

### `AfterPlan`

```
{
  "id": PlanID,
  "title": string,
  "summary": string,
  "context_id": ContextID,
  "context_title": string,         // denormalized for fast feed render
  "host_id": UserID,
  "host_name": string,
  "host_descriptor": string,
  "mode": "default_option" | "open_intent" | "exact",
  "visibility": "same_context_only" | "known_people" | "invite_only",
  "lifecycle": "open" | "forming" | "confirmed" | "active" | "closed",
  "time_label": string,
  "venue_label": string,
  "distance_label": string,
  "trust_blurb": string,
  "participants": [ParticipantSummary],
  "interested_count": int,
  "place_suggestions": [string],
  "participation_state": "browsing" | "interested" | "joined" | "confirmed",
  "created_at": ISO8601,
  "updated_at": ISO8601
}
```

`participation_state` is a **per-viewer** projection, not a global field. The same plan returned to two different users can carry different `participation_state`. The backend computes this against the viewer's `UserID` on read.

### `ParticipantSummary`

```
{
  "id": UserID,
  "name": string,
  "descriptor": string,            // "Met here before", "Same studio circle", etc.
  "is_organizer": bool,
  "is_known_to_viewer": bool       // per-viewer projection
}
```

### `InvitePreview`

```
{
  "title": string,
  "subtitle": string,
  "audience_headline": string,
  "audience_detail": string,
  "join_framing": string,
  "link_label": string,
  "qr_label": string,
  "next_step_title": string,
  "next_step_detail": string,
  "invite_code": InviteCode,
  "deep_link": string              // "afterplans://join/<code>"
}
```

### `SafetyReason`

```
{
  "id": "harassment" | "hate" | "spam" | "dating" | "unsafe",
  "title": string,
  "explanation": string
}
```

## Operations

### Identity

| Op | Idempotent | Description |
| --- | --- | --- |
| `current_user()` | yes | Returns the calling user's `UserProfile`. Creates one on first call if anonymous-auth is in use. |
| `update_profile(profile)` | yes | Updates user-editable fields only (`first_name`, `visibility_default`). Server reconstructs `descriptor` and `trust_headline`. |

### Plans (feed + lifecycle)

| Op | Idempotent | Description |
| --- | --- | --- |
| `feed(context_id)` | yes | Returns plans visible to the caller in or adjacent to `context_id`, ranked. Backend applies blocks, visibility, and ranking. |
| `plan(id)` | yes | Returns the full plan as visible to the caller. Returns `not_found` if blocked or out of visibility. |
| `create_plan(draft, context_id)` | no | Creates and returns the plan. Caller becomes host. |
| `join(plan_id)` | yes | Adds caller as participant. Promotes lifecycle from `open`→`forming` if applicable. Returns updated plan. |
| `express_interest(plan_id)` | yes | Records interest signal. No-op if already joined or interested. |
| `suggest_place(plan_id, place)` | yes | Adds place suggestion if not already present. Promotes lifecycle from `open`→`forming`. |
| `confirm(plan_id)` | yes | Locks the plan to `confirmed`. Caller becomes a confirmed participant. |
| `mark_active(plan_id)` | yes | Transitions `confirmed`→`active`. Only the host or a confirmed participant may call. |
| `wrap(plan_id)` | yes | Transitions `active`→`closed`. Records recap data. |

All mutating ops return the **updated `AfterPlan`** as visible to the caller.

### Invites

| Op | Idempotent | Description |
| --- | --- | --- |
| `invite_preview(plan_id)` | yes | Returns the share-time preview. Caller must be host or confirmed participant. |
| `resolve_invite(code)` | yes | Returns the plan referenced by an invite code, or `not_found` if expired/closed. |
| `record_share(plan_id, channel)` | yes | Tracks that a share was prepared on a channel. Used for instrumentation and the in-app prepared-share state. Does NOT actually post to the channel. |

### Reports & blocks

| Op | Idempotent | Description |
| --- | --- | --- |
| `report_reasons()` | yes | Returns the canonical list of report reasons. Cacheable. |
| `report_plan(plan_id, reason_id, note?)` | no | Files a report. Server enqueues for moderation. |
| `report_user(user_id, reason_id, note?)` | no | Files a report on a user. |
| `block_user(user_id)` | yes | Adds user to caller's block list. Caller no longer sees that user's plans, participation, or hosted invites. |

## Error taxonomy

Every operation can return one of:

| Code | Meaning | Client recovery |
| --- | --- | --- |
| `unauthorized` | Caller has no valid identity. | Run `current_user()` to bootstrap. |
| `not_found` | Resource missing or out of visibility. Indistinguishable to caller by design. | Show "no longer available" copy. |
| `forbidden` | Resource exists but caller is not allowed to act on it. | Show appropriate messaging; do not retry. |
| `conflict` | The action is invalid in the current lifecycle state (e.g. `confirm` on `closed`). | Refresh the plan; do not retry blindly. |
| `rate_limited` | Too many calls. | Backoff per `Retry-After`. |
| `transient` | Network or backend hiccup. | Retry with exponential backoff (capped). |
| `invalid` | Client sent a malformed payload. | Bug — surface to telemetry. |

Clients map these to user-facing copy locally. The server never returns user-facing strings for errors.

## Realtime channels

Clients optionally subscribe to:

| Channel | Event | Payload |
| --- | --- | --- |
| `plans:context:<context_id>` | `plan_created` \| `plan_updated` \| `plan_closed` | `AfterPlan` |
| `plans:plan:<plan_id>` | `participant_joined` \| `participant_left` \| `lifecycle_changed` | `AfterPlan` |
| `user:<user_id>` | `invite_resolved` \| `report_acknowledged` | event-specific |

Missing events are recovered by calling the corresponding REST op.

## Visibility rules (informative)

These are informational summaries of what the backend enforces. Clients must NOT re-implement them locally.

1. **Same-context-only**: a plan is visible if `viewer.recent_contexts ∩ {plan.context_id} ≠ ∅`.
2. **Known-people**: visible if the viewer has previously planned with the host or any confirmed participant.
3. **Invite-only**: visible only via direct invite-code resolution; never appears in `feed()`.
4. **Blocks override everything**: if the viewer has blocked the host or any confirmed participant, the plan is invisible regardless of mode.
5. **Lifecycle gating**: `closed` plans appear in `history()`, never in `feed()`.

In Postgres terms, these become RLS policies on `plans` and `plan_participants`. In Firestore terms, they would be security rules. Clients receive only what they are allowed to see.

## Versioning

This contract uses additive versioning. Breaking changes increment `v1`→`v2` and require a migration window. Additive changes (new optional fields, new event types) do not break existing clients.

The current version is `v1`. Implementation status:

- iOS: in-memory adapter is the canonical reference implementation
- Android: not yet implemented
- Web: not yet implemented
- Backend (Supabase): scaffold only — see `infra/supabase/`

## Out of scope for v1

The following are intentionally absent and will be added in later contract versions:

- in-app messaging or chat (handoff to native Messages remains the v1 path)
- payments / ticketing
- venue suggestion APIs (v1 places are user-typed)
- map discovery
- organizer / community premium features
- public profile pages
- push-notification preference endpoints (push fan-out happens server-side without client config in v1)
