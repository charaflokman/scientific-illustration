# Publisher AI-image policy: summary and decision rule

**Checked 2026-10-29.** These policies change often; two of the three below were revised in 2026. **Always tell the user to check the target journal's own author guidelines before submission.** A journal's rules can be stricter than its publisher's.

## 1. Per-publisher summary

### Springer Nature (incl. Nature Portfolio)
Source (read 2026-10-29): Springer Nature, "AI use in manuscript preparation", https://www.springernature.com/gp/policies/editorial-policies/ai-manuscript-preparation (linked from https://www.nature.com/nature-portfolio/editorial-policies/ai, which sets out a green / amber / red risk framework).
- The policy covers "visual content": figures, graphs, charts, maps, diagrams, illustrations, photographs, images and video.
- **Permitted with disclosure** when the visual comes from verifiable inputs. Their examples include charts from datasets, diagrams from author-developed content, and figures generated with code that the author has reviewed and verified. Conditions: disclose the model and purpose; the underlying data can be inspected and is attributed; there is human review; the output accurately represents the evidence; copyright is respected.
- **Not permitted:** AI-generated visuals that are not derived from independently verifiable data, sources, methods, computational outputs or author content ("opaque"). The red tier also lists photorealistic images (deepfakes) and producing data or figures as if they were empirical.
- Non-generative ML enhancement of existing images may be permitted if it does not misrepresent the original, and it must be disclosed.
- **Where to disclose:** in the caption or legend of the visual, and in an AI Declaration in the manuscript.
- Note: this **supersedes** the older summary "no generative AI images unless labelled" recorded in the dossier.

### Elsevier
Source (read 2026-10-29): https://www.elsevier.com/en-au/about/policies-and-standards/generative-ai-policies-for-journals (page states "Policy updated June 2026").
- **Prohibited:** using AI to create or alter images that represent primary observed or experimental data, and using AI to fabricate, invent or alter data. **General-purpose generative AI image tools must not be used for graphical abstracts.**
- **Allowed:** AI support for explanatory images (flow charts, schematics, workflow diagrams, timelines), with disclosure in **each image's caption** plus the general AI declaration. Data visualizations are allowed only if directly derived from the underlying data by reproducible, reported methods; disclose the tool and version in Methods. AI as part of the research methods must be described in Methods.
- Cover art needs prior permission from the editor and publisher.

### ACS Publications
Source (read 2026-10-29): "Artificial Intelligence (AI) Best Practices and Policies at ACS Publications", https://researcher-resources.acs.org/publish/aipolicy (last updated 13 Dec 2024). This is ACS's own page; earlier rounds relied on secondary sources.
- AI use for text or image generation must be disclosed (Acknowledgments, per the journal guidelines). Substantial use is described in Methods.
- For graphics, a brief description of AI use goes **in the figure caption**.
- **AI-generated images must not be used in Table of Contents (TOC) graphics.**
- AI cover art is permitted with disclosure in the cover-art caption, and the tool's terms must allow commercial use.
- Secondary sources (Enago, BioRender policycheck, journal-specific blogs) describe stricter per-journal readings for primary data images. Treat every primary-data image as off-limits.

### Others (not re-checked this pass; secondary only)
Cell Press and Taylor & Francis reportedly allow explanatory schematics and diagrams with disclosure and forbid altering research images (dossier §4). Survey: arXiv 2603.16159 (2026). **UNVERIFIED — check the journal.**

## 2. Decision rule for this skill

1. **Charts drawn by code from the user's own data:** OK. Keep the data and code, and offer the methods-level disclosure (sentence B).
2. **Schematics / fabrication diagrams drawn as vector code from the user's description:** OK with a caption disclosure (sentence C) under Springer Nature, Elsevier and ACS. Exception: **ACS TOC graphics and Elsevier graphical abstracts.** Warn the user, offer a plain hand-editable SVG they finish themselves, and tell them to check the journal before using it there.
3. **Primary images (SEM, TEM, optical, photographs, gels):** never generate, never alter. Only add overlays the user requests (scale bars, panel letters, arrows) on unaltered pixels, and disclose them.
4. **Never** produce photorealistic or micrograph-like raster imagery, and never generate data.
5. **Simulations / model curves in a paper:** label them as model output and describe the model in Methods (sentence B).
6. If the target journal is unknown, default to the strictest reading (Elsevier and ACS above) and say so.

## 3. Ready disclosure sentences (the user edits the brackets)

- **A. Caption level:** "This figure was drawn programmatically from the authors' data using [tool/library, version]. An AI assistant ([name, model]) helped write the plotting code, which the authors reviewed and verified. No data values were generated or altered."
- **B. Methods level:** "Figures [x–y] and the model curves in Figure [z] were produced with [Python/JavaScript] code ([libraries, versions]) written with assistance from an AI assistant ([name, model]). All plotted values come from the measured data described in Section [n]. Model equations and parameters are given in [Section/Table]. The authors checked the code and outputs and take full responsibility for them. Code is available at [repository/SI]."
- **C. Schematic:** "Schematic illustration drawn as vector graphics with code-generation assistance from an AI assistant ([name, model]), based on the authors' description of the procedure. It is conceptual and not to scale; no experimental images were used or modified."
