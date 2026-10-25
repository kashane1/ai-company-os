# Independent build and public repository handoff

This pack prepares a new application project. The existing `ai-company-os` checkout contains unrelated work and is not the repository to make public for this app. The eventual app deliverable must use a new, explicitly public repository, as requested by the founder.

## Independence boundary

Security reviewers inspected Guppy's installed package to assess its behavior. Product/architecture research used public descriptions and anonymized UI behavior. This is a source-separation practice, not a legal certification or a claim of a formal clean-room process: the integrating reviewer has seen summarized security findings.

Future implementation workers receive these product requirements and original tests, not vendor source, decompiled bundles, source maps, private endpoints, internal scripts, assets, catalogs, or machine audit evidence. They write independent algorithms and integrations against independently authorized interfaces. Security findings may become general requirements such as “deny unknown IPC senders”; they must not become copied code.

No Guppy code, screenshots, `.asar` contents, cookies, logs, IDs, keys, purchase/account history, or downloaded installer belongs in the app repo. Publicly describe verified app behavior only as needed for product research. Detailed potential-vulnerability material and private machine evidence remain separate; disclosure to a vendor requires a deliberate founder decision, and no message has been sent during this task.

## Public repository checklist

Before creating the app deliverable, resolve repository owner and final available name. Use a new path and a fresh Git history. Set visibility to **public** at creation; do not change the visibility of this existing repository or push its history. No repository has been created or published by this planning task.

The initial public commit should include:

- Original README with current capabilities, limitations, local/cloud distinction, supported platforms and build instructions.
- An explicitly chosen license. The pack proposes Apache-2.0 for all original application code, docs and fixtures; confirm it at M0 and retain third-party notices. If community modifications must remain open, evaluate a reciprocal license deliberately instead of assuming “public” means open-source. A public repository is already the founder's requirement; only its owner/name and license remain setup decisions.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, maintainer/contact information, issue templates, and a small public roadmap.
- Independent architecture decisions, permission model, data schema, connector contract, and original fixtures.
- `.gitignore` excluding runtime state, personal datasets, browser profiles, recordings, credentials, signing material, build artifacts, and local environment files.
- CI for tests, lint/type checks as appropriate, dependency review, secret detection, license inventory, and release artifact verification. Signing credentials stay in protected secret storage; pull requests cannot access them.

The public README may summarize Guppy as one reference product with primary links. It should not publish unsupported malware allegations, claim affiliation, or advertise superior reliability before measurement.

## Planning-to-build handoff prompt

Use this prompt to begin the independent application project after confirming the provisional direction:

> Build the first milestone of OpenTCG from its founder pack. Create a separate new public application repository under the founder-confirmed owner and available project name; do not publish or import the ai-company-os repository or private audit material. Follow the architecture and execution-plan gates. First demonstrate one authorized data source and a local watch → observation → explanation → notification → browser-handoff vertical slice with synthetic fixtures and one approved real connector. Default to account-free, no retailer-password collection, no browser-profile import, no spending, no telemetry, and no unapproved cloud dependency. Write all implementation independently. Keep mock data labeled. Add the specified correctness/security tests, show measured limitations, and provide a signed-distribution plan. Do not claim production coverage or full Guppy parity until the relevant milestones pass. Stop at any unresolved source-permission or transactional-authorization boundary and report the exact dependency.

The prompt is a handoff artifact, not an instruction that was executed during this audit.

## Review checklist for this founder pack

The complete pack should have a dated research trail, adopt/adapt/defer/skip decisions, proposed customer/problem, two or more strategic approaches, MVP/non-goals, UI flows including failures, technical architecture, data contracts, threat model, dependency-linked tasks and tests, realistic estimates, validation plan, free/paid tradeoffs, and independent public-repo guidance. Open questions must be labeled instead of disguised as settled facts.

The private audit report is a different deliverable. It must distinguish observed behavior, static capability, inferred risk, known-good evidence, and inaccessible/unperformed tests. It cannot certify that an app or computer is free from all malware.
