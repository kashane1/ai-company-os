/**
 * Motion entry (island). Progressive enhancement only — the page is complete and
 * readable with zero JS, and fully static under prefers-reduced-motion. Phase 2 of
 * the design engine expands this into the GSAP/ScrollTrigger choreography + the
 * Three.js/WebGL hero kit; this skeleton wires the safe baseline: a `js` flag,
 * Lenis smooth scroll, and IntersectionObserver reveals.
 */
import Lenis from "lenis";

const root = document.documentElement;
root.classList.add("js");

const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (!reduced) {
  // Smooth, inertia-based scroll — a core part of the premium feel.
  const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
  const raf = (time: number) => {
    lenis.raf(time);
    requestAnimationFrame(raf);
  };
  requestAnimationFrame(raf);

  // Reveal-on-scroll. Elements carry [data-reveal]; CSS hides them only when
  // `html.js` + no-reduced-motion, so this is the single opt-in to animation.
  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-in");
          io.unobserve(entry.target);
        }
      }
    },
    { rootMargin: "0px 0px -10% 0px", threshold: 0.15 },
  );
  for (const el of document.querySelectorAll("[data-reveal]")) io.observe(el);
}
