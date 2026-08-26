"""Tests for the Strategy Engine."""

import pytest
from lib.models import JudgeVerdict
from lib.strategist import decide_strategy, PHOTOREALISM_CUES, _augment_prompt

def make_verdict(r=5.0, a=5.0, photo=True, beautify=False):
    return JudgeVerdict(
        facial_similarity=r,
        scene_adaptation=7.0,
        adherence_score=a,
        is_photorealistic=photo,
        facial_similarity_rationale="test",
        scene_adaptation_rationale="Good scene match",
        adherence_rationale="test",
        anti_beautification_flag=beautify,
    )

def test_initial_iteration_regenerate():
    v = make_verdict()
    dec = decide_strategy(v, "Test prompt", 0)
    assert dec.strategy == "regenerate"

def test_anti_beautification_forces_regenerate():
    v = make_verdict(r=8.0, a=8.0, beautify=True)
    dec = decide_strategy(v, "Test prompt", 1)
    assert dec.strategy == "regenerate"

def test_low_resemblance_forces_regenerate():
    v = make_verdict(r=4.9, a=9.0)
    dec = decide_strategy(v, "Test prompt", 1)
    assert dec.strategy == "regenerate"

def test_low_adherence_forces_regenerate():
    v = make_verdict(r=9.0, a=4.9)
    dec = decide_strategy(v, "Test prompt", 1)
    assert dec.strategy == "regenerate"

def test_workable_scores_returns_edit():
    v = make_verdict(r=6.5, a=6.5)
    dec = decide_strategy(v, "Test prompt", 1)
    assert dec.strategy == "edit"

def test_multi_character_feedback_incorporation():
    v = JudgeVerdict(
        facial_similarity=4.5,
        scene_adaptation=7.5,
        adherence_score=8.0,
        is_photorealistic=True,
        facial_similarity_rationale="Kate has smoothed skin, Riccardo has wrong hair",
        scene_adaptation_rationale="Swimwear matches pool",
        adherence_rationale="Alps and pool present",
        character_facial_scores=[6.5, 4.5],
        character_facial_rationales=[
            "Kate has good smile but slightly smoothed skin",
            "Riccardo is missing his distinct jawline and has added thick beard",
        ],
    )
    dec = decide_strategy(v, "Kate and Riccardo in pool", 1, characters=["kate", "riccardo"])
    assert "CRITICAL FACIAL CORRECTIONS PER CHARACTER" in dec.augmented_prompt
    assert "Riccardo: Riccardo is missing his distinct jawline" in dec.augmented_prompt

def test_augmented_prompt_contains_photorealism():
    v = make_verdict(r=8.0, a=8.0)
    dec = decide_strategy(v, "Test prompt", 1)
    assert PHOTOREALISM_CUES in dec.augmented_prompt

def test_augmented_prompt_no_negative_words():
    v = make_verdict(r=4.0, a=4.0, beautify=True)
    dec = decide_strategy(v, "Test prompt", 1)
    negatives = ["DO NOT", "NO ", "NEVER", "don't", "avoid"]
    prompt_lower = dec.augmented_prompt.lower()
    for n in negatives:
        assert n.lower() not in prompt_lower

def test_augmented_prompt_resemblance_feedback():
    """When facial_similarity < target, the rationale should appear in the augmented prompt."""
    v = make_verdict(r=6.9, a=8.0)
    dec = decide_strategy(v, "Test prompt", 1, target_score=8.0)
    # Should include the specific rationale text, not a generic string
    assert "CRITICAL FACIAL CORRECTION" in dec.augmented_prompt
    assert "test" in dec.augmented_prompt  # the rationale text from make_verdict

    # Below 5.0 should also add the "exact photographic match" text
    v = make_verdict(r=4.9, a=8.0)
    dec = decide_strategy(v, "Test prompt", 1, target_score=8.0)
    assert "CRITICAL FACIAL CORRECTION" in dec.augmented_prompt
    assert "exact photographic match" in dec.augmented_prompt

def test_high_scores_minimal_augmentation():
    """When all scores exceed the target, only original prompt + style cues should appear."""
    v = JudgeVerdict(
        facial_similarity=9.0,
        scene_adaptation=9.0,
        adherence_score=9.0,
        is_photorealistic=True,
        facial_similarity_rationale="Perfect match",
        scene_adaptation_rationale="Perfect scene",
        adherence_rationale="Perfect adherence",
    )
    dec = decide_strategy(v, "Test prompt", 1, target_score=8.0)
    # No CORRECTION directives should appear when all scores are above target
    assert "CORRECTION" not in dec.augmented_prompt
    # But style cues should always be present
    assert PHOTOREALISM_CUES in dec.augmented_prompt

