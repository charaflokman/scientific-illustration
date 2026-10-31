---
name: scientific-illustration
description: Professional scientific illustration (BioRender-quality, code-drawn and editable), 3D models and 3D images, and attractive lesson summaries. Turn research content into editable, publication-ready scientific figures, text-to-diagram visuals and interactive process simulations, for researchers in any field (chemistry, biology, physics, materials, medicine, engineering) with special depth in biopolymer composites. Use it whenever the user wants a graphical abstract, fabrication or synthesis scheme, mechanism or interaction schematic, comparison panel (with vs without, treated vs untreated), PRISMA or study-design flow, signaling pathway, experimental-setup drawing, a plot or multi-panel figure of their data (FTIR, XRD, TGA/DTG, DSC, tensile, swelling, release, any CSV/Excel), a flowchart, mind map or concept map from pasted text, or a simulation/animation of a process (diffusion, water uptake, swelling, crosslinking, degradation, filler dispersion, release kinetics), even if they never say "figure". Also use it when the user wants to edit or restyle a figure made earlier, or asks for an alternative to BioRender, FigureLabs or Napkin, in any language. Also use it for short explainer or lesson videos (MP4) built from these figures, and when the user only names a topic ("a figure about ferroptosis") — it researches the topic first. Typical cues: chitosan, cellulose/CNC, starch, alginate, PLA, PHA, nanofiller, film, membrane, hydrogel, characterization.
---

# Scientific Illustration

Researchers come with a paragraph of methods, a CSV, a paper, or a rough idea, and need a figure they can put in
a manuscript, thesis or talk **and keep editing**. This skill produces code-drawn vector figures from the
researcher's own content, a text-to-diagram path, and interactive simulations. Three things set it apart from
image-generation tools, so protect them in every deliverable:

1. **Editable.** Every figure is an SVG with real text and stable element ids, plus a browser editor and a
   re-renderable source. The user can move, retype, recolour and delete without coming back to you, and when they
   do come back, their manual edits survive your next render.
2. **Faithful.** Every number, condition and claim traces to the user's material. Missing values become visible
   `[? …]` placeholders, never guesses. No fabricated data, spectra, micrographs or results.
3. **Journal-safe.** Deterministic, code-drawn schematics and data plots (not generative images), journal sizes,
   colour-blind-safe palette, plus a disclosure sentence. Publishers restrict AI-generated images
   (see `references/publishing-policy.md`).

Reply in the user's language, whatever it is. Keep figure text in English unless the user asks otherwise, because
journals expect it; lesson summaries and teaching material follow the user's language.

## Ask style and level first

At the start of a new visual (not an edit), ask one short question with two choices, unless the user already said:
"Academic or pixel-art style? And a simple version or a detailed one?" Defaults if they don't answer: academic, and
simple for slides, students and social media, detailed for journals, theses and reviews. Offer the other level as a
follow-on, since both come from the same spec.

| | **Simple** | **Detailed** |
|---|---|---|
| Purpose | one message at a glance (slides, teaching, abstract thumbnail, social) | the full mechanism for experts (paper, thesis, review) |
| Content | 3–6 elements, one panel, the main idea only | multi-panel (a)(b)(c), insets/zooms, intermediate steps, conditions |
| Text | 1–3-word labels, no references | labels + short notes, values and units, reference numbers [n] |
| Art | large icons, few colours, generous white space | full library art, molecular detail, legends, scale bars |
| Data | none or one key number | every stated value; `[? …]` placeholders for missing ones |

Build the detailed spec first when both are wanted, then derive the simple one by removing panels and notes (keep
ids and colours so the two look like a family). For lesson summaries: simple = key ideas + one equation + takeaway;
detailed = all cards (equations, steps, table, concept map, mistakes, sources). For video: simple ≈ 20 s, 5 scenes;
detailed ≈ 45–60 s with comparison, numbers and zooms.

**Pixel art:** draw the scene natively with `scripts/pixel_scene.py` (JSON spec → crisp game-style PNG). Never
convert a finished image with a pixelate filter: users judged that look noisy and unclear. The renderer applies
hand-pixel-art rules: a small canvas (about 280×180) upscaled with nearest-neighbour, 5-tone hue-shifted ramps, light
from the top-left, one dark outline per object, isometric 2:1 slabs (`pattern`: mesh / glass, `shadow` on the lowest),
shaded spheres with optional `sparkle`, fibres, brush chains, background `stars`, and labels in game dialog boxes
with a pixel font. Keep labels to 1–3 words in capitals; leave 10–15 px between stacked slabs so nothing hides.
Example: `assets/examples/dressing_pixel.json`. Render, look at it, move any label that is cut off or points at the
wrong thing, then render again. For video, render each pixel scene and sequence them with `render_video.py`.
Pixel art is for engagement and teaching; tell the user it is not suitable for journal figures.

## Research the topic before drawing

When the user gives only a topic or a thin description ("a figure on ferroptosis", "explain PLA degradation"), do not
draw from memory. Research first, then draw, so every element and label is backed by a source:

1. `python scripts/research.py "<topic>" --n 8` — free scholarly sources, no API key: OpenAlex (papers, open-access
   links, citation counts), Europe PMC / PubMed (biomedical abstracts) and Wikipedia (a plain overview). It prints a
   short brief: definition, key mechanisms/steps named in recent highly cited abstracts, and a numbered reference list
   with DOIs. `--recent 5` limits to the last 5 years; `--review` prefers review articles; `--json` for raw records.
2. If the harness has its own web search (or the agent-reach skill), use it too for very recent or non-academic facts.
3. Read the brief, pick the elements the figure needs, and put the reference numbers in the spec (labels at the
   detailed level, `provenance` always). Tell the user in two or three lines what you found and which sources you
   used, and flag anything contested.
4. When the user supplies their own text, data or paper, that material wins: research only to fill gaps they ask
   about, and never overwrite their numbers.

Never invent a mechanism step, value or citation; if the sources disagree or are silent, show `[? …]` and say so.

## Infer the output before asking

Users rarely name the output type ("something about the lesson", "need something for my thesis defence"). Work it out from
these signals, in this order, and say your choice in one line so they can redirect ("I'll make a 3D render + a figure"):

1. **What they attached.** CSV/Excel/instrument export → data plot. A paper or review paragraph → figure or graphical
   abstract. Lecture notes, a chapter, slides → lesson summary. An earlier output of this skill → edit that, same type.
2. **Where it will be used.** Journal, thesis chapter, poster → figure (vector, 180 mm, PDF). Graphical abstract for
   submission → figure at the journal's size. Class, revision, students → lesson summary. Slides, defence, conference
   talk → figure or 3D image at 16:9, plus a video if they want it to play. Social media, YouTube, WhatsApp → video
   (vertical 1080×1920 for reels). Website or teaching where people click → 3D page or simulation.
3. **The verb** (in whatever language). Draw / figure / scheme → figure. Summarise → lesson summary. Animate / video /
   montage → video. "Let me see how" / play with / what happens if → simulation. 3D / model / render → 3D.
4. **The content's shape.** Steps in sequence → diagram. Layers, particles, structures in space → 3D. With vs
   without → comparison figure. Equations and definitions → lesson summary. Change over time → simulation or video.

When signals point to several outputs, build the core still first (figure or 3D) and offer the rest as follow-ons
that reuse it: still → summary card → video. Ask only when the use (print vs screen vs motion) is truly unknown and
the choice would change the work a lot; otherwise pick, state it, and go.

## Pick the mode

| The user wants | Mode | Main tool | Output |
|---|---|---|---|
| A schematic: graphical abstract, fabrication scheme, mechanism, comparison panel, setup, cell/pathway cartoon | **Figure** | `scripts/render_figure.py` (spec → SVG) | `.svg` + `.editor.html` + PNG/PDF |
| A plot of their data, characterization panels (a)(b)(c)(d) | **Figure (data)** | `scripts/plot_data.py` | `.svg` (editable text) + PNG/PDF + caption draft |
| A quick diagram from text: flowchart, PRISMA, timeline, mind map, concept map | **Diagram** | `scripts/render_diagram.py` (Mermaid / D2 / Graphviz) | `.mmd`/`.d2` source + `.svg` + PNG |
| To see or play with a process | **Simulation** | the `process-simulator` skill + `references/simulation-models.md` | self-contained interactive `.html` |
| A 3D model or 3D image: filler dispersion in a film, membrane cross-section, molecule, particle, device | **3D** | `scripts/render_3d.py` (spec → Three.js page; light, no install, orbit + edit colours/labels, PNG 1x–4x) | `.html` + PNG |
| An attractive summary of a lesson, lecture, chapter or paper | **Lesson summary** | `scripts/render_summary.py` (cards: points, equations, numbered steps, table, concept map, mistakes, takeaway) | editable `.html` + PNG/PDF (A4 or slide) |
| A short explainer, lesson or graphical-abstract video (MP4) | **Video** | `scripts/render_video.py` (Remotion: title, image with slow zoom, animated bullets, captions, fades); preview one scene with `--still N` before the full render | `.mp4` + editable JSON spec |

**Professional look (what clients compare against BioRender):** anatomy, skin/wounds, cells, bacteria,
viruses, organelles and lab equipment come from Servier Medical Art via `scripts/servier.py` (hand-drawn by
medical illustrators, CC BY 4.0; the credits line is added automatically). Run `servier.py search <terms>`, view
the candidate PNGs, then `servier.py get` for a ready `image` element. If the library is missing, run
`servier.py fetch Dermatology Infectiology Intracellular-components Medical-equipment` (Windows + PowerPoint).
For anything else, search all free libraries at once with `scripts/library.py search <terms>` (Servier
Medical Art, DBCLS TogoTV, Reactome, Bioicons, SciDraw, Health Icons, PhyloPic; licence shown per hit;
`library.py get <key>` copies a sanitised file and prints the spec element). First-time setup: `library.py fetch`
(≈1.5 GB cache; `--only reactome phylopic` for a subset). Reactome is the place for named proteins, receptors,
transporters, drugs and cell types (search the gene or protein name, e.g. ACE2, EGFR, insulin); SciDraw for
neuroscience, lab animals and behaviour setups; PhyloPic for any organism as a silhouette, searched by its
scientific name (Chiroptera, Manis, Arabidopsis), which suits ecology, evolution and One Health figures.
Use code-drawn icons only for materials parts the libraries lack (films, fillers, networks, curves). Compose as a
scene: one large hero illustration per panel, short labels (≤ 6 words), details and numbers in the caption.
Example: `assets/examples/dispersion_wound_dressing_v2.json`.

**Rendered 3D hero (the "Nano Banana look" without AI images):** build the scene with `render_3d.py`
(types slab, scaffold, fibers, brush, spheres with finish metal/glass/matte), export a transparent PNG with
`--png 2400x1700`, then place it as an `image` element in a `render_figure.py` spec and put all text, arrows and
RDKit chemistry on top as editable vector. Example: `assets/examples/silane_roles.json` + `hero_dressing.json`.

Research before drawing when the user gives only a topic or a URL: use the `agent-reach` skill/CLI
(`agent-reach doctor` lists channels; web pages via Jina Reader, GitHub, YouTube subtitles, RSS). Use only
zero-config channels; never configure cookies or log in to accounts for this skill. Cite what you read in the
figure caption or summary `source`, and never draw a value you did not find: `[? ...]` instead.

3D rules: positions come from a fixed `seed`, so the picture is reproducible; the spec's `camera` is only a
viewing direction (distance auto-fits); label every component; mark illustrative geometry as schematic in the
caption. Start from `assets/examples/cnc_dispersion_3d.json`. Lesson summaries start from
`assets/examples/lesson_fick.json`; keep 4–7 cards, one idea per card, and put only what the lesson states.

Mixed requests (e.g. "graphical abstract plus a simulation") become separate deliverables; say so.
If the setup is unknown, run `python scripts/setup_check.py` once; it reports what is installed and how to add
the rest. `render_figure.py` itself needs only Python; export needs a browser (Chrome/Edge via Playwright).

## Workflow (plan → style → render → critique)

This is the PaperBanana-style loop, with an image model replaced by deterministic renderers so the output stays
editable and accurate.

### 1. Read the source and build the content plan
- Methods text / paper: extract materials, amounts, ratios, conditions (T, t, rpm, pH, solvent, atmosphere),
  sequence of steps, characterization methods, and the reported results with their direction and size.
- CSV/Excel: inspect columns, units and replicate structure before plotting. Print what you will use.
- Images the user supplies (micrographs, photos): use them as-is inside `image` elements; never retouch, trace
  or "clean up" primary data images.
- Write the plan down for yourself: entities, relations (what flows into what), the one message of the figure,
  and a list of values that are missing. Ask the user only for things that change the figure substantially
  (target journal/size, which result to emphasise); everything else becomes a placeholder.

### 2. Choose a layout and style
- Read `references/figure-style.md` (sizes, type, colour, layout rules) and, for Figure mode,
  `references/figure-spec.md` (the JSON format, icons, recipes).
- For chemistry/biopolymer work read `references/biopolymer-composites.md` (fabrication templates, what belongs
  on arrows, characterization rendering rules, sourced peak table). For biology, physics and other fields read
  `references/other-fields.md`.
- Start from a template in `assets/examples/` when one fits (fabrication by casting, side-by-side comparison).
- When the text supports several structures (timeline vs flow vs comparison), pick the best one and mention the
  alternative in one line — like Napkin's "several candidate visuals", without making the user wait.

### 3. Render
- Figure: write `spec.json` → `python scripts/render_figure.py spec.json -o <out>/name.svg`.
  Icons: built-in line art first (`--list-icons`); otherwise Bioicons via `scripts/bioicons.py search/get`
  (prefer `cc-0`; CC-BY icons are credited automatically on the figure). Molecules: `molecule` element (RDKit).
- Data: `python scripts/plot_data.py --help` for kinds (ftir, xrd, tga with DTG, dsc, tensile, bar, xy) and the
  multi-panel layout mode. Peak labels only at positions the user gives or the data show; computed quantities
  (T5%, Tmax, crystallinity index) come from the data with the formula stated.
- Diagram: write `.mmd` or `.d2` → `python scripts/render_diagram.py file.mmd --png 600`. See
  `references/diagram-mode.md`. Rendering is local; do not paste user content into online renderers.
- Simulation: see the Simulation section below.

### 4. Critique and fix (do not skip)
- `python scripts/export.py name.svg --check --png 300` → fix overlaps, outside-canvas items, text < 6 pt.
- Open the PNG with the Read tool and look at it as a reviewer would: Is the message obvious in 5 seconds? Do
  labels sit next to what they name? Are the arrows going the right way? Anything that contradicts the source?
  Is there dead space or crowding? Iterate on the spec (usually 1–3 rounds) until it is clean.
- Re-check every number and condition against the source.

### 5. Deliver
- Final exports: `python scripts/export.py name.svg --png 600 --pdf`.
- Save into the user's project folder (ask once if unclear) and give the **full path of every file**: `.svg`,
  `.editor.html`, `spec.json`, PNG, PDF, `.mmd/.d2`, `.html` simulation.
- In 2–4 lines: what is schematic vs drawn from their data, the list of `[? …]` placeholders to fill, any icon
  credits, and how to edit (open `name.editor.html`; or tell you what to change).
- Offer the caption draft and the disclosure sentence (`references/publishing-policy.md`).
- Offer one concrete next improvement.

## Editing requests (most follow-up turns)

Users will say "move the legend", "make the oven red", "change 40 °C to 60 °C", "add a step", "translate the
labels". Handle them without breaking their manual edits:
- If they edited in the editor, ask for (or locate) the SVG they saved. Then change `spec.json` and re-render with
  `--keep-edits <their saved svg>`; for pasted "Copy edits" JSON use `--overrides file.json`.
  The spec can also be recovered from any SVG this skill made: `render_figure.py saved.svg -o new.svg` reads the
  embedded spec.
- Keep element ids stable so their edits stay attached; add new ids for new elements.
- Small cosmetic changes they can do faster themselves: say so, and point at the editor control.
- For plots: re-run `plot_data.py` with new options; for diagrams: edit the `.mmd/.d2` text and re-render.

## Video mode (Remotion)

Make the stills first (figures, 3D renders, summary cards, pixel scenes), then sequence them in a JSON spec for
`scripts/render_video.py`. The default `--template pro` is a professional motion-graphics look (dark animated
background, kinetic type, slide/wipe/flip transitions, motion blur). Scene types: `open` (cold open: the most striking visual full-frame and already moving at frame 0, with a curiosity headline — always start with this, never with a fade from black or an empty panel), `demo` (prompt typing → spec → figure wipe), `hook` (big kinetic headline),
`counter` (animated numbers, 1–3 cards), `compare` (before vs after with ✓/✕ points and images), `bars` (animated bar
comparison), `showcase` (image on a 3D-tilted card next to a headline; `pixelated: true` for pixel art), `grid` (fast
montage of 3–6 images) and `cta` (closing line + link). Rhythm that reads as professional: hook → comparison → numbers
→ 2–3 showcases → montage → call to action, 3–5 s each, 25–40 s total, one idea per scene, numbers only from real
data. Example: `assets/examples/promo_pro.json`. Pro videos get an original soundtrack automatically (`scripts/make_audio.py`: a calm synthesised music bed plus whooshes on cuts, ticks on counters, pops on bars and tiles, a riser and hit on the call to action), so there is no music licence to clear; set `"audio": "path/to/track.mp3"` to use the user's own track, or `"audio": null` for silence. The look is editorial (serif headlines, mono numbers, one warm accent, film grain); avoid glowing blobs, gradient text and neon, which read as generic AI. `--template basic` keeps the plain white title/image/bullets look.
Keep it cheap in tokens and time: write the spec, render `--still N` for one or two scenes and look at them, then render the MP4 once.
Use 3–6 s per scene, one idea per scene, captions under 12 words, and put licence credits in `credits`.
For anything the template does not cover (voice-over, captions from audio, charts, transitions, maps), read only the matching file under `references/remotion/` (the official Remotion agent skill, routed from its `SKILL.md`), and write a custom composition in the cached project.
Remotion is free for individuals, non-profits and companies of up to 3 people; tell the user that larger companies need a Remotion licence.

## Simulation mode

Use the `process-simulator` skill to build the interactive HTML; this skill supplies the science.
1. Find the process in `references/simulation-models.md`: governing equations, parameter ranges with sources,
   validity limits, which sliders/toggles/readouts map to which terms, and the honest label for the model.
2. Hand process-simulator: the process name, the model (equations + parameter values marked *literature* /
   *assumed* / *user data*), the drivers, the readouts, the verdict, and the footer label (e.g. "Trend model:
   Halpin–Tsai with an empirical agglomeration penalty — not a prediction for your system").
3. Prefer analytic or ODE solutions computed in the page (Crank series, Flory–Rehner root, Arrhenius kinetics)
   for quantitative curves, and use agents/particles to make the invisible visible (water molecules entering the
   film, filler clustering). If the user has measurements, overlay their points and fit the parameter (e.g. D from
   the √t slope) instead of showing a free curve.
4. Verify as process-simulator requires (headless sweep), and additionally check one textbook number from the
   catalogue (e.g. the half-time of Fickian uptake) against the page.

## Domain depth: chemistry and biopolymer composites
Typical figure set for a biopolymer composite paper: (1) fabrication scheme with conditions on arrows;
(2) structure/interaction scheme (matrix chains, filler, crosslinker, proposed H-bonding) using hedged language;
(3) characterization panels (a) FTIR (b) XRD (c) TGA/DTG (d) tensile or swelling; (4) property-vs-loading plot
with error bars; (5) graphical abstract combining 1 + the key result; (6) optional simulation for talks/teaching.
`references/biopolymer-composites.md` has the templates, what usually goes missing from methods text, and the
peak/feature table with sources and confidence levels.

## Honesty rules (why they matter: reviewers trust figures more than text)
- A figure that states a wrong temperature or an invented improvement does more damage than no figure. When in
  doubt, `[? …]`.
- Illustrative curves, pictograms and simulations are labelled as such on the figure or in the caption.
- Mechanisms the source only proposes are drawn and worded as "proposed".
- No synthetic "example data" presented as results; test data you generate is named `ILLUSTRATIVE_*`.
- Never alter, enhance or generate micrographs, blots, spectra or photos.

## Files in this skill
- `scripts/research.py` topic research (OpenAlex, Europe PMC, Wikipedia) · `scripts/render_figure.py` spec → SVG + editor · `scripts/icons.py` built-in icons · `scripts/editor.html`
  editor template · `scripts/export.py` PNG/PDF + layout check · `scripts/plot_data.py` data plots/panels ·
  `scripts/render_diagram.py` Mermaid/D2/Graphviz · `scripts/bioicons.py` icon search/fetch with licences ·
  `scripts/setup_check.py` dependency report · `scripts/render_3d.py` 3D scenes · `scripts/render_summary.py`
  lesson summaries · `scripts/servier.py` + `servier_extract.ps1` Servier Medical Art library · `scripts/library.py` unified search over all free art libraries
- `references/figure-spec.md`, `figure-style.md`, `diagram-mode.md`, `simulation-models.md`,
  `biopolymer-composites.md`, `other-fields.md`, `publishing-policy.md`, `open-source-landscape.md`
- `assets/examples/*.json` starting templates
