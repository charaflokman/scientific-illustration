# Simulation model catalogue (biopolymer composites)

Use this file when building an interactive simulation (via `process-simulator` or by hand).
Every model below has a source, a validity range and an honesty label. Rules:

- Show the honesty label on the page, next to the plot title (e.g. "Textbook analytic solution", "Trend model").
- Parameter defaults are placeholders. Show them as "ASSUMED" until the user supplies their own values or data.
- If the user gives experimental points, plot them over the model and fit the free parameters. Report the fitted values with the fit range.
- Anything marked **UNVERIFIED** must not be hard-coded as fact. Put it behind a user input or show the warning text in the UI.
- Verification date of this file: 2026-10-29.

## Contents
1. Fickian water uptake, D extraction, n-exponent diagnosis, Case II / anomalous
2. Swelling and crosslink density (Flory–Rehner)
3. Modulus vs filler loading (Halpin–Tsai, random orientation, percolation, agglomeration penalty)
4. Hydrolytic degradation (PLA Mn decay; empirical mass loss)
5. Crosslinking kinetics (nth-order + Arrhenius, gel point)
6. Controlled release (Higuchi, Korsmeyer–Peppas)
7. Film casting / drying (qualitative)
8. Extrusion melt viscosity (power law / Cross + Arrhenius shift)
9. Filler dispersion / agglomeration (agent-based, illustrative only)
10. Source list

---

## 1. Fickian water uptake in a film

**Label:** "Textbook analytic solution (Fickian, constant D, plane sheet)".

**Equations** (sheet of full thickness L, exposed on both faces, constant D, constant surface concentration, no swelling):

```
Mt/M∞ = 1 − Σ_{n=0..∞} 8/((2n+1)² π²) · exp(−D (2n+1)² π² t / L²)        (full series)
Mt/M∞ ≈ (4/L) · sqrt(D t / π)                                            (short-time form)
D     = π · s² / 16,   s = slope of Mt/M∞ vs sqrt(t)/L in the linear region
t½    = 0.04918 · L² / D                                                 (time to Mt/M∞ = 0.5)
```

- Source: Crank, *The Mathematics of Diffusion*, 2nd ed., Oxford University Press, 1975 (ch. 4, plane sheet). Also Crank & Park (eds.), *Diffusion in Polymers*, Academic Press, 1968. Application note with the same D = π·s²/16 extraction: Surface Measurement Systems, App Note 16, https://surfacemeasurementsystems.com/wp-content/uploads/2022/07/App16-Diffusion-Thin-Films.pdf
- **Thickness convention:** Crank sets up the sheet as −l < x < l, so the full thickness is 2l. The exponent then reads −D(2n+1)²π²t/(4l²). The forms above use full thickness L = 2l. Check this in any code: with half-thickness l, the half-time constant is 0.1967 (= 4 × 0.04918). Crank's notation for l changes between sections, so always check that the D you extract matches the convention you used. (Note: the exact section numbering in Crank was not re-checked in this pass.)
- **Constant checked numerically (2026-10-29):** solving the 200-term series for Mt/M∞ = 0.5 gives D·t/L² = 0.049183. This matches the 0.04919 commonly quoted from Crank. Other points for test cases: Mt/M∞ = 0.4 at D·t/L² = 0.03142; 0.6 at 0.07160; 0.9 at 0.2120.
- **Validity of the short-time form:** it is accurate to within 1% up to Mt/M∞ ≈ 0.6 (numerical check: at the true 0.6 point it gives 0.6039). Fit D only on the initial linear part, typically Mt/M∞ < 0.4–0.6.
- **Physical validity:** constant D (no concentration dependence), no dimensional change, and edge effects negligible (film width ≫ L). Hydrophilic biopolymer films (chitosan, starch, gelatin, alginate) often swell a lot and have concentration-dependent D, so any D you extract is an *apparent* D. Say so in the readout.

**Worked example (all values ASSUMED, use it to sanity-check the code):**

| Input | Value |
|---|---|
| L (full thickness) | 50 µm = 5.0e-5 m (ASSUMED) |
| D | 1.0e-12 m²/s (ASSUMED) |
| L²/D | 2500 s |
| t for Mt/M∞ = 0.5 | 0.04918 × 2500 = **123 s** |
| t for Mt/M∞ = 0.9 | 0.2120 × 2500 = **530 s** |
| Short-time slope s = 4·sqrt(D/π) | 2.257e-6 m·s^-1/2; back-calculated D = π s²/16 = 1.0e-12 m²/s |

A correct implementation must reproduce these numbers to 3 significant figures. Truncating the series below about 5 terms at small t gives visible error, so use ≥ 50 terms or switch to the short-time form when Mt/M∞ < 0.2.

**Power-law (n-exponent) diagnosis:**

```
Mt/M∞ = k · t^n        (fit ln(Mt/M∞) vs ln t, only for Mt/M∞ ≤ 0.6)
```

- Source: Ritger & Peppas 1987, J. Control. Release 5:23–36, DOI 10.1016/0168-3659(87)90034-4 (non-swellable) and 5:37–42, DOI 10.1016/0168-3659(87)90035-6 (swellable). It was written for release, but the same classification is applied to sorption.
- Thin film or slab: n = 0.5 Fickian; 0.5 < n < 1 anomalous; n = 1 Case II. Cylinder 0.45 / 0.89 and sphere 0.43 / 0.85. These cut-offs come from secondary summaries of Ritger & Peppas and are **UNVERIFIED** (confirm in the paper's table before printing them in a figure). Use the slab values for films.
- The classes Case I (Fickian), Case II and anomalous come from Alfrey, Gurnee & Lloyd 1966, J. Polym. Sci. C 12:249–261, DOI 10.1002/polc.5070120119. Only the bibliographic record was checked, not the content.

**Case II (idealized) and anomalous options:**

- Case II, sharp front moving at constant speed v from both faces: Mt/M∞ = 2·v·t/L for t ≤ L/(2v). This follows from the geometry alone. Label it "idealized Case II". For a physical theory see Thomas & Windle 1982, Polymer 23:529–542, DOI 10.1016/0032-3861(82)90093-3 (record checked, equations not transcribed).
- Diffusion + relaxation (two-stage) toggle: Mt = M∞,F·[Fickian series] + M∞,R·(1 − exp(−k_R t)). Source: Berens & Hopfenberg 1978, Polymer 19:489–496, DOI 10.1016/0032-3861(78)90269-0 (record checked; confirm the exact form in the paper). Label it "empirical two-stage fit".
- Release-side equivalent: Peppas & Sahlin 1989, Int. J. Pharm. 57:169–172, DOI 10.1016/0378-5173(89)90306-2.
- The Peleg model fits sorption kinetics or isotherms empirically. It does **not** give D. Offer it only as a curve fit.

**UI mapping:**

| Control | Model term |
|---|---|
| Thickness slider (10–500 µm) | L |
| log D slider (1e-14 to 1e-10 m²/s, ASSUMED range; user value overrides) | D |
| Mechanism toggle: Fickian / Case II / two-stage | which equation is used |
| Readouts | t½, t(0.9), fitted n with its class, apparent D from the slope |
| Data upload | (t, Mt) or (t, mass); compute Mt/M∞ from the user's M∞ or the plateau |

**Data the user should supply:** film thickness (measured, with SD), mass vs time at a stated RH or in liquid water at a stated T, dry mass, and the equilibrium uptake. If the film swells, also give thickness after swelling.

---

## 2. Swelling and crosslink density (Flory–Rehner)

**Label:** "Equilibrium swelling theory (Flory–Rehner); χ is user-supplied".

```
−[ ln(1 − φ) + φ + χ φ² ] = (ρ V1 / Mc) · (1 − 2 Mc/Mn) · (φ^(1/3) − φ/2)
Q (volumetric swelling ratio) = 1/φ ;  crosslink density ν = ρ / Mc
```

- φ = polymer volume fraction in the swollen gel, V1 = molar volume of the solvent (water 18.0 cm³/mol), ρ = dry polymer density, Mn = primary chain Mn. Solve numerically for Mc (bisection on Mc).
- Sources: Flory & Rehner 1943, J. Chem. Phys. 11:521–526, DOI 10.1063/1.1723792. Flory, *Principles of Polymer Chemistry*, Cornell University Press, 1953. The form above, with the (1 − 2Mc/Mn) chain-end correction and the (φ^(1/3) − φ/2) term, was transcribed from secondary teaching sources (S. Abbott, Practical Solubility, https://www.stevenabbott.co.uk/practical-solubility/polymer-swelling.php ; G. Beaucage, Univ. Cincinnati course notes). Confirm the front factor in the primary source. Networks formed in solution need the Peppas–Merrill modification (Peppas & Merrill 1976, J. Polym. Sci. Polym. Chem. Ed. 14:441–457, DOI 10.1002/pol.1976.170140215). The DOI was verified; the equation was not transcribed here.
- **Chitosan–water χ:** Gámiz-González et al. 2015, Carbohydr. Polym. 133:110–116, DOI 10.1016/j.carbpol.2015.07.020 (author manuscript: https://riunet.upv.es/handle/10251/66730) report an *apparent* Flory–Huggins χ for chitosan films from water-vapour isotherms at 25 °C. It **increases with water activity** over 0.3 < aw < 1 and reaches **about 0.7 at the highest RH**. It is practically independent of degree of deacetylation (DD 50–85 %). The value at lower aw was only shown in a figure and is not transcribed here. So:
  - χ must be a **required user input** (no silent default). The UI may suggest "≈0.7 (high-aw value for chitosan films, Gámiz-González 2015)" with that citation shown.
  - The same paper reports liquid-water uptake of 250–600 % versus about 45 % (dry basis) from vapour at aw = 0.95. In chitosan the physical crosslinks are crystallites and entanglements, so Mc from Flory–Rehner is an *effective* value.
- Validity: equilibrium swelling, affine network, a single constant χ (an approximation here, since χ varies with φ for chitosan), and no ionization. Polyelectrolyte gels (alginate–Ca²⁺, protonated chitosan) need ionic terms that are not included. Say so in the UI if pH < ~6.5 for chitosan (**UNVERIFIED** threshold; it is near the commonly cited pKa ~6.3–6.5, confirm).

**UI:** sliders for crosslinker amount (mapped to Mc only if the user provides a calibration; otherwise Mc is the slider), χ (required), ρ, Mn. Readouts: Q, ν, mesh-size trend. **Data needed:** dry and swollen masses, densities of polymer and solvent, temperature, pH, and gel fraction.

---

## 3. Modulus vs filler loading

**Label:** "Semi-empirical micromechanics (Halpin–Tsai) + percolation option; trend model".

**Halpin–Tsai:**
```
E/Em = (1 + ξ η φ) / (1 − η φ),   η = (Ef/Em − 1) / (Ef/Em + ξ)
ξ = 2(l/d) for longitudinal modulus E_L;  ξ = 2 for transverse modulus E_T
Random in-plane (2D):  E ≈ (3/8) E_L + (5/8) E_T
```
- Sources: Halpin & Kardos 1976, Polym. Eng. Sci. 16:344–352, DOI 10.1002/pen.760160512 (verified). Moon et al. 2011, Chem. Soc. Rev. 40:3941–3994, DOI 10.1039/C0CS00108B (verified, full text read). Moon et al. note that ξ = 2k (k = aspect ratio) is "a common suggestion" but is not based on rigorous elasticity and does not agree well with shear-lag or numerical models. As ξ goes to infinity and to 0, Halpin–Tsai tends to the Voigt and Reuss bounds. For rubbery matrices, Halpin–Kardos predictions lie close to the lower bound, so experiments exceeding them are expected, not unusual.
- The 3/8–5/8 random in-plane average is attributed to Tsai & Pagano (1968). It is widely reproduced in composite textbooks. **UNVERIFIED — confirm in source** (the primary reference was not located in this pass). Label it "approximate orientation average".
- **CNC / CNF parameters (Moon et al. 2011):**

| Parameter | Value | Notes |
|---|---|---|
| CNC dimensions | 3–5 nm wide, 50–500 nm long | wood/plant CNC; crystallinity 54–88 % |
| Tunicate CNC | larger; Moon's models use k = 85, r = 5 nm | idealized particles |
| NFC | 4–20 nm wide, 500–2000 nm long | |
| MFC | 10–100 nm wide, 0.5 to tens of µm long | |
| Axial modulus E_A | XRD on fibres 120–138 GPa; IXS 220 ± 50 GPa; AFM t-CNC 151 ± 29 and 145 ± 31 GPa; Raman t-CNC 143 GPa; CNC in epoxy 57 or 105 GPa (2D or 3D assumption) | wide scatter; use 100–150 GPa as a slider range, with the citation shown |
| Transverse modulus E_T | wood CNC 18–50 GPa; t-CNC 9 ± 3 GPa | AFM indentation |
| Model matrices in Moon | glassy Em = 2.5 GPa; rubbery Em = 0.1 GPa | illustrative only |

- **Percolation option (Ouali / Takayanagi series–parallel, as used for cellulose whiskers by Favier et al.):**
```
E = [(1 − 2ψ + ψ φ) Em Ef + (1 − φ) ψ Ef²] / [(1 − φ) Ef + (φ − ψ) Em]
ψ = φ · ((φ − φc)/(1 − φc))^b  for φ ≥ φc,  ψ = 0 below;  φc ≈ 0.7/(l/d),  b = 0.4
```
  Sources: Favier et al. 1995, Macromolecules 28:6365–6367, DOI 10.1021/ma00122a053. Favier et al. 1997, Polym. Eng. Sci. 37:1732–1739, DOI 10.1002/pen.11821. Ouali, Cavaillé & Pérez 1991 (Plast. Rubber Compos. Process. Appl.). Capadona et al. 2008, Science 319:1370–1374, DOI 10.1126/science.1153307. The DOIs were verified. **The equation, the exponent b = 0.4 and φc = 0.7/(l/d) are UNVERIFIED — confirm in Favier 1997 before release.** Here Ef stands for the modulus of the percolated filler network, which is not the single-crystal E_A. Moon et al. 2011 stress that percolation cannot exceed the upper bound. The effect is strongest in rubbery matrices (high Ef/Em) and is weak in glassy ones (Ef/Em of about 60).
- **Agglomeration penalty (HEURISTIC, not from any model):** above a user-set threshold φ*, let the effective aspect ratio decay, for example l/d_eff = (l/d)·exp(−β(φ − φ*)). Display: "Heuristic penalty for agglomeration; not a physical model. Calibrate φ* and β to your data." The qualitative behaviour is documented: predictions overshoot when CNC agglomerates (USDA FS Treesearch 44265, https://www.fs.usda.gov/treesearch/pubs/44265). Moon et al. also treat imperfect interfaces with an interface stiffness Ds. Offer that as an "interface quality" slider only if it is implemented from Moon's equations.

**UI:** φ (vol fraction; convert from wt% using the densities the user gives), l/d, Ef, Em, orientation (aligned / random 2D / percolation), φ* and β (heuristic). Readouts: E/Em, predicted optimum (only in heuristic mode, flagged). **Data needed:** matrix modulus at the same RH and T, filler density, aspect ratio from TEM/AFM with its distribution, and measured moduli vs loading.

---

## 4. Hydrolytic degradation

**Label (PLA Mn):** "Kinetic model (non-catalytic vs autocatalytic); fit to your GPC data".

```
Non-catalytic (2nd order in bonds × water):  1/Mn = 1/Mn0 + (k2·Cs/M0) · t
Autocatalytic (acid chain ends catalyse):     ln Mn = ln Mn0 − k' · t
```
- Source: Lyu & Untereker 2009, Int. J. Mol. Sci. 10:4033–4065, DOI 10.3390/ijms10094033 (open access, full text read). Its eq. 3 is the 1/Mn form and eq. 4 is log Mn = log Mn0 − k3·C_B·C_S·t. The paper says that fitting data to both equations tells you which mechanism dominates. The autocatalytic linear ln Mn form is commonly traced to Pitt and co-workers (e.g. Pitt & Gu 1987, J. Control. Release 4:283–292, DOI 10.1016/0168-3659(87)90020-4; record verified, content not read).
- Rate-constant scale: Tan & Dorgan 2025, Macromolecules 58:2046–2052, DOI 10.1021/acs.macromol.4c02241 (PMC11866919, full text read). Reported apparent PLA hydrolysis rate constants at 37 °C span **2.5e-5 to 4.0e-3 h⁻¹**. They differ by orders of magnitude partly because apparent rates depend on stoichiometry and diffusion. An Arrhenius analysis of literature data from 37–250 °C gives **Ea = 16.7 ± 1.6 kcal/mol**. Their own fibres give **14 ± 1.4 kcal/mol**. Other literature values cited there are 11.8 kcal/mol (170–250 °C), 16.6 (120–160 °C) and 20.8 (100–130 °C, flagged by them as an outlier). Use these as the slider range for Ea and require the user's k at one temperature. The draft values "prefactor 1.12 h⁻¹" and "up to 71 h⁻¹" could not be confirmed in that paper and were **removed**.
- Validity: bulk-erosion regime (water diffusion faster than hydrolysis), amorphous or fixed crystallinity, and constant pH. It is not valid after mass loss begins (oligomer leaching), and not for thick parts where autocatalysis makes the core degrade faster than the surface. Lyu & Untereker discuss erosion-number criteria.

**Mass loss in soil burial or compost:** m(t)/m0 = exp(−k t). **Label: "Empirical first-order fit only. Not a mechanism; k is site-, soil-, moisture- and temperature-specific."** Never extrapolate beyond the measured time window, and never present a half-life as a material property.

**UI:** T, k_ref at T_ref (user value), Ea (slider 11–21 kcal/mol, cited), mechanism toggle. Readouts: Mn(t), time to Mn/Mn0 = 0.5, and the 1/Mn and ln Mn linearity plots of the user's data side by side. **Data needed:** Mn (GPC) vs time, T, medium and pH, sample thickness, crystallinity.

---

## 5. Crosslinking kinetics

**Label:** "Generic phenomenological kinetics; parameters must be fitted (no biopolymer defaults)".

```
dα/dt = k(T) · (1 − α)^n ,          k(T) = A · exp(−Ea / (R T))
autocatalytic option: dα/dt = (k1 + k2 α^m)(1 − α)^n   (Kamal & Sourour 1973)
gel point (ideal, Flory–Stockmayer), A2 + Bf stoichiometric: α_c = 1/sqrt(f − 1)
```
- nth-order + Arrhenius is a generic form with no single source. The autocatalytic form comes from Kamal & Sourour 1973, Polym. Eng. Sci. 13:59–64, DOI 10.1002/pen.760130110 (record verified). It was written for thermoset epoxy cure; applying it to genipin, glutaraldehyde or citric-acid crosslinking of biopolymers is an extrapolation. The gel-point criterion is from Flory 1953, *Principles of Polymer Chemistry* (not re-read in this pass, **confirm the expression for the stoichiometry used**). It assumes ideal, equal reactivity and no intramolecular loops, so real gels form later than predicted.
- The draft called this "second-order kinetics" and "Flory–Stauffer". Both were corrected: the form is nth-order, and the theory is Flory–Stockmayer (Stauffer is percolation theory).
- Ionic crosslinking (alginate–Ca²⁺) and physical gelation (gelatin cooling) are **not** described by this. If needed, give them a separate qualitative diagram.
- **UI:** T, n, Ea, A (all user-fitted), crosslinker functionality f. Readouts: α(t), t_gel. **Data needed:** degree of crosslinking vs time (ninhydrin assay, FTIR band ratio, DSC, rheology G′/G″ crossover).

---

## 6. Controlled release (active packaging, drug-loaded films)

**Label:** "Classical release models (Higuchi; Korsmeyer–Peppas power law)".

```
Higuchi (planar matrix, A ≫ Cs):  Q = sqrt( D (2A − Cs) Cs t ) ≈ sqrt(2 A D Cs t);  simplified Q = k_H sqrt(t)
Korsmeyer–Peppas:                 Mt/M∞ = k t^n   (first ~60 % of release only)
```
- Sources: Higuchi 1961, J. Pharm. Sci. 50:874–875, DOI 10.1002/jps.2600501018. Higuchi 1963, J. Pharm. Sci. 52:1145–1149, DOI 10.1002/jps.2600521210. Korsmeyer et al. 1983, Int. J. Pharm. 15:25–35, DOI 10.1016/0378-5173(83)90064-9. Ritger & Peppas 1987 (§1). DOIs verified. The Higuchi expression above is the standard textbook transcription; confirm it against the 1961 paper if it is printed in a figure.
- Validity (Higuchi): initial load A much greater than solubility Cs, perfect sink, non-swelling and non-eroding matrix, one-dimensional, constant D. Swelling chitosan or alginate films violate the non-swelling assumption, so offer Korsmeyer–Peppas and report n with the slab cut-offs from §1.
- **UI:** A, Cs, D (Higuchi); k, n (KP); thickness. Readouts: Mt/M∞(t), t50, mechanism class. **Data needed:** cumulative release vs time, loading, film thickness, and medium (simulant, T).

---

## 7. Film casting / drying

**Label:** "Qualitative schematic with a simple evaporation estimate; not predictive".

- Constant-rate period estimate: m_solvent(t) = m0 − J·A·t, with J (evaporation flux) as a **user-measured** value (mass vs time on a balance). The drying time to the end of the constant-rate period is about (m0 − m_crit)/(J·A). The falling-rate period (diffusion-limited, where skin formation happens) can be shown as a qualitative slow-down only. No source is attached and no defaults are given: J depends on T, RH, airflow and the solution.
- Draw thickness shrinkage as h(t) ≈ h_wet·(volume fraction of solids at time t)⁻¹ trend. Mark skin formation and defects (bubbles, cracks, uneven edges) as **qualitative risk indicators** tied to sliders (higher T means faster evaporation and a higher skin risk). Mark these as "illustrative".
- **Data needed:** solution concentration, cast volume and area, T, RH, final dry thickness, and mass-vs-time if available.

---

## 8. Extrusion melt viscosity

**Label:** "Generic rheology models; fit to capillary/rotational data for the actual grade".

```
Power law:  η = K · γ̇^(n−1)
Cross:      η = η0 / (1 + (λ γ̇)^(1−n))
T shift:    η0(T) = η0(Tref) · exp( (Ea/R) (1/T − 1/Tref) )
```
- Source for Cross: Cross 1965, J. Colloid Sci. 20:417–437, DOI 10.1016/0095-8522(65)90022-X (verified). The power law and the Arrhenius shift are standard, with no single source. Apply the Arrhenius form only well above Tg (for PLA well above Tg it is acceptable; near Tg use WLF).
- **No default K, n, η0 or Ea for PLA, PHA, PBAT or TPS are given.** They are grade-, moisture- and filler-dependent. Require user data or show the plot with "ASSUMED parameters — illustrative". Thermal and hydrolytic degradation flags (e.g. PLA moisture before processing, PHB's narrow processing window) are qualitative and must be **UNVERIFIED — confirm with the resin datasheet**.
- **UI:** T, screw rpm mapped to an apparent shear rate (the user gives the geometry factor), filler wt% (with an optional Krieger–Dougherty-type increase only if the user supplies φ_max; otherwise omit). Readouts: η, a torque trend.

---

## 9. Filler dispersion / agglomeration

**Label:** "Agent-based illustration — not a physical simulation; no quantitative output".

- 2D particles with a short-range attraction (surface-compatibility slider) and a shear-driven breakup probability (mixing-intensity slider). Readouts are *visual* only: cluster count and mean cluster size in particle units. No units of length or time, and no "percolation threshold" number. If a percolation flag is shown, compute it from the spanning-cluster rule in the simulation box and label it "simulation-box connectivity", not a material property.
- Purpose: teaching how sonication, compatibilizers and loading affect dispersion qualitatively. Link to §3 only through the heuristic penalty, and say so.

---

## 10. Sources (status as of 2026-10-29)

Verified bibliographic records (Crossref) and, where noted, full text read:
- Crank 1975 (book, not re-read; constant checked numerically). Crank & Park 1968 (book).
- Ritger & Peppas 1987 (I, II); Peppas & Sahlin 1989; Korsmeyer et al. 1983; Higuchi 1961, 1963.
- Alfrey, Gurnee & Lloyd 1966; Berens & Hopfenberg 1978; Thomas & Windle 1982.
- Flory & Rehner 1943; Peppas & Merrill 1976; Gámiz-González et al. 2015 (**full text read**).
- Halpin & Kardos 1976; Moon et al. 2011 (**full text read**); Favier et al. 1995, 1997; Capadona et al. 2008.
- Lyu & Untereker 2009 (**full text read**); Tan & Dorgan 2025 (**full text read**); Pitt & Gu 1987.
- Kamal & Sourour 1973; Cross 1965.

Still UNVERIFIED (behind a warning or a user input): the Ritger–Peppas cylinder/sphere cut-offs, the Tsai–Pagano 3/8–5/8 average, the exact percolation-model equation and constants, the Flory–Stockmayer expression for the user's stoichiometry, the chitosan pKa threshold, and all extrusion defaults.
