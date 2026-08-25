import pytest
from lib.judge import build_judge_prompt, _display_verdict, judge_image
from lib.models import JudgeVerdict

def test_build_judge_prompt():
    prompt = "A man walking on the moon"
    character_name = "John Doe"
    
    result = build_judge_prompt(prompt, character_name)
    
    # 1. contains character name and prompt
    assert character_name in result
    assert prompt in result
    
    # 2. mentions anti-beautification
    assert "anti_beautification_flag" in result
    assert "beautified" in result.lower() or "beautification" in result.lower()
    
    # 3. mentions photorealistic
    assert "is_photorealistic" in result
    assert "photorealistic" in result.lower() or "photorealism" in result.lower()


def test_display_verdict():
    # 4. _display_verdict doesn't crash
    verdict = JudgeVerdict(
        resemblance_score=8.5,
        resemblance_rationale="Looks just like him.",
        adherence_score=9.0,
        adherence_rationale="Scene matches prompt perfectly.",
        is_photorealistic=True,
        anti_beautification_flag=False,
        verdict_label="CAPOLAVORO"
    )
    # Should not raise an exception
    _display_verdict(verdict)


def test_judge_image_importable():
    # 5. judge_image function signature is importable
    assert callable(judge_image)

def test_judge_verdict_model():
    # 6. JudgeVerdict model works with the schema
    verdict = JudgeVerdict(
        resemblance_score=4.0,
        resemblance_rationale="Doesn't look like him.",
        adherence_score=5.0,
        adherence_rationale="Missing the moon.",
        is_photorealistic=False,
        anti_beautification_flag=True,
    )
    
    assert verdict.resemblance_score == 4.0
    assert verdict.verdict_label is not None
    assert "SCHIFO" in verdict.verdict_label # Since score < 5
