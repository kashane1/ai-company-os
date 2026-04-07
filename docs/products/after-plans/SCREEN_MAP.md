# Screen Map: After Plans

## Navigation Model

Recommended v1 structure:

- root stack for onboarding and account setup
- primary tab shell after activation
- modal flows for context selection, create plan, invite/share, and safety actions

Recommended tabs:

- Home
- Activity
- Profile

`Activity` is the live plan and history surface, not a chat tab.

## Screen Inventory

### 1. Welcome

Purpose:

- explain the continuation job in one sentence

Primary actions:

- continue onboarding
- sign in

### 2. How It Works

Purpose:

- teach the core mechanic quickly

Primary actions:

- continue
- skip details

### 3. Profile Basics

Purpose:

- collect first name, photo, and lightweight context cues

Primary actions:

- continue
- skip optional fields

### 4. Social Seed

Purpose:

- optionally import contacts or invite friends

Primary actions:

- continue
- skip

### 5. Privacy And Location Education

Purpose:

- explain why location and context matter before system prompts

Primary actions:

- allow when in use
- not now

### 6. First-Use Feed

Purpose:

- get the user to a live or seeded feed quickly

Primary actions:

- join
- interested
- start what's next

### 7. Home

Purpose:

- show current context, ranked after-plans, and a clear creation affordance

Primary sections:

- current context chip
- ranked discovery cards
- start what's next CTA
- invite/share entry

### 8. Current Context Selector

Purpose:

- anchor discovery and creation to the activity that just happened

Primary actions:

- choose context
- add context manually
- confirm

### 9. Plan Detail

Purpose:

- show plan summary, participants, visibility, lifecycle state, and actions

Primary actions:

- join
- interested
- suggest place
- share
- report
- block participant

### 10. Create Plan

Purpose:

- let the user create a continuation plan with minimal friction

Primary branches:

- exact plan
- default option
- open intent

### 11. Confirmation Room

Purpose:

- show convergence once enough momentum exists

Primary actions:

- confirm participation
- open handoff to text
- see place and timing

### 12. Invite / QR / Share

Purpose:

- bring in same-context or adjacent people without a heavy contact graph

Primary actions:

- copy link
- show QR
- share sheet

### 13. Activity

Purpose:

- show active, recent, and closed plans

Primary actions:

- reopen detail
- see prior partners
- leave feedback or note outcome later

### 14. Profile

Purpose:

- lightweight identity, circles, past partners, and settings

Primary actions:

- edit profile
- manage visibility defaults
- see block list
- open safety center

### 15. Safety Center

Purpose:

- centralize report, block, moderation, and help surfaces

Primary actions:

- report user
- report plan
- review block list
- see community rules

## Screen Priorities

Day-one implementation priority:

1. onboarding
2. context selector
3. home feed
4. create plan
5. plan detail
6. invite/share
7. safety center

Can follow after the core shell works:

- richer profile surfaces
- social memory
- activity recap polish
