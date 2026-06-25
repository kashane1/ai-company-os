import { useEffect, useMemo, useRef, useState } from "react";
import { motion, useMotionValueEvent, useScroll, useTransform } from "motion/react";
import Lenis from "lenis";

const VIDEO_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260618_100841_e2e90f11-7266-46f0-9e36-00fe38315b91.mp4";

const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+~|}{[]:;?><";
const easeOut = [0.215, 0.61, 0.355, 1] as const;

type ScrambleInProps = {
  text: string;
  scrollProgress: number;
  delay: number;
  trigger: boolean;
  className?: string;
};

function randomGlyph() {
  return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
}

function useDesktopLenis() {
  useEffect(() => {
    const ua = navigator.userAgent.toLowerCase();
    const isMobileUA = /android|iphone|ipad|ipod|mobile|tablet/.test(ua);
    const isMobileWidth = window.innerWidth < 768;

    if (isMobileUA || isMobileWidth) return;

    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      wheelMultiplier: 1.0,
      touchMultiplier: 1.5
    });

    let rafId = 0;
    const raf = (time: number) => {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    };

    rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      lenis.destroy();
    };
  }, []);
}

function SynapseLogo({ className = "" }: { className?: string }) {
  const path =
    "M 1.5,23 L 1.5,33 C 1.5,38.5 6,43 11.5,43 L 16.5,43 C 22,43 26.5,38.5 26.5,33 Q 28,28 33,26.5 C 38.5,26.5 43,22 43,16.5 L 43,11.5 C 43,6 38.5,1.5 33,1.5 L 23,1.5 Q 12,12 1.5,23 Z";

  return (
    <svg className={className} viewBox="-50 -50 100 100" aria-hidden="true">
      <g fill="currentColor">
        <path d={path} />
        <path d={path} transform="rotate(90)" />
        <path d={path} transform="rotate(180)" />
        <path d={path} transform="rotate(270)" />
      </g>
    </svg>
  );
}

function ScrambleText({ text, isHovered, className = "" }: { text: string; isHovered: boolean; className?: string }) {
  const [display, setDisplay] = useState(text);

  useEffect(() => {
    if (!isHovered) {
      setDisplay(text);
      return;
    }

    let frame = 0;
    const totalFrames = text.length * 4 + 4;

    const interval = window.setInterval(() => {
      frame += 1;
      setDisplay(
        text
          .split("")
          .map((char, index) => {
            if (char === " ") return " ";
            return frame >= index * 4 ? char : randomGlyph();
          })
          .join("")
      );

      if (frame >= totalFrames) {
        window.clearInterval(interval);
        setDisplay(text);
      }
    }, 25);

    return () => window.clearInterval(interval);
  }, [isHovered, text]);

  return <span className={className}>{display}</span>;
}

function ScrambleIn({ text, scrollProgress, delay, trigger, className = "" }: ScrambleInProps) {
  const blanks = useMemo(() => text.replace(/[^\s]/g, "\u00a0"), [text]);
  const [display, setDisplay] = useState(blanks);
  const startedRef = useRef(false);

  useEffect(() => {
    if (!trigger || startedRef.current || scrollProgress >= 0.015) return;

    startedRef.current = true;
    let frame = 0;
    const duration = 900;
    const frameMs = 32;
    const totalFrames = duration / frameMs;
    let interval = 0;

    const timeout = window.setTimeout(() => {
      interval = window.setInterval(() => {
        frame += 1;
        setDisplay(
          text
            .split("")
            .map((char, index) => {
              if (char === " ") return " ";
              const threshold = (index + 1) / text.length;
              const progress = frame / totalFrames;
              if (progress < threshold * 0.55) return "\u00a0";
              if (progress < threshold) return randomGlyph();
              return char;
            })
            .join("")
        );

        if (frame >= totalFrames) {
          window.clearInterval(interval);
          setDisplay(text);
        }
      }, frameMs);
    }, delay);

    return () => {
      window.clearTimeout(timeout);
      if (interval) window.clearInterval(interval);
    };
  }, [blanks, delay, scrollProgress, text, trigger]);

  useEffect(() => {
    if (!startedRef.current || scrollProgress <= 0.015) return;

    let frame = 0;
    const frameMs = 32;
    const totalFrames = 700 / frameMs;
    const interval = window.setInterval(() => {
      frame += 1;
      const progress = frame / totalFrames;
      setDisplay(
        text
          .split("")
          .map((char, index) => {
            if (char === " ") return " ";
            const threshold = index / Math.max(1, text.length - 1);
            if (progress > threshold * 0.85 + 0.1) return "\u00a0";
            return progress > threshold * 0.65 ? randomGlyph() : char;
          })
          .join("")
      );

      if (frame >= totalFrames) {
        window.clearInterval(interval);
        setDisplay(blanks);
      }
    }, frameMs);

    return () => window.clearInterval(interval);
  }, [blanks, scrollProgress, text]);

  return <span className={className}>{display}</span>;
}

function LiquidVideoCanvas({
  onEntranceComplete,
  scrollProgressRef
}: {
  onEntranceComplete: () => void;
  scrollProgressRef: React.MutableRefObject<number>;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    let frameId = 0;
    let currentProgress = 0;
    let currentTime = 0;
    let duration = 1;
    let isSeeking = false;
    let nextSeekTime: number | null = null;
    let consecutiveErrors = 0;
    let retryTimer = 0;

    const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

    const requestSeek = (time: number) => {
      const clampedTime = clamp(time, 0, Math.max(0, duration - 0.04));

      if (Math.abs(video.currentTime - clampedTime) < 0.016 && !video.seeking) {
        isSeeking = false;
        return;
      }

      if (!isSeeking && !video.seeking) {
        isSeeking = true;
        video.currentTime = clampedTime;
      } else {
        nextSeekTime = clampedTime;
      }
    };

    const seeked = () => {
      isSeeking = false;
      if (nextSeekTime !== null) {
        const queued = nextSeekTime;
        nextSeekTime = null;
        requestSeek(queued);
      }
    };

    const seeking = () => {
      isSeeking = true;
    };

    const metadata = () => {
      duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 1;
    };

    const ready = () => {
      if (video.readyState >= 3) setIsReady(true);
    };

    const errored = () => {
      consecutiveErrors += 1;
      if (consecutiveErrors > 3) return;

      window.clearTimeout(retryTimer);
      retryTimer = window.setTimeout(() => {
        video.load();
      }, consecutiveErrors * 450);
    };

    const loaded = () => {
      consecutiveErrors = 0;
    };

    const tick = () => {
      const targetProgress = scrollProgressRef.current;
      currentProgress += (targetProgress - currentProgress) * 0.12;
      currentTime += (currentProgress * duration - currentTime) * 0.12;
      requestSeek(currentTime);

      if (shellRef.current) {
        const earlyBlur = Math.min(currentProgress / 0.5, 1) * 5;
        const lateBlur = Math.max((currentProgress - 0.5) / 0.5, 0) * 50;
        const blur = earlyBlur + lateBlur;
        const scale = 1.03 + currentProgress * 0.08;
        shellRef.current.style.filter = `blur(${blur.toFixed(2)}px)`;
        shellRef.current.style.transform = `scale(${scale.toFixed(4)})`;
      }

      frameId = requestAnimationFrame(tick);
    };

    video.addEventListener("loadedmetadata", metadata);
    video.addEventListener("loadeddata", loaded);
    video.addEventListener("canplay", ready);
    video.addEventListener("canplaythrough", ready);
    video.addEventListener("seeking", seeking);
    video.addEventListener("seeked", seeked);
    video.addEventListener("error", errored);

    if (video.readyState >= 3) setIsReady(true);
    frameId = requestAnimationFrame(tick);
    const fallback = window.setTimeout(() => setIsReady(true), 3500);

    return () => {
      cancelAnimationFrame(frameId);
      window.clearTimeout(fallback);
      window.clearTimeout(retryTimer);
      video.removeEventListener("loadedmetadata", metadata);
      video.removeEventListener("loadeddata", loaded);
      video.removeEventListener("canplay", ready);
      video.removeEventListener("canplaythrough", ready);
      video.removeEventListener("seeking", seeking);
      video.removeEventListener("seeked", seeked);
      video.removeEventListener("error", errored);
    };
  }, [scrollProgressRef]);

  return (
    <motion.div
      ref={shellRef}
      className="fixed inset-0 z-[1] bg-black will-change-transform"
      initial={{ scale: 1.12, opacity: 0 }}
      animate={isReady ? { scale: 1, opacity: 1 } : { scale: 1.12, opacity: 0 }}
      transition={{ duration: 1.4, ease: [0.215, 0.61, 0.355, 1] }}
      onAnimationComplete={() => {
        if (isReady) onEntranceComplete();
      }}
    >
      <video
        ref={videoRef}
        className="h-full w-full object-cover"
        src={VIDEO_URL}
        muted
        loop
        playsInline
        preload="auto"
      />
    </motion.div>
  );
}

function ProgressiveBlur() {
  return (
    <div
      className="pointer-events-none fixed bottom-0 left-0 right-0 z-30 h-[150px]"
      style={{
        background: "linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.76) 100%)",
        backdropFilter: "blur(4px)",
        WebkitBackdropFilter: "blur(4px)",
        maskImage: "linear-gradient(to bottom, transparent 0%, black 70%)",
        WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 70%)"
      }}
    />
  );
}

function Header({ visible }: { visible: boolean }) {
  const [hovered, setHovered] = useState(false);

  return (
    <motion.header
      className="fixed left-0 right-0 top-0 z-50 h-20 px-4 sm:px-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
    >
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between">
        <motion.button
          type="button"
          className="flex h-9 items-center gap-2 rounded-[14px] bg-white/15 px-3 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.24)] backdrop-blur-md sm:h-12 sm:gap-3 sm:px-5"
          whileHover={{ scale: 1.02, backgroundColor: "rgba(255,255,255,0.22)" }}
          whileTap={{ scale: 0.98 }}
          aria-label="SynapseX home"
        >
          <SynapseLogo className="h-5 w-5 sm:h-7 sm:w-7" />
          <span className="text-[13px] font-medium sm:text-[16px]">SynapseX</span>
        </motion.button>

        <motion.button
          type="button"
          className="flex h-9 items-center gap-2 rounded-full bg-white px-4 text-[13px] font-bold text-black sm:h-12 sm:px-6 sm:text-[15px]"
          whileHover={{ scale: 1.03, backgroundColor: "#e2e2e6" }}
          whileTap={{ scale: 0.97 }}
          onHoverStart={() => setHovered(true)}
          onHoverEnd={() => setHovered(false)}
          aria-label="Download SynapseX"
        >
          <i className="bi bi-apple text-base leading-none sm:text-lg" aria-hidden="true" />
          <ScrambleText text="Download" isHovered={hovered} />
        </motion.button>
      </div>
    </motion.header>
  );
}

function HeroContent({ visible, scrollProgress }: { visible: boolean; scrollProgress: number }) {
  const { scrollYProgress } = useScroll();
  const heroOpacity = useTransform(scrollYProgress, [0, 0.26], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 0.26], [1, 0.96]);
  const descOpacity = useTransform(scrollYProgress, [0, 0.12], [1, 0]);
  const descY = useTransform(scrollYProgress, [0, 0.12], [0, -30]);

  return (
    <motion.main
      className="sticky top-0 z-10 h-screen px-4 pb-36 pt-20 sm:px-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: 1.0, ease: "easeOut" }}
      style={{ opacity: heroOpacity, scale: heroScale }}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#ffffff_1px,transparent_1px)] opacity-[0.05] [background-size:24px_24px]" />

      <div className="relative mx-auto flex min-h-[80vh] max-w-7xl flex-col justify-between">
        <div className="grid flex-1 grid-cols-1 content-start gap-8 pt-8 md:grid-cols-2 md:pt-12">
          <h1 className="flex flex-col text-[50px] font-light leading-[0.95] tracking-[-0.03em] text-white sm:text-[70px] md:text-[85px] lg:text-[100px]">
            <ScrambleIn text="Brain" scrollProgress={scrollProgress} delay={140} trigger={visible} />
            <ScrambleIn text="And Body" scrollProgress={scrollProgress} delay={300} trigger={visible} />
          </h1>
          <div className="hidden md:block" />
        </div>

        <div className="grid grid-cols-1 items-end gap-10 md:grid-cols-2">
          <motion.p
            className="max-w-sm text-[14px] leading-relaxed text-white/60 sm:text-[15px]"
            initial={{ y: 25, opacity: 0 }}
            animate={visible ? { y: 0, opacity: 1 } : { y: 25, opacity: 0 }}
            transition={{ duration: 0.9, ease: easeOut, delay: 0.2 }}
            style={{ opacity: descOpacity, y: descY }}
          >
            Built at the intersection of neuroscience and artificial intelligence. SynapseX continuously maps neural
            pathways, cognitive load, and physiological states into a single adaptive intelligence layer.
          </motion.p>

          <h2 className="flex flex-col items-start text-[50px] font-light leading-[0.95] tracking-[-0.03em] text-white sm:text-[70px] md:items-end md:text-right md:text-[85px] lg:text-[100px]">
            <ScrambleIn text="One" scrollProgress={scrollProgress} delay={480} trigger={visible} />
            <ScrambleIn text="Network" scrollProgress={scrollProgress} delay={640} trigger={visible} />
          </h2>
        </div>
      </div>
    </motion.main>
  );
}

function PostHeroReveal({ scrollProgress }: { scrollProgress: number }) {
  const revealProgress = Math.min(1, Math.max(0, (scrollProgress - 0.42) / 0.2));
  const y = (1 - revealProgress) * 54;
  const scale = 0.98 + revealProgress * 0.02;

  return (
    <motion.section
      className="relative z-10 flex min-h-screen items-end px-4 pb-28 pt-24 sm:px-8 sm:pb-32"
      style={{
        opacity: revealProgress,
        transform: `translateY(${y.toFixed(2)}px) scale(${scale.toFixed(4)})`
      }}
    >
      <div className="mx-auto grid w-full max-w-7xl gap-10 md:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)] md:items-end">
        <div className="max-w-3xl">
          <p className="mb-5 text-[12px] uppercase tracking-[0.24em] text-white/55">Adaptive layer online</p>
          <h3 className="text-[42px] font-light leading-[0.96] tracking-[-0.03em] text-white sm:text-[64px] md:text-[84px]">
            Every signal.
            <br />
            One nervous system.
          </h3>
        </div>

        <div className="grid gap-3 text-white">
          {[
            ["Neural map", "4.2M pathways indexed"],
            ["Body state", "Live physiological model"],
            ["Cognitive load", "Predictive adaptation"]
          ].map(([label, value]) => (
            <div
              key={label}
              className="grid grid-cols-[auto_1fr] items-center gap-4 border-t border-white/20 py-4 text-[13px] sm:text-[14px]"
            >
              <span className="h-2 w-2 rounded-full bg-white shadow-[0_0_18px_rgba(255,255,255,0.72)]" />
              <span className="grid gap-1">
                <span className="text-white/50">{label}</span>
                <strong className="font-normal text-white">{value}</strong>
              </span>
            </div>
          ))}
        </div>
      </div>
    </motion.section>
  );
}

export default function App() {
  const scrollProgressRef = useRef(0);
  const [entranceComplete, setEntranceComplete] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const { scrollYProgress } = useScroll();

  useDesktopLenis();

  useMotionValueEvent(scrollYProgress, "change", (latest) => {
    scrollProgressRef.current = latest;
    setScrollProgress(latest);
  });

  return (
    <div className="relative min-h-[220vh] overflow-x-hidden">
      <LiquidVideoCanvas onEntranceComplete={() => setEntranceComplete(true)} scrollProgressRef={scrollProgressRef} />
      <Header visible={entranceComplete} />
      <HeroContent visible={entranceComplete} scrollProgress={scrollProgress} />
      <PostHeroReveal scrollProgress={scrollProgress} />
      <ProgressiveBlur />
    </div>
  );
}
