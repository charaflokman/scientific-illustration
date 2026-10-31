# Figure spec reference (`scripts/render_figure.py`)

The spec is a JSON file. You decide the content and rough placement; the script draws the geometry,
keeps text as real text, gives every element a stable `id`, and embeds the spec inside the SVG.
All coordinates and sizes are in **millimetres at final print size**, origin top-left.

Contents: 1. Top level · 2. Element types · 3. Icons · 4. Placeholders · 5. Editing round-trip · 6. Layout recipes

## 1. Top level

```json
{
  "canvas": {"width_mm": 170, "height_mm": 90, "font_pt": 7, "font": "Arial, Helvetica, sans-serif",
             "background": "#FFFFFF", "stroke_mm": 0.25},
  "colors": {"matrix": "#56B4E9", "filler": "#E69F00", "crosslinker": "#009E73"},
  "provenance": "one line: what the figure is based on (user's methods text, their data, schematic only)",
  "show_credits": true,
  "elements": [ ... ]
}
```

- `colors` maps semantic roles to colours. Elements say `"color": "matrix"` (a role), an Okabe–Ito name
  (`orange skyblue green yellow blue vermillion purple black grey`) or a hex value. Built-in roles:
  matrix, filler, crosslinker, plasticizer, solvent, water, heat, good, bad, neutral, text, line.
  Keep one role → one colour across every figure of a paper.
- Widths: 85 mm (single column), ~114 mm (1.5 column), 170–180 mm (double). Check the journal.

## 2. Element types

Common keys: `id` (stable, short, meaningful: `dissolve`, `filmA`), `x`, `y`, `w`, `h`.

| type | keys | notes |
|---|---|---|
| `panel` | x y w h, `letter` "(a)", `title`, `fill`, `stroke`, `title_bar` (colour), `dashed`, `radius` | draw panels first (they sit underneath) |
| `box` | x y w h, `text`, `fill`/`color`, `stroke`, `dashed`, `weight`, `text_color`, `radius` | process boxes, callouts |
| `icon` | x y w [h], `icon`, `color`, `accent`, `params`, `label`, `label_pos` below/above/left/right/none, `label_width`, `seed`, `flip` | built-in line art (section 3); non-stretch icons keep 1:1 and centre in the box. Hide a label with `"label_pos": "none"` (never `"label": "none"`) |
| `svgfile` | x y w [h], `path`, `license`, `author`, `source`, `label` | external SVG (e.g. from `bioicons.py get`); scripts are stripped; CC-BY credits are added to the figure |
| `molecule` | x y w [h], `smiles`, `label` | RDKit 2D structure (falls back to a generic icon with a warning) |
| `image` | x y w h, `path`, `label` | the user's own raster (micrograph, photo); embedded unaltered |
| `placeholder` | x y w h, `text` | dashed box for an image the user must supply, e.g. "[? SEM, 5 wt% CNC]" |
| `text` | x y, `text`, `font_pt`, `weight`, `anchor` start/middle/end, `color`, `italic`, `w` (wrap width), `valign` | `\n` forces a line break |
| `arrow` | `from`, `to` (element ids or `[x, y]`), `label`, `label_side` above/below, `label_width`, `style` solid/dashed, `curve` (−0.5…0.5), `route` straight/elbow, `both`, `color`, `width_mm`, `gap` | endpoints clip to the element boxes, so arrows follow when elements move |
| `flow` | x y w h, `steps` [{id, icon, label, color, accent, params}], `arrows` [labels], `icon_size`, `icon_top` | expands into evenly spaced icons + labelled arrows; ids `flow.s0`…, `flow.a0`… unless steps give ids |
| `legend` | x y, `items` [{color, label, shape dot/square/line}], `direction` vertical/horizontal | |
| `inset` | `cx` `cy` `r`, `path` (image, usually a 3D close-up), `title`, `color`, `zoom`, `offset` [dx,dy], `to` [x,y] (optional dashed leader), `font_pt` | circular zoom-in with ring and title |
| `bracket` | x1 y1 x2 y2, `label`, `color` | groups a span of steps |

Draw order = list order. Arrows may reference elements defined later.

## 3. Built-in icons (original, CC0)

Run `python scripts/render_figure.py --list-icons` for the current list. Groups:
- Vessels: `beaker` (params level, particles, dispersion, shape dot/rod, stir_bar), `flask`, `petri_dish` (particles), `vial`, `centrifuge_tube`
- Equipment: `stir_plate`, `sonicator`, `oven`, `hot_press`, `extruder`, `pipette`, `syringe`, `thermometer`, `balance`, `microscope`, `spectrometer`, `tensile_tester`, `soil_burial`
- Materials: `film` (oblique slab, particles/dispersion/shape), `film_cross_section` (stretches; particles, dispersion uniform/agglomerated, shape, particle_r), `polymer_chain` (chains), `crosslinked_network`, `nanoparticle`, `coated_nanoparticle`, `agglomerate`, `nanocrystal_rods`, `water_drop`, `contact_angle` (angle)
- Biology: `cell`, `bacterium` (use Bioicons for anatomy, organisms, organelles)
- Readouts: `plot_curve` (kind rise/decay/peak/sigmoid: a *pictogram* of a trend, never data), `check`, `cross`, `crack`, `heat`, `molecule_generic`, `placeholder`

`color` paints the main body (`.rv-paint`), `accent` paints particles/filler (`.rv-accent`).
For anything not here, search Bioicons (`scripts/bioicons.py search …`), prefer `cc-0`, and keep the licence fields.

## 4. Placeholders — never invent a value

Write any missing number, condition or result as `[? …]`, e.g. `"Dry [? °C], [? h]"`, `"Tensile strength +[? %]"`.
The renderer colours them red/bold, keeps each on one line, and lists them after rendering; `export.py --check`
lists them again. Hand the list to the user. A `plot_curve` pictogram shows a direction the *user* reported,
not data; if the source does not state the direction, label it `[?]`.

## 5. Editing round-trip (the main selling point — explain it to the user)

1. `render_figure.py spec.json -o out/fig.svg` writes `fig.svg` and `fig.editor.html`.
2. The user opens `fig.editor.html` (double-click; works offline): click to select, drag to move (connected
   arrows follow), double-click text to retype, colour pickers for main/accent colour, A−/A+ for text size,
   Delete hides, Ctrl+Z / Ctrl+Y, "Add text", "Save SVG" (edits stored inside the file), PNG at 300/600/1200 dpi,
   "Copy edits" (JSON to paste back into chat). It also opens any other SVG (drag-drop), with simpler editing.
3. When the user asks for content changes later, edit the spec and re-render with
   `--keep-edits <the SVG they saved>` so their manual moves/retypes/colours survive. `--overrides edits.json` does
   the same from pasted "Copy edits" JSON. Overrides are keyed by element id, so keep ids stable between versions.
4. Other editors: the SVG opens in Inkscape, Illustrator, Affinity, and PowerPoint (Insert → Pictures → SVG,
   then right-click → "Convert to Shape" in Microsoft 365) with text still editable.

Override keys: `dx`, `dy` (mm), `text`, `color`, `accent`, `fill`, `stroke`, `font_pt`, `hidden`; `__added__` holds
elements created in the editor.

## 6. Layout recipes

- **Graphical abstract (process → product → properties):** canvas ~170 × 70–90 mm (or the journal's GA size).
  Row 1: a `flow` of 4–7 steps with conditions on arrows. Row 2: the product (film/particle) centred, with 3–4
  property readouts around it. Keep ≤ 25 words of text outside labels.
- **Comparison (treated vs untreated, with vs without):** two panels side by side, same internal layout, mirrored
  icons, colour title bars (cool for the favourable case, warm for the failure case), readouts row underneath,
  a shared legend. See `assets/examples/comparison_dispersion.json`.
- **Fabrication scheme:** `assets/examples/fabrication_casting.json` (solution casting). For extrusion use
  `extruder` → `hot_press` with temperature profile / screw speed / pressure / time on arrows.
- **Mechanism / interaction scheme:** chains (`polymer_chain`, `crosslinked_network`) + `molecule` (RDKit) +
  dashed arrows labelled "proposed H-bonding" etc. Mechanism words stay hedged unless the source shows evidence.
- **Biology pathway / cell scheme:** `box` nodes + arrows (`style: dashed` for inhibition is ambiguous — use a
  label or a `box` with a ⊣ in text), Bioicons cells/organelles; for large networks prefer Diagram mode.
- Spacing: ≥ 3 mm between labels, panel padding ≥ 3 mm, icons 12–20 mm in a 170 mm figure. If labels collide,
  increase `label_width` or the slot width rather than shrinking text below 6 pt.
