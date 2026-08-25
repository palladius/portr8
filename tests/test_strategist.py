"""Tests for the Strategy Engine."""

import pytest
from lib.models import JudgeVerdict
from lib.strategist import decide_strategy, PHOTOREALISM_CUES, _augment_prompt

def make_verdict(r=5.0, a=5.0, photo=True, beautify=False):
    return JudgeVerdict(
        resemblance_score=r,
        adherence_score=a,
        is_photorealistic=photo,
        resemblance_rationale="test",
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
    v = make_verdict(r=5.0, a=5.0)
    dec = decide_strategy(v, "Test prompt", 1)
    assert dec.strategy == "edit"

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
    v = make_verdict(r=6.9, a=8.0)
    dec = decide_strategy(v, "Test prompt", 1)
    assert "facial bone structure" in dec.augmented_prompt
    assert "exact photographic match" not in dec.augmented_prompt

    v = make_verdict(r=4.9, a=8.0)
    dec = decide_strategy(v, "Test prompt", 1)
    assert "facial bone structure" in dec.augmented_prompt
    assert "exact photographic match" in dec.augmented_prompt

def test_high_scores_minimal_augmentation():
    v = make_verdict(r=9.0, a=9.0)
    dec = decide_strategy(v, "Test prompt", 1)
    # prompt should only contain original + photorealism cues + period
    expected = "Test prompt. " + PHOTOREALISM_CUES + "."
    assert dec.augmented_prompt == expected
