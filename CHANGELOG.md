# 📝 CHANGELOG — portr8

All notable changes to this project will be documented in this file.
Format: [Gitmoji](https://gitmoji.dev/) + [Keep a Changelog](https://keepachangelog.com/).

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
