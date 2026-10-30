// Generic scene player for render_video.py. All content comes from inputProps (the JSON spec).
import React from "react";
import {AbsoluteFill, Composition, Img, Sequence, interpolate, registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig} from "remotion";

type Scene = {type: "title" | "image" | "bullets"; seconds?: number; title?: string; subtitle?: string;
  src?: string; caption?: string; points?: string[]; zoom?: number; bg?: string};
type Spec = {fps?: number; width?: number; height?: number; background?: string; accent?: string; ink?: string;
  font?: string; credits?: string; scenes: Scene[]};

const FADE = 12;

const Fade: React.FC<{dur: number; children: React.ReactNode}> = ({dur, children}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, FADE, dur - FADE, dur], [0, 1, 1, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};

const SceneView: React.FC<{s: Scene; spec: Spec; dur: number}> = ({s, spec, dur}) => {
  const f = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const ink = spec.ink ?? "#0B3D5C", accent = spec.accent ?? "#009E73";
  const pop = spring({frame: f, fps, config: {damping: 200}});
  const u = width / 1920;
  const font = spec.font ?? "Inter, Segoe UI, Arial, sans-serif";
  const caption = s.caption && (
    <div style={{position: "absolute", left: 80 * u, right: 80 * u, bottom: 60 * u, padding: `${18 * u}px ${28 * u}px`,
      background: "rgba(255,255,255,.92)", borderLeft: `${8 * u}px solid ${accent}`, borderRadius: 12 * u,
      fontSize: 40 * u, color: ink, transform: `translateY(${(1 - pop) * 40 * u}px)`}}>{s.caption}</div>);
  return (
    <AbsoluteFill style={{background: s.bg ?? spec.background ?? "#FFFFFF", fontFamily: font, color: ink}}>
      {s.type === "title" && (
        <AbsoluteFill style={{justifyContent: "center", alignItems: "center", textAlign: "center", padding: 140 * u}}>
          <div style={{fontSize: 96 * u, fontWeight: 800, lineHeight: 1.1, transform: `scale(${0.92 + 0.08 * pop})`}}>{s.title}</div>
          <div style={{width: 220 * u * pop, height: 8 * u, background: accent, margin: `${36 * u}px 0`, borderRadius: 4 * u}} />
          {s.subtitle && <div style={{fontSize: 44 * u, opacity: pop, color: "#445"}}>{s.subtitle}</div>}
        </AbsoluteFill>)}
      {s.type === "image" && s.src && (
        <AbsoluteFill style={{justifyContent: "center", alignItems: "center", padding: `${s.title ? 150 : 50}px ${60 * u}px ${s.caption ? 190 * u : 50 * u}px`}}>
          <Img src={staticFile(s.src)} style={{maxWidth: "100%", maxHeight: "100%", objectFit: "contain",
            transform: `scale(${interpolate(f, [0, dur], [1, s.zoom ?? 1.06])})`}} />
        </AbsoluteFill>)}
      {s.type === "bullets" && (
        <AbsoluteFill style={{padding: `${200 * u}px ${160 * u}px`}}>
          {(s.points ?? []).map((p, i) => {
            const k = spring({frame: f - 10 - i * 18, fps, config: {damping: 200}});
            return <div key={i} style={{display: "flex", gap: 28 * u, alignItems: "baseline", fontSize: 52 * u, margin: `${26 * u}px 0`,
              opacity: k, transform: `translateX(${(1 - k) * 60 * u}px)`}}>
              <span style={{minWidth: 56 * u, height: 56 * u, borderRadius: 28 * u, background: accent, color: "#fff", fontSize: 32 * u,
                display: "inline-flex", justifyContent: "center", alignItems: "center", fontWeight: 700}}>{i + 1}</span>{p}</div>;
          })}
        </AbsoluteFill>)}
      {s.type !== "title" && s.title && (
        <div style={{position: "absolute", top: 50 * u, left: 80 * u, fontSize: 58 * u, fontWeight: 750, opacity: pop}}>{s.title}
          <div style={{width: 120 * u, height: 6 * u, background: accent, marginTop: 14 * u}} /></div>)}
      {caption}
      {spec.credits && <div style={{position: "absolute", right: 24 * u, bottom: 12 * u, fontSize: 18 * u, color: "#778"}}>{spec.credits}</div>}
    </AbsoluteFill>);
};

const Main: React.FC<Spec> = (spec) => {
  const fps = spec.fps ?? 30;
  let at = 0;
  return <AbsoluteFill>{spec.scenes.map((s, i) => {
    const dur = Math.round((s.seconds ?? 4) * fps);
    const from = at; at += dur;
    return <Sequence key={i} from={from} durationInFrames={dur}><Fade dur={dur}><SceneView s={s} spec={spec} dur={dur} /></Fade></Sequence>;
  })}</AbsoluteFill>;
};

registerRoot(() => (
  <Composition id="Main" component={Main as any} durationInFrames={30} fps={30} width={1920} height={1080}
    defaultProps={{scenes: []} as Spec}
    calculateMetadata={({props}) => {
      const p = props as Spec, fps = p.fps ?? 30;
      return {fps, width: p.width ?? 1920, height: p.height ?? 1080,
        durationInFrames: Math.max(1, p.scenes.reduce((a, s) => a + Math.round((s.seconds ?? 4) * fps), 0))};
    }} />
));
