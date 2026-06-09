/**
 * Custom cursor + magnetic CTAs — design engine v3, Phase 4.
 *
 * A lerped dot + trailing ring that replaces the native cursor on fine pointers,
 * and primary CTAs that "pull" toward the pointer (magnetic). Pure progressive
 * enhancement: no-ops on touch/coarse pointers (returns null) and is fully torn
 * down by the returned handle on a view-transition navigation.
 */
import gsap from "gsap";

export interface MotionHandle {
  destroy(): void;
}

export function initCursor(): MotionHandle | null {
  // Fine pointers only — touch/coarse devices keep the native cursor.
  if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return null;

  const root = document.documentElement;
  const dot = document.createElement("div");
  dot.className = "cursor-dot";
  dot.setAttribute("aria-hidden", "true");
  const ring = document.createElement("div");
  ring.className = "cursor-ring";
  ring.setAttribute("aria-hidden", "true");
  document.body.append(dot, ring);
  root.classList.add("has-cursor");

  const xDot = gsap.quickTo(dot, "x", { duration: 0.12, ease: "power3" });
  const yDot = gsap.quickTo(dot, "y", { duration: 0.12, ease: "power3" });
  const xRing = gsap.quickTo(ring, "x", { duration: 0.4, ease: "power3" });
  const yRing = gsap.quickTo(ring, "y", { duration: 0.4, ease: "power3" });

  const onMove = (e: PointerEvent) => {
    xDot(e.clientX);
    yDot(e.clientY);
    xRing(e.clientX);
    yRing(e.clientY);
  };
  window.addEventListener("pointermove", onMove);

  // Magnetic CTAs: primary buttons (and anything [data-magnetic]) pull toward the
  // pointer and the ring grows on hover.
  const cleanups: Array<() => void> = [];
  for (const el of gsap.utils.toArray<HTMLElement>(".btn-primary, [data-magnetic]")) {
    const mx = gsap.quickTo(el, "x", { duration: 0.4, ease: "power3" });
    const my = gsap.quickTo(el, "y", { duration: 0.4, ease: "power3" });
    const enter = () => ring.classList.add("is-hot");
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      mx((e.clientX - (r.left + r.width / 2)) * 0.3);
      my((e.clientY - (r.top + r.height / 2)) * 0.3);
    };
    const leave = () => {
      ring.classList.remove("is-hot");
      mx(0);
      my(0);
    };
    el.addEventListener("pointerenter", enter);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", leave);
    cleanups.push(() => {
      el.removeEventListener("pointerenter", enter);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", leave);
    });
  }

  return {
    destroy() {
      window.removeEventListener("pointermove", onMove);
      for (const c of cleanups) c();
      dot.remove();
      ring.remove();
      root.classList.remove("has-cursor");
    },
  };
}
