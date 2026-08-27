# Specification: Track omega13-chimeric-fusion (P4)

## 1. Overview & Inspiration

The **Omega 13 Strategy** (inspired by the Galaxy Quest matter-rearranger device) solves the fundamental bottleneck of multi-character portrait convergence: **asymmetric probabilistic likeness**.

In multi-character runs (e.g. `-c kate2016,riccardo2016`), random sampling often generates an exceptional likeness for one character while missing the other:
- **Iteration 3**: Kate achieves $F_1 = 8.3 / 10$, but Riccardo is only $F_2 = 6.0 / 10$.
- **Iteration 7**: Riccardo achieves $F_2 = 8.5 / 10$, but Kate regresses to $F_1 = 6.2 / 10$.

Currently, `portr8` relies on single-image editing or blind regeneration, discarding past golden representations. Waiting for both faces to independently hit $\ge 8.0$ in a single forward pass can require 30+ iterations. 

The Omega 13 strategy rewinds time and fuses the best historical representations into a single coherent image.

---

## 2. Functional Requirements

### 2.1 Per-Character High-Water Mark Tracking
- `Ledger` must track the historical best score and iteration for each character:
  $$\text{best\_char\_records} = \{ C_k: (\text{iter}_m, \text{score}_m) \mid k \in [1..n] \}$$
- If an iteration sets a new personal best for Character $k$ with $F_k \ge 7.8$, it is tagged as a candidate for Omega 13.

### 2.2 Strategy Trigger Conditions in `lib/strategist.py`
The strategist triggers strategy `"omega13"` when:
1. **Multi-character run**: `len(characters) >= 2`.
2. **Complementary peaks exist**: Every character in the run has a prior iteration with $F_k \ge 7.8$ (or configured threshold), but no single iteration has achieved simultaneous convergence ($F_k \ge 8.0 \, \forall k$).
3. **Patience threshold**: The run has progressed at least $N \ge 6$ iterations without full convergence.

### 2.3 Chimeric Multimodal Generation in `lib/generator.py`
- `generate_image` must accept a list of reference images for editing: `edit_source_images: list[Path]`.
- Both historical images (Image A for Character 1, Image B for Character 2) are passed to the Gemini image generation model.
- Augmented prompt constructs an explicit fusion blueprint:
  > *"Chimeric Portrait Fusion (Omega 13): Reconstruct the scene seamlessly by taking Character 1 ({char1_name}) from Image 1 and Character 2 ({char2_name}) from Image 2. Blend identical skin tones, unified ambient lighting, matching color temperature, and natural gaze alignment. Maintain authentic skin texture with visible pores."*

### 2.4 Provenance & Reporting
- Ledger and summary JSON mark `strategy: "omega13"`.
- Table and overlay pills display `omega13` as the generation strategy.
- Convergence graph annotates the Omega 13 fusion iteration.

---

## 3. Non-Functional Requirements & Safety
- **Anti-Frankenstein Guardrail**: The LLM judge evaluates facial similarity and photorealism; if seams or lighting mismatches occur, `scene_adaptation` or `photorealism` will reflect it.
- **Graceful Fallback**: If multi-image editing fails on the underlying model, fall back to standard `regenerate` or single-image `edit`.

---

## 4. Acceptance Criteria
- [ ] `lib/ledger.py` exposes `get_best_iterations_by_character()`.
- [ ] `lib/strategist.py` returns strategy `"omega13"` and augmented fusion prompt when complementary peaks exist.
- [ ] `lib/generator.py` supports multi-source image inputs for editing.
- [ ] Unit tests pass for single-char (no-op), multi-char trigger, and prompt generation.
