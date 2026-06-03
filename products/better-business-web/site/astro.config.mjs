import { defineConfig } from "astro/config";

// Better Business Web — the agency's own funnel/landing site (its own Astro
// project, NOT the shared prospect-preview scaffold). Built with `astro build`
// (plan §4 decision); deployed to Netlify, which detects the contact form
// natively from the built HTML.
export default defineConfig({
  site: "https://better-business-web.netlify.app",
});
