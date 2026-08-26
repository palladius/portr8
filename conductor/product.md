# Product Definition: portr8

## 1. Vision & Overview
**portr8** is an iterative character-consistent portrait and scene convergence engine. It generates photorealistic images of single or multiple real individuals using Google GenAI models, evaluates them with an unsparing multi-axis LLM judge measuring facial likeness (F1..Fn), scene adaptation (S), and prompt adherence (A), and **piggybacks specific qualitative feedback from the previous iteration into the next prompt generation**, creating a closed-loop semantic feedback engine that converges until all quality metrics hit ≥ 8.0/10.

## 2. Target Audience
- **DevRel & AI Engineers**: Developers and researchers exploring multi-turn visual prompt refinement, character consistency across complex environments, and LLM-as-a-judge steering.
- **Creative Builders**: Creators producing consistent character stories, historical/vintage scenes, and high-fidelity photorealistic multi-character media.

## 3. Core Differentiators
1. **The Powerful Semantic Feedback Loop**: Qualitative rationales from iteration N-1 are synthesized into positive biometric blueprints and actionable directives for iteration N.
2. **Files API Reference Transport**: Uploading uncompressed full-resolution references via Gemini Files API preserves micro-biometrics and prevents artificial doll-face AI smoothing.
3. **Multi-Character Independent Biometrics (F1, F2, ...)**: Each individual is scored independently to prevent bottleneck regressions where one subject degrades while another improves.
4. **Authoritative character.yaml Ingestion**: Physical definitions (hair, clean-shaven rules, wardrobe anchors) are automatically parsed from character vaults into generation and judging prompts.

## 4. Key Success Metrics
- **Convergence Rate**: Reaching ≥ 8.0/10 across all facial scores (F1..Fn), scene adaptation (S), and prompt adherence (A).
- **Anti-Beautification & Photorealism**: Enforcing authentic skin textures, natural lighting, and visible pores over plastic AI smoothing.
- **Reproducibility & Observability**: Complete JSONL provenance, multi-curve convergence plots (`convergence.png`), floating score pill overlays, and cloud reporting via Storagify.
