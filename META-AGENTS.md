# 🤖 META-AGENTS — How portr8 Was Built (Agentic Development Log)

> **Purpose**: This document records the agentic development methodology used to build portr8.
> It's meta-documentation — documenting how the AI agent built the tool, for Riccardo's future article
> on AI-assisted software development.

## 🧬 The Agentic DNA

**Date**: 2026-08-25
**Human**: Riccardo Carlesso (RiccardinoCM26 🦖), Developer Advocate @ Google Cloud
**Agent**: Antigravity (Gemini CLI), running on Derek (Linux work machine)
**Conversation ID**: `f9208df6-827f-4f6a-a2a6-1746298a0cce`

---

## 📋 Phase 0: Specification (This Session)

### Skill Used: `superpowers:writing-plans`

The user invoked `/write-plan` which delegates to the `writing-plans` superpowers skill.
This skill enforces: bite-sized tasks, TDD, DRY, exact file paths, plan saved to `docs/`.

### Research Phase

Before writing a single line of spec, two **research subagents** were dispatched in parallel:

| Subagent | Role | What It Researched | Conversation ID |
|:---|:---|:---|:---|
| `research` | Gemini tools researcher | Full codebase analysis of `~/git/gemini-tools/` — scripts, APIs, patterns, models | `1d5ddb75-88e3-44ed-90e2-fd40249abdf2` |
| `research` | Portr8 directory researcher | Project conventions (Justfile, pyproject.toml, .env patterns) across `~/git/` | `8c2ea2aa-1851-46e6-baec-b45b7c9f87e6` |

Both returned comprehensive findings that shaped the spec.

### Empirical Knowledge Extraction

The agent read **all empirical documentation** from `~/git/gemini-tools/docs/`:
- `EVAL.md` — AI vs Human score benchmarks (the kate_lion disaster: AI 7.0 vs Human 1.0)
- `INVESTIGATION_GCS_DIRECT_REFERENCES.md` — Files API vs base64 vs GCS URI transport
- `PROMPT_STRATEGY_EXPERIMENTS.md` — Positive blueprinting wins, negative constraints fail
- `ARCHITECTURE.md` — Approccio A vs B for real person consistency

These were distilled into **13 Lessons Learned** that became hard design constraints.

### Spec Review Loop

The spec went through **3 iterations** of human review:
1. **v1**: Initial 12-component spec (BEFORE reading all empirical docs)
2. **v2**: Added 13 Lessons Learned section with benchmark tables
3. **v3**: Incorporated Riccardo's inline comments — resolved 6 design decisions

Key decisions made through inline artifact comments:
- Target score overridable (default 8)
- Public repo / private character data strategy
- LLM-smart strategy engine with "stupid" fallback
- Exit non-zero on failure, still produce red-banner report
- Reproducible output capsules with SW version tracking

---

## 🏗️ Phase 1: Implementation (Planned)

### Skill Used: `superpowers:subagent-driven-development`

**Why this over Conductor?** The spec is already a detailed plan with 11 bite-sized tasks across
4 phases. Conductor's track/phase infrastructure would be overhead for a single-plan greenfield build.
Subagent-driven-development lets us:
- **Parallelize** independent tasks (scaffolding + models + ledger = Phase 1, all independent)
- **Review** between phases
- **Commit incrementally** after each task

### Alternatives Considered

| Skill | Why NOT |
|:---|:---|
| `conductor` | Riccardo's usual go-to. Excellent for long-lived multi-track projects. Overkill for a single-plan greenfield build with 11 tasks. |
| `pickle-rick` | Opinionated iterative loop with PRD → Plan → Implement. We already have the spec, so the PRD/Plan phases are redundant. |
| `superpowers:executing-plans` | Good for separate-session execution. But `subagent-driven-development` keeps everything in one session with parallelism. |

### Execution Strategy

```
Phase 1: Foundation (parallel subagents)
├── Subagent A: Project scaffolding (pyproject.toml, Justfile, .gitignore, etc.)
├── Subagent B: Data models (lib/models.py + tests)
└── Subagent C: Ledger (lib/ledger.py + tests)
    ↓ review checkpoint
Phase 2: Core Pipeline (sequential, depends on Phase 1)
├── Subagent D: Image generator (lib/generator.py + tests)
├── Subagent E: Dual-axis judge (lib/judge.py + tests)
└── Subagent F: Strategy engine (lib/strategist.py + tests)
    ↓ review checkpoint
Phase 3: Polish (parallel)
├── Subagent G: Score overlay (lib/overlay.py + tests)
├── Subagent H: Main CLI loop (bin/portr8.py)
└── Subagent I: Report generator (lib/reporter.py + tests)
    ↓ review checkpoint
Phase 4: Advanced (sequential)
├── Subagent J: Rater calibration (bin/calibrate.py)
└── Subagent K: Human override mechanism
    ↓ final review + `just test`
```

---

## 🧠 Key Observations (for the Article)

### What Worked Well

1. **Research subagents before spec writing** — Two parallel subagents explored the codebase
   before a single line of spec was written. This prevented "spec by vibes".

2. **Empirical docs as design constraints** — The 13 Lessons Learned weren't just informational —
   each one ended with a concrete `→ portr8 design constraint:` that the implementation MUST follow.
   This is the bridge between R&D experiments and production code.

3. **Inline artifact comments** — Riccardo reviewed the spec by adding inline comments directly
   on the Markdown artifact. This preserved context ("yes 8 is default but can be changed") that
   would be lost in chat messages.

4. **The "honest question" pattern** — The agent asked "do you think this belongs in a NEW repo
   or should we reuse gemini-tools?" and Riccardo corrected three wrong assumptions. This prevented
   architectural mistakes.

### What Was Tricky

1. **File changed during review** — The agent overwrote the spec while Riccardo was adding inline
   comments. Lesson: don't write to artifacts while the human is reviewing.

2. **Wrong assumptions about gemini-tools** — The agent assumed gemini-tools was private (it's public),
   that data/characters/ contained real photos (they're symlinks), and that it was a "workshop"
   (it's a proper tool suite). The human corrected all three.

3. **PII handling complexity** — The public repo / private character data split required careful
   thought. The solution (`.gitignore` + `--ref-dir` + `character.yaml` metadata) emerged through
   dialogue, not unilateral agent decision.

### Metrics (Spec Phase)

| Metric | Value |
|:---|:---|
| Time from `/write-plan` to approved spec | ~45 minutes |
| Research subagents dispatched | 2 (parallel) |
| Source files read from gemini-tools | 8 (scripts + docs) |
| Spec iterations | 3 |
| Design decisions resolved | 6 |
| Lessons learned encoded | 13 |
| Open questions remaining | 4 (deferred to v0.2) |

---

## 📚 Reference Links

- **Spec**: [`docs/SPECS.md`](docs/SPECS.md)
- **Agent instructions**: [`GEMINI.md`](GEMINI.md)
- **Upstream codebase**: [`~/git/gemini-tools/`](file:///usr/local/google/home/ricc/git/gemini-tools/)
- **Respec copy**: [`~/git/respec/docs/llm-apps/portr8/SPECS.md`](file:///usr/local/google/home/ricc/git/respec/docs/llm-apps/portr8/SPECS.md)
- **Conversation transcript**: `~/.gemini/antigravity/brain/f9208df6-827f-4f6a-a2a6-1746298a0cce/`
