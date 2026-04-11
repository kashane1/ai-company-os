# Catchbook — Campaign Calendar

Phase 2.3 artifact. 14-day pre-launch schedule. The GTM worker reads this
file to decide which `CONTENT_DRAFT` and `SOCIAL_POST_SCHEDULE` tasks to
emit each day. All scheduled posts still go through approval before
publish.

Dates are YYYY-MM-DD.

| Date | Platform | Hook | Asset | Owner |
|---|---|---|---|---|
| 2026-04-10 | threads | "The logbook I wish I had in my tackle box" | still #1 | gtm-worker |
| 2026-04-11 | instagram | First-fish carousel (3 slides) | carousel #1 | gtm-worker |
| 2026-04-12 | tiktok | 15s rod-setup + app overlay | video #1 | gtm-worker |
| 2026-04-13 | instagram | Species-of-the-week: smallmouth | carousel #2 | gtm-worker |
| 2026-04-14 | tiktok | "Three taps to log a catch" | video #2 | gtm-worker |
| 2026-04-15 | threads | Water-temp micro-tip | still #2 | gtm-worker |
| 2026-04-16 | instagram | Beta tester testimonial | carousel #3 | gtm-worker |
| 2026-04-17 | tiktok | Release-responsibly PSA | video #3 | gtm-worker |
| 2026-04-18 | threads | Pre-launch countdown | still #3 | gtm-worker |
| 2026-04-19 | instagram | Screenshots reveal | carousel #4 | gtm-worker |
| 2026-04-20 | tiktok | Founder intro | video #4 | gtm-worker |
| 2026-04-21 | threads | Beta -> launch story | still #4 | gtm-worker |
| 2026-04-22 | instagram | Launch day carousel | carousel #5 | gtm-worker |
| 2026-04-23 | tiktok | Launch day video | video #5 | gtm-worker |
