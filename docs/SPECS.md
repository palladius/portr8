# 🎯 portr8 — Iterative Character-Consistent Portrait Convergence Engine

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build `portr8`, a CLI tool that generates photorealistic character-consistent images in an iterative feedback loop — generating, judging, and refining until both **resemblance** and **prompt adherence** scores hit ≥ 8/10 (hence the name: "portr-8").

**Architecture:** A closed-loop pipeline: Generate → Judge → Overlay scores → Decide strategy (edit vs. regenerate) → Feed back critique → Repeat. All iterations are tracked in a JSONL ledger. A final Markdown report/slide deck is auto-generated showing the convergence journey. A separate calibration mode lets Riccardo cross-rate the AI judge against multiple models.

**Tech Stack:** Python 3.11+, `uv` (PEP 723 inline script deps), `google-genai` SDK, Pillow, FFmpeg, `rich`, `pydantic`, Markdown/HTML slide generation.

**Upstream dependency:** Reuses patterns and libraries from [`~/git/gemini-tools/`](file:///usr/local/google/home/ricc/git/gemini-tools/) — specifically [`generate_photo.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/generate_photo.py), [`judge_image.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/judge_image.py), and [`eval_single_model.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/eval_single_model.py).

**Direct ancestor:** [`find_golden_kate_candidate.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/find_golden_kate_candidate.py) — a linear generate→judge→stop loop with fixed prompts. portr8 generalizes this into a closed-loop system with feedback piggybacking, dual-axis scoring, and adaptive strategy.

---

## 🧪 Lessons Learned from gemini-tools (Empirical Findings)

> [!IMPORTANT]
> These lessons are distilled from **months of empirical experimentation** documented in [`EVAL.md`](file:///usr/local/google/home/ricc/git/gemini-tools/docs/EVAL.md), [`INVESTIGATION_GCS_DIRECT_REFERENCES.md`](file:///usr/local/google/home/ricc/git/gemini-tools/docs/INVESTIGATION_GCS_DIRECT_REFERENCES.md), [`PROMPT_STRATEGY_EXPERIMENTS.md`](file:///usr/local/google/home/ricc/git/gemini-tools/docs/PROMPT_STRATEGY_EXPERIMENTS.md), and [`ARCHITECTURE.md`](file:///usr/local/google/home/ricc/git/gemini-tools/docs/ARCHITECTURE.md). **portr8 MUST encode these as hard design constraints.**

### Lesson 1: Reference Transport Matters More Than Prompting

| Method | Typical Score | Finding |
|:---|:---:|:---|
| Inline Base64 (PIL resize) | 5.2 – 6.0 | ❌ Client-side resampling causes **AI beautification** — facial smoothing, generic model features |
| Files API (`client.files.upload`) | 6.8 – 8.2 | ✅ Preserves full-resolution micro-biometrics (cheek moles, iris color, teeth gaps) |
| GCS Direct URI (`types.Part.from_uri`) | 4.8 – 7.0 | 🟡 Zero network overhead but requires bucket setup; quality varies |

**→ portr8 design constraint:** Default to **Files API** (`--files-api`) for reference image transport. Support PIL fallback and GCS as options, but Files API is the proven winner for human-rated scores.

### Lesson 2: AI Judge Scores Correlate With Human Scores — Mostly

From the Alessandro benchmark matrix in [`EVAL.md`](file:///usr/local/google/home/ricc/git/gemini-tools/docs/EVAL.md):

| Image | AI Score | Human Score | Match? |
|:---|:---:|:---:|:---:|
| `candidate5.png` | 3.5 | 2.0 | ✅ Exact alignment ("Che schifo") |
| `candidate2.png` | 5.2 | 5.0 | ✅ Exact alignment |
| `candidate4.png` | 7.8 | 6.5 | ⚠️ AI overrates by ~1.3 |
| `candidate7_files_api.png` | 7.8 | **8.2** | ✅ AI underrates slightly |

But from the Kate matrix — **catastrophic miscalibration found:**

| Image | AI Score | Human Score | Match? |
|:---|:---:|:---:|:---:|
| `kate2016_kenya_lion.png` | **7.0** | **1.0** | 🚨 **6-point gap!** "non le somiglia per niente" |
| `exp1_cand1..3` | 7.5 – 7.8 | 6.5 | ⚠️ AI overrates |
| `exp2_cand1..3` | 4.2 – 4.5 | 0.0 | 🗑️ Both agree it's trash |

**→ portr8 design constraint:** The AI judge is **necessary but not sufficient**. The calibration tool (`bin/calibrate.py`) is NOT optional — it's a first-class feature. The system must warn when AI scores are high but past calibration data suggests the judge is unreliable for this character.

### Lesson 3: Negative Prompt Constraints FAIL

From [`PROMPT_STRATEGY_EXPERIMENTS.md`](file:///usr/local/google/home/ricc/git/gemini-tools/docs/PROMPT_STRATEGY_EXPERIMENTS.md):

| Strategy | Approach | Score |
|:---|:---|:---:|
| Strategy 1 | Explicit A/B/C Reference Binding + Anti-Beautification | **6.5** |
| Strategy 2 | Negative Constraints ("NO model skin", "NO altered nose") | **3.6** ❌ |
| Strategy 3 | Biometric Feature Blueprint (positive descriptions) | **6.5** 👑 |

**→ portr8 design constraint:** The strategist MUST NEVER generate negative constraint prompts ("DO NOT", "NO", "AVOID"). Instead, it must use **positive biometric blueprinting** ("authentic natural skin texture with visible pores", "warm smile with fine lines around eyes") and **explicit reference binding** ("the exact person shown in the reference photographs").

### Lesson 4: Consistency in Cartoons is TOO EASY — Non-Goal

From [`EVAL.md`](file:///usr/local/google/home/ricc/git/gemini-tools/docs/EVAL.md):
> "Consistency in Cartoons is TOO EASY, so it's a non-goal. We want photo-realistic pics."

**→ portr8 design constraint:** The judge MUST include a **photorealism axis** (`is_photorealistic: bool`). If an iteration produces a cartoon/illustration, it's rated 0 on that axis and the strategist forces a full regeneration with explicit photorealism cues. The system should add "photorealistic, 85mm lens, camera-like depth of field" to ALL prompts.

### Lesson 5: The "Schifo Threshold" — Scores Below 6.0 Are Garbage

From empirical data, Riccardo's ratings follow a clear pattern:
- **≥ 8.0**: "Buono!" / CAPOLAVORO — usable in production
- **7.0 – 7.9**: "Meh" — recognizable but not convincing
- **5.0 – 6.9**: "Non le/gli somiglia" — reject
- **< 5.0**: "Fa SCHIFO" / "Che schifo" — total failure

**→ portr8 design constraint:** Use Italian-flavored verdict labels: `CAPOLAVORO` (≥8), `BUONO` (≥7), `COSÌ-COSÌ` (≥5), `SCHIFO` (<5). This matches Riccardo's natural vocabulary and makes the output immediately interpretable.

### Lesson 6: AI Beautification is the #1 Enemy

From [`INVESTIGATION_GCS_DIRECT_REFERENCES.md`](file:///usr/local/google/home/ricc/git/gemini-tools/docs/INVESTIGATION_GCS_DIRECT_REFERENCES.md):
> "Client-side base64 / PIL resizing causes AI beautification and facial smoothing (scores ~5.2 – 6.0)."

And from EVAL.md, Kate experiments:
> "Abbellimento artificiale" / "sembra troppo vecchia e brutta" / "Invecchiamento AI irrealistico"

The models tend to either **smooth/beautify** (doll face) or **age/uglify** (wrong wrinkles). Both are failures.

**→ portr8 design constraint:** The judge prompt MUST explicitly penalize beautification:
> "If the generated face has unnaturally smooth skin, symmetrical doll-like features, or shows obvious AI beautification/smoothing, REDUCE the resemblance score to ≤ 5.0."

### Lesson 7: Reference Photo Quality Determines the Ceiling

From [`evaluate_reference_photos.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/evaluate_reference_photos.py) and the LOO (Leave-One-Out) evaluation:
- Photos scoring < 6.0 against the rest of the set are classified as `PRUNE_BAD_ANGLE` and cause **model drift**
- Photos in `grid_cleaned/` (pre-cropped single-subject) outperform raw multi-person photos
- Sorting by file size (descending) prioritizes high-resolution photos

**→ portr8 design constraint:** Before the main loop starts, run a quick reference quality check. If `grid_cleaned/` directory exists for the character, prefer it. Warn the user if reference photos score poorly against each other. Consider adding a `portr8 check-refs -c riccardo` subcommand.

### Lesson 8: The Seed Parameter Enables Reproducibility

From [`eval_single_model.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/eval_single_model.py#L188):
```python
current_seed = seed if seed is not None else random.randint(1, 2147483647)
```

The seed is passed to `GenerateContentConfig(seed=current_seed)` and logged in the JSONL record.

**→ portr8 design constraint:** Every iteration MUST log its seed. Provide `--seed` for deterministic replay. When running dual strategy (edit vs. regenerate), use the same seed for fair comparison.

### Lesson 9: FFmpeg Overlay Pattern is Proven

From [`eval_single_model.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/eval_single_model.py#L82-L129):
1. Create a transparent PNG banner with Pillow (`ImageDraw.Draw`)
2. Composite with FFmpeg: `ffmpeg -y -i input.png -i banner.png -filter_complex "[0:v][1:v]overlay=(W-w)/2:H-h-30"`
3. Fall back to pure Pillow if FFmpeg is unavailable

**→ portr8 design constraint:** Reuse this exact pattern. The banner should be positioned at the **bottom** of the image. Include iteration number, both scores, photorealism check, and verdict.

### Lesson 10: Provenance Metadata is Essential

From [`generate_photo.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/generate_photo.py#L206-L217): Every generated image gets a `.json` sidecar with:
- `generated_asset_path` (tilde-normalized)
- `source_reference_paths`
- `prompt`
- `model_used`
- `generation_timestamp`

**→ portr8 design constraint:** Every iteration record in the JSONL ledger must include full provenance. Use `to_tilde_path()` for human-readable paths. Also store the augmented prompt (with feedback piggybacked), not just the original.

### Lesson 11: The `find_golden_kate_candidate.py` Pattern = portr8 v0

[`find_golden_kate_candidate.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/find_golden_kate_candidate.py) is literally a simpler version of portr8:
1. Fixed list of 10 prompt variants → portr8 uses a **single prompt with adaptive augmentation**
2. Linear generate → judge → stop if ≥ 8.0 → portr8 adds **feedback piggybacking**
3. Single-axis score (biometric only) → portr8 uses **dual-axis** (resemblance + adherence)
4. No strategy selection → portr8 adds **edit vs. regenerate intelligence**
5. No report generation → portr8 adds **slide deck**

**→ portr8 design constraint:** This is the spiritual successor. Maintain the same Rich console output style (Panel, bold colors, emoji), the same threshold semantics (≥ 8.0 = GOLDEN), and the same "wake up Riccardo" celebration when convergence is reached.

### Lesson 12: `gemini-3.5-flash` is the Proven Judge Model

Across all experiments in gemini-tools, `gemini-3.5-flash` is used as the default judge. It supports structured JSON output via `response_schema=PydanticModel` and `response_mime_type="application/json"`.

Fallback chain for judging: `gemini-3.5-flash` → `gemini-3.6-flash` → `gemini-3.1-pro-preview`.

**→ portr8 design constraint:** Default `--judge-model` to `gemini-3.5-flash`. The calibration tool should test this against alternatives.

### Lesson 14: Overlay Score Philosophy & Visual Hygiene

From empirical testing on UI presentation and human review:
1. **Pill-style minimalism over cluttered text banners**: Instead of massive multi-line banners obscuring the art, use two clean rounded pills:
   - **Top-left**: Big `#N` (iteration number).
   - **Bottom-right**: `X.X` (single aggregate score).
2. **Color scheme**:
   - Background: Dark semi-transparent pill (`rgba(0, 0, 0, 0.65)`).
   - Foreground Text: Warm bright yellow (`#FFE000` / `RGB 255, 224, 0`) for crisp contrast against both snow, pool water, and dark scenery.
   - Quality-colored border/fill on score pill (Green for $\ge 8.0$, Dark for $\ge 6.0$, Red for $< 6.0$).
3. **Single Score Metric = Arithmetic Mean (Media)**:
   - The overlay pill shows the **AVERAGE (Media)** across all active axes ($F_1, F_2, \dots, S, A$).
   - The full forensic breakdown ($F_1, F_2, S, A$, bottleneck, rationales) is preserved in reports, ledgers, and terminal output.
4. **Generic Multi-Character Indexing ($F_1, F_2, \dots$)**:
   - Avoid letter collisions (e.g. Riccardo & Rosamaria both starting with 'R') by indexing characters as $F_1, F_2, \dots, F_N$.

### Lesson 15: Minimum Iteration Floor in Testing ($N \ge 5$)

In empirical experimentation and agentic testing:
- **NEVER use fewer than 5 iterations ($N \ge 5$)**.
- 1–3 iterations are too few to observe whether the feedback loop actually guides prompt refinement, if the strategist makes sound edit-vs-regenerate choices, or if regression/drift occurs.
- 5–10 iterations provide the necessary trajectory depth to evaluate convergence curves, rater variance, and prompt steering effectively.
- **Tokens are free: don't truncate runs early.**

### Lesson 16: Complete Feedback Loop Transmission & Per-Character Rationales

From empirical debugging of iteration regression and "blind edits":
1. **The Judge's feedback must never be lost in transit**: In both `EDIT` and `REGENERATE` modes, the prompt passed to Gemini MUST include the exact feedback and rationale produced by the Judge in iteration $N-1$.
2. **Per-character breakdown ($F_1, F_2, \dots$)**: For multi-character prompts, feedback must specify each individual character's biometric flaw (e.g. `Character 2 (Riccardo): beard must be removed, hair darkened`).
3. **Explicit Edit Mode Instructions**: In `EDIT` mode, the payload must explicitly instruct Gemini: *"You are refining the provided image. Modify and correct the image according to these specific instructions..."* rather than relying on an ambiguous prompt.

### Lesson 17: Authoritative `character.yaml` Biometric Ingestion

From real-world character consistency testing:
1. **Automated extraction**: Physical features (hair color/length, facial hair vs. clean-shaven, facial structure, visual look) and wardrobe guidelines defined in `data/characters/<name>/character.yaml` must be automatically loaded by the harness.
2. **Prompt enrichment**: Physical features must be formatted into positive biometric blueprints and injected into generation prompts automatically, without forcing the user to manually write physical descriptions in every CLI prompt.
3. **Judge alignment**: The authoritative character profile must also be passed to `lib/judge.py` so the evaluator penalizes contradictions (e.g. adding a beard when the YAML specifies clean-shaven).

---

## ✅ Resolved Design Decisions (from Riccardo's Review)

### Decision 1: Target Score — Overridable, Default 8

`--target-score N` defaults to `8.0` (matching the project name "portr-8") but is fully overridable. For quick tests use `--target-score 6.0`, for production quality use `--target-score 9.0`.

### Decision 2: Character Reference Images — Public Repo, Private Data

The portr8 repo is **public**. Character reference photos are **private** (PII — real family photos). Strategy:

- `data/characters/` exists in the repo but is in `.gitignore` — NO images committed
- `data/characters/.gitkeep` + `README.md` explains the setup
- `--ref-dir` flag (default: `data/characters/`) lets the user point to ANY directory
- For Riccardo's private testing: `--ref-dir ~/git/gic/private/projects/git-privatize/github.com__palladius__media-arneis/data/characters/`
- Each character folder MAY contain a `character.yaml` with metadata (name, age, hair color, eye color, description, `synthetic: bool`). portr8 reads this to enrich judge prompts.
- For CI/demos: ship 2-3 **synthetic test characters** (AI-generated "personas" with 5 reference photos each, `synthetic: true`) that ARE committable — but resemblance testing is skipped/soft for synthetic characters.

> [!NOTE]
> The private character vault chain: `~/git/gic/private/.../media-arneis/data/characters/` → symlinked into `~/git/gemini-tools/data/characters/` → usable via `--ref-dir`.

### Decision 3: Edit vs. Regenerate — LLM-Smart + Stupid Fallback

The strategist uses **LLM intelligence** to decide based on the judge feedback (Lesson #3 logic). But when `--dual-strategy` is active, it does BOTH (edit + regenerate), judges both, picks the winner. This is the "stupid but thorough" route.

**Critical requirement**: Every step's strategy choice, prompts used, and rationale MUST be kept **deterministically** in the JSONL ledger. Full trace, full reproducibility.

### Decision 4: Slide Deck — Markdown → HTML ✅

Zero-dependency Markdown → HTML. Self-contained (base64-embedded images).

### Decision 5: Convergence Failure — Exit Non-Zero, Still Produce Report

If `--max-iterations` is exhausted without reaching the target:
- Exit code = `1` (non-zero)
- **Still produce** the full slide deck / report, but with a **red failure banner**: "❌ FAILED — Best: R:6.5 A:7.0 (target was 8.0)"
- Highlight the best-so-far iteration with 🥈 instead of 🏆
- The trace/markdown is still **super useful** for debugging and iterating

### Decision 6: Reproducible Output Folders

All run outputs go into: `out/YYYYMMDD-HHMM-<prompt-slug>/`

Each folder is a **self-contained reproducibility capsule** containing:
- All generated images (`image_001.png`, `image_001_scored.png`, ...)
- All prompts used (original + augmented) in the JSONL ledger
- All judge verdicts as JSON sidecars
- The `character.yaml` snapshot (copy of the character metadata at run time)
- Reference image paths (tilde-normalized, not the images themselves — those are private)
- `run_config.json` — full CLI config used
- `portr8_version` — software version string (from `VERSION` file)
- `report.md` + `report.html` — the convergence report

This means tomorrow, with newer software, you can inspect exactly what happened today and compare.

## Remaining Open Questions

1. **Multi-character scenes**: Should portr8 support multiple characters in one image (e.g., "Riccardo and Kate eating gelato")? → Per-character resemblance scores needed. **Proposing: v0.1 = single character only, v0.2 = multi-character.**
2. **Rater calibration**: Separate `portr8 calibrate` subcommand vs. `--calibrate-first` flag? **Proposing: separate subcommand** — calibration is a distinct workflow.
3. **Edit model**: Same `--image-model` for both edit and regenerate? **Proposing: same model, simplest approach.** Add `--edit-model` later if needed.
4. **API key**: `GEMINI_API_KEY` from env (matching gemini-tools pattern). No `--api-key` flag — env vars are safer.

---

## Proposed Changes

### Project Structure

```
~/git/portr8/
├── bin/
│   ├── portr8.py                    # [NEW] Main CLI entry point (uv run)
│   ├── calibrate.py                 # [NEW] Rater calibration tool
│   └── report.py                    # [NEW] Standalone report/slide generator
├── lib/
│   ├── __init__.py                  # [NEW]
│   ├── models.py                    # [NEW] Pydantic data models
│   ├── generator.py                 # [NEW] Image generation (wraps google-genai)
│   ├── judge.py                     # [NEW] Dual-axis LLM judge (resemblance + adherence)
│   ├── strategist.py                # [NEW] Decides edit-vs-regenerate, builds augmented prompts
│   ├── overlay.py                   # [NEW] Pillow/FFmpeg score overlay on images
│   ├── ledger.py                    # [NEW] JSONL iteration tracking
│   └── reporter.py                  # [NEW] Markdown/HTML slide deck generator
├── data/
│   └── characters/                  # Symlink → ~/git/gemini-tools/data/characters/ (or standalone)
├── out/                             # Generated outputs per run
│   └── <run-id>/
│       ├── image_001.png
│       ├── image_001_scored.png
│       ├── image_001_audit.json
│       ├── image_002.png
│       ├── ...
│       ├── ledger.jsonl
│       ├── report.md
│       └── report.html
├── calibration/                     # Calibration session outputs
│   └── <session-id>/
│       ├── matrix.json
│       └── report.md
├── tests/
│   ├── test_judge.py                # [NEW]
│   ├── test_strategist.py           # [NEW]
│   ├── test_overlay.py              # [NEW]
│   └── test_ledger.py               # [NEW]
├── Justfile                         # [NEW] Task runner
├── pyproject.toml                   # [NEW] uv project config
├── .env.dist                        # [NEW] Required env vars documentation
├── .gitignore                       # [NEW]
├── GEMINI.md                        # [NEW] AI instructions for the repo
├── README.md                        # [NEW]
├── CHANGELOG.md                     # [NEW]
└── VERSION                          # [NEW] → "0.1.0"
```

---

### Component 1: Core Data Models (`lib/models.py`)

#### [NEW] [`lib/models.py`](file:///usr/local/google/home/ricc/git/portr8/lib/models.py)

Pydantic models for structured judge output and iteration tracking.

```python
from pydantic import BaseModel, Field
from enum import Enum

class Strategy(str, Enum):
    REGENERATE = "regenerate"     # Generate from scratch with augmented prompt
    EDIT = "edit"                 # Edit previous image with targeted instructions
    DUAL = "dual"                 # Try both, pick the better one

class JudgeVerdict(BaseModel):
    """Dual-axis evaluation of a generated image.
    Lessons applied: #4 (photorealism check), #5 (Italian verdicts),
    #6 (anti-beautification penalty in judge prompt)."""
    resemblance_score: float = Field(ge=1.0, le=10.0,
        description="How much the person looks like the reference photos (1-10)")
    adherence_score: float = Field(ge=1.0, le=10.0,
        description="How well the image matches the prompt description (1-10)")
    is_photorealistic: bool = Field(
        description="True if image looks like a real photo, False if cartoon/illustration")
    resemblance_rationale: str = Field(
        description="Why the resemblance score was given — specific facial features, hair, etc.")
    adherence_rationale: str = Field(
        description="Why the adherence score was given — missing/present scene elements")
    photorealism_note: str = Field(
        description="Note on photorealism quality — skin texture, lighting, etc.")
    improvement_suggestion: str = Field(
        description="Concrete actionable suggestion to improve the WORST-scoring axis")
    verdict: str = Field(
        description="CAPOLAVORO (both ≥8) | BUONO (avg ≥7) | COSÌ-COSÌ (avg ≥5) | SCHIFO (avg <5)")

class IterationRecord(BaseModel):
    """One iteration in the convergence loop.
    Lesson #10: full provenance, tilde paths, augmented prompt logged."""
    iteration: int
    run_id: str
    strategy_used: Strategy
    original_prompt: str           # The user's original prompt
    augmented_prompt: str          # The prompt with feedback piggybacked (Lesson #11)
    image_path: str                # Tilde-normalized (Lesson #10)
    scored_image_path: str
    audit_json_path: str
    image_model: str
    judge_model: str
    seed: int                      # Lesson #8: always logged
    resemblance_score: float
    adherence_score: float
    is_photorealistic: bool
    resemblance_rationale: str
    adherence_rationale: str
    improvement_suggestion: str
    verdict: str
    reference_images_used: list[str]  # Tilde-normalized paths
    reference_transport: str          # "files_api" | "pil" | "gcs" (Lesson #1)
    human_override: dict | None = None  # {"resemblance": 6.0, "adherence": 8.0, "note": "..."}
    elapsed_seconds: float
    timestamp: str

class RunConfig(BaseModel):
    """Configuration for a portr8 run."""
    prompt: str
    character: str
    max_iterations: int = 10
    target_score: float = 8.0          # The magic number (Lesson #5)
    image_model: str = "gemini-3.1-flash-image-preview"
    judge_model: str = "gemini-3.5-flash"  # Lesson #12: proven default
    ref_dir: str | None = None
    ref_transport: str = "files_api"   # Lesson #1: Files API is default
    dual_strategy: bool = False
    seed: int | None = None            # Lesson #8
```

---

### Component 2: Image Generator (`lib/generator.py`)

#### [NEW] [`lib/generator.py`](file:///usr/local/google/home/ricc/git/portr8/lib/generator.py)

Wraps `google-genai` for both **generation** (text+refs → image) and **editing** (image+refs+instructions → image). Reuses the same API patterns as [`generate_photo.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/generate_photo.py).

**Key functions:**
- `generate_from_prompt(prompt, ref_images, model, output_path, seed, transport)` → generates a new image from scratch
- `edit_image(source_image, edit_instructions, ref_images, model, output_path, seed, transport)` → edits an existing image with targeted instructions
- `resolve_character_refs(character_name, ref_dir, max_images=5)` → finds reference photos, prioritizing `grid_cleaned/` (Lesson #7)

**Reference Transport** (Lesson #1):
```python
def load_references(image_paths: list[str], transport: str, client) -> list:
    """Load reference images using the specified transport method."""
    if transport == "files_api":
        # Lesson #1: Best quality — preserves micro-biometrics
        return [client.files.upload(file=p) for p in image_paths]
    elif transport == "gcs":
        return [types.Part.from_uri(file_uri=to_gcs_uri(p), mime_type=guess_mime(p)) for p in image_paths]
    else:  # "pil" fallback
        return [PILImage.open(p).convert("RGB") for p in image_paths]
```

**Models & Fallback chain:**
1. Primary: `--image-model` (default: `gemini-3.1-flash-image-preview`)
2. Fallback: `gemini-3.1-flash-image` → `gemini-2.5-flash-image`

**Prompt hardening** (Lessons #3, #4): ALL prompts get photorealism cues appended:
```python
PHOTOREALISM_SUFFIX = (
    ". Photorealistic photograph, 85mm lens, natural lighting, "
    "authentic skin texture with visible pores, camera-like depth of field, "
    "natural imperfections, NOT a cartoon or illustration."
)
```

---

### Component 3: Dual-Axis Judge (`lib/judge.py`)

#### [NEW] [`lib/judge.py`](file:///usr/local/google/home/ricc/git/portr8/lib/judge.py)

An LLM-based judge that evaluates TWO separate axes (unlike gemini-tools' single biometric score). Uses structured JSON output via Pydantic schema.

**Key function:** `judge_image(generated_image_path, ref_images, original_prompt, model) → JudgeVerdict`

**Judge prompt** (incorporates Lessons #3, #4, #6):
```
You are an unsparing forensic photographic critic evaluating AI-generated portrait images.
You MUST evaluate TWO separate axes and a photorealism check.

AXIS 1 — RESEMBLANCE (1-10): Compare the person in the generated image against
the reference photos. Scrutinize: bone structure, eye shape/color, nose, lips,
hair color/texture, skin tone, age appearance, distinctive features (moles, dimples).
Score ≥8 means "I would recognize this as the same person in real life."

CRITICAL: If the generated face has unnaturally smooth skin, symmetrical doll-like
features, or shows obvious AI beautification/smoothing, REDUCE the resemblance
score to ≤ 5.0. Real humans have pores, fine lines, and asymmetry.

AXIS 2 — PROMPT ADHERENCE (1-10): Compare the generated image against the original
prompt: "{original_prompt}". Check: scene elements, clothing, actions, setting,
lighting, mood. Score ≥8 means "the image faithfully depicts the described scene."

AXIS 3 — PHOTOREALISM CHECK: Is this a photorealistic image (like a real camera
photo) or does it look like a cartoon, illustration, painting, or 3D render?
A photorealistic image has: natural skin texture, realistic lighting/shadows,
camera-like depth of field, natural imperfections.

Be brutally honest. Use POSITIVE descriptions in your improvement suggestions
(e.g. "add authentic skin texture with visible pores" NOT "do not smooth skin").
```

**Config:**
- `response_mime_type="application/json"`
- `response_schema=JudgeVerdict`
- `temperature=0.2` (deterministic judging)
- Fallback chain: `gemini-3.5-flash` → `gemini-3.6-flash` → `gemini-3.1-pro-preview` (Lesson #12)

---

### Component 4: Strategy Engine (`lib/strategist.py`)

#### [NEW] [`lib/strategist.py`](file:///usr/local/google/home/ricc/git/portr8/lib/strategist.py)

The "brain" that decides what to do next based on the judge's feedback.

**Decision logic:**

```python
def decide_strategy(verdict: JudgeVerdict, iteration: int, config: RunConfig) -> tuple[Strategy, str]:
    """Returns (strategy, augmented_prompt).
    Lesson #3: NEVER use negative constraints in augmented prompts.
    Lesson #4: Force regeneration if not photorealistic."""

    # Lesson #4: Non-photorealistic = always regenerate with stronger cues
    if not verdict.is_photorealistic:
        return Strategy.REGENERATE, augment_for_photorealism(config.prompt)

    # If resemblance is the bottleneck → edit (preserve scene, fix face)
    if verdict.adherence_score >= verdict.resemblance_score + 1.5:
        return Strategy.EDIT, build_edit_instructions_for_resemblance(verdict)

    # If adherence is the bottleneck → edit (preserve face, fix scene)
    if verdict.resemblance_score >= verdict.adherence_score + 1.5:
        return Strategy.EDIT, build_edit_instructions_for_adherence(verdict)

    # Both roughly equal and both need improvement → regenerate with full feedback
    if config.dual_strategy:
        return Strategy.DUAL, augment_prompt_with_feedback(config.prompt, verdict)
    else:
        return Strategy.REGENERATE, augment_prompt_with_feedback(config.prompt, verdict)
```

**Prompt augmentation** piggybacks the judge's feedback using ONLY positive instructions (Lesson #3):

```python
def augment_prompt_with_feedback(original_prompt: str, verdict: JudgeVerdict) -> str:
    """Lesson #3: Only positive biometric blueprinting, never negative constraints."""
    return (
        f"{original_prompt}\n\n"
        f"CRITICAL REQUIREMENTS BASED ON PREVIOUS ATTEMPT:\n"
        f"- Resemblance area to improve: {verdict.resemblance_rationale}\n"
        f"- Scene adherence area to improve: {verdict.adherence_rationale}\n"
        f"- Specific improvement needed: {verdict.improvement_suggestion}\n"
        f"- The person MUST match the reference photographs exactly — "
        f"same bone structure, eye color, nose shape, hair texture, skin tone.\n"
        f"- The image MUST be a photorealistic photograph (authentic skin texture "
        f"with visible pores, 85mm lens, natural lighting, camera-like depth of field)."
    )
```

When `--dual-strategy` is active and `Strategy.DUAL` is chosen, the engine generates BOTH an edit AND a regeneration, judges both, and picks the winner for the next iteration.

---

### Component 5: Score Overlay (`lib/overlay.py`)

#### [NEW] [`lib/overlay.py`](file:///usr/local/google/home/ricc/git/portr8/lib/overlay.py)

Creates a scored version of each image with an overlay banner. Reuses the exact Pillow+FFmpeg pattern from [`eval_single_model.py`](file:///usr/local/google/home/ricc/git/gemini-tools/bin/eval_single_model.py#L82-L129) (Lesson #9).

**Banner content:**
```
┌─────────────────────────────┐
│ portr8 #3/10                │
│ 👤 resemblance: 6.0/10     │
│ 🎯 adherence:   7.5/10     │
│ 📷 photorealistic: ✅       │
│ verdict: BUONO              │
└─────────────────────────────┘
```

**Function:** `create_scored_image(image_path, verdict, iteration, max_iter, output_path)`

1. Create transparent banner PNG with Pillow (`ImageDraw.Draw`) — semi-transparent black background (alpha 195)
2. Composite with FFmpeg: `ffmpeg -y -i input.png -i banner.png -filter_complex "[0:v][1:v]overlay=(W-w)/2:H-h-30"`
3. Fall back to pure Pillow `Image.alpha_composite()` if FFmpeg unavailable

---

### Component 6: Iteration Ledger (`lib/ledger.py`)

#### [NEW] [`lib/ledger.py`](file:///usr/local/google/home/ricc/git/portr8/lib/ledger.py)

JSONL-based append-only log tracking every iteration (Lesson #10, #13).

```python
class Ledger:
    def __init__(self, run_dir: Path): ...
    def append(self, record: IterationRecord): ...
    def load_all(self) -> list[IterationRecord]: ...
    def best_so_far(self) -> IterationRecord | None:
        """Returns the record with highest min(resemblance, adherence)."""
    def apply_human_override(self, iteration: int, overrides: dict): ...
```

Each run gets its own directory: `out/<run-id>/` where `run-id` is `YYYY-MM-DD-HH-MM-<prompt-slug>`.

**JSONL format** compatible with gemini-tools' `evaluations.jsonl` pattern (Lesson #13):
```json
{
  "iteration": 3,
  "run_id": "2026-08-25-11-30-riccardo-eats-ice-cream",
  "strategy_used": "regenerate",
  "original_prompt": "Riccardo eats an ice cream...",
  "augmented_prompt": "Riccardo eats an ice cream... CRITICAL REQUIREMENTS...",
  "image_path": "~/git/portr8/out/.../image_003.png",
  "seed": 1234567890,
  "resemblance_score": 6.0,
  "adherence_score": 7.5,
  "is_photorealistic": true,
  "verdict": "BUONO",
  "reference_transport": "files_api",
  "robot_eval": { ... },
  "human_eval": null,
  "status": "PENDING_HUMAN",
  "elapsed_seconds": 42.3,
  "timestamp": "2026-08-25T11:30:42Z"
}
```

---

### Component 7: Report Generator (`lib/reporter.py`)

#### [NEW] [`lib/reporter.py`](file:///usr/local/google/home/ricc/git/portr8/lib/reporter.py)

Generates a Markdown + HTML slide deck from the ledger.

**Report contents:**
1. **Header**: Run configuration, prompt, character, models used
2. **Convergence chart** (ASCII/text): Shows scores over iterations
   ```
   Iteration  Resemblance  Adherence  Photo?  Verdict
   ─────────  ───────────  ─────────  ──────  ─────────
   1          4.0          7.0        ✅      COSÌ-COSÌ
   2          5.5          6.5        ✅      COSÌ-COSÌ
   3          6.0          7.5        ✅      BUONO
   4          5.0 ↓        8.0        ✅      COSÌ-COSÌ   ← score went DOWN
   5          7.5          8.0        ✅      BUONO
   6          8.2          8.5        ✅      CAPOLAVORO 🏆
   ```
3. **Image gallery**: All iterations with their scored overlay images
4. **Strategy log**: Which strategy was used per iteration and why
5. **Best result**: Highlighted with 🏆
6. **Human overrides**: Section showing any calibration corrections
7. **Footer**: Total time, API calls made, final verdict

The HTML version embeds images as base64 for a self-contained portable slide deck.

---

### Component 8: Main CLI (`bin/portr8.py`)

#### [NEW] [`bin/portr8.py`](file:///usr/local/google/home/ricc/git/portr8/bin/portr8.py)

The main orchestrator. PEP 723 uv-runnable script.

**Usage:**
```bash
# Basic run (will run undisturbed for ~10 min)
./bin/portr8.py -p "Riccardo eats an ice cream in the savannah surrounded by lions, photorealistic" \
  -c riccardo --max-iterations 10

# With dual strategy and custom models
./bin/portr8.py -p "Riccardo surfing in Hawaii" -c riccardo \
  --image-model gemini-3.1-flash-image-preview \
  --judge-model gemini-3.5-flash \
  --max-iterations 15 \
  --dual-strategy

# With external ref directory and GCS transport
./bin/portr8.py -p "Kate at a cafe in Paris" -c kate \
  --ref-dir ~/git/gemini-tools/data/characters \
  --ref-transport gcs
```

**CLI Parameters:**

| Flag | Type | Default | Description |
|:---|:---|:---|:---|
| `-p`, `--prompt` | `str` | **required** | Scene description |
| `-c`, `--character` | `str` | **required** | Character name (loads refs from `data/characters/<name>/`) |
| `--max-iterations` | `int` | `10` | Maximum loop iterations |
| `--target-score` | `float` | `8.0` | Min score on BOTH axes to declare success |
| `--image-model` | `str` | `gemini-3.1-flash-image-preview` | Model for image generation |
| `--judge-model` | `str` | `gemini-3.5-flash` | Model for judging (Lesson #12) |
| `--ref-dir` | `str` | `data/characters` | Base directory for character reference photos |
| `--ref-transport` | `str` | `files_api` | Reference transport: `files_api`, `pil`, `gcs` (Lesson #1) |
| `--dual-strategy` | `flag` | `false` | Try both edit AND regenerate each iteration |
| `--seed` | `int` | random | Random seed for reproducibility (Lesson #8) |
| `--open` | `flag` | `false` | Auto-open each generated image |
| `-o`, `--output-dir` | `str` | `out/` | Base output directory |

**Main loop pseudocode:**

```python
def main_loop(config: RunConfig):
    run_id = generate_run_id(config.prompt)
    run_dir = Path(config.output_dir) / run_id
    ledger = Ledger(run_dir)
    ref_images = resolve_character_refs(config.character, config.ref_dir)

    # Lesson #4: Always append photorealism suffix
    current_prompt = config.prompt + PHOTOREALISM_SUFFIX
    previous_image = None
    strategy = Strategy.REGENERATE  # First iteration always regenerates

    console.print(Panel.fit(
        f"🎯 portr8 — Target: {config.target_score}/10 on BOTH axes\n"
        f"👤 Character: {config.character}\n"
        f"📷 Image model: {config.image_model}\n"
        f"⚖️ Judge model: {config.judge_model}\n"
        f"🔄 Max iterations: {config.max_iterations}\n"
        f"📡 Reference transport: {config.ref_transport}",
        title="🚀 CONVERGENCE ENGINE STARTING"
    ))

    for i in range(1, config.max_iterations + 1):
        t0 = time.time()
        seed = config.seed or random.randint(1, 2147483647)  # Lesson #8

        # 1. GENERATE
        if strategy == Strategy.REGENERATE or i == 1:
            image_path = generate_from_prompt(
                current_prompt, ref_images, config.image_model,
                run_dir / f"image_{i:03d}.png", seed, config.ref_transport
            )
        elif strategy == Strategy.EDIT:
            image_path = edit_image(
                previous_image, edit_instructions, ref_images,
                config.image_model, run_dir / f"image_{i:03d}.png",
                seed, config.ref_transport
            )
        elif strategy == Strategy.DUAL:
            # Try both, judge both, pick winner
            img_regen = generate_from_prompt(...)
            img_edit = edit_image(...)
            verdict_regen = judge_image(img_regen, ...)
            verdict_edit = judge_image(img_edit, ...)
            image_path, verdict = pick_better(...)

        # 2. JUDGE
        if strategy != Strategy.DUAL:
            verdict = judge_image(image_path, ref_images, config.prompt, config.judge_model)

        # 3. OVERLAY SCORES (Lesson #9)
        scored_path = create_scored_image(
            image_path, verdict, i, config.max_iterations,
            run_dir / f"image_{i:03d}_scored.png"
        )

        # 4. LOG (Lesson #10)
        record = IterationRecord(
            iteration=i, seed=seed,
            original_prompt=config.prompt,
            augmented_prompt=current_prompt,
            reference_transport=config.ref_transport,
            ..., elapsed_seconds=time.time()-t0
        )
        ledger.append(record)

        # 5. PRINT STATUS (Lesson #11: same Rich style as find_golden_kate)
        color = "green" if min(verdict.resemblance_score, verdict.adherence_score) >= config.target_score \
                else ("yellow" if min(...) >= 6.0 else "red")
        console.print(f"🏆 Iteration {i}: [{color}]R:{verdict.resemblance_score:.1f} A:{verdict.adherence_score:.1f}[/{color}] | {verdict.verdict}")

        # 6. CHECK CONVERGENCE
        if (verdict.resemblance_score >= config.target_score and
            verdict.adherence_score >= config.target_score and
            verdict.is_photorealistic):
            console.print(Panel.fit(
                f"🎉 CONVERGENCE REACHED at iteration {i}!\n"
                f"👤 Resemblance: {verdict.resemblance_score}/10\n"
                f"🎯 Adherence: {verdict.adherence_score}/10\n"
                f"📁 Image: {image_path}\n"
                f"🔔 WAKING UP RICCARDO!",
                title="🏆 CAPOLAVORO! TARGET ≥ 8.0 SUPERATO"
            ))
            break

        # 7. DECIDE NEXT STRATEGY (Lessons #3, #4)
        strategy, current_prompt = decide_strategy(verdict, i, config)
        previous_image = image_path

    # 8. GENERATE REPORT
    generate_report(ledger, run_dir)
    best = ledger.best_so_far()
    console.print(f"\n📊 Report: {run_dir}/report.html")
    console.print(f"🏆 Best result: iteration {best.iteration} — R:{best.resemblance_score:.1f} A:{best.adherence_score:.1f}")
```

---

### Component 9: Rater Calibration (`bin/calibrate.py`)

#### [NEW] [`bin/calibrate.py`](file:///usr/local/google/home/ricc/git/portr8/bin/calibrate.py)

A separate tool for calibrating the AI judge against human ratings (Lesson #2).

**Workflow:**
1. Takes N pre-generated images (or generates fresh ones)
2. Has M judge models rate each image (default: `gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3.1-pro-preview`, `gemini-2.5-pro`, `gemini-2.5-flash`)
3. Presents each image to the human for manual scoring via terminal input
4. Produces a **calibration matrix** with Pearson correlation per model
5. Recommends the best judge model (highest correlation with human ratings)
6. Flags known miscalibration patterns (Lesson #2: kate_lion.png = 7.0 AI vs 1.0 human)

**Usage:**
```bash
# Generate 5 test images and calibrate 5 judge models
./bin/calibrate.py -c riccardo -p "Riccardo at a cafe in Rome" --num-images 5

# Calibrate on existing images from a previous run
./bin/calibrate.py --images-dir out/2026-08-25-11-30-riccardo/ -c riccardo
```

**Output (calibration matrix):**

```
┌────────────┬───────────┬──────────────────┬──────────────────┬──────────┐
│ Image      │ Human     │ gemini-3.5-flash │ gemini-3.1-pro   │ Δ (best) │
├────────────┼───────────┼──────────────────┼──────────────────┼──────────┤
│ image_001  │ R:7 A:8   │ R:6.5 A:7.0      │ R:7.2 A:8.1      │ pro ✅   │
│ image_002  │ R:4 A:9   │ R:5.0 A:8.5      │ R:3.8 A:9.0      │ pro ✅   │
│ image_003  │ R:8 A:6   │ R:8.2 A:5.5      │ R:7.5 A:6.5      │ flash ✅ │
├────────────┼───────────┼──────────────────┼──────────────────┼──────────┤
│ Correlation│ —         │ 0.85             │ 0.92             │ pro 👑   │
└────────────┴───────────┴──────────────────┴──────────────────┴──────────┘
```

---

### Component 10: Human Override Mechanism

#### Integrated into [`bin/portr8.py`](file:///usr/local/google/home/ricc/git/portr8/bin/portr8.py) and [`lib/ledger.py`](file:///usr/local/google/home/ricc/git/portr8/lib/ledger.py)

After a run completes (or during, if interrupted), Riccardo can override any AI score:

```bash
# Override scores for iteration 3
./bin/portr8.py override --run-id 2026-08-25-11-30-riccardo-eats-ice-cream \
  --iteration 3 --resemblance 5.0 --adherence 8.0 --note "Face is too smooth, AI beautification"

# Re-generate report with human corrections
./bin/report.py --run-id 2026-08-25-11-30-riccardo-eats-ice-cream
```

This patches the ledger JSONL with a `human_override` field (compatible with gemini-tools' `human_eval` pattern, Lesson #13).

---

### Component 11: Justfile

#### [NEW] [`Justfile`](file:///usr/local/google/home/ricc/git/portr8/Justfile)

```just
# Default: list tasks
list:
    @just --list

# Run the main portr8 convergence loop
run prompt character="riccardo" max_iter="10":
    ./bin/portr8.py -p "{{prompt}}" -c {{character}} --max-iterations {{max_iter}}

# Run with dual strategy (edit + regenerate)
run-dual prompt character="riccardo":
    ./bin/portr8.py -p "{{prompt}}" -c {{character}} --dual-strategy

# Quick demo run (3 iterations)
demo:
    ./bin/portr8.py -p "Riccardo eats an ice cream in the savannah surrounded by lions, photorealistic" -c riccardo --max-iterations 3

# Calibrate the AI judge against human ratings
calibrate character="riccardo":
    ./bin/calibrate.py -c {{character}} -p "Test portrait of {{character}} at a cafe" --num-images 5

# Check reference photo quality for a character
check-refs character="riccardo":
    @echo "🔬 Checking reference photos for {{character}}..."
    @ls -la data/characters/{{character}}/

# Generate report from existing run
report run-id:
    ./bin/report.py --run-id {{run-id}}

# Override a score
override run-id iteration resemblance adherence note="manual correction":
    ./bin/portr8.py override --run-id {{run-id}} --iteration {{iteration}} --resemblance {{resemblance}} --adherence {{adherence}} --note "{{note}}"

# Run tests
test:
    uv run python -m pytest tests/ -v

# Install dependencies
install:
    uv sync

# Show latest run status
status:
    @echo "📁 Recent runs:"
    @ls -lt out/ | head -10
```

---

### Component 12: Configuration & Environment

#### [NEW] `.env.dist`
```bash
# Required: Google GenAI API key
GEMINI_API_KEY=your-api-key-here

# Optional: default image generation model
PORTR8_IMAGE_MODEL=gemini-3.1-flash-image-preview

# Optional: default judge model (Lesson #12: gemini-3.5-flash is proven)
PORTR8_JUDGE_MODEL=gemini-3.5-flash

# Optional: default target score (Lesson #5: 8.0 = CAPOLAVORO threshold)
PORTR8_TARGET_SCORE=8.0

# Optional: default max iterations
PORTR8_MAX_ITERATIONS=10

# Optional: reference transport method (Lesson #1: files_api > pil > gcs)
PORTR8_REF_TRANSPORT=files_api
```

#### [NEW] `pyproject.toml`
```toml
[project]
name = "portr8"
version = "0.1.0"
description = "Iterative character-consistent portrait convergence engine — converges to ≥8/10"
requires-python = ">=3.11"
dependencies = [
    "google-genai>=1.0.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "pillow>=10.0.0",
    "python-slugify>=8.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["lib"]

[tool.uv]
index-url = "https://pypi.org/simple"
```

---

## Implementation Order (Task Breakdown)

### Phase 1: Foundation (Tasks 1-3)
1. **Project Scaffolding**: Create directory structure, git init, pyproject.toml, Justfile, .env.dist, .gitignore, README.md, VERSION, CHANGELOG.md, GEMINI.md. Symlink `data/characters/`.
2. **Data Models** (`lib/models.py`): All Pydantic models. Tests for serialization.
3. **Ledger** (`lib/ledger.py`): JSONL append/read/query/override. Tests.

### Phase 2: Core Pipeline (Tasks 4-6)
4. **Image Generator** (`lib/generator.py`): `generate_from_prompt()`, `edit_image()`, `resolve_character_refs()`, reference transport. Tests with mocked API.
5. **Dual-Axis Judge** (`lib/judge.py`): `judge_image()` with anti-beautification prompt. Tests.
6. **Strategy Engine** (`lib/strategist.py`): `decide_strategy()`, prompt augmentation (positive only!). Tests.

### Phase 3: Polish (Tasks 7-9)
7. **Score Overlay** (`lib/overlay.py`): Banner creation + FFmpeg composite. Tests.
8. **Main CLI Loop** (`bin/portr8.py`): Wire everything together. Rich console output. End-to-end smoke test.
9. **Report Generator** (`lib/reporter.py` + `bin/report.py`): Markdown + HTML. Tests.

### Phase 4: Advanced (Tasks 10-11)
10. **Rater Calibration** (`bin/calibrate.py`): Multi-model comparison, human input, correlation matrix.
11. **Human Override** (`bin/portr8.py override`): Score patching, report regeneration.

---

## Verification Plan

### Automated Tests
```bash
uv run python -m pytest tests/ -v
```

### Manual Verification
1. **Smoke test**: `just demo` (3 iterations) — verify images generated, scored, logged, report produced
2. **Convergence test**: Full 10 iterations — verify early stop when 8/8 reached
3. **Dual strategy test**: `--dual-strategy` — verify both paths tried
4. **Calibration test**: `just calibrate` — verify matrix output
5. **Override test**: Override a score and regenerate report
6. **Report test**: Open HTML slide deck in browser — verify self-contained

### Expected Runtime
- Each iteration: ~30-60s (generation ~15-30s + judging ~5-10s + overlay ~2s)
- 10 iterations: ~5-10 minutes (the "10min undisturbed" target 🎯)
- Dual strategy: ~2x generation time per iteration
- Calibration (5 images × 5 models): ~10-15 minutes
