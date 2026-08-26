# 🎯 portr8 — User Manual & Critical User Journeys (CUJs)

> **portr8** is an iterative, character-consistent portrait convergence engine powered by Google Gemini multimodal models.
> It generates photorealistic portraits of real people in diverse scenarios, scores them on three independent axes using an LLM judge, and iterates until the portrait converges to a masterpiece (**≥ 8.0/10**).

---

## 🏗️ Architecture & Philosophy

### 1. Complete vs Incomplete Pipeline

| Dimension | 🚫 Incomplete / One-Off Generation | 🎯 Complete portr8 Pipeline (`bin/portr8.py`) |
| :--- | :--- | :--- |
| **Generation** | Single-shot prompt call | Multi-iteration adaptive loop |
| **Evaluation** | None or ad-hoc visual check | Forensic 3-Axis LLM Judge (`gemini-3.5-flash`) |
| **Feedback Loop** | None | Directed prompt mutation based on judge rationales |
| **Visual Output** | Raw PNG image | Raw PNG + Overlaid **`_scored.png`** banner |
| **Analytics** | None | **`convergence.png`** progression graph |
| **Provenance** | None | Append-only **`ledger.jsonl`** + **`summary.json`** |
| **Documentation** | None | Per-run **`README.md`** & **`index.md`** |
| **Cataloging** | Lost in temporary folders | Auto-indexed in global **`out/index.md`** & **`out/README.md`** |
| **Cloud Hosting** | Manual uploads | 1-click **`just storagify`** to Google Cloud Storage |

---

## ⚖️ The 3-Axis Scoring System

portr8 evaluates every generated image against authentic reference photos across three distinct dimensions:

1. **👤 Facial Identity (`facial_similarity`, 1.0–10.0)**:
   - Evaluates bone structure, nose bridge, eye shape, lip contour, skin texture, and distinctive facial traits.
   - **Anti-beautification guardrail**: Heavily penalizes AI smoothing/doll-face filters (caps at ≤ 5.0).
2. **👔 Scene Adaptation (`scene_adaptation`, 1.0–10.0)**:
   - Evaluates whether clothing, hair styling, accessories, and posture match the requested scene (e.g. swimsuit in Iceland, tuxedo in a gala), rather than cloning the reference photo outfit.
3. **🎯 Prompt Adherence (`adherence_score`, 1.0–10.0)**:
   - Evaluates environmental fidelity, background accuracy (e.g. Jökulsárlón glacier lagoon, icebergs), props (e.g. Aperol Spritz, snacks), and lighting.

### Italian Verdict Tiers:
- 🏆 **CAPOLAVORO** (Bottleneck score ≥ 8.0) — *Goal achieved, convergence reached!*
- 👍 **BUONO** (Bottleneck score 7.0–7.9) — *Promising, close to convergence.*
- 😐 **COSÌ-COSÌ** (Bottleneck score 5.0–6.9) — *Acceptable, requires targeted refinement.*
- 🤮 **SCHIFO** (Bottleneck score < 5.0) — *Unusable, triggers complete regeneration.*

---

## 🚀 Critical User Journeys (CUJs)

### 🎯 CUJ 1: Standard Portrait Convergence
**Goal**: Generate a character-consistent portrait and let the engine iterate until quality reaches ≥ 8.0.

```bash
# Run portrait convergence for Riccardo
uv run bin/portr8.py -p "Riccardo presenting at a tech conference keynote on stage with slides" -c riccardo

# With custom iteration limit and target
uv run bin/portr8.py -p "Riccardo cooking homemade pasta in an Italian kitchen" -c riccardo --max-iterations 5 --target 8.5
```

---

### 🍹 CUJ 2: Creative & Absurd Vacation / Roleplay Scenarios
**Goal**: Place characters into high-contrast, humorous, or imaginative environments while preserving biometric identity and authentic skin texture.

```bash
# Iceland Glacial Aperitivo
uv run bin/portr8.py -p "Riccardo having an Italian summer aperitivo in Iceland near Jokulsarlon glacial lagoon, comically wearing a tropical Hawaiian retro beach swimsuit and sunglasses, lounging in a deckchair with a cold glass of Aperol Spritz surrounded by icebergs" -c riccardo

# Cyberpunk Barista in Tokyo
uv run bin/portr8.py -p "Riccardo as a cyberpunk barista in futuristic Neo-Tokyo brewing espresso surrounded by neon holographic signs" -c riccardo
```

---

### 🧬 CUJ 3: Dual Strategy Exploration (Edit vs Regenerate)
**Goal**: Simultaneously evaluate whether editing the previous candidate or generating a fresh seed from scratch converges faster.

```bash
uv run bin/portr8.py -p "Riccardo hiking in the Swiss Alps during golden hour" -c riccardo --dual-strategy
```

---

### 🔬 CUJ 4: AI Rater Calibration (`bin/calibrate.py`)
**Goal**: Compare how different judge models (e.g. `gemini-3.5-flash`, `gemini-2.5-pro`) rate the same set of images and calibrate judging strictness.

```bash
uv run bin/calibrate.py --run-dir out/20260826-1506-riccardo-having-an-italian-summer-aperit
```

---

### 👤 CUJ 5: Human Rating Override & Alignment (`bin/human_rate.py`)
**Goal**: Interactively review an output folder, provide ground-truth human scores, and compute AI vs Human alignment metrics.

```bash
uv run bin/human_rate.py --run-dir out/20260826-1506-riccardo-having-an-italian-summer-aperit
```

---

### 🌐 CUJ 6: Cloud Publishing & Public Showcase (`just storagify`)
**Goal**: Build the global run catalog and sync all output folders, scored images, convergence graphs, and HTML pages to Google Cloud Storage.

```bash
# Update local index (out/index.md, out/README.md, out/index.csv, out/catalog.json)
just index

# Sync all runs and interactive galleries to GCS
just storagify
```

---

### 📁 CUJ 7: Character Onboarding & Reference Management
**Goal**: Add a new character to portr8 for consistent generation.

1. Create directory `data/characters/<character_name>/`
2. Add high-resolution reference photos (3–6 diverse angles, authentic lighting, no heavy filters)
3. (Optional) Add `data/characters/<character_name>/character.yaml`:
```yaml
name: "Riccardo"
age: 45
hair_color: "Brown"
eye_color: "Brown"
description: "Italian man with short brown hair, beard/stubble, warm cheerful smile."
```
4. (Optional) Provide cropped face close-ups in `data/characters/<character_name>/grid_cleaned/`.

---

## 📊 Artifacts Produced Per Run

Every completed run in `out/YYYYMMDD-HHMM-<slug>/` contains:
- `iter_01.png`, `iter_02.png` ...: Raw generated images.
- `iter_01_scored.png` ...: Images with score badge and verdict overlay.
- `convergence.png`: Visual progression graph of Facial, Scene, and Adherence scores.
- `ledger.jsonl`: Append-only JSONL recording prompt augmentations, seeds, models, and scores.
- `summary.json`: High-level summary of convergence status and best scores.
- `run_config.json`: Run parameters for 100% deterministic replay.
- `README.md` & `index.md`: Rich Markdown presentation ready for GitHub, Astro, and Storagify.

---

## 💡 Best Practices & Empirical Rules
1. **Always use Files API transport** (`--ref-transport files_api`): Yields ~8.2 human resemblance rating vs ~5.5 for inline base64.
2. **Never use negative constraints**: Do not say "no model skin" or "do not smooth". Always use positive biometric blueprints ("authentic skin pores, natural wrinkles").
3. **Photorealism is non-negotiable**: The judge strictly verifies `is_photorealistic=true` for photo runs.
4. **Keep `out/README.md` and `out/index.md` synchronized**: Ensures instant navigation both on Git remotes and on live HTTP storage buckets.
