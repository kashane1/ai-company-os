import { defineConfig } from "astro/config";

// Premium stack — static-first shell with interactive/WebGL islands shipped only
// where used (Astro bundles per-page <script> imports, so GSAP/Lenis/Three.js are
// tree-shaken out of pages that don't reference them). Builds to portable
// HTML/CSS/JS in dist/, validated by the web gate and deployed by the deploy lane.
export default defineConfig({
  output: "static",
  site: "{{SITE_URL}}",
  build: { format: "directory" },
});
