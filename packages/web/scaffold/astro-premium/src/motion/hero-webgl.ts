/**
 * WebGL hero backdrop — a slow aurora rendered on a full-screen shader plane,
 * tinted by the SYNTHESIZED tokens (--accent over --canvas). This is the literal
 * tie between the design-system synthesizer and the motion layer: the same accent
 * the palette engine produced drives the hero's light.
 *
 * Degrades cleanly: if there's no [data-hero-canvas], no WebGL context, or the
 * user prefers reduced motion (this module is never loaded in that case), the CSS
 * .glow halo already carries the hero — nothing here is required to read the page.
 */
import * as THREE from "three";

const FRAG = /* glsl */ `
  precision highp float;
  uniform vec2  uRes;
  uniform float uTime;
  uniform vec3  uAccent;
  uniform vec3  uCanvas;

  // Cheap value-noise fbm for soft, organic aurora bands.
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p){
    vec2 i = floor(p), f = fract(p);
    vec2 u = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), u.x),
               mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y);
  }
  float fbm(vec2 p){
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 5; i++){ v += a*noise(p); p *= 2.0; a *= 0.5; }
    return v;
  }

  void main(){
    vec2 uv = gl_FragCoord.xy / uRes.xy;
    vec2 p = uv * vec2(uRes.x/uRes.y, 1.0);
    float t = uTime * 0.04;
    float n = fbm(p * 2.4 + vec2(t, -t*0.6));
    n += 0.5 * fbm(p * 4.0 - vec2(t*0.7, t));
    // Concentrate the glow toward the top so it reads as light behind the headline.
    float vignette = smoothstep(1.15, 0.1, uv.y) * smoothstep(1.2, 0.2, abs(uv.x-0.5)*2.0);
    float glow = pow(clamp(n, 0.0, 1.0), 2.2) * vignette;
    vec3 col = mix(uCanvas, uAccent, glow * 0.85);
    gl_FragColor = vec4(col, 1.0);
  }
`;

const VERT = /* glsl */ `
  void main(){ gl_Position = vec4(position, 1.0); }
`;

function cssColor(name: string, fallback: string): THREE.Color {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  try {
    return new THREE.Color(raw || fallback);
  } catch {
    return new THREE.Color(fallback);
  }
}

export function initHeroWebGL(): void {
  const canvas = document.querySelector<HTMLCanvasElement>("[data-hero-canvas]");
  if (!canvas) return;

  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false });
  } catch {
    return; // no WebGL — CSS .glow carries the hero
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const scene = new THREE.Scene();
  const camera = new THREE.Camera();
  const uniforms = {
    uRes: { value: new THREE.Vector2(1, 1) },
    uTime: { value: 0 },
    uAccent: { value: cssColor("--accent", "#cf8530") },
    uCanvas: { value: cssColor("--canvas", "#0e111b") },
  };
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(2, 2),
    new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms }),
  );
  scene.add(mesh);

  const resize = () => {
    const { clientWidth: w, clientHeight: h } = canvas;
    renderer.setSize(w, h, false);
    uniforms.uRes.value.set(w, h);
  };
  resize();
  window.addEventListener("resize", resize);

  const start = performance.now();
  let raf = 0;
  const tick = () => {
    uniforms.uTime.value = (performance.now() - start) / 1000;
    renderer.render(scene, camera);
    raf = requestAnimationFrame(tick);
  };
  tick();

  // Pause when the hero scrolls out of view (saves battery on long pages).
  new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting && !raf) tick();
      else if (!e.isIntersecting && raf) {
        cancelAnimationFrame(raf);
        raf = 0;
      }
    }
  }).observe(canvas);
}
