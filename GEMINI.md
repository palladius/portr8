# 🎯 GEMINI.md — AI Agent Instructions for portr8

> **For AI agents**: Read this file FIRST when working on this repository.

## Project Overview

**portr8** is an iterative character-consistent portrait convergence engine.
It generates photorealistic images of real people using Gemini's image generation models,
judges them on TWO axes (resemblance + prompt adherence), and loops until both scores hit ≥ 8/10.

## Architecture

```
bin/portr8.py     → Main CLI orchestrator (PEP 723, uv-runnable)
bin/calibrate.py  → Rater calibration tool
bin/report.py     → Standalone report generator
lib/models.py     → Pydantic data models (JudgeVerdict, IterationRecord, RunConfig)
lib/generator.py  → Image generation (wraps google-genai SDK)
lib/judge.py      → Dual-axis LLM judge (resemblance + adherence + photorealism)
lib/strategist.py → Decides edit-vs-regenerate, builds augmented prompts
lib/overlay.py    → Pillow/FFmpeg score overlay on images
lib/ledger.py     → JSONL iteration tracking (append-only ledger)
lib/reporter.py   → Markdown/HTML slide deck generator
```

## Critical Design Constraints (from empirical research)

These are NON-NEGOTIABLE. Violating them will produce bad results:

1. **Files API for reference transport** — Use `client.files.upload()`, NOT inline PIL/base64.
   Base64 causes AI beautification and scores ~5.2-6.0. Files API scores ~6.8-8.2.

2. **NEVER use negative prompt constraints** — "NO model skin", "DO NOT smooth" → scores 3.6/10.
   Always use POSITIVE biometric blueprinting ("authentic skin texture with visible pores").

3. **Photorealism is mandatory** — Cartoon consistency is too easy and is a non-goal.
   ALL prompts must include photorealism cues. The judge checks `is_photorealistic`.

4. **Anti-beautification in judge prompt** — The judge MUST penalize doll-face smoothing.
   If detected, resemblance score ≤ 5.0.

5. **Every iteration logs its seed** — For reproducibility. `--seed` flag for deterministic replay.

6. **Full provenance in JSONL** — Every record includes: augmented prompt, tilde-normalized paths,
   reference transport method, model used, SW version, elapsed time.

## Implementation Approach

This project uses **superpowers:subagent-driven-development** for implementation.
See [`META-AGENTS.md`](META-AGENTS.md) for the full agentic development methodology.

### Task Breakdown (4 Phases, 11 Tasks)

**Phase 1: Foundation** (parallelizable)
1. Project scaffolding (pyproject.toml, Justfile, .gitignore, etc.)
2. Data models (`lib/models.py`) + tests
3. Ledger (`lib/ledger.py`) + tests

**Phase 2: Core Pipeline** (sequential)
4. Image generator (`lib/generator.py`) + tests
5. Dual-axis judge (`lib/judge.py`) + tests
6. Strategy engine (`lib/strategist.py`) + tests

**Phase 3: Polish** (parallelizable)
7. Score overlay (`lib/overlay.py`) + tests
8. Main CLI loop (`bin/portr8.py`)
9. Report generator (`lib/reporter.py`) + tests

**Phase 4: Advanced** (sequential)
10. Rater calibration (`bin/calibrate.py`)
11. Human override mechanism

### If This Session Gets Interrupted

1. Check `META-AGENTS.md` for where we left off
2. Check `docs/SPECS.md` for the full specification
3. Run `just test` to see what's already working
4. Resume from the next uncompleted task in the phase breakdown above
5. Use `superpowers:subagent-driven-development` skill to continue

## Tech Stack

- **Python 3.11+** with `uv` for package management
- **PEP 723** inline script dependencies for `bin/` scripts
- **google-genai** SDK for image generation and LLM judging
- **Pydantic** for structured JSON output from judges
- **Pillow** + **FFmpeg** for score overlays
- **Rich** for terminal UI (panels, colors, progress)
- **hatchling** build backend

## Conventions

- Use `just` as the task runner. `just` (no args) shows available tasks.
- Use `uv` for Python (NOT virtualenv). `UV_INDEX_URL="https://pypi.org/simple"`.
- Environment variables in `.env` (gitignored). Document new vars in `.env.dist`.
- NEVER edit `.env` directly — only `.env.dist`.
- Versioning in `VERSION` file. Update `CHANGELOG.md` with gitmoji on every change.
- Output folders: `out/YYYYMMDD-HHMM-<prompt-slug>/`
- Character data: `data/characters/` is gitignored. Use `--ref-dir` to point to private vault.
- Tests: `tests/test_*.py`, run with `uv run python -m pytest tests/ -v`

## Upstream Heritage

Patterns adapted from [`~/git/gemini-tools/`](file:///usr/local/google/home/ricc/git/gemini-tools/):
- `generate_photo.py` → `lib/generator.py`
- `judge_image.py` → `lib/judge.py`
- `eval_single_model.py` → `lib/overlay.py` + `lib/reporter.py`
- `find_golden_kate_candidate.py` → `bin/portr8.py` (spiritual successor)

See `docs/SPECS.md` §"Lessons Learned" for the 13 empirical findings that shaped this codebase.
