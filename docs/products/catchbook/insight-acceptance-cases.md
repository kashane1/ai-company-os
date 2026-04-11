# Insight Acceptance Cases

## Purpose

These cases define the expected output shape for the first deterministic cards. They are examples the implementation should be able to reproduce from seeded fixtures.

## Cases

### Best Time Window At A Waterbody

- rule: `best_time_window`
- expected title: `Best time window at Pine Lake`
- expected body: `At Pine Lake, your highest bass catch count is 6-9 AM.`
- confidence label: `strong`
- supporting sample count: `4`

### Top Lure At A Spot

- rule: `top_lure`
- expected title: `Top lure at Cedar Point`
- expected body: `Spinnerbait has been your top producer here in the last 10 trips.`
- confidence label: `medium`
- supporting sample count: `10`

### Similar Conditions Recall

- rule: `similar_conditions`
- expected title: `Similar conditions have worked here`
- expected body: `You've logged 4 productive trips here in light wind conditions.`
- confidence label: `medium`
- supporting sample count: `4`

### Seasonal Pattern

- rule: `seasonality`
- expected title: `Spring has been strongest here`
- expected body: `Your last 3 successful trips at this spot were all in spring.`
- confidence label: `strong`
- supporting sample count: `3`

## Acceptance Notes

- cards must remain traceable to local data
- cards must not invent unsupported recommendations
- if support is too thin, the rule should emit no card rather than weak copy
