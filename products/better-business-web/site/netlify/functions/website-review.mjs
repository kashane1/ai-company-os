// Netlify Function — capture "free website review" form submissions.
//
// Used instead of native Netlify Forms because this site is deployed manually
// (file-digest / CLI, no git build), which doesn't trigger form detection. The
// function writes each submission to a Netlify Blobs store ("inbound-reviews");
// a local poller (scripts/web/pull-inbound.mjs) pulls them into the platform as
// typed WebsiteReviewRequest records under state/prospects/inbound/ (todo 068).
//
// The "website" field is the prospect's current site (or "none"). It is stored
// raw and treated as UNTRUSTED — any automated fetch downstream must pass it
// through packages.policies.url_guard first (todo 065).

import { getStore } from "@netlify/blobs";

const redirect = (req, to, status = 303) =>
  new Response(null, { status, headers: { Location: new URL(to, req.url).toString() } });

export default async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });

  let form;
  try {
    form = await req.formData();
  } catch {
    return new Response("Bad request", { status: 400 });
  }
  const field = (k) => (form.get(k) ?? "").toString().trim();

  // Honeypot: silently accept-and-drop obvious bots.
  if (field("bot-field")) return redirect(req, "/thanks/");

  const name = field("name");
  const contact = field("contact");
  if (!name || !contact) return new Response("Missing required fields", { status: 400 });

  const submission = {
    submission_id: crypto.randomUUID(),
    name,
    contact,
    business: field("business"),
    website: field("website"),
    received_at: new Date().toISOString(),
    source: "netlify-function",
  };

  try {
    const store = getStore("inbound-reviews");
    await store.setJSON(submission.submission_id, submission);
  } catch (err) {
    console.error("blob write failed", err);
    return new Response("Could not store submission", { status: 500 });
  }

  return redirect(req, "/thanks/");
};
