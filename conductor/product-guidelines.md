# Product Guidelines: portr8

## 1. Brand & Voice
- **Tone**: Pragmatic, empirical, transparent, and developer-centric.
- **Evaluation Standards**: Clean numeric thresholds with 3-color status:
  - **≥ 8.0 (Green)**: Good / Converged
  - **6.0 – 7.9 (Yellow)**: Mediocre / Workable
  - **0.0 – 5.9 (Red)**: Bad / Unacceptable
- **Demonstration Philosophy**: "Show, don't tell" — always present tangible visual artifacts (scored images with pills, convergence plots, HTML decks) over dry textual summaries.

## 2. Visual & UI Principles
- **Minimalist Pill Overlays**:
  - Top-Left pill: `#N` (iteration index).
  - Bottom-Right pill: `MEDIA` score (e.g. `7.3`).
  - Warm bright yellow text (`#FFE000` / `RGB 255, 224, 0`) with dark translucent pill backing (`rgba(0,0,0,0.65)`) for optimal contrast against light and dark scenes.
- **De-cluttered Graphs**: Multi-curve convergence plots (`convergence.png`) showing metric trajectories with soft background bands and no text clutter.
- **Self-Contained Slide Decks**: Generated HTML reports (`index.html`) embed images and stylesheets for zero-dependency portability and GCS cloud sync via Storagify.

## 3. Human-in-the-Loop & Multi-Model Rater Calibration
- **Multi-Model Judge Benchmarking**: Foresee and evaluate multiple rater models (`gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3.1-pro-preview`, etc.) using automated calibration (`bin/calibrate.py`).
- **Private Ground-Truth Calibration**: Calibrate raters using private reference photos (strictly kept outside of version control in `data/characters/`) to prevent score inflation and align AI judges with human perception.
- **Human Overrides**: Support explicit human scoring corrections (`bin/human_rate.py` and ledger overrides) to establish golden benchmark sets.

## 4. Engineering & Prompt Guidelines
- **Positive Biometric Blueprinting**: Never inject negative constraints (e.g. "no model skin", "do not smooth"); always blueprint positive authentic attributes ("authentic skin texture with visible pores, natural wrinkles").
- **Strict Photorealism**: Enforce authentic photographic cues (85mm portrait lens, natural lighting) and penalize AI beautification or doll-face smoothing.
- **Testing Iteration Floor**: Enforce a minimum of 5 iterations ($N \ge 5$, default 10) in experimentation to ensure feedback loop convergence and prevent premature evaluation.
