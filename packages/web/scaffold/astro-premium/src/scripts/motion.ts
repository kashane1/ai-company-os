/**
 * Motion entry (island). Progressive enhancement only — every page is complete
 * and readable with zero JS, and fully static under prefers-reduced-motion. The
 * heavy modules (GSAP/Lenis scroll choreography, Three.js hero) are dynamically
 * imported so they ship only when motion actually runs.
 *
 * Robustness contract: we add `html.js` (which lets CSS pre-hide [data-reveal] to
 * avoid a flash) only alongside loading the motion modules, and REMOVE it if the
 * import fails — so a chunk error can never leave content invisible.
 */
const root = document.documentElement;
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (!reduced) {
  root.classList.add("js");
  Promise.all([import("../motion/scroll"), import("../motion/hero-webgl")])
    .then(([scroll, hero]) => {
      scroll.initScroll();
      hero.initHeroWebGL();
    })
    .catch(() => {
      // Motion failed to load — drop the flag so [data-reveal] stays visible.
      root.classList.remove("js");
    });
}
