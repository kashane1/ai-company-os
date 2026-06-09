/**
 * Scroll choreography — Lenis smooth scroll synced to GSAP ScrollTrigger.
 *
 * - Choreography is keyed to the build's `--motion-preset` token (v3): cinematic
 *   builds get a slower, deeper stagger + stronger parallax; precise/product builds
 *   get a tight, restrained reveal. (In v2 the token was synthesized but never read.)
 * - Hero entrance: a staggered reveal (eyebrow → headline → subhead → CTA).
 * - Section reveals: each [data-reveal] outside the hero fades up once on enter.
 * - Parallax: [data-parallax] drifts at a configurable depth × the preset multiplier.
 *
 * Returns a teardown handle so the entry (scripts/motion.ts) can revert cleanly
 * across Astro view-transition navigations. Only loaded when motion is enabled, so
 * reduced-motion users never pay for it and content is fully visible without it.
 */
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

export interface MotionHandle {
  destroy(): void;
}

interface Preset {
  stagger: number;
  ease: string;
  y: number;
  duration: number;
  parallax: number;
}

// Motion personality per archetype (the synthesizer sets --motion-preset).
const PRESETS: Record<string, Preset> = {
  cinematic: { stagger: 0.14, ease: "power3.out", y: 34, duration: 1.0, parallax: 1.3 },
  precise: { stagger: 0.06, ease: "power2.out", y: 16, duration: 0.6, parallax: 0.7 },
  gallery: { stagger: 0.1, ease: "power2.out", y: 24, duration: 0.8, parallax: 1.1 },
  editorial: { stagger: 0.12, ease: "power3.out", y: 28, duration: 0.9, parallax: 1.0 },
  calm: { stagger: 0.1, ease: "power2.out", y: 22, duration: 0.8, parallax: 1.0 },
};

function activePreset(): Preset {
  const name = getComputedStyle(document.documentElement)
    .getPropertyValue("--motion-preset")
    .replace(/['"]/g, "")
    .trim();
  return PRESETS[name] ?? PRESETS.calm;
}

export function initScroll(): MotionHandle {
  gsap.registerPlugin(ScrollTrigger);
  const p = activePreset();

  // Drive ScrollTrigger from Lenis so smooth scroll and scroll-linked animation
  // share one source of truth (avoids the classic double-scroll desync).
  const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
  lenis.on("scroll", ScrollTrigger.update);
  const tick = (time: number) => lenis.raf(time * 1000);
  gsap.ticker.add(tick);
  gsap.ticker.lagSmoothing(0);

  // All animations live in a context so a single revert() tears them (and their
  // ScrollTriggers) down on a view-transition navigation.
  const ctx = gsap.context(() => {
    const heroBits = gsap.utils.toArray<HTMLElement>("[data-hero] [data-reveal]");
    if (heroBits.length) {
      gsap.set(heroBits, { opacity: 0, y: p.y });
      gsap.to(heroBits, {
        opacity: 1,
        y: 0,
        duration: p.duration,
        ease: p.ease,
        stagger: p.stagger,
        delay: 0.1,
      });
    }

    for (const el of gsap.utils.toArray<HTMLElement>("[data-reveal]")) {
      if (el.closest("[data-hero]")) continue;
      gsap.fromTo(
        el,
        { opacity: 0, y: p.y * 0.8 },
        {
          opacity: 1,
          y: 0,
          duration: p.duration * 0.8,
          ease: p.ease,
          scrollTrigger: { trigger: el, start: "top 86%", once: true },
        },
      );
    }

    for (const el of gsap.utils.toArray<HTMLElement>("[data-parallax]")) {
      const depth = parseFloat(el.dataset.parallax || "0.2") * p.parallax;
      gsap.to(el, {
        yPercent: -depth * 100,
        ease: "none",
        scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true },
      });
    }
  });

  return {
    destroy() {
      ctx.revert();
      gsap.ticker.remove(tick);
      lenis.destroy();
    },
  };
}
