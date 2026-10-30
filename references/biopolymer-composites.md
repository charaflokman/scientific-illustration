# Biopolymer composites: systems, fabrication schematics, characterization rendering

Use this file for figures about biopolymer composites: graphical abstracts, fabrication schemes and characterization panels. For interactive models see `simulation-models.md`. For journal rules see `publishing-policy.md`.
Verification date: 2026-10-29. The confidence column means: **High** = checked in a primary or review full text this session; **Medium** = consistent across secondary sources, primary not read; **UNVERIFIED** = do not print as fact, read the value from the user's data.

## Contents
1. Typical systems
2. Fabrication schematic templates
3. Characterization rendering rules
4. Peak / feature reference table
5. Honesty rules

---

## 1. Typical systems

- **Matrices:** chitosan, starch (thermoplastic starch, TPS), cellulose and derivatives (CMC, cellulose acetate), alginate, gelatin, pectin, PLA, PHA/PHB, PBAT (and PLA/PBAT blends), PCL, PVA (blend partner).
- **Fillers / reinforcements:** nanocellulose (CNC, CNF/NFC, MFC, bacterial cellulose), clays (MMT, halloysite), metal or oxide nanoparticles (ZnO, Ag, TiO₂), graphene oxide, natural fibres (flax, jute, hemp, date palm), lignin, biochar.
- **Additives:** plasticizers (glycerol, sorbitol, PEG), crosslinkers (glutaraldehyde, genipin, citric acid, tannic acid; Ca²⁺ for alginate), compatibilizers (e.g. maleic-anhydride-grafted PLA), active agents (essential oils, extracts).
- Nanocellulose dimension and modulus ranges are in `simulation-models.md` §3 (Moon et al. 2011, Chem. Soc. Rev. 40:3941, DOI 10.1039/C0CS00108B).
- Use a fixed visual legend in every figure of a project: matrix = one hue family, filler = a second, crosslinker or additive = a neutral with a distinct glyph. Keep it identical across panels.

---

## 2. Fabrication schematic templates

Draw each step as a labelled icon. Process conditions go **on the arrows**. If a condition is unknown, write a visible placeholder `[? °C]`. Never invent a value. Before finalising, list which placeholders are still open.

| Route | Steps (icons) | Conditions that belong on arrows | Commonly missing (ask the user) |
|---|---|---|---|
| **Solution casting** | dissolve matrix → add plasticizer → disperse filler → (crosslink) → cast → dry → peel / condition | solvent and concentration (% w/v), acid type and % for chitosan, stirring time / T / rpm, plasticizer % (relative to polymer), sonication (power, time, pulse, ice bath), degassing, cast volume per area, drying T / RH / time | **cast volume per area (sets thickness)**, sonication energy, drying RH, conditioning before testing (T, RH, days), final thickness ± SD |
| **Melt extrusion** | dry resin → premix / masterbatch → twin-screw → strand / pellet → (film blow or cast) | drying of resin (T, time), T profile per zone, screw speed (rpm), feed rate, die T, L/D | **resin moisture before processing**, residence time, number of passes, cooling method |
| **Hot pressing / compression moulding** | pellets or film stack → preheat → press → cool | T, pressure (MPa or tonnes **with platen area**), preheat time, press time, cooling rate | pressure units without area, cooling rate, spacer thickness |
| **Electrospinning** | solution → syringe / pump → needle → field → collector | polymer % and solvent, flow rate, voltage, tip-to-collector distance, needle gauge, collector type and speed, T / RH | **ambient RH and T**, collection time, post-treatment (crosslinking vapour, annealing) |
| **Freeze-drying (aerogels / scaffolds)** | suspension / gel → mould → freeze → lyophilize → (crosslink) | concentration, freezing T and rate (or freezing direction), primary drying pressure / T / time | **freezing rate or direction** (controls pore morphology), shelf T, final density / porosity |

Rules:
- Put the units on the arrow. Do not write "60 °C, 2 h" unless the user gave those numbers.
- Indicate chemistry (e.g. "Schiff base, proposed") as a side callout, not on the process arrow. Use the word "proposed" unless the user has proof (see §5).
- Show sample codes (e.g. CS-CNC3) exactly as in the user's manuscript.

---

## 3. Characterization rendering rules

General: plot only the user's data. Reference positions from §4 can be drawn as thin dashed guide lines, labelled with the band or plane and "ref." Do not snap peaks to reference values. Annotate the peak positions measured in the user's data.

- **FTIR:** x axis is wavenumber (cm⁻¹), reversed (4000 → 400 or the measured range). y is absorbance or transmittance, and say which. Stack spectra with offsets, state "offset for clarity", and do not show a y-tick scale for offset traces. Mark only bands relevant to the claim. Shifts of a few cm⁻¹ are within instrument resolution, so print the resolution if the user gives it. Do not call a shift "interaction" unless it exceeds the resolution and is reproducible.
- **XRD:** x axis is 2θ (°) with the **radiation stated** (e.g. Cu Kα, λ = 1.5406 Å). Peak positions in §4 are for Cu Kα only, so convert them for other sources via d-spacing. Stack with offsets. Only show a crystallinity index if it was computed from the user's data, and **always name the method** (Segal peak height, deconvolution, amorphous subtraction). Segal CrI values are not comparable with deconvolution values (Park et al. 2010).
- **TGA / DTG:** weight % vs T, DTG on a secondary axis or a separate panel. State the heating rate and atmosphere (N₂ or air) in the caption, since both shift the temperatures. Tabulate T_onset or T5%, T_max (DTG peak) and the residue at the final T. Use the user's numbers only.
- **DSC:** heat flow vs T with an **"exo up" or "exo down" arrow**. State the heating or cooling scan number and rate. Mark Tg (midpoint or onset, say which), Tc, Tcc and Tm from the user's analysis. Crystallinity Xc = ΔHm / (w·ΔH°m) needs ΔH°m with a citation provided by the user (value **UNVERIFIED** here).
- **SEM / TEM / AFM:** user-supplied images only, with a scale bar. Panel letters follow the figure-style rules. If no image is supplied, draw a grey placeholder box labelled "SEM image here". Never draw or generate a micrograph-like texture.
- **Tensile:** representative stress–strain curves (label them "representative", give the replicate count n) plus bar or dot plots of modulus, strength and elongation with mean ± SD and n. Name the test standard if the user gives it (e.g. ASTM D882 for thin sheeting; **confirm the edition**). Show the conditioning RH, because hydrophilic films are very RH-sensitive.
- **WVP:** bar chart with SD. Units must be explicit (e.g. g·m⁻¹·s⁻¹·Pa⁻¹, or g·mm/(m²·day·kPa)), with the RH gradient and T. Method: user-specified (gravimetric cup, e.g. ASTM E96/E96M; **confirm the edition**).
- **Contact angle:** bars ± SD, with droplet volume, time after deposition and liquid. Optionally add a user droplet photo (unaltered).
- **Swelling / water uptake:** (Ws − Wd)/Wd × 100 % vs time. State the medium, T and pH. Fitting curves come from `simulation-models.md` §1–2 and are labelled as fits.
- **Statistics:** significance letters or asterisks are supplied by the user, along with the test name. Never compute or imply significance that the user did not provide.

---

## 4. Peak / feature reference table

Use these only as labelled guide lines or as "expected near" notes. Assignments vary with DD (chitosan), polymorph, hydration, crystallinity and the instrument.

### 4.1 XRD (Cu Kα)

| Material | 2θ (°) | Assignment | Source | Confidence |
|---|---|---|---|---|
| Cellulose Iβ | ~14.9 | (1-10) | Computed from Iβ unit cell a = 7.784, b = 8.201, c = 10.380 Å, γ = 96.5° (Nishiyama et al. 2002, JACS 124:9074, cell values **UNVERIFIED in this pass**) → 14.86°; French 2014, Cellulose 21:885–896, DOI 10.1007/s10570-013-0030-4 (idealized patterns; full text not accessed) | Medium |
| Cellulose Iβ | ~16.5–16.7 | (110) | same; computed 16.66° | Medium |
| Cellulose Iβ | ~22.5–23.0 | (200) (= "002" in the older Segal indexing) | same; computed 22.98°. Measured maxima are often 22.5–22.7° because of peak overlap and crystallite size | Medium |
| Cellulose Iβ | ~34.5 | (004) | computed 34.54° | Medium |
| Cellulose, amorphous (Segal I_am) | ~18 (minimum between peaks) | Segal "amorphous" height | Segal et al. 1959, Text. Res. J. 29:786–794, DOI 10.1177/004051755902901003 (abstract: amorphous scatter at 2θ = 18°); Park et al. 2010, Biotechnol. Biofuels 3:10, DOI 10.1186/1754-6834-3-10 (full text read: the minimum is at ~18.3° but the true amorphous apex is at ~20.5–21.5°, so the Segal method overestimates CrI; use it only for relative comparison) | High |
| Chitosan, hydrated form | ~10 | (020) | Podgorbunskikh et al. 2022, Polymers 14:4438, DOI 10.3390/polym14204438 (full text read) | High (for that sample set) |
| Chitosan, hydrated form | ~19–20 | (200) | same; anhydrous form: (110) at 15–16°, (020) at 21–22°. Indexing differs between papers. Cast films are often a broad halo near 20° | Medium–High |
| PLA / PLLA, α form | ~16.6–16.8 | (200)/(110) | Secondary only (RSC SI for PDLA; a patent for PLLA crystallized at 140 °C). Primary not read | **UNVERIFIED — confirm** |
| PLA / PLLA, α form | ~18.9–19.4 | (203) | same | **UNVERIFIED — confirm** |
| PLA, quenched / amorphous | broad halo ~15–20 | amorphous | general | **UNVERIFIED** |
| Clay (MMT) d001 | depends on gallery spacing; compute 2θ = 2·asin(λ/2d) | intercalation is a shift to lower 2θ | Bragg's law; no fixed value given | n/a (derive from data) |

### 4.2 FTIR (chitosan / chitin)

Main source: Kumirska et al. 2010, Mar. Drugs 8:1567–1636, DOI 10.3390/md8051567 (review, full text read).

| Band (cm⁻¹) | Assignment | Notes | Confidence |
|---|---|---|---|
| ~3400–3450 (broad; e.g. 3429) | O–H stretch overlapping N–H stretch | position broadens or shifts with moisture and H-bonding | High |
| ~2920, ~2870 | C–H stretch | 2870–2880 is used as an internal reference band | High |
| ~1650–1660 (1655 typical; 1640 in some chitosan spectra) | amide I (C=O of the acetyl group) | **intensity falls as DD increases**; α-chitin splits into 1660/1630 | High |
| ~1590–1600 | N–H bending of free NH₂ | grows with deacetylation; some papers call it "amide II" in chitosan | High (the assignment wording varies) |
| ~1550–1560 | amide II (N–H bend + C–N stretch) | 1558 (α-chitin), 1562 (β-chitin); the 1560 band is used for DD determination | High |
| ~1375–1380, ~1315–1320 | CH₃ deformation; amide III | the amide III band is used as a reference band | High |
| ~1150–1160 | antisymmetric C–O–C bridge stretch | | High |
| ~1030–1075 | C–O stretch (C6–OH ~1035, C3–OH ~1070) | skeletal region, strongly overlapped | High |
| ~890–895 | C–H deformation of the β-glycosidic bond | 890 (β-chitin) and 895 (α-chitin) | High |
| 1641, 1545, 1149, 892 (dossier values) | amide I, N–H, C–O–C, saccharide | values from one chitosan–NCC film study (dossier §8.5). They fall within the ranges above; use them only if the user's own spectrum shows them | Medium |

Cellulose, starch, PLA (C=O ~1750), alginate (COO⁻ ~1600/1410) and gelatin (amide I/II) bands are **UNVERIFIED** in this pass. Label them from the user's own assignment and its citation.

### 4.3 Thermal (TGA)

| Material | Feature | Value | Source | Confidence |
|---|---|---|---|---|
| CNC (H₂SO₄) | onset of thermal degradation | ~260 °C (vs ~300 °C for the parent MCC); CNs overall 200–300 °C depending on heating rate, type and surface modification | Moon et al. 2011 (full text read), citing Petersson et al. | High |
| Chitosan | water-loss step | below ~150 °C | several film and powder studies (secondary search) | Medium |
| Chitosan | main decomposition | roughly 210–320 °C, DTG peak ~260–310 °C depending on film, MW, heating rate and atmosphere | secondary search, multiple studies, none read in full | **UNVERIFIED — use the user's data** |
| Cellulose (bulk) | main decomposition | ~300–375 °C (draft value) | not confirmed | **UNVERIFIED** |
| PLA | main single-step decomposition | ~300–400 °C (draft value) | not confirmed | **UNVERIFIED** |

The DSC values for Tg / Tm of PLA, PHB and starch are intentionally **not tabulated**. Read them from the user's thermograms.

---

## 5. Honesty rules

1. **Never fabricate data or images.** No synthetic micrographs, spectra, diffractograms or thermograms presented as measured. No made-up error bars, n or significance.
2. **Illustrative curves** (needed for a schematic or a model) carry a visible label: "Illustrative — not measured data" or "Model curve (see Methods)".
3. **Mechanism language:** use "proposed interaction", "suggested hydrogen bonding" or "consistent with" unless the user's evidence establishes the claim. Draw speculative bonds as dashed lines and include a legend entry.
4. **Reference positions are guides.** Never move, smooth or rescale user data to match them. Report differences as they are.
5. **Primary images are not altered** beyond uniform, whole-image adjustments the user approves. Crop and scale-bar edits must be disclosed (see `publishing-policy.md`).
6. **Units and significant figures** are kept exactly as in the source. Convert units only on request and note the conversion.
7. **Placeholders stay visible** (`[? °C]`, "SEM image here") until the user fills them. List them to the user at the end of each figure job.
8. **Values marked UNVERIFIED** in this file or in `simulation-models.md` must not appear in a figure as fact. Use the user's value with their citation, or show the warning.

### Removed or changed from the v0 draft
- "Cellulose I ~15, 22.5°" was replaced by the indexed table above (the 22.5° value kept as a measured-range note). "PLA ~16.5°" became 16.6–16.8° and is marked UNVERIFIED.
- The generic FTIR markers "C=O ~1650–1740" and "C–O–C ~1030–1150" were split into sourced chitosan bands. Non-chitosan bands were not tabulated.
- The draft's conditions example "60 °C, 2 h, 500 rpm" on arrows was removed and replaced by placeholders.
