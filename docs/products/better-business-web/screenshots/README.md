# Screenshot evidence

These are screenshots of rendered website work and design iterations. They show
the implementation at capture time; they are not evidence of customer adoption,
revenue, or a current production deployment.

Large display screenshots were converted from PNG to WebP at quality 92 on
September 8, 2026, keeping their original dimensions. This reduced the current
tree by about 122 MiB across 35 files. Original PNGs remain in Git history and in
the author's private archive. No history was rewritten. Images referenced by
the visual calibration corpus remain unchanged PNGs so scoring inputs stay exact.

New evidence should use a readable display image and a short caption identifying
the product, state, and capture context. Keep full-resolution originals outside
the default source tree when they are not necessary for a reproducible test.

`make tokens-check` enforces an 8 MiB individual-file budget, 150 MiB for docs,
and 250 MiB for the entire current public tree. Budgets include new unignored
files and are reviewed in code, with no blanket exemption for legacy assets.
These limits reduce checkout weight; they do not shrink an ordinary full-history
clone. Use a shallow clone when only the current source is needed.
