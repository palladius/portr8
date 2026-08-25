# 📝 CHANGELOG — portr8

All notable changes to this project will be documented in this file.
Format: [Gitmoji](https://gitmoji.dev/) + [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — 2026-08-25

### 🎉 Initial Release

- 📝 Project specification (`docs/SPECS.md`) with 13 empirical lessons from `gemini-tools`
- 🤖 Meta-agentic development log (`META-AGENTS.md`) documenting the AI-assisted build process
- 📋 Agent instructions (`GEMINI.md`) with critical design constraints and task breakdown
- 🏗️ Project scaffolding: `pyproject.toml`, `Justfile`, `.env.dist`, `.gitignore`
- 🔒 Private data strategy: `.env` privatized via gprism, `data/characters/` symlinked to private vault

### Planned (not yet implemented)

- `lib/models.py` — Pydantic data models (JudgeVerdict, IterationRecord, RunConfig)
- `lib/generator.py` — Image generation with Files API transport
- `lib/judge.py` — Dual-axis LLM judge (resemblance + adherence + photorealism)
- `lib/strategist.py` — Edit-vs-regenerate decision engine
- `lib/overlay.py` — Pillow/FFmpeg score overlay
- `lib/ledger.py` — JSONL iteration tracking
- `lib/reporter.py` — Markdown/HTML convergence report
- `bin/portr8.py` — Main CLI orchestrator
- `bin/calibrate.py` — Rater calibration tool
- `bin/report.py` — Standalone report generator
