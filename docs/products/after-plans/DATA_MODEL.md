# Data Model: After Plans

This document defines the product contract, not a final backend schema.

The first implementation pass can use mocked or stubbed services in iOS, but these entities should remain the shared vocabulary across product, iOS, and future service work.

## Core Entities

### User

Purpose:

- represents a real participant in the product

Core fields:

- `user_id`
- `first_name`
- `profile_photo_url`
- `bio_short` optional
- `age_band` or `eligibility_state`
- `home_region` optional
- `identity_state`
- `safety_state`
- `created_at`

### Context

Purpose:

- anchors an after-plan to the shared activity that just happened

Examples:

- meetup
- class
- dinner
- conference session
- service
- hobby gathering

Core fields:

- `context_id`
- `context_type`
- `title`
- `venue_name`
- `starts_at`
- `ends_at`
- `location_hint`
- `context_source`
- `visibility_scope`

### AfterPlan

Purpose:

- the main continuation object

Core fields:

- `plan_id`
- `context_id`
- `creator_user_id`
- `plan_mode` (`exact`, `default_option`, `open_intent`)
- `title`
- `summary`
- `proposed_time`
- `proposed_place`
- `visibility_mode`
- `lifecycle_state`
- `momentum_score`
- `participant_count`
- `interested_count`
- `created_at`
- `updated_at`

### PlanParticipant

Purpose:

- records each user's relationship to a plan

Core fields:

- `plan_id`
- `user_id`
- `state` (`joined`, `interested`, `invited`, `declined`, `confirmed`)
- `joined_from`
- `created_at`

### PlaceSuggestion

Purpose:

- captures lightweight venue convergence without requiring full chat

Core fields:

- `suggestion_id`
- `plan_id`
- `user_id`
- `place_name`
- `distance_hint`
- `vote_count`
- `created_at`

### ShareInvite

Purpose:

- represents a QR or deep-link invitation path

Core fields:

- `invite_id`
- `plan_id`
- `created_by_user_id`
- `channel` (`link`, `qr`)
- `visibility_scope`
- `expires_at`
- `created_at`

### RelationshipEdge

Purpose:

- stores familiarity and prior shared history for ranking

Core fields:

- `from_user_id`
- `to_user_id`
- `edge_type` (`known_contact`, `same_context`, `prior_plan_partner`)
- `strength`
- `last_seen_at`

### Report

Purpose:

- records trust and safety escalations

Core fields:

- `report_id`
- `reporter_user_id`
- `subject_type` (`user`, `plan`)
- `subject_id`
- `reason_code`
- `details`
- `status`
- `created_at`

### Block

Purpose:

- prevents visibility and participation between users

Core fields:

- `block_id`
- `blocker_user_id`
- `blocked_user_id`
- `created_at`

## Supporting Enumerations

### VisibilityMode

Recommended initial values:

- `same_context`
- `invite_only`
- `known_people`
- `friends_of_participants`

### LifecycleState

- `open`
- `forming`
- `confirmed`
- `active`
- `closed`

### IdentityState

- `basic_profile`
- `verified_contact_method`
- `restricted`

### SafetyState

- `good_standing`
- `under_review`
- `limited_visibility`
- `blocked`

## Ranking Inputs

Feed ranking should consume:

- current context match
- known-people edges
- prior plan partner edges
- distance or travel plausibility
- time relevance
- current momentum
- block and safety exclusions

## Privacy Rules

- do not expose raw location more broadly than visibility mode allows
- blocked users should not appear in discovery or participant lists to each other
- invite previews should reveal only the minimum details needed to join safely

## Implementation Notes

- the iOS shell can start with local models and service protocols
- final network/storage choices are deferred
- do not let the first implementation invent extra entities that widen scope into chat, public feeds, or organizer CRM
