# `/last30days` Social Media Marketing Report

Date: April 14, 2026

Update: rerun on April 14, 2026 with the project `.env` loaded and Gemini reasoning enabled via `GEMINI_API_KEY`

## Scope

This report uses the local `/last30days` skill runtime to research how an AI company should approach social media marketing, with a focus on TikTok, Instagram, and X/Twitter.

The skill was available locally, but this environment did not have credentials configured for:

- `XAI_API_KEY` or `AUTH_TOKEN` + `CT0` for X/Twitter
- `SCRAPECREATORS_API_KEY` for TikTok and Instagram
- `BRAVE_API_KEY` or `SERPER_API_KEY` for broader web search
- `OPENAI_API_KEY` or `GOOGLE_API_KEY` for alternate reasoning-provider support

The rerun confirmed that `GEMINI_API_KEY` does work with `/last30days` when `.env` is sourced. That enabled Gemini-backed planning and brought in YouTube results for some queries. Even so, this is still a partial `/last30days` report. The strongest evidence comes from Reddit, with some YouTube support and some GitHub noise. The recommendations for TikTok, Instagram, and X are therefore a mix of:

- direct `/last30days` evidence from available sources
- clear inferences from that evidence
- platform-specific adaptation for an AI company

## Queries Run

Completed runs:

- `AI startup marketing`
- `how founders use AI for social media`
- `best AI content workflow for founders`
- `How are people actually using AI for social media marketing on TikTok, Instagram, and X? Focus on recurring hooks, creator formats, audience pain points, objections, and the kinds of AI use cases that get the strongest engagement. Then synthesize what an AI company should post about if it wants to attract founders and operators.`

Attempted but blocked by missing source credentials:

- `AI marketing for startups --search=tiktok,instagram,x`
- `AI founder content --search=x`
- `AI business reels --search=instagram,tiktok`

Raw outputs were saved under:

- `state/last30days_social_report/`

Runtime note:

- the first pass ran without the repo `.env` loaded
- the report was then rerun with `.env` sourced, which enabled Gemini-backed planning and added YouTube retrieval in some results

## Executive Summary

The clearest pattern from the rerun evidence is that AI marketing works best when it feels concrete, skeptical, and operational rather than polished, abstract, or hype-heavy.

For an AI company, the highest-leverage content is not generic "AI tips." It is proof-oriented content showing:

- what a workflow looked like before automation
- what changed after automation
- what still breaks
- what founders and operators should stop doing manually
- why your product is more than "just a chatbot"

The available `/last30days` evidence also shows a strong community allergy to fake sophistication. When people feel a startup is using "AI" as a label rather than as real product value, skepticism shows up immediately. That means your social presence should sound like an operator sharing receipts, not a marketer decorating copy with AI buzzwords.

The rerun added one more useful theme: content systems and workflow playbooks surface more reliably than generic "AI tips." The stronger matches were about repeatable content processes, automation steps, and distribution systems.

## Source Coverage and Quality

What worked in this environment:

- Reddit
- Hacker News availability, but little relevant signal in these runs
- GitHub availability, but broad marketing prompts often returned noisy/off-target results
- YouTube availability once `.env` was sourced and Gemini reasoning was active

What did not work in this environment:

- X/Twitter
- TikTok
- Instagram
- broad web search

Important caveat:

- every successful query produced the warning `Top evidence is highly concentrated in one source`
- several Gemini-enabled YouTube results were kept even when none were inside the strict last-30-days window, so older promotional videos should be treated as secondary context rather than primary evidence

So the report is directionally useful, but not a substitute for a fully credentialed rerun.

## What The Evidence Says

### 1. Audiences are skeptical of "AI-powered" positioning without obvious substance

The strongest result from `AI startup marketing` was a Reddit thread arguing that many startups are just slapping "AI-powered" on products that do not feel meaningfully intelligent.

Key evidence:

- [Almost every SG startup is slapping "AI-powered" on their product. Most of it is just if-else logic with a chatbot. Change my mind.](https://www.reddit.com/r/singaporestartups/comments/1sfjqaa/almost_every_sg_startup_is_slapping_aipowered_on/) from April 8, 2026 with roughly 149 upvotes and 72 comments
- The quoted reactions in the result included lines mocking posts that themselves "sound AI-powered"

Implication for your company:

- avoid brand copy that sounds like polished AI boilerplate
- show the exact job your system does
- make the user outcome legible in one sentence
- use demos, screenshots, logs, or workflow diagrams as proof

### 2. Founders struggle to explain their startup simply

One of the most useful findings in the marketing query was a thread explicitly asking founders to describe their startup in one sentence and explain how they are marketing it.

Key evidence:

- [Drop your startup in one sentence and how you’re marketing it](https://www.reddit.com/r/micro_saas/comments/1s2a9ke/drop_your_startup_in_one_sentence_and_how_youre/) from March 24, 2026

Implication for your company:

- your best-performing social posts will likely center on a simple, repeatable sentence
- every post should make it obvious who the product is for, what job it performs, and what manual pain it removes

Good pattern:

- "We help operators turn messy recurring work into agent-run workflows with approval gates."

Weak pattern:

- "We are redefining AI-native execution for the future of autonomous operations."

### 3. Social fatigue is real for solo founders, and consistency is a bigger problem than inspiration

The `how founders use AI for social media` run surfaced a useful founder-oriented thread about social media dread and inconsistent posting behavior.

Key evidence:

- [How I Stopped Dreading Social Media as a Solo Founder](https://www.reddit.com/r/founder/comments/1rva9lj/how_i_stopped_dreading_social_media_as_a_solo/) from March 16, 2026
- The snippet in the result described posting in random bursts, cross-posting the same caption everywhere, and letting multiple platforms go stale

Implication for your company:

- content about reducing social-media overhead will resonate
- content systems matter more than content inspiration
- "one core artifact, multiple native edits" is a better story than "AI writes everything for you"

The Gemini rerun strengthened this point. The top YouTube result for the same query was `If I Started Social Media From Scratch in 2026, I’d Do This`, and the broader YouTube matches clustered around repeatable content systems, automation workflows, and step-by-step creation processes rather than pure inspiration.

Additional implication for your company:

- teach a system, not just a tactic
- show how one insight becomes multiple native posts
- make your workflow visible enough that operators can imagine adopting the same discipline

### 4. The audience responds to anti-bot transparency and visible human ownership

One surprising but important result in the same query set came from a local-business launch post where the author emphasized transparency, truth, and anti-bot/anti-AI straightforwardness.

Key evidence:

- [Officially, HELLO Hoboken from Bricks & Minifigs!](https://www.reddit.com/r/Hoboken/comments/1s83j2r/officially_hello_hoboken_from_bricks_minifigs/) from March 30, 2026 with roughly 134 upvotes and 61 comments
- The snippet explicitly framed the post as coming from a real personal account "as an exercise in transparency"

Implication for your company:

- founder-led posts likely outperform faceless brand voice
- "here is how we actually use this internally" is a better angle than generic best-practice content
- real opinions, tradeoffs, and limitations build trust faster than perfectly polished explainer copy

### 5. AI content is useful, but audiences are wary of content farms

The `best AI content workflow for founders` run surfaced direct concern about AI-generated content farms.

Key evidence:

- [Are solo founders just building "AI content farms" now?](https://www.reddit.com/r/AskMarketing/comments/1saix4m/are_solo_founders_just_building_ai_content_farms/) from April 2, 2026

Implication for your company:

- do not position AI as infinite-volume content generation
- emphasize judgment, editing, sourcing, and operator leverage
- talk about what not to automate as often as what to automate

### 6. Distribution beats copy generation

The strongest actionable finding in the workflow query was not about writing better prompts. It was about solving the distribution and trust problem.

Key evidence:

- [I think most "AI SEO" tools are solving the wrong problem](https://www.reddit.com/r/AI_Agents/comments/1skgt1y/i_think_most_ai_seo_tools_are_solving_the_wrong/) from April 13, 2026
- The top snippet argued that most tools obsess over writing, while the real bottleneck is whether pages can be crawled, trusted, connected, and surfaced

Implication for your company:

- social content should not just help people "write faster"
- your message should focus on workflow reach, operational leverage, discoverability, and decision quality
- posts about system design, approvals, reliability, and end-to-end execution will likely differentiate better than generic prompt tips

### 7. Creator-style distribution and UGC remain powerful

The same workflow query surfaced a high-engagement thread about scaling apps via UGC and creator marketing instead of paid ads.

Key evidence:

- [We scaled 6 apps to $1M+ MRR using UGC and creator marketing instead of paid ads. Here's everything we learned](https://www.reddit.com/r/AppBusiness/comments/1shycts/we_scaled_6_apps_to_1m_mrr_using_ugc_and_creator/) from April 10, 2026 with roughly 115 upvotes and 113 comments

Implication for your company:

- a founder/operator brand can be a distribution asset
- customer-style narratives and proof clips are probably stronger than polished brand campaigns
- social content should be structured so customers, partners, and creators can easily remix or quote it

### 8. Gemini improved breadth, but not all added breadth was equally trustworthy

After rerunning with `GEMINI_API_KEY`, `/last30days` pulled in YouTube for `AI startup marketing` and `how founders use AI for social media`.

Useful additions:

- YouTube broadened the query surface beyond Reddit-only discussion
- the additional results reinforced that marketers and founders are searching for systems, playbooks, and workflow breakdowns

Important limitation:

- many of the YouTube matches were from 2025 or 2024 because the tool found no strong in-window hits and kept older items
- several titles were highly promotional, like broad "AI marketing tools" or "get customers with AI" videos

Implication for your company:

- use the YouTube additions as pattern confirmation, not as your strongest evidence base
- prioritize the recurring idea of workflow systems over the specific claims made in older, promo-heavy videos

## Strategic Recommendations For Your AI Company

### Positioning Principles

Your content should consistently communicate these ideas:

- AI is useful when it removes recurring operational work, not when it merely decorates output
- Human judgment still matters
- Approval boundaries, reliability, and clear ownership are features
- The product should feel like a working system, not an inspirational concept
- Specificity beats aspiration

### Content Pillars

These are the best-fit pillars based on the evidence above.

#### 1. Before/After Workflow Posts

Show a painful manual workflow and the AI-assisted or agent-run version beside it.

Examples:

- before: founder checks 6 dashboards, chases updates, rewrites status notes
- after: one agent packet, one approval step, one summary with citations

Why it fits:

- it proves substance
- it avoids the "AI-powered" credibility gap
- it gives clear operator value

#### 2. Anti-Hype Posts

Publish contrarian takes such as:

- "Most AI content workflows optimize writing when the real bottleneck is distribution."
- "If your AI product still needs a human to do the annoying parts, it is not automation yet."
- "The fastest way to lose trust is to sound like AI generated marketing copy."

Why it fits:

- aligns with the skepticism in the results
- gives you a clear founder voice
- performs well on X and in short-form video hooks

#### 3. Build-In-Public Operational Content

Share how you actually run your company:

- task routing
- approval gates
- worker boundaries
- failures and fixes
- prompts that did not work

Why it fits:

- transparency signal was one of the clearest trust markers in the data
- real systems are inherently more interesting than generic tips

#### 4. Distribution-System Content

Create posts explaining how to turn one operational insight into multiple native assets.

Examples:

- one internal memo becomes an X thread, a short Reel, and a founder note
- one customer workflow becomes a teardown, carousel, and demo clip

Why it fits:

- directly addresses founder social-media fatigue
- connects better to operator pain than "use AI to create 100 posts"

## Platform Playbooks

These recommendations are partially inferred because direct TikTok, Instagram, and X retrieval was blocked in this environment.

### TikTok

Best angles:

- fast screen-recorded workflow transformations
- "I replaced this weekly founder task with an agent"
- "here is the exact approval step we refuse to automate"
- "3 places AI marketing still fails in real companies"
- "if I started our social presence from scratch, this is the system I would use"

Format guidance:

- open with tension in the first sentence
- keep one post focused on one job-to-be-done
- show the product or workflow quickly
- let the founder or operator voice the lesson plainly

Good hooks:

- "Most AI marketing advice is solving the wrong problem."
- "This used to take our team 90 minutes every week."
- "If your AI tool only writes copy, you still have the hard part left."

What to avoid:

- vague "5 AI tools" listicles
- heavy jargon
- synthetic voice-of-brand scripting

### Instagram

Best angles:

- carousel breakdowns of a workflow transformation
- founder/operator Reels with subtitles
- before/after process diagrams
- short customer-proof clips
- visible content systems showing how one internal artifact becomes multiple platform-native outputs

Format guidance:

- carousel 1: problem
- carousel 2: old workflow
- carousel 3: new workflow
- carousel 4: approval boundary
- carousel 5: measurable outcome

Good topics:

- "The 4 steps we automate and the 1 we always keep human"
- "Why most AI startups sound fake online"
- "How we turn one internal ops insight into a week of content"

What to avoid:

- posting the same caption used on X
- abstract trend posts without a visual artifact

### X / Twitter

Best angles:

- contrarian operator takes
- short build-in-public threads
- lessons from failed automations
- clear opinions on where AI helps and where it still does not
- simple system posts that compress one repeatable workflow into 3 to 6 short steps

Format guidance:

- lead with the opinion, not the background
- add one concrete example or metric
- include a screenshot or artifact when possible
- write in a human founder voice, not a brand committee voice

Good post shapes:

- one-line observation plus screenshot
- 5-post thread about one workflow lesson
- "We tried X, it failed because Y, here is what worked"

What to avoid:

- generic threads assembled from recycled blog content
- polished claims with no receipts

## Recommended Editorial System

Use one weekly operating rhythm.

### Weekly cadence

- 1 operator insight post
- 1 before/after workflow post
- 1 anti-hype opinion post
- 1 build-in-public artifact post
- 1 lightweight proof or customer-like story

### Content production loop

1. Capture one real internal workflow, mistake, or decision each week.
2. Write the plain-English lesson in one sentence.
3. Turn it into a short X post first.
4. Expand it into an Instagram carousel.
5. Condense it into a TikTok script with a visual demo.
6. End each asset with one opinion or one proof point.

### Editorial filter

Before posting, ask:

- does this sound like a real operator speaking?
- is the outcome specific?
- are we showing a workflow, proof, or tradeoff?
- would this still be interesting if the phrase "AI-powered" were removed?

If the answer to the last question is no, the post is probably too weak.

## Concrete Post Ideas For Your Company

### TikTok ideas

- "We stopped asking AI to write content. We started asking it to run workflows."
- "This founder task wasted an hour every Monday. Here is the agent version."
- "3 AI automations we trust and 2 we still keep human."
- "Why most AI startup marketing feels fake."
- "How we turn one internal ops decision into 3 platform-native posts."
- "If I had to rebuild our company social presence from zero, this is the weekly system I’d use."

### Instagram ideas

- carousel: "The AI marketing trap: better writing, same broken distribution"
- carousel: "Our workflow before and after agent-based operations"
- Reel: founder explains one automation that genuinely saved time
- Reel: "where AI should stop and approval should begin"
- carousel: "5 signs your AI company messaging sounds synthetic"
- carousel: "One operator insight, three platform-native posts"

### X ideas

- "Most AI marketing tools optimize writing. The bottleneck is distribution, trust, and surfacing."
- "If your product pitch gets weaker when you remove the phrase 'AI-powered,' your positioning is doing the wrong work."
- "The most credible AI company content is not inspiration. It is receipts."
- "Founders do not need 100 posts. They need one clear point of view expressed natively on each platform."
- "The fastest way to sound fake on social is to let AI flatten your opinions."
- "The strongest AI marketing content I’m seeing is really workflow content in disguise."

## Recommended Next Step

To make this report truly strong for TikTok, Instagram, and X, rerun the same query set after adding:

- `SCRAPECREATORS_API_KEY` for TikTok and Instagram
- `XAI_API_KEY` or `AUTH_TOKEN` + `CT0` for X
- `BRAVE_API_KEY` for web coverage

Then keep the same reporting structure, but replace the inferred platform sections with direct evidence:

- recurring creator hooks
- exact engagement patterns
- platform-native post structures
- creators and accounts worth studying
- language patterns that outperform generic AI copy

## Appendix

### Raw result files

- `state/last30days_social_report/q1_ai_startup_marketing.json`
- `state/last30days_social_report/q2_founders_use_ai_social_media.json`
- `state/last30days_social_report/q3_best_ai_content_workflow_for_founders.json`
- `state/last30days_social_report/q7_high_leverage_prompt.json`

### Notes on discarded or noisy output

- The broad synthesis query still returned mostly GitHub-heavy noise even after Gemini was enabled and was not treated as a primary evidence source.
- The source-restricted social queries failed exactly because the requested sources were not configured, which is useful in itself because it confirms the missing-credentials boundary rather than silently inventing results.
- The Gemini rerun improved retrieval breadth, especially by adding YouTube to `q1` and `q2`, but many of those YouTube results were older than the target window and were treated as secondary context only.
