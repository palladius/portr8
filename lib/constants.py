"""portr8 constants — model lists, defaults, and calibration config.

Central place for all model names and calibration parameters.
Updated: 2026-08-27 based on multi-model calibration experiments.
"""

# ─────────────────────────────────────────────────────────────────────
# Judge Models
# ─────────────────────────────────────────────────────────────────────

# Default judge model — empirically best discrimination (see calibration results)
DEFAULT_JUDGE_MODEL = "gemini-3.5-flash"

# Recommended judge model — ONLY model that correctly rejects cross-gender
# in our multi-character calibration (Riccardo→Kate = 4.0, not 7.5!)
# More expensive per call but converges faster → cheaper overall.
RECOMMENDED_JUDGE_MODEL = "gemini-3.1-pro-preview"

# All text models suitable for judging (support multi-image + structured JSON)
# Ordered by calibration spread (best discrimination first).
# Calibration date: 2026-08-26, characters: Kate, Kate2016, Riccardo
JUDGE_MODELS_CALIBRATED = [
    "gemini-3.1-pro-preview",    # 🏅 BEST discrimination: Ricc→Kate=4.0, Kate2016→Ricc=3.0
    "gemini-3.5-flash",          # ★  Current default. Spread ~3.5 but zero cross-gender rejection
    "gemini-3.7-flash",          #    Newest flash, prone to 503 errors (2026-08-26)
    "gemini-3.6-flash",          #    User requested — mid-gen flash
    "gemini-3.1-flash-lite",     #    Gives 8.5 to EVERYTHING — zero discrimination
    "gemini-pro-latest",         #    Alias — decent spread=4.0
    "gemini-flash-latest",       #    Alias — resolves to latest flash
    "gemini-flash-lite-latest",  #    Alias — resolves to latest flash-lite
]

# Image-generation models — NEVER use as judges! They give 9.5 to strangers.
IMAGE_MODELS_BLIND = [
    "gemini-3.1-flash-image",      # 💀 Spread=0.0, gives 9.5 to everything
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image",          # 💀 Spread=0.7, nearly blind
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-lite-image",
    "gemini-2.5-flash-image",
]

# Models that DON'T support multi-image structured JSON output
MODELS_INCOMPATIBLE = [
    "gemini-omni-flash-preview",   # ❌ 400 INVALID_ARGUMENT on multi-image
]

# ─────────────────────────────────────────────────────────────────────
# Image Generation Models
# ─────────────────────────────────────────────────────────────────────

DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image-preview"

IMAGE_MODELS = [
    "gemini-3.1-flash-image-preview",  # Default — good quality, fast
    "gemini-3.1-flash-image",
    "gemini-3-pro-image-preview",      # Pro quality
    "gemini-3-pro-image",
    "gemini-2.5-flash-image",          # Older gen
]

# ─────────────────────────────────────────────────────────────────────
# Calibration Config
# ─────────────────────────────────────────────────────────────────────

# Models to use in calibration benchmark runs (bin/calibration/*.py)
CALIBRATION_MODELS = [
    "gemini-3.1-pro-preview",    # 🏅 Best discrimination
    "gemini-3.5-flash",          # ★  Current default
    "gemini-3.7-flash",          #    Newest flash
    "gemini-3.6-flash",          #    Mid-gen flash (user requested)
    "gemini-3.1-flash-lite",     #    Lite — generous but blind
    "gemini-pro-latest",         #    Alias
    "gemini-flash-latest",       #    Alias — test what "latest" resolves to
]

# Calibration score expectations (used as regression test thresholds)
CALIBRATION_THRESHOLDS = {
    "self_recognition_min": 8.0,   # Kate-vs-Kate, Ricc-vs-Ricc should score ≥ this
    "wrong_person_max": 2.0,       # Wrong person should score ≤ this
    "cross_gender_max": 3.0,       # Man judged against woman refs should score ≤ this
    "same_person_aging_min": 6.0,  # Kate-vs-Kate2016 (same person, 10yr gap) should score ≥ this
    "min_spread": 6.0,             # self_avg - worst_wrong should be ≥ this
}

# Characters used for calibration
CALIBRATION_CHARACTERS = ["kate", "kate2016", "riccardo"]

# ─────────────────────────────────────────────────────────────────────
# Sigmoid Remap Parameters (stretch compressed [3,8] → [0,10])
# ─────────────────────────────────────────────────────────────────────

SIGMOID_REMAP_CENTER = 5.5       # Score treated as midpoint
SIGMOID_REMAP_STEEPNESS = 1.5    # Higher = more aggressive stretch
