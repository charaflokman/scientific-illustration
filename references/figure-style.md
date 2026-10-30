# Figure style guide

Sizes and rules below are common defaults. The target journal's author guide wins whenever it differs; ask
the user for the journal when it matters (graphical abstracts especially).

## Size (design at final size, in mm)
- Single column ≈ 85–90 mm wide; 1.5 column ≈ 114–140 mm; double column ≈ 170–180 mm. Max height usually ≈ 225–240 mm.
- Graphical abstracts vary by journal (pixel sizes such as 1328 × 531 px or 1200 × 600 px, or ~13 × 5 cm are
  common examples — check). Keep the aspect ratio the journal asks for and the text readable when shrunk.
- Text 6–8 pt at final size (never below 5 pt; `export.py --check --min-pt 6` enforces). Panel letters 8–10 pt bold.
- Lines: axes/outlines 0.25–0.5 pt-equivalent (≈ 0.1–0.2 mm); data lines and arrows ≈ 0.35–0.5 mm.
- Raster export: 300 dpi for photos/halftones, 600 dpi for combination art, 1000–1200 dpi for line art. Vector
  (SVG/PDF/EPS) is preferred wherever the journal accepts it.

## Type
- Sans-serif (Arial/Helvetica) for labels; consistent size hierarchy (title > label > annotation).
- Variables italic (*T*, *D*, *M*<sub>t</sub>), units upright with a space: "60 °C", "5 wt%", "10 µm".
- Write units in parentheses on axes: "Temperature (°C)", "Wavenumber (cm⁻¹)".
- Sentence case labels; no all-caps blocks; spell out abbreviations in the caption.

## Colour (colour-vision-deficiency safe)
- Okabe–Ito: #E69F00 orange · #56B4E9 sky blue · #009E73 green · #F0E442 yellow · #0072B2 blue · #D55E00
  vermillion · #CC79A7 purple · #000000 black (Okabe & Ito 2008, "Color Universal Design").
- Map colour to meaning and keep it across the whole paper (matrix = blue, filler = orange, crosslinker = green…).
- Never encode meaning by colour alone: add shape, line style, marker, pattern or a direct label, so the figure
  still works in greyscale and for red–green colour blindness. Avoid red/green pairs and rainbow maps; use
  viridis/cividis for continuous data.
- Backgrounds: white or very light tints (≤ 15 % saturation) for grouping zones; saturated colour only for the
  thing that matters.

## Layout
- One message per figure; reading order left→right or top→bottom; number steps when order matters.
- Conditions (T, t, rpm, concentration, solvent, atmosphere) go on the arrows, not in a separate legend.
- Align elements on a grid; equal spacing between repeated steps; consistent icon size within a row.
- Panel letters (a), (b), (c)… top-left inside each panel, same size everywhere.
- Whitespace is part of the design: ≥ 3 mm padding inside panels; nothing touching the canvas edge.
- Comparisons: identical internal layout in both panels so the eye compares like with like.

## Data plots
- Start bar charts at zero; no 3D bars; no dual axes unless the quantities are physically linked (TGA + DTG).
- Show individual points when n is small; state n and the error measure (SD, SEM, 95 % CI) in the caption.
- Spectra: FTIR wavenumber decreasing left→right; XRD 2θ increasing; stack with offsets and say "offset for clarity".
- Label only peaks the data show and the user (or a cited source) assigns.
- Significance letters/asterisks only from the user's statistics.

## Captions
Draft one per figure: title sentence, what each panel shows, abbreviations, n and error type, which parts are
schematic/illustrative, and the disclosure sentence from `publishing-policy.md` when an AI assistant helped draw it.

## Visual QA before delivering (do it every time)
1. `python scripts/export.py fig.svg --check --png 300` and fix every overlap, outside-canvas and small-text issue.
2. Open the PNG with the Read tool and look at it at the size it will be printed: legible? balanced? anything
   cut off? colours distinguishable? any label pointing at the wrong thing?
3. Compare every number and condition with the source; unresolved ones stay `[? …]` and go in the reply.
