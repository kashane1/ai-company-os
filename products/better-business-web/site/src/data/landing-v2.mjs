import portfolio from "./portfolio.json";

export const featuredDemoSlugs = ["dog-grooming", "fish-tacos", "auto-repair", "gun-store"];

export const stats = [
  { value: "2 days", label: "Until your first preview" },
  { value: "$0", label: "Due before you say yes" },
  // Reflects the real number of demos; updates automatically as more are added.
  { value: String(portfolio.demos.length), label: "Sample sites to explore" },
];

export const storyPanels = [
  {
    kicker: "Step 1",
    title: "See it before you pay",
    body: "Tell us about your business and we turn it into a real, clickable preview. You can open it on your phone and judge the look for yourself before any money changes hands.",
  },
  {
    kicker: "Step 2",
    title: "Get the message right",
    body: "A good site answers four things fast: what you do, where you do it, why people can trust you, and what to do next. We make sure yours does all four without making anyone hunt.",
  },
  {
    kicker: "Step 3",
    title: "Launch when you're happy",
    body: "Once you give the go-ahead, we polish the writing, make everything work on a phone, set up your forms, and handle the launch so the finished site feels solid from day one.",
  },
];

export const packages = [
  {
    name: "Conversion Snapshot",
    price: "$100",
    description:
      "A quick, focused look at what's confusing or missing on your current site, plus the easy wins you can fix right away.",
  },
  {
    name: "Website Audit",
    price: "$250",
    description:
      "A deeper, page-by-page review with clear recommendations you can use, whether or not we end up building your site together.",
  },
  {
    name: "Preview Build",
    price: "Free first look",
    description:
      "A free, clickable preview of a new homepage built for your business. You see the full price up front and pay nothing until you give the word.",
  },
];

export const labItems = [
  "A clear offer",
  "Reasons to trust you",
  "Local search basics",
  "Built for phones",
  "Easy contact forms",
  "A real launch",
];

// Risk-reversal chips — the strongest trust signal for a studio with no client
// roster yet. Plain facts, no hype.
export const riskBar = [
  "$0 before you say yes",
  "Cancel the monthly anytime",
  "You own your site and everything on it",
];

// Founder line — first-person on purpose (the personal corner of the page).
export const founder =
  "Hi, I'm Kashane. I build every site myself, so the person you talk to is the person doing the work.";

// Underdog / affordability pitch — company "we" voice. Anchors our real prices
// against a defensible top-agency figure. Prices here must match packages.json.
export const pitch = {
  eyebrow: "Fair pricing",
  title: "Why we cost less than a top agency.",
  body: "A top agency would charge $8,000 to $15,000 to build a site like this, then bill you every month after. We're a newer, smaller studio still building our name, so we charge a fraction of that. Sites start at $600 to set up plus $50 a month, and you get the same careful work.",
};
