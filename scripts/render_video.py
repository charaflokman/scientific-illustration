#!/usr/bin/env python3
"""Turn a JSON spec of scenes into an MP4 with Remotion (React video), reusing the skill's figures, 3D renders and summaries.

  python render_video.py spec.json out.mp4            # renders; images in the spec are paths relative to the spec
  python render_video.py spec.json out.mp4 --still 2  # one PNG of scene 3 instead, for a cheap preview

Spec: {"width":1920,"height":1080,"fps":30,"accent":"#009E73","credits":"Art: Servier Medical Art (CC BY 4.0)",
       "scenes":[{"type":"title","title":"...","subtitle":"...","seconds":3},
                 {"type":"image","src":"figure.png","title":"...","caption":"...","zoom":1.08,"seconds":5},
                 {"type":"bullets","title":"...","points":["...","..."],"seconds":6}]}
Remotion lives once in ~/.cache/scientific-illustration/remotion (npm, versions pinned, install scripts off).
Licence: free for individuals, non-profits and companies of up to 3 people; bigger companies need a Remotion licence.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CACHE = Path(os.environ.get("RV_CACHE", Path.home() / ".cache" / "scientific-illustration"))
PROJ = CACHE / "remotion"
VERSION = "4.0.539"


def ensure():
    guide = Path(__file__).resolve().parent.parent / "references" / "remotion"
    if not guide.exists():  # the official guide has no licence for redistribution, so fetch it on first use
        tmp = CACHE / "remotion-skills"
        if not tmp.exists():
            subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/remotion-dev/skills", str(tmp)], check=False)
        if (tmp / "skills" / "remotion-best-practices").exists():
            shutil.copytree(tmp / "skills" / "remotion-best-practices", guide)
    if (PROJ / "node_modules" / "@remotion" / "cli").exists():
        return
    PROJ.mkdir(parents=True, exist_ok=True)
    if not (PROJ / "package.json").exists():
        (PROJ / "package.json").write_text('{"name":"si-video","private":true}', encoding="utf-8")
    subprocess.run(["npm", "i", "--ignore-scripts", "--no-audit", "--no-fund", f"remotion@{VERSION}",
                    f"@remotion/cli@{VERSION}", f"@remotion/transitions@{VERSION}", f"@remotion/motion-blur@{VERSION}",
                    f"@remotion/google-fonts@{VERSION}", "react@19", "react-dom@19"], cwd=PROJ, check=True, shell=os.name == "nt")


def soundtrack(spec, pub, template):
    """Generate an original music bed + sound effects timed to the scenes (make_audio.py); returns the staged file name."""
    fps = spec.get("fps", 30)
    default, overlap = (3.5, 14) if template == "pro" else (4, 0)
    starts, at = [], 0
    for s in spec["scenes"]:
        starts.append(at / fps)
        at += round(s.get("seconds", default) * fps) - overlap
    total = (at + overlap) / fps
    brk = None
    ev = []  # no hit on frame 0: starting loud makes everything after feel flat
    for i, (s, t) in enumerate(zip(spec["scenes"], starts)):
        if i:
            ev.append({"t": t + overlap / fps / 2, "kind": "whoosh"})
        if s["type"] == "counter":
            ev.append({"t": t + .3, "kind": "ticks", "dur": 1.4})
        if s["type"] in ("bars", "compare"):
            ev += [{"t": t + .35 + k * .25, "kind": "pop"} for k in range(len(s.get("bars", [0, 1])))]
        if s["type"] == "grid":
            ev += [{"t": t + k * 4 / fps, "kind": "pop"} for k in range(len(s.get("srcs", [])))]
        if s["type"] == "cta":
            ev += [{"t": t + .3, "kind": "riser", "dur": 1.6}, {"t": t + .3, "kind": "hit", "gain": .7}]
            brk = t + .3
    events = PROJ / "audio_events.json"
    events.write_text(json.dumps({"seconds": total, "bpm": 96, "events": ev, "break_at": brk}), encoding="utf-8")
    subprocess.run([sys.executable, str(Path(__file__).with_name("make_audio.py")), str(events), str(pub / "soundtrack.wav")], check=True)
    return "soundtrack.wav"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--template", choices=["basic", "pro"], default="pro",
                    help="pro: dark motion graphics (hook, counter, compare, bars, showcase, grid, cta); basic: title/image/bullets")
    ap.add_argument("--still", type=int, help="render one frame from the middle of this scene (0-based) as PNG")
    a = ap.parse_args()
    ensure()
    spec_path = Path(a.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    pub = PROJ / "public"
    shutil.rmtree(pub, ignore_errors=True)
    pub.mkdir()
    def stage(rel):
        src = (spec_path.parent / rel).resolve()
        name = hashlib.md5(str(src).encode()).hexdigest()[:8] + src.suffix
        shutil.copy2(src, pub / name)
        return name
    for s in spec["scenes"]:
        if s.get("src"):
            s["src"] = stage(s["src"])
        if s.get("srcs"):
            s["srcs"] = [stage(x) for x in s["srcs"]]
        for side in ("left", "right"):
            if isinstance(s.get(side), dict) and s[side].get("image"):
                s[side]["image"] = stage(s[side]["image"])
    music = spec.get("audio", "auto" if a.template == "pro" else None)
    if music == "auto" and a.still is None:
        spec["audio"] = soundtrack(spec, pub, a.template)
    elif music:
        spec["audio"] = stage(music) if music != "auto" else None
    (PROJ / "src").mkdir(exist_ok=True)
    shutil.copy2(Path(__file__).with_name("video_template") / ("Pro.tsx" if a.template == "pro" else "Root.tsx"), PROJ / "src" / "index.tsx")
    props = PROJ / "props.json"
    props.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    out = Path(a.out).resolve()
    cmd = ["npx", "remotion"]
    if a.still is not None:
        fps = spec.get("fps", 30)
        default, overlap = (3.5, 14) if a.template == "pro" else (4, 0)
        dur = [round(s.get("seconds", default) * fps) for s in spec["scenes"]]
        frame = sum(dur[:a.still]) - overlap * a.still + dur[a.still] * 2 // 3
        cmd += ["still", "src/index.tsx", "Main", str(out), f"--frame={frame}"]
    else:
        cmd += ["render", "src/index.tsx", "Main", str(out), "--codec=h264"]
    cmd += [f"--props={props}", "--log=error"]
    sys.exit(subprocess.run(cmd, cwd=PROJ, shell=os.name == "nt").returncode)


if __name__ == "__main__":
    main()
