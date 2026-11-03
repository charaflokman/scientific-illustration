# House style profile (learned from client feedback)

Read this before every new visual. It records what clients accepted and rejected, so each job starts at the level
the last one ended. Per-client additions live in `<project folder>/client_profile.md` (see SKILL.md, "Learn the
client"); when the two disagree, the client's own profile wins.

## What clients rejected, and why

| Rejected | What they said | Rule that follows |
|---|---|---|
| Plain primitives (spheres on straight sticks, flat slabs, grey floor) | "old and undeveloped", "no details" | every object carries its own structural and surface detail (see the 3D section of SKILL.md) |
| Sea-urchin nanoparticles: straight identical ligands, mirror core | "too simple", "I don't like it" | curved ligands of varied length, faceted or atomic core, depth of field, neighbours out of focus |
| Clear refractive gel block | "looks like glass" | hydrogel = icy, pale, slightly milky, water IOR, soft highlights; never a clean glass box |
| Opaque saturated gel | (hides the contents) | the inside must stay legible: fibres, particles, drug visible through a light haze |
| Decorative rods / crystals with no scientific meaning | "what are these sticks?" | nothing in the scene that the science does not contain; crystals only for crystalline materials |
| Boxes-and-panels layout with a small 3D image | preferred an AI image with a central hero | hero-centred composition (below) |
| Slogans, casual wording | — | formal journal prose (SKILL.md, "Write figure text like a journal") |
| Fibre mats of thick, evenly bent tubes; CNC drawn as long curly fibres | "did not like the fibre" | draw fibres as they look in SEM: many fine fibres of near-constant diameter that meander and interweave, cut at the sample edge; CNC are short rigid needles (`rods` with `lengthVar`), never long curls |

## What clients accepted

- Molecules from SMILES with CPK colours: "very acceptable".
- Formal, precise wording: "legendary, clear".
- Silane-capped Ag NPs with curved ligands, a faint steric haze and out-of-focus neighbours (demo-silane2 inset_steric).
- Reference look they chose (Nano Banana / Dola AI images): a single large 3D hero, pale blue-white palette,
  frosted and icy materials with visible inclusions, porous organic substrates, soft studio light, circular zoom
  insets in the same style, an icon/legend strip. They also noticed those images were chemically wrong (S for Si,
  Si=O, wrong QAS orientation, typos): our edge is the same beauty with correct chemistry.

## Default composition for a graphical abstract or overview figure

1. Title (full technical subject) and a one-line subtitle with "schematic, not to scale".
2. One photoreal hero in the centre, about 50–60 % of the canvas width; exploded layers if the system is layered.
3. Left: 3–5 layer labels (bold heading + one grey line) with thin arrows into the hero.
4. Right: 3 circular insets, each a mechanism, rendered in the same palette and light as the hero, title above and
   one sentence below.
5. Bottom strip: chemistry (2D structures from SMILES, reactions) in panels with the same pale fills.
6. Footnote with abbreviations.

## Palette and light

- One hue family per figure (default pale blue: #F5F8FB background, #CFE5F4 gels, #B9D9EE fibre mats, #123B63 ink,
  #2F6FAE accents); CPK colours only on atoms; at most one warm accent (drug or bacteria).
- Soft high-key studio light, but with real contact shadows and depth of field so it reads as a photograph.

## Realism checklist (look at the render before showing it)

- Would a macro photograph look like this? Perfectly clean, identical, evenly lit objects read as CG.
- Variation: no two fibres, particles, pores or ligands identical (size, tint, roughness, bend).
- Micro-detail at the scale of the camera: surface relief, roughness variation, fused fibre junctions, pore walls
  with smaller pores.
- Light: a clear key direction, contact shadow/occlusion where things touch, a rim that separates objects from
  the background.
- Lens: depth of field, slight vignette, faint grain and bloom on highlights (`photo` post-process).
- Scale: contents large enough to read at the printed size of the inset (≥ 1 mm per particle on paper).
