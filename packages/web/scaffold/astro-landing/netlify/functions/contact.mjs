// Netlify Function — capture a client site's contact-form submissions + notify.
//
// This is the `contact_forms` service backend: the scaffolded site's contact
// form posts here. It mirrors the agency's own website-review function — native
// Netlify Forms isn't used because client sites deploy via file-digest / CLI
// (no git build), which doesn't trigger Netlify form detection.
//
// Flow: persist each submission to a Netlify Blobs store ("inbound-leads") FIRST
// (the durable record), then best-effort email the business owner via Resend.
// A Resend outage never 500s the form or loses a lead (persist-first, 303 either
// way). Set per client in their Netlify env (never a PUBLIC_/VITE_ prefix,
// never shipped in dist/):
//   RESEND_API_KEY   — the agency (or client) Resend key
//   LEAD_NOTIFY_EMAIL — where leads go (the client's inbox)
//   LEAD_FROM_EMAIL   — a verified @send.<domain> sender (never @resend.dev in prod)
//
// SMS + CRM routing are NOT wired here: form→SMS hits the same A2P 10DLC / TCPA
// gate as review-SMS, so it stays off until that lands; CRM routing is delivered
// via the `crm_setup` service. See docs/agency/runbooks/contact-forms-setup.md.

import { getStore } from "@netlify/blobs";

const redirect = (req, to, status = 303) =>
  new Response(null, { status, headers: { Location: new URL(to, req.url).toString() } });

// Escape user text before placing it in the notification HTML so a crafted
// name/message can't inject markup into the owner's inbox.
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]),
  );

// Best-effort owner notification. Returns the Resend message id, or null on any
// failure (missing config, non-2xx, thrown). Never throws.
async function notifyOwner(submission) {
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.LEAD_NOTIFY_EMAIL;
  const from = process.env.LEAD_FROM_EMAIL || "Lead Bot <onboarding@resend.dev>";
  if (!apiKey || !to) {
    console.error("contact: resend not configured (RESEND_API_KEY/LEAD_NOTIFY_EMAIL) — skipping notify");
    return null;
  }
  const { submission_id, name, contact, message, received_at } = submission;
  const looksEmail = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(contact || "");
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "Idempotency-Key": `lead-${submission_id}`,
      },
      body: JSON.stringify({
        from,
        to,
        ...(looksEmail ? { reply_to: contact } : {}),
        subject: `New website lead: ${name || contact}`,
        html: [
          "<h2>New website lead</h2>",
          `<p><strong>Name:</strong> ${esc(name) || "—"}</p>`,
          `<p><strong>Contact:</strong> ${esc(contact)}</p>`,
          `<p><strong>Message:</strong> ${esc(message) || "—"}</p>`,
          `<p><strong>Received:</strong> ${esc(received_at)}</p>`,
          `<p><strong>Submission ID:</strong> <code>${esc(submission_id)}</code></p>`,
        ].join("\n"),
      }),
    });
    if (!res.ok) {
      console.error("contact: resend send failed", res.status, await res.text());
      return null;
    }
    const data = await res.json();
    return data?.id ?? null;
  } catch (err) {
    console.error("contact: resend send threw", err);
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

  const contact = field("contact");
  if (!contact) return new Response("Missing required fields", { status: 400 });

  const submission = {
    submission_id: crypto.randomUUID(),
    name: field("name"),
    contact,
    message: field("message"),
    received_at: new Date().toISOString(),
    source: "contact-form",
    notified_at: null,
    notify_message_id: null,
  };

  // 1) PERSIST FIRST — the durable record. Only this path may 500.
  const store = getStore("inbound-leads");
  try {
    await store.setJSON(submission.submission_id, submission);
  } catch (err) {
    console.error("contact: blob write failed", err);
    return new Response("Could not store submission", { status: 500 });
  }

  // 2) NOTIFY (best-effort, non-fatal). Failure → still 303 to /thanks/.
  const messageId = await notifyOwner(submission);
  if (messageId) {
    try {
      await store.setJSON(submission.submission_id, {
        ...submission,
        notified_at: new Date().toISOString(),
        notify_message_id: messageId,
      });
    } catch (err) {
      console.error("contact: notify-stamp write failed (non-fatal)", err);
    }
  }

  return redirect(req, "/thanks/");
};
