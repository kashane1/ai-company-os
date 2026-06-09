/**
 * Motion entry (island). Progressive enhancement only — every page is complete
 * and readable with zero JS, and fully static under prefers-reduced-motion. The
 * heavy modules (GSAP/Lenis scroll choreography, Three.js hero, custom cursor) are
 * dynamically imported so they ship only when motion actually runs.
 *
 * Lifecycle-safe (v3): init is wrapped in boot()/shutdown() and re-runs on Astro's
 * `astro:page-load` while tearing down on `astro:before-swap` — so the motion layer
 * survives client-side (view-transition) navigations without leaking ScrollTriggers
 * or double-binding. Without ViewTransitions enabled those events simply never fire
 * and boot() runs once on initial load (the MPA path).
 *
 * Robustness contract: we add `html.js` (which lets CSS pre-hide [data-reveal] to
 * avoid a flash) only alongside loading the motion modules, and REMOVE it if the
 * import fails — so a chunk error can never leave content invisible.
 */
const root = document.documentElement;
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let active = false;
let teardown: (() => void) | null = null;

async function boot(): Promise<void> {
  if (reduced || active) return;
  active = true;
  root.classList.add("js");
  try {
    const [scroll, hero, cursor] = await Promise.all([
      import("../motion/scroll"),
      import("../motion/hero-webgl"),
      import("../motion/cursor"),
    ]);
    const scrollHandle = scroll.initScroll();
    hero.initHeroWebGL();
    const cursorHandle = cursor.initCursor();
    teardown = () => {
      scrollHandle?.destroy?.();
      cursorHandle?.destroy?.();
    };
  } catch {
    // Motion failed to load — drop the flag so [data-reveal] stays visible.
    root.classList.remove("js");
    active = false;
  }
}

function shutdown(): void {
  teardown?.();
  teardown = null;
  active = false;
}

boot();
// View-transition lifecycle (no-ops unless <ViewTransitions/ClientRouter> is on).
document.addEventListener("astro:before-swap", shutdown);
document.addEventListener("astro:page-load", () => {
  void boot();
});
