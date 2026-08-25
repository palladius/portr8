# 🎯 Reference Overfitting — Split Resemblance into Identity + Adaptation

> **Status**: PLANNED (Option 3 = primary, Option 2 = fallback)
> **Created**: 2026-08-25
> **Priority**: HIGH — directly impacts image quality

## Problem

The AI model copies **everything** from reference photos — not just the person's face,
but also their clothing, pose, accessories, and sometimes background elements.

Example: if Riccardo's reference photos show him in a blue tourist t-shirt,
EVERY generated image will have that same t-shirt, even when the prompt says
"chef in a Tuscan kitchen" or "giving a keynote at Google I/O".

This is **reference overfitting** — the model conflates "look like this person"
with "reproduce this entire image".

## Root Cause

The current `resemblance_score` (0-10) is a vague "looks like them" metric that
rewards matching clothing/pose/accessories in addition to facial identity.
A generated image that copies the t-shirt gets a HIGHER resemblance score,
reinforcing the behavior.

---

## Option 3: Split Resemblance (PRIMARY — implement first)

### New Model

Replace `resemblance_score` with two axes:

```python
# JudgeVerdict (v0.4)
facial_similarity: float     # 0-10, FACE ONLY: shape, skin, hair, glasses, facial hair
scene_adaptation: float      # 0-10, clothing/pose/setting match the PROMPT (not refs)
facial_similarity_rationale: str
scene_adaptation_rationale: str
```

### Judge Prompt Changes

The judge must be told:

> **Facial Similarity** (0-10): Does this person look like the same person in the
> reference photos? Score based ONLY on: face shape, skin tone, hair color/style,
> facial hair, glasses, age, body build. Do NOT score higher for matching clothing,
> accessories, or pose.
>
> **Scene Adaptation** (0-10): Is the person dressed and posed appropriately for
> the scene described in the prompt? Score LOWER if they're wearing the same outfit
> as the reference photos when the scene calls for different clothing.
> Score HIGHER if their clothing, pose, and accessories match the scene context.

### Convergence Logic

```python
converged = (
    facial_similarity >= target_score
    AND adherence >= target_score
    AND scene_adaptation >= 5.0  # soft floor, not hard target
)
```

### Strategist Changes

When `scene_adaptation < 5.0`:
- Force REGENERATE (not edit — editing preserves the outfit)
- Add to prompt: "The person should wear clothing appropriate for [scene], 
  NOT the outfit from reference photos. Use reference photos for FACIAL IDENTITY ONLY."

When `scene_adaptation >= 5.0 but < 7.0`:
- Allow EDIT but add scene-appropriate clothing hints

### Overlay Changes

Banner becomes: `Iter 1 | F:7.5 A:7.8 S:6.0 | BUONO | Photo:YES`

### Graph Changes

Add third line (orange) for scene_adaptation.

### Breaking Changes

- `resemblance_score` → `facial_similarity` everywhere
- `resemblance_rationale` → `facial_similarity_rationale`  
- New field `scene_adaptation` + `scene_adaptation_rationale`
- `RunSummary.best_resemblance` → `best_facial_similarity`
- All existing `summary.json` in out/ become legacy (gitignored, no problem)
- ~15-20 tests to update
- Verdict labels: min(facial_similarity, adherence) for label, but scene_adaptation
  must be >= 5.0 floor

### Risks

- The LLM judge might struggle to separate facial identity from clothing —
  these are intertwined in "character consistency" by design
- scene_adaptation might be too strict — a "tourist in Rome" prompt legitimately
  matches a tourist t-shirt from reference photos
- Three axes are harder to visualize and explain than two

---

## Option 2: Reference Leakage Flag (FALLBACK — use if Option 3 fails)

### Design

Keep `resemblance_score` as-is but add a boolean flag:

```python
# JudgeVerdict (v0.4-alt)
reference_leakage: bool     # True if non-identity elements copied from refs
reference_leakage_rationale: str
```

### Judge Prompt

> **Reference Leakage**: Does the generated image copy specific non-identity
> elements (clothing, accessories, specific poses, background elements) from the
> reference photos that are NOT appropriate for the scene described in the prompt?

### Strategist

When `reference_leakage == True`:
- Force REGENERATE (like anti_beautification)
- Add guidance: "Use reference photos for facial identity only. 
  Clothing and accessories should match the scene description."

### Pros vs Option 3

- ✅ Simpler — one boolean, not a new score axis
- ✅ Less test breakage (~5 tests vs ~20)
- ✅ Faster to implement
- ❌ `resemblance_score` stays polluted (rewards clothing match)
- ❌ Binary flag loses nuance (how MUCH leakage?)
- ❌ Doesn't help the judge learn what "resemblance" actually means

---

## Option 1: Negative Prompt (REJECTED)

Hardcoding "don't copy the t-shirt" or similar negative prompts.
Fragile, doesn't scale, doesn't fix the judge. Jerry-work.

---

## Decision Log

| Date | Decision |
|:---|:---|
| 2026-08-25 | Riccardo approves Option 3 as primary, Option 2 as fallback |
