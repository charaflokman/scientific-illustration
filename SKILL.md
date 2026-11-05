---
name: scientific-illustration
description: Publication-ready, editable scientific illustration for researchers in any field (chemistry, biology, materials, medicine, physics, engineering), with depth in biopolymer composites. Makes graphical abstracts, fabrication and mechanism schemes, with/without comparisons, signaling pathways, setups, PRISMA and flowcharts from text, plots of the user's data (FTIR, XRD, TGA/DTG, DSC, tensile, swelling, release, any CSV/Excel), photoreal 3D renders, lesson summaries, short MP4 explainers and interactive process simulations (diffusion, swelling, crosslinking, release). Use it whenever the user wants a figure, scheme, diagram, 3D image or animation of research content, even without saying 'figure', names only a topic (it researches first), wants to edit a figure made earlier, or asks for an alternative to BioRender, FigureLabs or Napkin, in any language. Cues: chitosan, cellulose/CNC, alginate, PLA, nanofiller, film, membrane, hydrogel, nanoparticles, characterization.
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
3. **Honest about origin.** Route B figures and data plots are deterministic and journal-safe. AI images are
   used only in Route A (see "Two routes"), always checked by Claude and always disclosed, because many publishers
   restrict AI-generated images (see `references/publishing-policy.md`).

Reply in the user's language, whatever it is. Keep figure text in English unless the user asks otherwise, because
journals expect it; lesson summaries and teaching material follow the user's language.

## First use: check the tools

The first time the skill is used on a machine (and again every 30 days), run
`python scripts/setup_check.py --first-run` before anything else. It lists what is installed (Python packages,
browser, Blender and GPU, Molecular Nodes, studio HDRIs, art libraries, TPMS venvs, Remotion, node) and writes
`~/.cache/scientific-illustration/setup_report.txt`; within 30 days it just prints that report. Tell the user in 3–5
lines what is ready and what is missing for the output they want, and offer to install the missing pieces (each
line gives the command). Install nothing without the user's yes; audit downloaded tools first and keep Python tools
in their own venvs under `~/.cache/scientific-illustration/venvs/`.

## Learn the client (every job, every piece of feedback)

The skill works for clients who come back with new requests at any time; each request must start from what they
already taught us. Before a new visual, read `references/style-profile.md` (house style learned from all clients)
and, if it exists, `client_profile.md` in the client's project folder. After every piece of client feedback
("looks like glass", "too simple", "I like this one", a reference image they prefer), do three things in the same
turn: (1) write the feedback, the image it refers to, and the rule that follows into `client_profile.md`
(create it if missing: client, field, preferred look, rejected looks with reasons, accepted outputs, reference
images and what in them is wrong); (2) if the lesson is general, add it to `references/style-profile.md`;
(3) apply it to the current work. When the client sends a reference image, analyse it in writing before
changing anything: composition, palette, materials, scale of contents, light, insets, text, and every scientific
error in it, then say which parts you will match and which you will not copy. Keep accepted outputs unchanged
(pin their specs) unless the client asks.

## Two routes: choose one at the start of every job

Ask once, right after the tool check, before anything is drawn:

| | **Route A: with AI** | **Route B: without AI** |
|---|---|---|
| Who draws the scene | an image AI the user chooses | code: `render_figure.py`, `render_3d.py --blender`, `plot_data.py`, library art |
| Who writes text and chemistry | Claude, always | Claude, always |
| Look | richest, fastest | fully reproducible, every part editable |
| Journals | disclosure required; some refuse it | no AI disclosure needed |
| Needs | the user signed in to the AI | local tools only |

**Route A steps:** the user names any image AI. Open it in Claude's built-in browser and ask them to sign in themselves;
never ask for or type a password, and never pay or subscribe for them. **Verify the sign-in yourself before writing any prompt**:
read the page in the browser tab you will use (an account avatar or name, a chat box that accepts input, no "Sign in"
button) and do not rely on the user's word, because sign-ins do not always carry over between sessions or tabs. If
the page still shows a sign-in button, tell the user what you see and wait. Then follow "Route A: the AI draws, Claude does
everything else". If that AI fails (sign-in blocked, no image, no download), direct them to Gemini, the tested service.
If Gemini fails too or they decline it, switch to Route B.

**Route B steps:** skip every AI service and follow "Pick the mode" and "Workflow". Choose it when the user asks, or
when the target journal refuses AI images.

Save the choice in `client_profile.md`, do not mix routes in one figure unless asked, and always say which route
produced a deliverable.

## Project intake: ask about the project first, with choices

Clients judge figures as "basic" mostly when the figure was built from too little about the project. Before a new
visual (not an edit), run a short intake in one message: 5–7 numbered questions, each with lettered choices plus
"other", so the user can answer like "1b 2c 3a…". Use the harness's multiple-choice tool if it has one. Skip any
question the user's material already answers, and never ask more than once.

1. **Where will it be used?** a) journal figure b) graphical abstract c) thesis/review chapter d) talk/poster
   e) teaching/lesson f) social media/video
2. **Who reads it?** a) specialists in your exact field b) scientists from other fields c) students d) general public
3. **Complexity level:** a) simple — one message b) detailed — the full mechanism c) expert/complex — every actor,
   sub-cellular location, inset zooms, regulatory loops, drugs and references (BioRender "publication" level)
4. **Style:** a) academic (clean, Servier/Reactome art) b) rich 3D render c) pixel art d) match a figure I'll send
5. **The one message** the figure must leave (one sentence), and **must-include** elements (genes, materials,
   conditions, steps, organisms).
6. **Your project context:** title or aim, your material/model system, your key result or hypothesis, and any of
   your own data, images or a previous figure to match.
7. **Format:** size (single 85 mm / double 180 mm / 16:9 / square), colour constraints (journal or lab palette),
   language of labels, deadline for a first draft.

Then summarise the brief back in 3–4 lines, including the four look decisions (reference, palette, typeface,
layout; see `references/style-profile.md`) ("Expert-level journal figure, 180 mm, specialists, message: …") and
start. Defaults if they skip: journal, specialists, detailed, academic, double column.

| | **Simple** | **Detailed** | **Expert / complex** |
|---|---|---|---|
| Purpose | one message at a glance | the full mechanism for experts | a review-grade figure that maps the whole system |
| Content | 3–6 elements, one panel | multi-panel (a)(b)(c), steps, conditions | 25–60 elements across compartments (membrane, cytoplasm, organelles, nucleus), inset zooms with molecular detail, feedback loops, inducers/inhibitors, a summary strip |
| Text | 1–3-word labels | labels + notes, values, [n] | the same plus enzyme names on every arrow, gene names, a short legend of symbols |
| Art | large icons, white space | library art, molecular detail | library art for every actor (Reactome proteins, Servier organelles, RDKit molecules), shaded 3D-style membranes, a 3D render as hero when space allows |
| Data | none or one number | every stated value; `[? …]` gaps | the same, with each node traceable to a numbered source |

**Write figure text like a journal, never like an ad.** Titles state the subject in full technical terms
("Organofunctional silanes at the filler–polymer interface of …"), not slogans ("One molecule, three jobs"). Notes are
terse, declarative and use standard nomenclature (oxirane ring-opening, siloxane linkage, steric stabilisation); no
second person, no exclamation, no marketing words (powerful, amazing, game-changing), no casual phrasing ("nothing has
to leach out"). Define abbreviations in a footnote line at the bottom, panel letters (a)(b)(c), roman numerals for
reactions, and "schematic, not to scale" in the subtitle. Point at details with small numbered markers and a keyed
list instead of long crossing leader lines.

**Chemistry is checked atom by atom.** Molecules come from SMILES (RDKit 2D, or 3D via `render_3d.py` molecule objects
with `smiles` + `anchor` to graft them on a surface), never drawn freehand. Before delivering, verify: valences (Si is
tetravalent: one Si–C, three Si–O; no Si=O, no S in silanes), charges and counter-ions, the side of a molecule that faces
a surface (e.g. QAS: N⁺ near the surface, alkyl chain outward), balanced reactions, and spelling of every label.

**Expert level is never boxes and arrows.** Every protein, organelle, molecule and cell gets real art (search
`library.py` first: Reactome for named proteins/receptors/transporters, Servier for organelles and cells, RDKit for
small molecules); boxes are only for short notes. Lay the figure out in biological space (outside → membrane →
cytoplasm → organelles → nucleus) instead of a flowchart grid, and add at least one inset that zooms into the key
molecular event.

Build the most detailed spec first when several levels are wanted, then derive the simpler ones by removing panels and notes (keep
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

**Every request starts with an internet search, and the user sees the references.** Before the first draft of any new
visual (figure, 3D render, summary, video, simulation) search the web for everything the request touches: the
science (mechanism, structures, accepted nomenclature, typical values), how experts draw it (published figures and
graphical abstracts on the topic, the real shape and scale of each object, e.g. Ag NP habit, bacterial pili), and
the tools or open art that could make it better. Use the harness's web search and `scripts/research.py`. Then show
the user, before or with the draft, a short numbered reference list (title, source, year, link) and one line per
reference on what it was used for. Every element, label and number in the visual must trace to the user's material
or to one of these references; put the numbers in `provenance` and, at detailed level, on the labels. Skip a fresh
search only for small edits to a visual whose references were already shown. Never present a reference you did not
open, and never cite from memory alone.

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

## Route A: the AI draws, Claude does everything else

The steps name Gemini, but they apply to any service. In its website, choose its image tool first when it has one
(otherwise it may reply with text), and if it still replies with text, ask it to generate the image now.

1. **Prompt.** From the user's text and the references, list the panels, the exact labels and every number. Tell Gemini
   not to draw molecules, chemical structures or formulas, micrographs, blots, spectra, photos or data plots, and to
   leave clean empty space where molecules go. Gemini also draws **no text at all** (no letters, numbers or symbols): **Claude adds all text** as editable vector labels with `render_figure.py`. **Claude makes every molecule from SMILES** (RDKit 2D, or `render_3d.py`
   3D with a transparent background) and places it on the image with `render_figure.py`. If the user wants their text used as it is, send
   it unchanged.
   Asking Gemini to remove text from an existing image failed in testing, while a new chat with a wordless scene description
   ("textless wordless illustration ... no words, no letters, no numbers, no labels") worked. Describe scenes only.
   In Gemini, start the prompt with "Use your image generation tool." so it draws instead of replying with text.
2. **Generate.** `python scripts/gemini_image.py prompt.txt -o draft.png` (`GEMINI_API_KEY`; the API needs billing). With no
   paid API, use the Gemini website in a browser where the user is signed in: pick the image tool, send the prompt,
   download the full-size image with the image's full-size download button (not a screenshot or the preview).
   Then verify the file is new: its modified time is after the prompt was sent and its hash differs from every earlier
   download, because a failed download once silently reused an old image. Stop for the user at any sign-in or payment step.
3. **Check at full resolution, in crops.** Screen-sized previews hide errors. Read every word and report by location:
   - Spelling and invented words in all text.
   - Numbers, units and citations: each must match the source, and none may be invented.
   - Chemistry: Si drawn as S, Si=O, valence, charges and counter-ions, N+ with H on a quaternary ammonium, wrong
     functional groups, orientation on a surface. Any molecule Gemini drew anyway is removed and replaced by Claude's.
   - Fabricated evidence: anything resembling a TEM/SEM image, photo, blot or spectrum, and curves with no data behind
     them. Remove these; real data goes in a `[? ...]` placeholder for the user's own images.
   - Claims and direction: arrows, cause and effect, "proposed" stated as proven, anything absent from the source.
4. **Fix.** Correct with `--edit` and a narrow instruction ("Change only ..."), then check the whole image again, because
   edits can break other parts. After two failed attempts on an item, cover it with editable output from
   `render_figure.py`: real text, RDKit structures, `plot_data.py` plots.
5. **Report.** Give the user the list of errors found, fixed and remaining. Never call an image error-free when any part
   could not be read. State that it is AI-generated, keep the `.provenance.json`, include a disclosure sentence, and
   tell the user to check the target journal's policy, since the journal may refuse it.

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

**Rendered 3D hero (code-drawn alternative for journals that refuse AI images):** build the scene with `render_3d.py`
(types slab, scaffold, fibers, brush, spheres with finish metal/glass/matte), export a transparent PNG with
`--png 2400x1700`, then place it as an `image` element in a `render_figure.py` spec and put all text, arrows and
RDKit chemistry on top as editable vector. Example: `assets/examples/silane_roles.json` + `hero_dressing.json`.

**Photoreal 3D (what clients now expect): `render_3d.py scene.json --blender 2400x1700 --samples 160`.** Plain
primitives read as "old and undeveloped", so `render_blender.py` gives every object structural and surface detail:
`scaffold` `style` foam (pores inside pores, cut faces as a cross-section) / gyroid (TPMS) / nonwoven (layered fibres
of varied diameter); slabs are bevelled and, when translucent, a milky gel whose embedded fibres and particles stay
visible (`milk`); `corona` = faceted multiply-twinned Ag core, curved ligands of varied length with heads, a faint
steric-layer haze, optional `cutaway` (degrees) to open the shell towards the camera; `capsule` = bacterium with a
wrinkled translucent envelope, `pili`, `flagella`; `crystals` only when the material really is crystalline; molecules
from SMILES with split-colour bonds. Lighting is a Poly Haven studio HDRI (`hdri`, CC0) plus soft key/fill/rim and
reflection softboxes; `blur` and `focus` set depth of field; `background: null` gives a transparent PNG for insets;
`shadow: false` for floating objects. The camera is fitted tightly to the projected scene (`fit`, default 1.06, is the
margin), the contact shadow covers only the footprint (`shadowSize`, default 1.25), and tone mapping is AgX Medium High
Contrast (`"look": "AgX - Punchy"` and `exposure` in stops when a pale scene washes out). Metal `spheres` are
faceted satin-silver particles (`"facets": false` for smooth spheres), because mirror spheres inside a gel read as air bubbles. Compose like a magazine render: one large hero object in focus, neighbours
behind it out of focus, nothing decorative that is not in the science (no stray rods or crystals "for looks").
Molecular Nodes (Blender add-on, installed per machine) is the route for proteins and PDB/AlphaFold structures.

**Specialised scientific 3D tools** (each in its own venv under `~/.cache/scientific-illustration/venvs/`, or as a
Blender extension; `setup_check.py` lists what is present). Pick by subject, and let the real structure supply the detail:

| Subject | Tool | Use |
|---|---|---|
| Metal NPs, clusters, crystal surfaces | ASE (`venvs/atomistic`) | `corona` with `"core": "icosahedron"/"decahedron"/"octahedron"/"cuboctahedron"`, `"shells": n`, `"element": "Ag"`: the NP is built atom by atom on its real lattice and scaled to `radius` |
| Atomistic snapshots, MD frames | OVITO (`venvs/atomistic`), v_ase (`venvs/vase`, exports to Blender) | render or convert particle data before composing |
| Proteins, receptors, enzymes | Molecular Nodes (Blender), PyMOL open-source (`venvs/pymol`) | cartoon / surface styles from a PDB or AlphaFold id |
| Nanoparticles and crystals inside Blender | Atomic Blender cluster + PDB/XYZ (Blender extensions) | import .xyz/.pdb written by ASE, VESTA or the user |
| Crowded cell interiors (mesoscale) | cellPACK (`venvs/cellpack`, Python 3.9) | pack proteins and organelles into compartments from a recipe |
| TPMS scaffolds for exact geometry | PyScaffolder (`venvs/scaffold`), microgen (`venvs/microgen`) | export a mesh when the scaffold geometry itself is the data |

Tool status (smoke-tested 2026-11-05 on Windows, Blender 5.1):
- Works: PyMOL, PyScaffolder, ASE (Ag icosahedron, 147 atoms, written to .xyz/.pdb); OVITO (Tachyon PNG of that .xyz); Atomic Blender
  (`bpy.ops.import_mesh.xyz`); Molecular Nodes (`mn.Molecule.load(path).add_style("ball_and_stick")`); microgen
  (`Tpms(surface_function=gyroid, ...).generate_vtk(type_part="sheet")` → STL); v_ase and cellPACK import.
- In Blender scripts, Molecular Nodes is an extension: `importlib.import_module("bl_ext.user_default.molecularnodes")`
  after `addon_utils.enable(...)`; plain `import molecularnodes` fails.
- cellPACK writes `./.creds` (the OS username) into the current folder on import: run it only from a scratch work
  folder, never from the client's project folder, and delete that file afterwards.
- PyMOL on Windows: install `pymol-open-source-whl` (bundles its libraries; plain `pymol-open-source` built without
  them fails to load `_cmd`); `cmd.png(path, ray=1)` with `ray_opaque_background 0` gives a transparent PNG.
  PyScaffolder needs numpy in its venv (`generate_scaffold(vertices, faces, Parameter())`, e.g. gyroid, porosity reported).
- `setup_check.py` now imports each venv module, so a tool that is installed but cannot load is reported as broken.

A capability sheet with one render per object type is built by `scripts/gallery.py --out <folder>`; show
it to new users so they can choose a look.

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
- Audit the "AI-look tells" list in `references/style-profile.md` (neon, purple gradients, emoji, uniform boxes,
  marketing words) and remove any the client did not ask for.

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
For anything the template does not cover (voice-over, captions from audio, charts, transitions, maps), read only the matching file under `references/remotion/` (the official Remotion agent skill, routed from its `SKILL.md`;
it is not shipped with this skill, so when the folder is missing use the docs at remotion.dev/docs), and write a custom composition in the cached project.
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
- `scripts/gemini_image.py` Gemini image generation and correction · `scripts/research.py` topic research (OpenAlex, Europe PMC, Wikipedia) · `scripts/render_figure.py` spec → SVG + editor · `scripts/icons.py` built-in icons · `scripts/editor.html`
  editor template · `scripts/export.py` PNG/PDF + layout check · `scripts/plot_data.py` data plots/panels ·
  `scripts/render_diagram.py` Mermaid/D2/Graphviz · `scripts/bioicons.py` icon search/fetch with licences ·
  `scripts/setup_check.py` dependency report · `scripts/render_3d.py` 3D scenes · `scripts/render_summary.py`
  lesson summaries · `scripts/servier.py` + `servier_extract.ps1` Servier Medical Art library · `scripts/library.py` unified search over all free art libraries
- `references/figure-spec.md`, `figure-style.md`, `diagram-mode.md`, `simulation-models.md`,
  `biopolymer-composites.md`, `other-fields.md`, `publishing-policy.md`, `open-source-landscape.md`
- `assets/examples/*.json` starting templates
