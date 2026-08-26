# Technology Stack: portr8

## 1. Core Architecture
- **Language & Runtime**: Python 3.11+ (executed on Python 3.13 via `uv`)
- **Package & Dependency Management**: `uv` with PEP 723 inline script headers and standard `pyproject.toml`
- **Build Backend**: `hatchling`

## 2. Generative AI & Multimodal SDK
- **Primary SDK**: `google-genai` (Gemini SDK)
- **Reference Transport**: Gemini Files API (`client.files.upload()`) as primary to preserve micro-biometrics; PIL/base64 fallback.
- **Image Generation Models**:
  - `gemini-2.5-flash-image` (default fast iteration model)
  - `gemini-3.1-flash-image-preview` (high fidelity preview model)

## 3. Multi-Model Judge & Calibration Engine
- **Multi-Model Evaluators**:
  - `gemini-3.5-flash` (standard default judge, temperature 0.2)
  - `gemini-3.6-flash` (experimental)
  - `gemini-3.1-pro-preview` (high-capacity forensic judge)
  - `gemini-2.5-pro` / `gemini-2.5-flash` (comparative evaluation)
- **Automated Rater Calibration**:
  - `bin/calibrate.py`: Correlates multi-model judge verdicts against human ground-truth ratings on private reference datasets to detect and correct rater inflation/drift.
  - `bin/human_rate.py`: Terminal-based interactive rating tool to capture human ground-truth scores and ledger overrides.

## 4. Data Modeling & Processing
- **Schema Validation & Structured Output**: `pydantic` v2 (`JudgeVerdict`, `IterationRecord`, `RunConfig`, `RunSummary`)
- **Image Composition & Pill Overlays**: `Pillow` (PIL) + `FFmpeg`
- **Convergence Graphing**: `matplotlib` (multi-curve F1..Fn, S, A trajectory plots)
- **Serialization**: `pyyaml` (character profiles), `python-slugify`, JSON/JSONL (append-only ledgers)

## 5. Development, CI/CD & Operations
- **Task Runner**: `just` (`Justfile`)
- **Test Suite**: `pytest` (automated unit and integration tests)
- **Cloud Publishing**: `Storagify` syncing to Google Cloud Storage (`gs://palladius-genai-storagify/...`)
