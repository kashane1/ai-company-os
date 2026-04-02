# Deterministic Insight Rules

## Contract

All insight cards in MVP must be:

- deterministic
- reproducible from local user data
- understandable from their inputs
- supportable with sample counts or simple evidence

No generative summarization is in scope.

These rules power the private recall layer. They should not become a separate product identity or a second insight engine.

## Composition Rule

- a compact Spot DNA style "what worked here" summary may combine outputs from these deterministic rules
- the summary must remain traceable to the underlying rules and supporting trips
- "last time here" and broader pattern replay surfaces are a next-phase consumer of these rules, not a reason to broaden the rule set prematurely

## Initial Rules

### 1. Top Species By Waterbody

- scope: `waterbody`
- rule type: `catch_rate`
- inputs: waterbody, species counts, trip outcomes
- output: most productive species at a saved water

### 2. Top Lure By Species

- scope: `species`
- rule type: `top_lure`
- inputs: species, lure or bait, recent catches
- output: most productive lure for a species or spot

### 3. Best Time Window

- scope: `trip_context`
- rule type: `best_time_window`
- inputs: catch timestamps bucketed by time of day
- output: most productive time bucket such as 6-9 AM

### 4. Best Month Or Season

- scope: `seasonal`
- rule type: `seasonality`
- inputs: month, season, catch totals, successful trips
- output: strongest seasonal window for a spot or species

### 5. Average Catches Per Trip

- scope: `trip_context`
- rule type: `catch_rate`
- inputs: catches per trip, trip count
- output: average productivity summary

### 6. Catch Vs Skunk Rate

- scope: `trip_context`
- rule type: `catch_rate`
- inputs: successful trips, skunked trips
- output: simple success rate framing

### 7. Similar Conditions Retrieval

- scope: `spot`
- rule type: `similar_conditions`
- inputs: time bucket, wind, cloud cover, precipitation, season
- output: prior productive trips under similar conditions

## Output Shape

Each card should include:

- short title
- concise body
- support count
- stable rule source
