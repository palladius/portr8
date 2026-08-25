import pytest
from pathlib import Path
from lib.models import RunSummary, RunConfig, IterationRecord, JudgeVerdict
from lib.reporter import generate_report

def create_mock_summary(converged: bool = True) -> RunSummary:
    config = RunConfig(
        prompt="A nice portrait",
        character="Alice",
        target_score=8.0
    )
    
    verdict1 = JudgeVerdict(
        resemblance_score=7.0,
        adherence_score=6.5,
        is_photorealistic=True,
        resemblance_rationale="Okay",
        adherence_rationale="Needs work"
    )
    
    verdict2 = JudgeVerdict(
        resemblance_score=8.5 if converged else 7.5,
        adherence_score=9.0 if converged else 7.0,
        is_photorealistic=True,
        resemblance_rationale="Good",
        adherence_rationale="Great"
    )
    
    iter1 = IterationRecord(
        iteration=0,
        timestamp="2023-01-01T12:00:00",
        image_path="img1.png",
        original_prompt="A nice portrait",
        augmented_prompt="A nice portrait",
        strategy="initial",
        image_model="gemini",
        judge_model="gemini",
        verdict=verdict1,
        elapsed_seconds=10.0,
        portr8_version="1.0"
    )
    
    iter2 = IterationRecord(
        iteration=1,
        timestamp="2023-01-01T12:01:00",
        image_path="img2.png",
        original_prompt="A nice portrait",
        augmented_prompt="A nice portrait 2",
        strategy="regenerate",
        image_model="gemini",
        judge_model="gemini",
        verdict=verdict2,
        elapsed_seconds=12.0,
        portr8_version="1.0"
    )
    
    return RunSummary(
        config=config,
        iterations=[iter1, iter2],
        best_iteration=1,
        best_resemblance=verdict2.resemblance_score,
        best_adherence=verdict2.adherence_score,
        converged=converged,
        total_elapsed=22.0,
        output_dir="/tmp/fake_dir"
    )

def test_generate_report_sections(tmp_path: Path):
    summary = create_mock_summary(converged=True)
    report_path = generate_report(summary, tmp_path)
    
    assert report_path.exists()
    content = report_path.read_text()
    
    assert "## Configuration" in content
    assert "## Score Progression" in content
    assert "## Best Iteration" in content
    assert "## Summary" in content
    assert "## All Iterations" in content

def test_generate_report_config_table(tmp_path: Path):
    summary = create_mock_summary()
    report_path = generate_report(summary, tmp_path)
    content = report_path.read_text()
    
    assert "| Parameter | Value |" in content
    assert "| Prompt | A nice portrait |" in content
    assert "| Character | Alice |" in content

def test_generate_report_score_progression(tmp_path: Path):
    summary = create_mock_summary()
    report_path = generate_report(summary, tmp_path)
    content = report_path.read_text()
    
    assert "| Iter | Resemblance | Adherence | Strategy | Verdict | Time |" in content
    # Look for a specific iteration line
    assert "| 0 |" in content
    assert "| 1 |" in content

def test_generate_report_converged(tmp_path: Path):
    summary = create_mock_summary(converged=True)
    report_path = generate_report(summary, tmp_path)
    content = report_path.read_text()
    
    assert "✅ **CONVERGED**" in content
    assert "❌ **FAILED**" not in content

def test_generate_report_failed(tmp_path: Path):
    summary = create_mock_summary(converged=False)
    report_path = generate_report(summary, tmp_path)
    content = report_path.read_text()
    
    assert "❌ **FAILED**" in content
    assert "✅ **CONVERGED**" not in content

