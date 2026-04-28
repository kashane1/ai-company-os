# After Plans — Privacy Policy

**Effective:** 2026-04-25
**Contact:** ksakhakorn@gmail.com (see [SUPPORT.md](SUPPORT.md))

> Canonical source: `docs/products/after-plans/legal/PRIVACY_POLICY.md` in
> the ai-company-os monorepo. Published mirror:
> https://kashane1.github.io/afterplans-privacy/. When changing, update the
> monorepo first, then sync to the published mirror.

After Plans is a small social-coordination app for the few minutes after a real-world activity ends. We collect the minimum information needed to make the app work and we do not share or sell what we collect.

This policy describes what data the app handles, why, and how. It is written to match what the app actually does — not as a generic template — so it stays current with the shipping build.

## What we collect

**Identity (required)**

- A first name you type. Up to 24 characters.
- A user account identifier the app generates for you. This is a random UUID, not a device identifier and not linked to anything outside After Plans.

**Things you create in the app**

- Plans you create or edit: title, optional description, optional time hint, optional venue hint.
- Place suggestions you contribute to a plan.
- Reports you file: the report reason and an optional note.
- Records of which plans you have joined or expressed interest in.
- Activity and venue declarations from onboarding (e.g. "basketball at Westside Court"). Venues are addresses we look up via Apple's MKLocalSearch when you type a place name; we never read your location to do this. Freeform venues you type that don't match a real address are stored as plain text only.
- Push notification tokens for the device you use, so we can deliver
  in-app notifications about plans you joined, contexts you're part of,
  and follow-ups after you wrap a plan.

**Things you do not give us**

- We do not request or use your location.
- We do not request access to your contacts, photos, microphone, camera, motion sensors, or health data.
- We do not collect your phone number, email address, browsing history, search history, or precise device identifiers.
- We do not use third-party advertising or analytics SDKs.

The first time you open the app, we sign you in anonymously to our backend. This creates the user account identifier described above. There is no account creation form and no password.

## What we do with what we collect

- **Make the app work.** Your first name and account identifier let other people in the same context recognize you and let the app show you the right plans. Plans, suggestions, and reports are stored so other people in the same context can see and act on them.
- **Enforce visibility rules.** The app applies row-level security on the backend so that you only see plans visible to you, and other people only see your plans according to the visibility you chose (same context, known people, or invite-only).
- **Trust and safety.** Reports route to a moderation queue we review by hand. Blocking another user is enforced server-side so that user no longer sees your plans, participation, or invites.

We do not use your data to:

- target advertising,
- build profiles for resale or third-party sharing,
- track you across other apps or websites.

## Where it is stored

After Plans is built on Supabase, a hosted Postgres + auth platform. Your plan data, profile row, and report records live in our Supabase project. Supabase processes this data on our behalf as a sub-processor; we control what goes in and what comes out.

Backend region and provisioning details will be added here once the production project is created.

## Sharing with third parties

We do not sell your data. We do not share it with advertisers, data brokers, or analytics networks.

We share data with the following service providers strictly to operate the app:

- **Supabase** — database, authentication, and realtime delivery.
- **Apple** — App Store delivery and crash diagnostics you opt into via iOS settings (we do not run our own crash analytics).

We may disclose data if required by valid legal process, or to protect the safety of users or the public. If we ever receive a government request, we will push back on overreach and notify affected users where legally permitted.

## Retention and deletion

- **Open and active plans** stay queryable so you and other participants can see them.
- **Closed plans** stay queryable in your history so the recap is meaningful.
- **Reports** are retained as long as needed to operate moderation, then summarized and pruned.

You can request deletion of your account and associated data by emailing the support address in SUPPORT.md. We will delete your profile row, your hosted plans, your participation records, and your report history within 30 days of a verified request. Plans you joined that other people host will remain, with your participation row removed.

## Your choices

- You can decline to install the app at any time.
- You can delete the app from your device at any time. This removes the local copy but does not delete the data on the backend; use the deletion request above for that.
- You can change the first name shown to other users in the app's profile screen.
- You can block any user from your block list; the change takes effect immediately.

## Children

After Plans is intended for users 17 and older. We do not knowingly collect personal data from anyone under 13 anywhere, or anyone under 17 in the United States. If we learn we have collected data from someone under those thresholds, we will delete it.

## Changes to this policy

When we change this policy, we will update the effective date at the top and post a short summary of the change in the app's What's New screen. Material changes will be flagged in-app before they take effect.

## Contact

Questions about this policy or about the data we hold about you go to the support address in [SUPPORT.md](SUPPORT.md).
