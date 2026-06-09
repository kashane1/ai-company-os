/**
 * Scroll choreography — Lenis smooth scroll synced to GSAP ScrollTrigger.
 *
 * - Hero entrance: a staggered reveal (eyebrow → headline → subhead → CTA).
 * - Section reveals: each [data-reveal] outside the hero fades up once on enter.
 * - Parallax: [data-parallax] drifts at a configurable depth on scroll.
 *
 * Only loaded when motion is enabled (see scripts/motion.ts), so reduced-motion
 * users never pay for it and content is fully visible without it.
 */
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

export function initScroll(): void {
  gsap.registerPlugin(ScrollTrigger);

  // Drive ScrollTrigger from Lenis so smooth scroll and scroll-linked animation
  // share one source of truth (avoids the classic double-scroll desync).
  const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((time) => lenis.raf(time * 1000));
  gsap.ticker.lagSmoothing(0);

  // Hero entrance stagger.
  const heroBits = gsap.utils.toArray<HTMLElement>("[data-hero] [data-reveal]");
  if (heroBits.length) {
    gsap.set(heroBits, { opacity: 0, y: 26 });
    gsap.to(heroBits, {
      opacity: 1,
      y: 0,
      duration: 0.9,
      ease: "power3.out",
      stagger: 0.12,
      delay: 0.1,
    });
  }

  // Section reveals (everything that's [data-reveal] but not inside the hero).
  for (const el of gsap.utils.toArray<HTMLElement>("[data-reveal]")) {
    if (el.closest("[data-hero]")) continue;
    gsap.fromTo(
      el,
      { opacity: 0, y: 22 },
      {
        opacity: 1,
        y: 0,
        duration: 0.7,
        ease: "power2.out",
        scrollTrigger: { trigger: el, start: "top 86%", once: true },
      },
    );
  }

  // Parallax drift.
  for (const el of gsap.utils.toArray<HTMLElement>("[data-parallax]")) {
    const depth = parseFloat(el.dataset.parallax || "0.2");
    gsap.to(el, {
      yPercent: -depth * 100,
      ease: "none",
      scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true },
    });
  }
}
