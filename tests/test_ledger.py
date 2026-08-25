import pytest
from pathlib import Path
from lib.models import IterationRecord, RunConfig, RunSummary, JudgeVerdict
from lib.ledger import Ledger, create_output_dir, save_run_config
from datetime import datetime

@pytest.fixture
def run_config():
    return RunConfig(
        prompt="A cute cat",
        character="test_char"
    )

@pytest.fixture
def iteration_records():
    return [
        IterationRecord(
            iteration=1,
            timestamp="2026-08-25T12:00:00Z",
            image_path="img1.jpg",
            original_prompt="Prompt 1",
            augmented_prompt="Prompt 1",
            strategy="initial",
            seed=123,
            image_model="gemini-test",
            judge_model="gemini-test",
            verdict=JudgeVerdict(
                facial_similarity=7.0,
        scene_adaptation=7.0,
                adherence_score=6.0,
                is_photorealistic=True,
                facial_similarity_rationale="Not bad",
        scene_adaptation_rationale="Good scene match",
                adherence_rationale="Needs more cat"
            ),
            elapsed_seconds=10.5,
            portr8_version="0.1.0"
        ),
        IterationRecord(
            iteration=2,
            timestamp="2026-08-25T12:01:00Z",
            image_path="img2.jpg",
            original_prompt="Prompt 2",
            augmented_prompt="Prompt 2",
            strategy="regenerate",
            seed=124,
            image_model="gemini-test",
            judge_model="gemini-test",
            verdict=JudgeVerdict(
                facial_similarity=8.5,
        scene_adaptation=7.0,
                adherence_score=8.0,
                is_photorealistic=True,
                facial_similarity_rationale="Great",
        scene_adaptation_rationale="Good scene match",
                adherence_rationale="None"
            ),
            elapsed_seconds=12.0,
            portr8_version="0.1.0"
        ),
        IterationRecord(
            iteration=3,
            timestamp="2026-08-25T12:02:00Z",
            image_path="img3.jpg",
            original_prompt="Prompt 3",
            augmented_prompt="Prompt 3",
            strategy="edit",
            seed=125,
            image_model="gemini-test",
            judge_model="gemini-test",
            verdict=JudgeVerdict(
                facial_similarity=9.0,
        scene_adaptation=7.0,
                adherence_score=7.5,
                is_photorealistic=True,
                facial_similarity_rationale="Almost",
        scene_adaptation_rationale="Good scene match",
                adherence_rationale="Fix ears"
            ),
            elapsed_seconds=11.0,
            portr8_version="0.1.0"
        )
    ]

def test_append_and_load(tmp_path: Path, iteration_records):
    ledger = Ledger(tmp_path)
    for record in iteration_records:
        ledger.append(record)
    
    assert len(ledger.records) == 3
    assert ledger.ledger_path.exists()
    
    # Read back
    ledger2 = Ledger(tmp_path)
    loaded = ledger2.load()
    assert len(loaded) == 3
    assert loaded[0].iteration == 1
    assert loaded[1].iteration == 2
    assert loaded[2].iteration == 3
    
    # Values should match
    assert loaded[0].verdict.facial_similarity == 7.0

def test_best_iteration(tmp_path: Path, iteration_records):
    ledger = Ledger(tmp_path)
    for record in iteration_records:
        ledger.append(record)
    
    best = ledger.best_iteration()
    assert best is not None
    assert best.iteration == 2  # min(8.5, 8.0) = 8.0. Iter 3 is min(9.0, 7.5) = 7.5
    
def test_empty_ledger(tmp_path: Path):
    ledger = Ledger(tmp_path)
    assert ledger.best_iteration() is None
    assert not ledger.is_converged()
    
def test_is_converged(tmp_path: Path, iteration_records):
    ledger = Ledger(tmp_path)
    ledger.append(iteration_records[0]) # 7.0, 6.0
    assert not ledger.is_converged(8.0)
    
    ledger.append(iteration_records[1]) # 8.5, 8.0
    assert ledger.is_converged(8.0)

def test_create_output_dir(tmp_path: Path):
    prompt = "A very long prompt that goes beyond forty characters easily and then some"
    out_dir = create_output_dir(prompt, base_dir=str(tmp_path))
    assert out_dir.exists()
    assert out_dir.parent == tmp_path
    
    # The slug part should be derived from first 40 chars
    name_parts = out_dir.name.split("-")
    assert len(name_parts) >= 3 # YYYYMMDD-HHMM-slug
    # Date/time checks
    assert len(name_parts[0]) == 8 # YYYYMMDD
    assert len(name_parts[1]) == 4 # HHMM
    assert "a-very-long-prompt-that-goes-beyond-forty" in out_dir.name or "a-very-long-prompt-that-goes-beyond-fort" in out_dir.name

def test_to_summary(tmp_path: Path, iteration_records, run_config):
    ledger = Ledger(tmp_path)
    for record in iteration_records:
        ledger.append(record)
        
    summary = ledger.to_summary(run_config)
    assert summary.config == run_config
    assert len(summary.iterations) == 3
    assert summary.best_iteration == 1 # 0-indexed index of record 2
    assert summary.best_facial_similarity == 8.5
    assert summary.best_adherence == 8.0
    assert summary.converged is True
    assert summary.total_elapsed == 10.5 + 12.0 + 11.0
    assert summary.output_dir == str(tmp_path)

def test_save_run_config(tmp_path: Path, run_config):
    save_run_config(run_config, tmp_path)
    config_file = tmp_path / "run_config.json"
    assert config_file.exists()
    loaded_config = RunConfig.model_validate_json(config_file.read_text())
    assert loaded_config.prompt == "A cute cat"
