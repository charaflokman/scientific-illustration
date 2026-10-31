# Changelog

## 1.0.0 — 2026-10-30

First public release.

- Figures from a JSON spec (SVG, PNG, PDF) with a browser editor, data plots, diagrams from text.
- 3D scenes with Three.js (interactive HTML and transparent PNG up to 4×).
- Lesson summary cards (HTML, PNG, PDF; A4 or slide).
- Native pixel-art scenes (`pixel_scene.py`).
- Video with Remotion: `pro` motion-graphics template (input→output demo, comparison, counters, bars, showcases, montage, call to action) and an original synthesised soundtrack (`make_audio.py`).
- Unified search over 8,806 free drawings (Servier Medical Art, DBCLS TogoTV, Bioicons, Health Icons) with automatic credits.
- Works with any agent that can run commands (`AGENTS.md`).

## 1.1.0 — 2026-10-31

- Reactome, PhyloPic and SciDraw art libraries (~23,000 drawings in total).
- `research.py`: researches a topic before drawing (OpenAlex, Europe PMC, Wikipedia; no API key) and returns a brief with key terms and numbered references.
- Simple vs detailed versions: the skill asks for style and level together and can derive both from one spec.
- Skill text is now English only and replies in the user's language.
