import { defineConfig } from "astro/config";

// Static-first output: the landing page builds to plain HTML/CSS in dist/,
// which is portable, cheap to host, and what the web gate validates. The
// `site` is set at deploy time (DeployTarget) once a URL/domain is known.
export default defineConfig({
  output: "static",
  site: "{{SITE_URL}}",
  build: { format: "directory" },
});
