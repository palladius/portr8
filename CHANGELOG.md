# 📝 CHANGELOG — portr8

All notable changes to this project will be documented in this file.
Format: [Gitmoji](https://gitmoji.dev/) + [Keep a Changelog](https://keepachangelog.com/).

## [0.7.0] — 2026-08-27

### 🚫 No-Edit Mode & Centralized Constants

- 🚫 **`--no-edit` flag**: Forces ALWAYS REGENERATE mode — never passes previous image to the generator. Judge feedback is still incorporated into the augmented prompt, but each iteration produces a truly independent face. Fixes the "90% edit = same face" problem where edit mode just tweaked colors/lighting without changing facial identity.
- 📦 **`lib/constants.py`**: New centralized constants module with all model lists, calibration config, and sigmoid remap parameters. No more hardcoded model names scattered across scripts.
- 🧹 **Dead model cleanup**: Removed 2.X models from judge/calibration lists (dead for text, still alive for image generation). Added `gemini-3.6-flash` per user request.
- 🔗 **Judge imports refactored**: `DEFAULT_JUDGE_MODEL` now imported from `lib/constants.py` instead of hardcoded in `lib/judge.py`.
- 🔬 **Calibration scripts updated**: `bin/calibration/*.py` now import `CALIBRATION_MODELS` from constants — single source of truth.

## [0.6.2] — 2026-08-27

### 🎯 Forensic Multi-Character Reference Mapping & Clean Crop Refinements

- 🎯 **Explicit Reference Photo Mapping**: `lib/judge.py` now informs the LLM judge of the exact reference image slice assigned to each character (`Images 2-5: Kate`, `Images 6-9: Riccardo`), eliminating cross-contamination during multi-character judging.
- 🔬 **Anti-Beautification & Profile Guardrails**: Judge prompt strictly penalizes generic AI facial beauty (capped at 5.0) and caps unverified profile angles at 6.0–6.5 to stop false-positive premature convergence.
- ✂️ **Surgical Crop Purge in `kate2016`**: Re-cropped `KR-e-0135` and `KR-e-0133` using Gemini-verified bounding boxes to completely eliminate Riccardo from Kate's reference crops; quarantined corrupted crop `KR-e-0136`.
- 📖 **Authoritative Character Profile**: Added `data/characters/kate2016/character.yaml` specifying ground truth 2016 wedding biometrics, hair, and anti-smoothing directives.

## [0.6.1] — 2026-08-26

### 🔄 Enhanced Feedback Loop Transmission & YAML Character Ingestion

- 🧠 **Complete Feedback Loop**: In both `EDIT` and `REGENERATE` modes, the prompt explicitly transfers the judge's exact per-character biometric rationales ($F_1, F_2, \dots$) as structured positive directives.
- 📖 **Automatic `character.yaml` Ingestion**: The harness automatically parses ground-truth physical characteristics (hair, clean-shaven / beard rules, visual look) and injects them into generation prompts and judge evaluation criteria.
- ✂️ **Structured Edit Payloads**: Refined `EDIT` payloads with clear instructions to preserve composition while modifying detected facial/scene defects.
- 🧪 **Unit Tests**: Added tests for YAML character profile parsing, biometric blueprint generation, and multi-character feedback transmission.
- 📑 **SPECS.md Lessons 16 & 17**: Codified complete feedback transmission and YAML metadata ingestion rules.

## [0.6.0] — 2026-08-26

### 👥 Multi-Character Consistency & Refined Scoring Overlay

- 👥 **Multi-Character Architecture**: Added full multi-character support (`-c kate,riccardo` / `--characters`), resolving and uploading reference images for all characters with distinct prompt context binding.
- 👨‍⚖️ **Multi-Biometric LLM Judge**: Independent facial similarity tracking ($F_1, F_2, \dots$) alongside Scene Adaptation ($S$) and Prompt Adherence ($A$).
- 🏷️ **Pill Overlay Refinement (Lesson 14)**: Score pill now computes the arithmetic mean (MEDIA) in warm yellow (`#FFE000`) with optimized font scaling (-10%) and rounded dark pill backdrop.
- 🧪 **Minimum Testing Floor (Lesson 15)**: Enforced minimum 5 iterations in testing ($N \ge 5$) to track real convergence curves and drift prevention.
- 📈 **Multi-Curve Graphing**: Independent plotting for each character ($F_1, F_2$), Scene, Adherence, and Bottleneck score.
- 📑 **Comprehensive Docs & SPECS Alignment**: Synchronized `GEMINI.md`, `docs/SPECS.md`, and `docs/USER_MANUAL.md`.

## [0.5.7] — 2026-08-26

### 🎨 Graph De-Cluttering & Multi-Iteration Honeymoon Progression

- 🧹 Removed text labels from convergence graph background zones (clean aesthetic driven solely by soft zone colors)
- 🏊‍♀️ Generated full multi-iteration honeymoon progression for Kate & Riccardo in Switzerland (3 iterations: initial -> regenerate -> edit)
- 📊 Fully synchronized Storagify cloud catalog with newly formatted graphs and reports

## [0.5.6] — 2026-08-26

### 📈 Convergence Graphing, Reports & Comprehensive User Manual

- 📖 Created comprehensive [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) detailing architecture, the 3-axis scoring rubric, and 7 Critical User Journeys (CUJs)
- 🤖 Updated `GEMINI.md` to reference `docs/USER_MANUAL.md` with instructions for all agents to keep it updated
- 📑 `bin/index.py` now writes/updates both `out/index.md` and `out/README.md` concurrently
- 📊 Fixed x-axis indexing in `lib/grapher.py` to match 1-based iteration counts
- 📄 `lib/reporter.py` now writes both `README.md` and `index.md` per run for seamless Storagify & web rendering
- 📦 Added `matplotlib` to `bin/portr8.py` inline script metadata
- 🏆 Verified full convergence pipeline with dual-axis judge (`gemini-3.5-flash`), score overlays, and JSON ledger

## [0.5.5] — 2026-08-26

### 🌿 Universal Environment Variable & DRY Configuration

- 🌐 Full DRY support for `PORTR8_MAX_ITERATIONS` (and other `PORTR8_*` env vars)
- ⚙️ `RunConfig` in `lib/models.py` uses `default_factory` reading from `os.getenv`
- 🖥️ `bin/portr8.py` automatically loads `.env` on startup and defaults CLI flags to env values
- 📜 `Justfile` enabled `set dotenv-load := true` and `env_var_or_default("PORTR8_MAX_ITERATIONS", "20")`
- 📝 `.env.dist` updated with `PORTR8_MAX_ITERATIONS=20`

## [0.5.4] — 2026-08-26

### 🔄 Default Iterations & Metric Simplification

- ⏱️ Increased default maximum iterations from 10 to 20 across CLI, `Justfile`, `RunConfig`, and docs
- 🎯 Simplified index score display to single bottleneck rating with Italian verdict badges
- 🔗 Hardened subfolder links in index with explicit `index.html` targets for reliable GCS hosting

## [0.5.3] — 2026-08-26

### 📑 Automated Indexing & Storagify Integration

- 📁 Direct subfolder links in `out/index.md` and public HTML for easy 1-click navigation
- 🧹 Cleaned and decluttered index table layout (focused on folder, character emoji, prompt, iterations, best scores, status, and artifact links)
- 🔄 Automatic index updating at the end of `portr8.py` runs
- 🛠️ Robust backward compatibility in `models.py` and `index.py` for legacy run schemas
- 📦 Added `just storagify` and `just sync` recipes to easily build and push the public HTML gallery to GCS

## [0.5.2] — 2026-08-26

### 🎨 Two-Pill Overlay Redesign

- 🏷️ Big `#N` top-left + score bottom-right (two rounded pills)
- 🟢 Color-coded score pill: green (≥8.0), dark (6.0-7.9), red (<6.0)
- 🔴 Failure overlay: both pills red
- 📐 Font sizes: iteration ~10% of image height, score ~7%

## [0.5.1] — 2026-08-26

### 🏷️ Simplified Overlay

- 🏷️ Overlay text simplified: `#1 F=7.2 A=7.8 S=7.5` → `#1 7.2` (single number = min of 3 axes)
- 🏷️ Same change for failure overlays
- 📄 README.md generation confirmed working in each output folder

## [0.5.0] — 2026-08-26

### 🔁 Feedback Loop Fix — "The Loop That Actually Loops"

**BREAKING**: The convergence loop now genuinely improves between iterations.

Three critical bugs fixed:

- 🐛 **Bug #1 — Dead prompt**: Augmented prompt was IDENTICAL every iteration. Strategist now
  extracts specific judge rationale text and includes it in the next prompt (e.g., "nose too wide",
  "wrong hair color"), so the image model gets directed, evolving feedback.
- 🐛 **Bug #2 — Fake edit mode**: "edit" vs "regenerate" was logged but both did the same thing.
  Now "edit" passes the previous iteration's image to the generator for refinement, while
  "regenerate" starts from scratch with references only.
- 🐛 **Bug #3 — Judge ceiling at 7.5**: Judge had no scoring rubric, invented its own scale where
  7.5 = "strong resemblance" and 8.0 = impossible. Added explicit scoring anchors:
  8.0 = "immediately recognizable", 9.0 = "could fool a friend".
- 🎯 Strategist now receives `target_score` to calibrate feedback thresholds (below-target scores
  trigger specific CORRECTION directives, above-target scores get no corrections).

## [0.4.1] — 2026-08-25

### 📄 README.md + Version in Reports

- 📄 Renamed per-run `report.md` → `README.md` for auto-rendering in GitHub/GitLab
- 🏷️ Version and character name in report title: `# portr8 v0.4.1 — riccardo`
- ⏰ Generation timestamp in report header
- 🔙 Index generator: backward-compatible fallback (`README.md` → `report.md`)
- ✅ Tests: assert `README.md` filename + version presence

## [0.4.0] — 2026-08-25

### 🔬 3-Axis Scoring + Floating Overlay + Per-Run Reports

**BREAKING**: `resemblance_score` → `facial_similarity` + new `scene_adaptation` axis.

- 🔬 Split resemblance into **facial_similarity** (face identity only, NOT clothing) + **scene_adaptation** (clothing/pose match PROMPT)
- 🎯 New convergence rule: `facial_similarity >= target AND adherence >= target AND scene_adaptation >= 5.0`
- 👔 Strategist: regenerate when scene_adaptation < 5.0, guide "wear scene-appropriate clothing"
- 👨‍⚖️ Judge prompt: 3-axis evaluation, prompt overrides for "without beard/glasses" are ground truth
- 🖼️ Overlay redesigned: floating semi-transparent banner ON the image (same dimensions), minimal text `#N F=X.X A=X.X S=X.X`
- 📊 Grapher: 3 lines (blue=Facial, green=Adherence, orange=Scene) + scene floor line at 5.0
- 📄 Per-run `report.md`: auto-generated in each output folder with config, score table, images, rationales
- 📋 Reporter wired into main CLI loop (generates report.md after each run)
- 📊 Index updated: Best F / Best S / Best A columns, report.md links
- ✅ 50 tests passing

## [0.3.0] — 2026-08-25

### 📊 Convergence Graphs & Run Index

- 📊 `lib/grapher.py` — Matplotlib convergence graph per run (R/A scores, target line, best ⭐, color-coded bg)
- 📊 `bin/index.py` — Deterministic run index generator (`just index` → `out/index.md`, `just index-csv` → CSV)
- 📊 `RunSummary.best_image_path` + `graph_path` — no duplicate JSON, enrich existing summary
- 🐛 Fix emoji □ rendering in Pillow overlay — `_strip_emoji()` helper, ASCII labels (YES/NO) instead
- 📝 GEMINI.md: experimentation philosophy — "tokens are free, show don't tell"
- ➕ `matplotlib>=3.8.0` dependency added

## [0.2.0] — 2026-08-25

### 🚀 Full Implementation — All 11 Tasks Complete (50 tests ✅)

#### Phase 1: Foundation
- ✨ `lib/models.py` — 6 Pydantic v2 data models (JudgeVerdict, IterationRecord, RunConfig, etc.) with Italian verdict labels (CAPOLAVORO 🏆 / BUONO 👍 / COSÌ-COSÌ 😐 / SCHIFO 🤮)
- 📝 `lib/ledger.py` — JSONL append-only ledger with convergence tracking and run summaries
- 🏗️ `pyproject.toml` + `Justfile` — UV-based project scaffolding with 12 recipes

#### Phase 2: Core Pipeline
- ✨ `lib/generator.py` — Image generation with Files API transport, model fallback chain, and grid_cleaned priority
- 👨‍⚖️ `lib/judge.py` — Dual-axis LLM judge (resemblance + adherence) with anti-beautification detection and photorealism check
- 🧠 `lib/strategist.py` — Edit-vs-regenerate strategy engine with positive-only prompt augmentation (NEVER negative constraints)

#### Phase 3: Polish
- 🎨 `lib/overlay.py` — Pillow score banner overlay with color-coded Italian verdict labels
- 🚀 `bin/portr8.py` — Main convergence loop CLI (PEP 723 inline deps, `uv run` compatible)
- 📊 `lib/reporter.py` + `bin/report.py` — Markdown report generator with score progression and image gallery

#### Phase 4: Advanced
- 📏 `bin/calibrate.py` — AI judge calibration tool (multi-model comparison, interactive human ratings)
- 👤 `bin/human_rate.py` — Human rating override tool with AI-vs-human comparison table

## [0.1.0] — 2026-08-25

### 🎉 Initial Release

- 📝 Project specification (`docs/SPECS.md`) with 13 empirical lessons from `gemini-tools`
- 🤖 Meta-agentic development log (`META-AGENTS.md`) documenting the AI-assisted build process
- 📋 Agent instructions (`GEMINI.md`) with critical design constraints and task breakdown
- 🏗️ Project scaffolding: `pyproject.toml`, `Justfile`, `.env.dist`, `.gitignore`
- 🔒 Private data strategy: `.env` privatized via gprism, `data/characters/` symlinked to private vault
