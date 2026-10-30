# Open-source landscape (analysed 2026-10-29)

Why this file exists: it records what was borrowed from which project and why the skill is built the way it is.
Load it only when the user asks about alternatives or tool choices.

Method: repositories were shallow-cloned into an isolated scratch folder, licence files read, key source files
inspected; only dependency-free code was executed (see "Ran"). Star counts come from the GitHub API at the time.

| Project | Licence (file checked) | What it does | Ran? | Taken into this skill |
|---|---|---|---|---|
| dwzhu-pku/PaperBanana (Google Research, arXiv 2601.23265) | Apache-2.0 | 5-agent loop: Retriever → Planner → Stylist → Visualizer (image model) → Critic; NeurIPS style guides | No (needs Gemini/OpenAI keys) | The plan → style → render → critique workflow; the critic's checks (fidelity to the methods text, text QA, validity of examples, caption not inside the image). Replaced the image model with deterministic SVG so output is editable and journal-safe. Its style guide is CS-centric ("NeurIPS look"); not reused. |
| llmsresearch/paperbanana | MIT | Unofficial CLI, MCP server, Claude Code skills, plot-batch | No (keys) | Packaging ideas (commands for generate / plot / evaluate). |
| PlutoLei/paperbanana-skill | MIT | Skill wrapper; editable PPTX built locally | No | Decision-tree routing table at the top of SKILL.md. |
| Ahmedn1/scientific-figure-svg | MIT | LLM writes a JSON plan; deterministic Python renderers draw grids, Petri nets, trees, circuits | **Yes** — `pipeline/det_render.py` (imports only `math`, `html`) rendered a 5-step plan as petri/network/grid SVGs; flowchart type returns None by design | Core principle: the model plans semantics, code owns geometry. `render_figure.py` follows it with a richer, mm-based spec and editability. |
| ResearAI/AutoFigure, AutoFigure-Edit | MIT | Text-to-image draft → SAM3 segmentation → background removal → SVG template with icons | No (GPU models) | Confirms demand for editable SVG; we avoid raster-to-vector because it can distort content. |
| khatvangi/chitra-katha | MIT | Local Napkin alternative: Ollama LLM → Mermaid, 12 diagram types | No (needs Ollama running) | Diagram mode pattern: text → Mermaid → local render, user edits text. |
| felizvida/helixcanvas | Apache-2.0 | Local biomedical figure editor over Bioicons/Servier with provenance tracking | No | Per-icon licence + attribution tracking (`bioicons.py` license.json, automatic credits line). |
| wpang4032-oss/scientific-paper-figures | **no licence file** | Skill: read paper → choose figures from meaning, not field stereotypes → inspect published figures → integrity review | No | Ideas only (no text copied): choose the figure from the scientific relationship, check coverage of the main contribution. |
| duerrsimon/bioicons | MIT (site); icons per-folder: cc-0 486, cc-by-3.0 1375, cc-by-4.0 873, cc-by-sa 37, mit 39, bsd 3 (2,813 SVG) | Icon library | Used via `bioicons.py` (index from GitHub tree; downloads stripped of scripts) | Icon source with licence parsed from the path. |
| garrettj403/SciencePlots | MIT | matplotlib journal styles | Installed | Optional style in `plot_data.py`. |
| mermaid-js/mermaid-cli 11.x | MIT | Mermaid → SVG/PNG | **Yes** (with system Chrome; puppeteer's browser download was blocked by npm's install-script policy) | Diagram renderer. |
| terrastruct/d2 v0.9.0 | MPL-2.0 | D2 → SVG | **Yes** | Diagram renderer for polished layouts. |
| RDKit 2026.09 | BSD-3 | Molecule drawing | **Yes** (pip, isolated venv) | `molecule` element. |

Gaps no open project fills (and this skill targets): chemistry/biopolymer-specific schematic templates,
characterization panels with honest peak handling, interactive simulations of composite processes with sourced
models, and a round-trip editor that preserves manual edits across re-renders.

Security notes for users: run third-party repos in an isolated folder/venv; never paste API keys into figures or
specs; this skill's scripts do not send figure content anywhere (only `bioicons.py` contacts GitHub, to list and
download icons).
