import { defineConfig } from "astro/config";
import react from "@astrojs/react";

// Better Business Web — the agency's own funnel/landing site (its own Astro
// project, NOT the shared prospect-preview scaffold). Built with `astro build`
// (plan §4 decision); deployed to Netlify, which detects the contact form
// natively from the built HTML.
//
// React is added only for the interactive Build-Your-Own-Bundle island
// (src/components/BundleBuilder.tsx); the rest of the site stays static Astro.
export default defineConfig({
  site: "https://better-business-web.netlify.app",
  integrations: [react()],
});
