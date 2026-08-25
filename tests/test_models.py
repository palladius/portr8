import pytest
from pydantic import ValidationError
from lib.models import (
    CharacterMetadata,
    JudgeVerdict,
    StrategyDecision,
    IterationRecord,
    RunConfig,
    RunSummary,
)

def test_judge_verdict_labels():
    # CAPOLAVORO (>=8)
    v1 = JudgeVerdict(
        resemblance_score=8.5,
        adherence_score=9.0,
        is_photorealistic=True,
        resemblance_rationale="Great",
        adherence_rationale="Perfect"
    )
    assert v1.verdict_label == "CAPOLAVORO 🏆"

    # BUONO (>=7)
    v2 = JudgeVerdict(
        resemblance_score=7.0,
        adherence_score=9.0,
        is_photorealistic=True,
        resemblance_rationale="Good",
        adherence_rationale="Great"
    )
    assert v2.verdict_label == "BUONO 👍"

    # COSÌ-COSÌ (>=5)
    v3 = JudgeVerdict(
        resemblance_score=9.0,
        adherence_score=5.5,
        is_photorealistic=True,
        resemblance_rationale="Awesome",
        adherence_rationale="Okay"
    )
    assert v3.verdict_label == "COSÌ-COSÌ 😐"

    # SCHIFO (<5)
    v4 = JudgeVerdict(
        resemblance_score=4.9,
        adherence_score=8.0,
        is_photorealistic=True,
        resemblance_rationale="Bad",
        adherence_rationale="Good"
    )
    assert v4.verdict_label == "SCHIFO 🤮"

def test_judge_verdict_anti_beautification():
    v = JudgeVerdict(
        resemblance_score=6.0,
        adherence_score=6.0,
        is_photorealistic=True,
        resemblance_rationale="Ok",
        adherence_rationale="Ok",
        anti_beautification_flag=True
    )
    assert v.anti_beautification_flag is True

def test_score_validation():
    # Valid scores
    JudgeVerdict(
        resemblance_score=0.0,
        adherence_score=10.0,
        is_photorealistic=True,
        resemblance_rationale="Ok",
        adherence_rationale="Ok"
    )

    # Invalid scores
    with pytest.raises(ValidationError):
        JudgeVerdict(
            resemblance_score=-0.1,
            adherence_score=5.0,
            is_photorealistic=True,
            resemblance_rationale="Ok",
            adherence_rationale="Ok"
        )
        
    with pytest.raises(ValidationError):
        JudgeVerdict(
            resemblance_score=5.0,
            adherence_score=10.1,
            is_photorealistic=True,
            resemblance_rationale="Ok",
            adherence_rationale="Ok"
        )

def test_iteration_record_serialization():
    v = JudgeVerdict(
        resemblance_score=8.0,
        adherence_score=8.0,
        is_photorealistic=True,
        resemblance_rationale="Good",
        adherence_rationale="Good"
    )
    sd = StrategyDecision(
        strategy="regenerate",
        augmented_prompt="New prompt",
        rationale="Because",
        feedback_incorporated=["Feedback 1"]
    )
    record = IterationRecord(
        iteration=1,
        timestamp="2023-01-01T12:00:00Z",
        image_path="~/images/1.png",
        original_prompt="Prompt",
        augmented_prompt="New prompt",
        strategy="regenerate",
        seed=12345,
        image_model="model_a",
        judge_model="model_b",
        verdict=v,
        strategy_decision=sd,
        elapsed_seconds=10.5,
        portr8_version="0.1.0"
    )
    
    json_data = record.model_dump_json()
    assert isinstance(json_data, str)
    
    loaded_record = IterationRecord.model_validate_json(json_data)
    assert loaded_record.iteration == record.iteration
    assert loaded_record.verdict.resemblance_score == 8.0

def test_run_config_defaults():
    config = RunConfig(
        prompt="A photo",
        character="bob"
    )
    assert config.ref_dir == "data/characters"
    assert config.image_model == "gemini-3.1-flash-image-preview"
    assert config.judge_model == "gemini-3.5-flash"
    assert config.target_score == 8.0
    assert config.max_iterations == 10
    assert config.dual_strategy is False
    assert config.seed is None
    assert config.ref_transport == "files_api"
    assert config.portr8_version == "0.1.0"

def test_character_metadata():
    c1 = CharacterMetadata(name="Alice")
    assert c1.synthetic is False
    
    c2 = CharacterMetadata(name="Bob", synthetic=True)
    assert c2.synthetic is True

def test_run_summary_converged():
    config = RunConfig(prompt="P", character="C")
    
    # Converged case
    summary = RunSummary(
        config=config,
        iterations=[],
        best_iteration=1,
        best_resemblance=8.5,
        best_adherence=9.0,
        converged=True,
        total_elapsed=30.0,
        output_dir="~/out"
    )
    assert summary.converged is True
    
    # Not converged case
    summary2 = RunSummary(
        config=config,
        iterations=[],
        best_iteration=1,
        best_resemblance=7.5,
        best_adherence=8.0,
        converged=False,
        total_elapsed=30.0,
        output_dir="~/out"
    )
    assert summary2.converged is False
