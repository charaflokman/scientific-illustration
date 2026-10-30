// Pro motion-graphics template for render_video.py --template pro.
// Editorial, journal-like look (serif headlines, mono numbers, one warm accent, film grain, hairline frame) instead of
// the generic "AI startup" look (glowing blobs, gradient text, neon). Kinetic type, animated counters, comparisons,
// bar charts, tilted showcases, grid montage, real transitions (@remotion/transitions), motion blur and a soundtrack.
import React from "react";
import {AbsoluteFill, Audio, Composition, Easing, Img, interpolate, registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import {TransitionSeries, springTiming} from "@remotion/transitions";
import {slide} from "@remotion/transitions/slide";
import {wipe} from "@remotion/transitions/wipe";
import {flip} from "@remotion/transitions/flip";
import {fade} from "@remotion/transitions/fade";
import {CameraMotionBlur} from "@remotion/motion-blur";
import {loadFont as loadDisplay} from "@remotion/google-fonts/Fraunces";
import {loadFont as loadBody} from "@remotion/google-fonts/IBMPlexSans";
import {loadFont as loadMono} from "@remotion/google-fonts/IBMPlexMono";

const {fontFamily: DISPLAY} = loadDisplay("normal", {weights: ["600"], subsets: ["latin"]});
loadDisplay("italic", {weights: ["600"], subsets: ["latin"]});
const {fontFamily: BODY} = loadBody("normal", {weights: ["400", "500"], subsets: ["latin"]});
const {fontFamily: MONO} = loadMono("normal", {weights: ["500"], subsets: ["latin"]});

type Scene = {type: string; seconds?: number; transition?: string; [k: string]: any};
type Spec = {fps?: number; width?: number; height?: number; accent?: string; scenes: Scene[]; credits?: string; audio?: string; brand?: string};

const TR = 14; // transition length in frames
const INK = "#0F1115", PAPER = "#F4F1EA", MUTED = "#A9AFBC", LINE = "rgba(255,255,255,.12)";
const ease = Easing.bezier(0.16, 1, 0.3, 1);

const useEnter = (delay = 0, damping = 200) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: f - delay, fps, config: {damping}});
};

// flat ink, soft vignette light, film grain that changes every 2 frames, hairline frame
const Bg: React.FC = () => {
  const f = useCurrentFrame();
  const seed = Math.floor(f / 2) % 8;
  return (
    <AbsoluteFill style={{background: INK, overflow: "hidden"}}>
      <AbsoluteFill style={{background: "radial-gradient(ellipse at 28% 18%, rgba(255,255,255,.06), transparent 62%)"}} />
      <svg width="100%" height="100%" style={{position: "absolute", opacity: .10, mixBlendMode: "screen"}}>
        <filter id={`g${seed}`}><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed={seed} /></filter>
        <rect width="100%" height="100%" filter={`url(#g${seed})`} /></svg>
      <div style={{position: "absolute", inset: 36, border: "1px solid rgba(255,255,255,.09)"}} />
    </AbsoluteFill>);
};

const Kicker: React.FC<{text?: string; delay?: number}> = ({text, delay = 0}) => {
  const k = useEnter(delay);
  if (!text) return null;
  return <div style={{fontFamily: MONO, fontSize: 26, letterSpacing: 4, textTransform: "uppercase", color: "var(--a)",
    opacity: k, transform: `translateY(${(1 - k) * 20}px)`, marginBottom: 24, display: "flex", alignItems: "center", gap: 16}}>
    <span style={{width: 44 * k, height: 2, background: "var(--a)", display: "inline-block"}} />{text}</div>;
};

// words rise in one by one behind a mask; highlighted words in accent italic
const Kinetic: React.FC<{text: string; size: number; delay?: number; hi?: string; left?: boolean}> = ({text, size, delay = 0, hi, left}) => {
  const f = useCurrentFrame();
  const his = (hi ?? "").split(" ");
  return <div style={{fontFamily: DISPLAY, fontWeight: 600, fontSize: size, lineHeight: 1.08, letterSpacing: -size * .012, color: PAPER,
    display: "flex", flexWrap: "wrap", justifyContent: left ? "flex-start" : "center", gap: `0 ${size * .26}px`}}>
    {text.split(" ").map((w, i) => {
      const t = interpolate(f - delay - i * 4, [0, 16], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease});
      const isHi = hi && his.includes(w);
      return <span key={i} style={{overflow: "hidden", display: "inline-block", paddingBottom: size * .12}}>
        <span style={{display: "inline-block", transform: `translateY(${(1 - t) * 110}%)`, color: isHi ? "var(--a)" : PAPER,
          fontStyle: isHi ? "italic" : "normal"}}>{w}</span></span>;
    })}</div>;
};

const Hook: React.FC<{s: Scene}> = ({s}) => {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, (s.seconds ?? 3) * 30], [1.06, 1]);
  const sub = useEnter(22);
  return <AbsoluteFill style={{justifyContent: "center", alignItems: "center", padding: 160, textAlign: "center", transform: `scale(${z})`}}>
    <Kicker text={s.kicker} />
    <Kinetic text={s.title} size={s.size ?? 130} hi={s.highlight} delay={4} />
    {s.subtitle && <div style={{marginTop: 34, fontFamily: BODY, fontSize: 38, color: MUTED, opacity: sub}}>{s.subtitle}</div>}
  </AbsoluteFill>;
};

// cold open: the most striking visual, full frame and already moving at frame 0, with a curiosity headline.
// Nothing fades in from black: the first frame is the thumbnail and must earn the next second.
const Open: React.FC<{s: Scene}> = ({s}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const dur = (s.seconds ?? 2.5) * fps;
  const z = interpolate(f, [0, dur], [1.18, 1.32]);
  const rot = interpolate(f, [0, dur], [-2, 2]);
  const tag = interpolate(f, [dur * .35, dur * .55], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  return <AbsoluteFill>
    <AbsoluteFill style={{justifyContent: "center", alignItems: "center", transform: `translateX(${s.offset ?? 260}px) scale(${z}) rotate(${rot}deg)`}}>
      <Img src={staticFile(s.src)} style={{width: "78%", objectFit: "contain", filter: "drop-shadow(0 60px 80px rgba(0,0,0,.6))"}} />
    </AbsoluteFill>
    <AbsoluteFill style={{background: "linear-gradient(90deg, rgba(15,17,21,.97) 0%, rgba(15,17,21,.85) 34%, rgba(15,17,21,0) 62%)"}} />
    <AbsoluteFill style={{justifyContent: "center", padding: "0 120px"}}>
      <div style={{width: 900}}>
        <div style={{fontFamily: MONO, fontSize: 26, letterSpacing: 4, color: "var(--a)", marginBottom: 26}}>{s.kicker}</div>
        <div style={{fontFamily: DISPLAY, fontWeight: 600, fontSize: s.size ?? 124, lineHeight: 1.02, letterSpacing: -1.5, color: PAPER}}>
          {s.title}<br /><span style={{color: "var(--a)", fontStyle: "italic"}}>{s.highlight}</span></div>
        {s.subtitle && <div style={{marginTop: 34, fontFamily: BODY, fontSize: 36, color: MUTED, opacity: tag, transform: `translateY(${(1 - tag) * 16}px)`}}>{s.subtitle}</div>}
      </div>
    </AbsoluteFill>
  </AbsoluteFill>;
};

// input -> output in one shot: a prompt types itself, a few spec lines flash, then the finished figure wipes in
const Demo: React.FC<{s: Scene}> = ({s}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const dur = (s.seconds ?? 5) * fps;
  const prompt: string = s.prompt ?? "";
  const typed = prompt.slice(0, Math.floor(interpolate(f, [0, dur * .25], [0, prompt.length], {extrapolateLeft: "clamp", extrapolateRight: "clamp"})));
  const spec: string[] = s.spec ?? [];
  // never start on an empty frame: the figure is already a third visible at frame 0 and finishes by 45%
  const reveal = interpolate(f, [0, dur * .45], [35, 100], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease});
  const card = {background: "#161920", border: `1px solid ${LINE}`, borderRadius: 4, padding: "28px 32px"};
  return <AbsoluteFill style={{padding: "130px 110px 100px", flexDirection: "column"}}>
    <div style={{display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 34}}>
      <Kinetic text={s.title} size={64} hi={s.highlight} left delay={-20} />
      {s.kicker && <div style={{fontFamily: MONO, fontSize: 22, color: "var(--a)", letterSpacing: 3}}>{s.kicker}</div>}
    </div>
    <div style={{display: "flex", gap: 44, flex: 1, minHeight: 0}}>
      <div style={{width: 640, display: "flex", flexDirection: "column", gap: 24}}>
        <div style={card}>
          <div style={{fontFamily: MONO, fontSize: 18, color: "#7C8496", marginBottom: 14}}>YOU WRITE</div>
          <div style={{fontFamily: BODY, fontSize: 36, lineHeight: 1.4, color: PAPER, minHeight: 250}}>{typed}
            <span style={{opacity: Math.floor(f / 8) % 2 ? 0 : 1, color: "var(--a)"}}>▍</span></div>
        </div>
        <div style={{...card, flex: 1}}>
          <div style={{fontFamily: MONO, fontSize: 18, color: "#7C8496", marginBottom: 12}}>THE AGENT WRITES</div>
          {spec.map((l, i) => <div key={i} style={{fontFamily: MONO, fontSize: 28, lineHeight: 1.5, color: "#C9CFDA", whiteSpace: "pre",
            opacity: interpolate(f, [dur * .12 + i * 4, dur * .12 + i * 4 + 6], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"})}}>{l}</div>)}
        </div>
      </div>
      <div style={{flex: 1, position: "relative", background: "#fff", borderRadius: 4, overflow: "hidden", boxShadow: "0 40px 90px rgba(0,0,0,.55)"}}>
        <div style={{position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center", fontFamily: MONO, fontSize: 22, color: "#9AA0AE", background: "#1A1D24"}}>
          rendering…</div>
        <Img src={staticFile(s.src)} style={{position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain", background: "#fff",
          clipPath: `inset(0 ${100 - reveal}% 0 0)`}} />
        <div style={{position: "absolute", top: 0, bottom: 0, left: `${reveal}%`, width: 3, background: "var(--a)", opacity: reveal > 0 && reveal < 100 ? 1 : 0}} />
      </div>
    </div>
  </AbsoluteFill>;
};

const fmt = (v: number, dec: number) => v.toLocaleString("en-US", {minimumFractionDigits: dec, maximumFractionDigits: dec});

const CounterCard: React.FC<{it: any; i: number; n: number}> = ({it, i, n}) => {
  const f = useCurrentFrame();
  // start counting only after the incoming transition has settled
  const t = interpolate(f - 22 - i * 6, [0, 40], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic)});
  const k = useEnter(14 + i * 6);
  return <div style={{opacity: k, transform: `translateY(${(1 - k) * 40}px)`, padding: "36px 50px", borderRadius: 4, background: "#161920",
    border: `1px solid ${LINE}`, minWidth: 340}}>
    <div style={{fontFamily: MONO, fontSize: 20, color: "#7C8496", marginBottom: 16}}>{String(i + 1).padStart(2, "0")}</div>
    <div style={{fontFamily: DISPLAY, fontWeight: 600, fontSize: n > 2 ? 130 : 170, lineHeight: 1, color: PAPER, fontVariantNumeric: "tabular-nums"}}>
      {it.prefix ?? ""}{fmt(it.value * t, it.decimals ?? 0)}<span style={{color: "var(--a)"}}>{it.suffix ?? ""}</span></div>
    <div style={{fontFamily: BODY, fontSize: 30, color: MUTED, marginTop: 14}}>{it.label}</div>
    <div style={{height: 2, marginTop: 26, background: "rgba(255,255,255,.1)"}}>
      <div style={{height: 2, width: `${t * 100}%`, background: "var(--a)"}} /></div>
  </div>;
};

const Counter: React.FC<{s: Scene}> = ({s}) => {
  const items: any[] = s.items ?? [{value: s.value, suffix: s.suffix, prefix: s.prefix, label: s.label}];
  return <AbsoluteFill style={{justifyContent: "center", alignItems: "center", padding: 100}}>
    <Kicker text={s.kicker} />
    {s.title && <Kinetic text={s.title} size={68} hi={s.highlight} delay={2} />}
    <div style={{display: "flex", gap: 50, marginTop: 56}}>
      {items.map((it, i) => <CounterCard key={i} it={it} i={i} n={items.length} />)}
    </div>
  </AbsoluteFill>;
};

const Side: React.FC<{d: any; good: boolean; i: number}> = ({d, good, i}) => {
  const f = useCurrentFrame();
  const k = useEnter(6 + i * 10);
  return <div style={{flex: 1, borderRadius: 4, padding: "30px 40px", opacity: k, transform: `translateX(${(1 - k) * (good ? 80 : -80)}px)`,
    background: good ? "#171B22" : "#131519", border: good ? "1px solid rgba(233,185,73,.55)" : `1px solid ${LINE}`,
    borderTop: good ? "4px solid var(--a)" : "4px solid #4A505E"}}>
    <div style={{fontFamily: MONO, fontSize: 24, letterSpacing: 4, textTransform: "uppercase", color: good ? "var(--a)" : "#8892A8"}}>{d.tag}</div>
    <div style={{fontFamily: DISPLAY, fontWeight: 600, fontSize: 56, color: PAPER, margin: "10px 0 22px"}}>{d.title}</div>
    {(d.points ?? []).map((p: string, j: number) => {
      const q = interpolate(f - 18 - i * 10 - j * 6, [0, 12], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
      return <div key={j} style={{display: "flex", gap: 18, alignItems: "center", fontFamily: BODY, fontSize: 32, color: good ? PAPER : "#9AA0AE", margin: "12px 0", opacity: q}}>
        <span style={{width: 40, height: 40, borderRadius: 20, display: "inline-flex", justifyContent: "center", alignItems: "center", fontSize: 22, fontWeight: 500,
          background: good ? "var(--a)" : "rgba(255,255,255,.08)", color: good ? "#14110A" : "#C76B5E"}}>{good ? "✓" : "✕"}</span>{p}</div>;
    })}
    {d.image && <Img src={staticFile(d.image)} style={{width: "100%", height: 330, objectFit: "contain", marginTop: 18, borderRadius: 2,
      background: "#fff", filter: good ? "none" : "grayscale(.6) contrast(.92)"}} />}
  </div>;
};

const Compare: React.FC<{s: Scene}> = ({s}) => {
  const vs = useEnter(14, 14);
  return <AbsoluteFill style={{padding: "110px 120px 120px", flexDirection: "column"}}>
    <div style={{textAlign: "center"}}><Kicker text={s.kicker} /><Kinetic text={s.title} size={68} hi={s.highlight} /></div>
    <div style={{display: "flex", gap: 60, marginTop: 44, alignItems: "stretch", position: "relative", flex: 1}}>
      <Side d={s.left} good={false} i={0} /><Side d={s.right} good i={1} />
      <div style={{position: "absolute", left: "50%", top: "45%", transform: `translate(-50%,-50%) scale(${vs})`, width: 92, height: 92, borderRadius: 46,
        background: INK, border: "1px solid rgba(255,255,255,.3)", display: "flex", justifyContent: "center", alignItems: "center",
        fontFamily: DISPLAY, fontStyle: "italic", fontWeight: 600, fontSize: 36, color: PAPER}}>vs</div>
    </div>
  </AbsoluteFill>;
};

const Bars: React.FC<{s: Scene}> = ({s}) => {
  const f = useCurrentFrame();
  const max = Math.max(...s.bars.map((b: any) => b.value));
  return <AbsoluteFill style={{padding: "120px 180px", justifyContent: "center"}}>
    <Kicker text={s.kicker} />
    <Kinetic text={s.title} size={68} hi={s.highlight} left />
    <div style={{marginTop: 56}}>
      {s.bars.map((b: any, i: number) => {
        const t = interpolate(f - 10 - i * 7, [0, 34], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease});
        return <div key={i} style={{display: "flex", alignItems: "center", gap: 30, margin: "24px 0", paddingBottom: 18, borderBottom: `1px solid ${LINE}`}}>
          <div style={{width: 380, fontFamily: BODY, fontSize: 32, color: b.highlight ? PAPER : MUTED, fontWeight: b.highlight ? 500 : 400}}>{b.label}</div>
          <div style={{flex: 1, height: 46, background: "rgba(255,255,255,.03)"}}>
            <div style={{height: "100%", width: `${(b.value / max) * 100 * t}%`, background: b.highlight ? "var(--a)" : "rgba(244,241,234,.28)"}} /></div>
          <div style={{width: 190, textAlign: "right", fontFamily: MONO, fontSize: 40, color: b.highlight ? "var(--a)" : PAPER, fontVariantNumeric: "tabular-nums"}}>
            {fmt(b.value * t, b.decimals ?? 0)}{b.suffix ?? ""}</div>
        </div>;
      })}
    </div>
  </AbsoluteFill>;
};

// image on a card with a gentle 3D tilt that settles, next to an editorial headline
const Showcase: React.FC<{s: Scene}> = ({s}) => {
  const f = useCurrentFrame();
  const k = useEnter(2, 18);
  const cap = useEnter(18);
  const p = f / Math.max(1, (s.seconds ?? 4) * 30);
  const left = s.align !== "right";
  return <AbsoluteFill style={{flexDirection: left ? "row" : "row-reverse", alignItems: "center", padding: "0 120px", gap: 80}}>
    <div style={{width: 620}}>
      <Kicker text={s.kicker} delay={4} />
      <Kinetic text={s.title} size={84} hi={s.highlight} delay={6} left />
      {s.caption && <div style={{fontFamily: BODY, fontSize: 34, color: MUTED, marginTop: 26, lineHeight: 1.45, opacity: cap}}>{s.caption}</div>}
    </div>
    <div style={{flex: 1, perspective: 1800}}>
      <div style={{transform: `rotateY(${(left ? -1 : 1) * interpolate(p, [0, 1], [9, 3])}deg) rotateX(${interpolate(p, [0, 1], [3, 1])}deg) translateY(${(1 - k) * 140}px) scale(${.88 + .12 * k})`,
        opacity: k, borderRadius: 4, padding: 14, background: s.dark ? "#141824" : "#fff", boxShadow: "0 50px 100px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.12)"}}>
        <div style={{overflow: "hidden"}}>
          <Img src={staticFile(s.src)} style={{width: "100%", maxHeight: 760, objectFit: "contain", display: "block",
            imageRendering: s.pixelated ? "pixelated" : "auto",
            // focus: {x, y, zoom} pushes in on one detail in the second half so small labels become readable
            transformOrigin: s.focus ? `${s.focus.x * 100}% ${s.focus.y * 100}%` : "50% 50%",
            transform: s.focus ? `scale(${interpolate(p, [.35, .8], [1, s.focus.zoom ?? 2.2], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease})})` : undefined}} />
        </div>
      </div>
      {s.note && <div style={{fontFamily: MONO, fontSize: 20, color: "#7C8496", marginTop: 22}}>{s.note}</div>}
    </div>
  </AbsoluteFill>;
};

const Tile: React.FC<{src: string; i: number}> = ({src, i}) => {
  const f = useCurrentFrame();
  const k = spring({frame: f - i * 4, fps: 30, config: {damping: 16, mass: .6}});
  return <div style={{borderRadius: 3, overflow: "hidden", background: "#fff", height: 320, opacity: Math.min(1, k * 1.4),
    transform: `scale(${.7 + .3 * k}) rotate(${(1 - k) * (i % 2 ? 3 : -3)}deg)`, boxShadow: "0 30px 70px rgba(0,0,0,.5)"}}>
    <Img src={staticFile(src)} style={{width: "100%", height: "100%", objectFit: "cover"}} /></div>;
};

const Grid: React.FC<{s: Scene}> = ({s}) => {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, (s.seconds ?? 3) * 30], [1, 1.06]);
  return <AbsoluteFill style={{padding: 110, justifyContent: "center", alignItems: "center"}}>
    {s.title && <div style={{marginBottom: 40}}><Kinetic text={s.title} size={62} hi={s.highlight} /></div>}
    <div style={{display: "grid", gridTemplateColumns: `repeat(${s.cols ?? 3},1fr)`, gap: 26, width: "100%", transform: `scale(${z})`}}>
      {s.srcs.map((src: string, i: number) => <Tile key={i} src={src} i={i} />)}
    </div>
  </AbsoluteFill>;
};

const Cta: React.FC<{s: Scene}> = ({s}) => {
  const k = useEnter(16, 14);
  const sub = useEnter(26);
  return <AbsoluteFill style={{justifyContent: "center", alignItems: "center", textAlign: "center", padding: 140}}>
    <Kicker text={s.kicker} />
    <Kinetic text={s.title} size={112} hi={s.highlight} />
    <div style={{marginTop: 52, padding: "22px 44px", borderRadius: 3, fontFamily: MONO, fontSize: 36, color: "#14110A",
      background: "var(--a)", opacity: k, transform: `translateY(${(1 - k) * 30}px)`}}>{s.url}</div>
    {s.command && <div style={{marginTop: 22, fontFamily: MONO, fontSize: 30, color: PAPER, background: "#0B0C0F", border: `1px solid ${LINE}`,
      padding: "18px 30px", borderRadius: 3, opacity: sub}}><span style={{color: "var(--a)"}}>$ </span>{s.command}</div>}
    {s.subtitle && <div style={{marginTop: 30, fontFamily: MONO, fontSize: 24, color: MUTED, opacity: sub}}>{s.subtitle}</div>}
  </AbsoluteFill>;
};

const VIEWS: Record<string, React.FC<{s: Scene}>> = {open: Open, demo: Demo, hook: Hook, counter: Counter, compare: Compare, bars: Bars, showcase: Showcase, grid: Grid, cta: Cta};

const presentation = (name: string | undefined, i: number): any => {
  const n = name ?? ["slide", "wipe"][i % 2];  // no default crossfade: overlapping text layers read as a glitch
  if (n === "wipe") return wipe({direction: "from-left"});
  if (n === "flip") return flip({direction: "from-right"});
  if (n === "fade") return fade();
  return slide({direction: i % 2 ? "from-bottom" : "from-right"});
};

const Main: React.FC<Spec> = (spec) => {
  const fps = spec.fps ?? 30;
  const vars = {"--a": spec.accent ?? "#E9B949"} as React.CSSProperties;
  const items: React.ReactNode[] = [];
  spec.scenes.forEach((s, i) => {
    const V = VIEWS[s.type] ?? Hook;
    if (i > 0) items.push(<TransitionSeries.Transition key={`t${i}`} presentation={presentation(s.transition, i)}
      timing={springTiming({config: {damping: 200}, durationInFrames: TR})} />);
    items.push(<TransitionSeries.Sequence key={`s${i}`} durationInFrames={Math.round((s.seconds ?? 3.5) * fps)}>
      <AbsoluteFill><CameraMotionBlur shutterAngle={140} samples={s.blur === false ? 1 : 4}><V s={s} /></CameraMotionBlur></AbsoluteFill>
    </TransitionSeries.Sequence>);
  });
  return <AbsoluteFill style={vars}>
    <Bg />
    <TransitionSeries>{items}</TransitionSeries>
    <div style={{position: "absolute", left: 60, top: 54, fontFamily: MONO, fontSize: 20, letterSpacing: 3, color: "rgba(244,241,234,.55)"}}>
      {(spec.brand ?? "Scientific Illustration").toUpperCase()}</div>
    {spec.credits && <div style={{position: "absolute", right: 60, bottom: 50, fontFamily: MONO, fontSize: 20, color: "rgba(255,255,255,.7)", background: "rgba(15,17,21,.75)", padding: "4px 10px"}}>{spec.credits}</div>}
    {spec.audio && <Audio src={staticFile(spec.audio)} />}
  </AbsoluteFill>;
};

registerRoot(() => (
  <Composition id="Main" component={Main as any} durationInFrames={30} fps={30} width={1920} height={1080}
    defaultProps={{scenes: []} as Spec}
    calculateMetadata={({props}) => {
      const p = props as Spec, fps = p.fps ?? 30;
      const total = p.scenes.reduce((a, s) => a + Math.round((s.seconds ?? 3.5) * fps), 0) - TR * Math.max(0, p.scenes.length - 1);
      return {fps, width: p.width ?? 1920, height: p.height ?? 1080, durationInFrames: Math.max(1, total)};
    }} />
));
