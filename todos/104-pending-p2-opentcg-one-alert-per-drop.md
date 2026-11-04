---
status: pending
priority: p2
issue_id: "104"
tags: [open-tcg, alerts, dedupe]
dependencies: ["098"]
---

# OpenTCG: one banner and one browser tab per drop

## Problem Statement

A single post naming two watched items becomes two episodes, and so two banners. At Costco it also opens two tabs. One Costco drop posted by two accounts gets two different text keys, again two banners and two tabs.

## Findings

- Real case: episodes 64 and 65 both come from observation 27.
- The two-account Costco case was verified in simulation during the 2026-09-29 reliability review.

## Proposed Solutions

1. **(Recommended)** Deduplicate notifications per post, not per episode. Key rule matches by `rule:{retailer}|{set}` within the episode window. Deduplicate browser opens by resolved URL, or by retailer, set and window. Send one banner listing all matched items.

## Acceptance Criteria

- [ ] A multi-item post produces one banner and at most one tab.
- [ ] The same Costco drop from two accounts produces one banner and one tab, and the scorecard still credits both sources.
