# 📝 CHANGELOG — portr8

All notable changes to this project will be documented in this file.
Format: [Gitmoji](https://gitmoji.dev/) + [Keep a Changelog](https://keepachangelog.com/).

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
