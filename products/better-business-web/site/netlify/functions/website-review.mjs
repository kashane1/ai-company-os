// Netlify Function — capture "free website review" form submissions + notify.
//
// Used instead of native Netlify Forms because this site is deployed manually
// (file-digest / CLI, no git build), which doesn't trigger form detection. The
// function writes each submission to a Netlify Blobs store ("inbound-reviews");
// a local poller (scripts/web/pull-inbound.mjs) pulls them into the platform as
// typed WebsiteReviewRequest records under state/prospects/inbound/ (todo 068).
//
// G2a: after persisting, it emails the operator (LEAD_NOTIFY_EMAIL) via Resend.
// The email is BEST-EFFORT — the durable record is the Blob, so a Resend outage
// never 500s the form or loses the lead (persist-first, return 303 either way).
// RESEND_API_KEY / LEAD_NOTIFY_EMAIL / LEAD_FROM_EMAIL are read from process.env
// (set in Netlify env only) — never a PUBLIC_/VITE_ prefix, never shipped in dist/.
//
// The "website" field is the prospect's current site (or "none"). It is stored
// raw and treated as UNTRUSTED — any automated fetch downstream must pass it
// through packages.policies.url_guard first (todo 065).

import { getStore } from "@netlify/blobs";

const redirect = (req, to, status = 303) =>
  new Response(null, { status, headers: { Location: new URL(to, req.url).toString() } });

// Escape user-supplied text before placing it in the notification HTML so a
// crafted name/business/website can't inject markup into the operator's inbox.
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]),
  );

// Best-effort operator notification. Returns the Resend message id, or null on
// any failure (missing config, non-2xx, thrown). Never throws.
async function notifyLead(submission) {
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.LEAD_NOTIFY_EMAIL || "ksakhakorn@gmail.com";
  const from = process.env.LEAD_FROM_EMAIL || "Lead Bot <onboarding@resend.dev>";
  if (!apiKey) {
    console.error("resend not configured (RESEND_API_KEY missing) — skipping notify");
    return null;
  }

  const { submission_id, name, contact, business, website, city, state, interest, notes, received_at } = submission;
  const looksEmail = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(contact || "");
  // "City, ST" — feeds the operator's lookup + the process command's --city.
  const location = [city, state].map((s) => (s || "").trim()).filter(Boolean).join(", ");
  // Map the radio value to a readable line for the operator email.
  const interestLabel = {
    preview: "Preview of a new website",
    review: "Review of their current website",
    both: "Both — review current site + preview a new one",
  }[interest] || "Not specified";

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        // Dedupe function retries within Resend's 24h idempotency window.
        "Idempotency-Key": `lead-${submission_id}`,
      },
      body: JSON.stringify({
        from,
        to,
        ...(looksEmail ? { reply_to: contact } : {}),
        subject: `New website-review lead: ${name}${business ? ` (${business})` : ""}`,
        // website is shown as escaped TEXT, never a clickable link (untrusted).
        html: [
          "<h2>New website-review lead</h2>",
          `<p><strong>Name:</strong> ${esc(name)}</p>`,
          `<p><strong>Contact:</strong> ${esc(contact)}</p>`,
          `<p><strong>Business:</strong> ${esc(business) || "—"}</p>`,
          `<p><strong>Location:</strong> ${esc(location) || "—"}</p>`,
          `<p><strong>Looking for:</strong> ${esc(interestLabel)}</p>`,
          `<p><strong>Current site:</strong> ${esc(website) || "none"}</p>`,
          `<p><strong>Notes:</strong> ${esc(notes) || "—"}</p>`,
          `<p><strong>Received:</strong> ${esc(received_at)}</p>`,
          `<p><strong>Submission ID:</strong> <code>${esc(submission_id)}</code></p>`,
          "<hr>",
          "<p>Pull + act on it:</p>",
          "<pre>node scripts/web/pull-inbound.mjs\n" +
            `python scripts/agency/process_inbound_review.py --id ${esc(submission_id)}` +
            `${location ? ` --city ${esc(JSON.stringify(location))}` : ""}</pre>`,
        ].join("\n"),
      }),
    });
    if (!res.ok) {
      console.error("resend send failed", res.status, await res.text());
      return null;
    }
    const data = await res.json();
    return data?.id ?? null;
  } catch (err) {
    console.error("resend send threw", err);
    return null;
  }
}

export default async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });

  let form;
  try {
    form = await req.formData();
  } catch {
    return new Response("Bad request", { status: 400 });
  }
  const field = (k) => (form.get(k) ?? "").toString().trim();

  // Honeypot: silently accept-and-drop obvious bots. No persist, no notify.
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
    city: field("city"),
    state: field("state").toUpperCase().slice(0, 2),
    interest: field("interest"), // preview | review | both
    notes: field("notes").slice(0, 1000), // optional free-text; capped as a guard
    received_at: new Date().toISOString(),
    source: "netlify-function",
    notified_at: null,
    notify_message_id: null,
  };

  // 1) PERSIST FIRST — the durable record. Only this path may 500.
  const store = getStore("inbound-reviews");
  try {
    await store.setJSON(submission.submission_id, submission);
  } catch (err) {
    console.error("blob write failed", err);
    return new Response("Could not store submission", { status: 500 });
  }

  // 2) NOTIFY (best-effort, non-fatal). Failure → still 303 to /thanks/.
  const messageId = await notifyLead(submission);
  if (messageId) {
    try {
      await store.setJSON(submission.submission_id, {
        ...submission,
        notified_at: new Date().toISOString(),
        notify_message_id: messageId,
      });
    } catch (err) {
      console.error("notify-stamp write failed (non-fatal)", err);
    }
  }

  return redirect(req, "/thanks/");
};
