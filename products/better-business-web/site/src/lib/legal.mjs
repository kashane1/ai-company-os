// Single source of truth for the real-world facts the legal pages share, so the
// Privacy Policy, Terms, Refund Policy, and Cookie Policy can never drift apart.
// Edit values HERE, not in each page.
//
// ⚠️ ONE value can't be derived from the codebase and MUST be set by a human
//    before these pages are relied on: `governingLawState`. Until it's filled
//    in, the Terms page renders a visible "needs input" marker in its place so
//    it can't ship unnoticed. Everything else below is grounded in how the site
//    actually works (Netlify hosting + Functions + Blobs, Stripe Checkout,
//    Resend operator notifications).
//
// These are plain-English, good-faith drafts — not legal advice. Have a
// professional review them before depending on them.

export const legal = {
  businessName: "Better Business Web",
  operatorName: "Kashane Sakhakorn",
  // Honest description of who the customer is contracting with. If you register
  // an LLC, change this to e.g. "Better Business Web LLC, a Georgia limited
  // liability company".
  entityDescription: "a sole proprietorship operated by Kashane Sakhakorn",

  // Published contact for privacy/legal questions. Change here to use a
  // dedicated address (e.g. hello@yourdomain) instead of the personal inbox.
  contactEmail: "ksakhakorn@gmail.com",

  siteUrl: "https://better-business-web.netlify.app",
  domain: "better-business-web.netlify.app",

  // The U.S. state whose law governs our agreements — California, where the
  // operator resides and does business. (No LLC yet; update entityDescription
  // above if/when one is registered.)
  governingLawState: "California",

  // Update whenever you materially change any policy.
  effectiveDate: "June 13, 2026",
};

// Third parties that process data on our behalf ("sub-processors"), kept here so
// the Privacy Policy lists exactly what the code actually uses.
export const subProcessors = [
  {
    name: "Netlify",
    role: "Website hosting, serverless functions, and storage of form/order submissions.",
    url: "https://www.netlify.com/privacy/",
  },
  {
    name: "Stripe",
    role: "Payment processing for setup fees and monthly subscriptions. Card details go directly to Stripe; we never receive or store full card numbers.",
    url: "https://stripe.com/privacy",
  },
  {
    name: "Resend",
    role: "Sends the email that notifies us when you submit the review form or place an order.",
    url: "https://resend.com/legal/privacy-policy",
  },
];
