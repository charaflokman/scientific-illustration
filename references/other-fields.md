# Other fields: what to draw and with which tool

The same three modes cover every field; this file lists the figure types researchers ask for most and the
quickest faithful way to build each. The honesty rules from SKILL.md apply unchanged.

## Chemistry (general)
- **Reaction schemes:** `molecule` elements (RDKit from SMILES) left→right, `arrow` with reagents above and
  conditions below (`label_side`), yields only from the user. Check every SMILES renders the intended structure
  (look at the PNG) — a wrong stereocentre or charge is a factual error.
- **Synthesis / work-up flow:** `flow` with vessels and equipment icons, or Diagram mode for long procedures.
- **Mechanisms with curved arrows:** draw intermediates with RDKit, electron-pushing arrows as curved `arrow`
  elements (`curve` 0.3–0.5) between `[x, y]` points; keep it hedged if not established in the source.
- **Spectra/chromatograms:** `plot_data.py` (`xy`, `ftir`, `xrd` kinds); peak labels only from user assignments.
- **Energy diagrams:** `text` + short horizontal `box` levels + dashed connectors; energies from the user.

## Biology and biomedicine
- **Signaling pathways:** for ≤ 12 nodes use Figure mode (boxes/Bioicons + arrows, label activation "→" and
  inhibition "⊣" explicitly in text); larger networks → Diagram mode (Mermaid flowchart / D2). Colour node types
  consistently (receptor, kinase, TF, output).
- **Cell / tissue / organism cartoons:** Bioicons (cells, organelles, organs, mice, bacteria; prefer cc-0, credit
  CC-BY such as Servier Medical Art). Built-in `cell`, `bacterium` for simple cases.
- **Named proteins, receptors, transporters, drugs:** Reactome via `library.py search <gene/protein> --lib reactome`
  (CC BY 4.0, credited automatically).
- **Whole organisms (ecology, evolution, zoology, botany, One Health):** PhyloPic silhouettes via
  `library.py search <scientific name> --lib phylopic` (black silhouettes; use one per taxon, label with the name).
- **Neuroscience and behaviour setups, lab animals:** SciDraw via `library.py search <term> --lib scidraw`.
- **Experimental design / animal study timelines:** Diagram mode (Mermaid `timeline` or `gantt`) or a `flow` with
  time labels on arrows; group sizes `n = [?]` unless given.
- **PRISMA 2020 flow:** Diagram mode template in `references/diagram-mode.md`; every count from the user.
- **Assay plots:** `plot_data.py bar` with individual points, SD/SEM stated, significance from the user's stats.
- **Primary images (blots, gels, microscopy):** place the user's file with `image`; never adjust, crop
  selectively, or generate them.

## Physics and engineering
- **Experimental setups (optics bench, beamline, electrochemical cell, rig):** Figure mode boxes for components,
  `arrow` for beams/flows (colour by wavelength/medium), dimensions with `bracket`; Bioicons has some lab apparatus.
- **Schematics of models (springs, slabs, boundary conditions):** boxes + text with italic variables; equations as
  plain text labels (keep them simple; LaTeX is not rendered).
- **Field / flow / phase diagrams from data:** matplotlib via `plot_data.py xy`, or a short custom matplotlib
  script saved as SVG with `svg.fonttype: none` (editable text) when the plot kind is not covered.
- **Process/control block diagrams:** Diagram mode (D2 handles nested blocks and ports well).
- **Simulations:** diffusion, heat conduction, oscillators, kinetics: use the analytic/ODE approach of
  `simulation-models.md` with process-simulator; cite the textbook solution used.

## Social science, medicine and reviews
- Conceptual frameworks / causal loop diagrams: Diagram mode (Mermaid flowchart with labelled edges, `+`/`−`
  polarity in edge labels).
- Study flow / CONSORT: Diagram mode, counts as placeholders.

## When the built-in tools are not enough
- A plot type `plot_data.py` lacks: write a small matplotlib script in the user's folder, same style rules
  (Okabe–Ito, 6–8 pt, `svg.fonttype: none`), and keep the script so the user can rerun it.
- An icon that exists nowhere: draw it as a few SVG primitives in a `svgfile`, or approximate with boxes and a
  clear label; tell the user it is a simplified drawing.
