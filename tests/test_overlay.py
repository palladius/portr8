import pytest
from pathlib import Path
from PIL import Image as PILImage
import tempfile
import os

from lib.overlay import get_verdict_color, create_score_overlay, create_failure_overlay
from lib.models import JudgeVerdict


def create_test_image(path: Path, size=(100, 100)):
    img = PILImage.new('RGB', size, color='blue')
    img.save(path)


def test_get_verdict_color():
    assert get_verdict_color("CAPOLAVORO (8)") == (0, 180, 0)
    assert get_verdict_color("BUONO (7)") == (0, 120, 200)
    assert get_verdict_color("COSÌ-COSÌ (6)") == (200, 160, 0)
    assert get_verdict_color("SCHIFO (4)") == (200, 0, 0)


def test_create_score_overlay_size():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.jpg"
        output_path = Path(tmpdir) / "output.jpg"
        
        create_test_image(input_path, size=(100, 100))
        
        verdict = JudgeVerdict(
            verdict_label="BUONO (7)",
            resemblance_score=7.0,
            resemblance_rationale="Good",
            adherence_score=7.5,
            adherence_rationale="Good",
            is_photorealistic=True,
            anti_beautification_flag=False,
            critique="Test critique",
            improvements="Test improvements"
        )
        
        result_path = create_score_overlay(
            image_path=input_path,
            verdict=verdict,
            iteration=1,
            output_path=output_path
        )
        
        assert result_path.exists()
        
        # Check size increased
        img = PILImage.open(result_path)
        width, height = img.size
        
        assert width == 100
        assert height > 100  # Height should be 100 + banner height (at least 60)


def test_create_score_overlay_default_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.jpg"
        create_test_image(input_path)
        
        verdict = JudgeVerdict(
            verdict_label="SCHIFO (4)",
            resemblance_score=4.0,
            resemblance_rationale="Bad",
            adherence_score=4.5,
            adherence_rationale="Bad",
            is_photorealistic=False,
            anti_beautification_flag=True,
            critique="Bad",
            improvements="Better"
        )
        
        result_path = create_score_overlay(
            image_path=input_path,
            verdict=verdict,
            iteration=1
        )
        
        assert result_path.exists()
        assert result_path.name == "test_scored.jpg"


def test_create_failure_overlay():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.jpg"
        create_test_image(input_path, size=(100, 100))
        
        verdict = JudgeVerdict(
            verdict_label="SCHIFO (4)",
            resemblance_score=4.0,
            resemblance_rationale="Fail",
            adherence_score=4.0,
            adherence_rationale="Fail",
            is_photorealistic=True,
            anti_beautification_flag=False,
            critique="Fail",
            improvements="Try harder"
        )
        
        result_path = create_failure_overlay(
            image_path=input_path,
            verdict=verdict,
            iteration=5
        )
        
        assert result_path.exists()
        assert result_path.name == "test_failure.jpg"
        
        img = PILImage.open(result_path)
        width, height = img.size
        
        border = 8
        assert width == 100 + 2 * border
        assert height > 100 + 2 * border


@pytest.mark.parametrize("label", [
    "CAPOLAVORO",
    "BUONO",
    "COSÌ-COSÌ",
    "SCHIFO"
])
def test_overlay_all_verdicts(label):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.jpg"
        create_test_image(input_path)
        
        verdict = JudgeVerdict(
            verdict_label=label,
            resemblance_score=6.0,
            resemblance_rationale="Rational",
            adherence_score=6.0,
            adherence_rationale="Rational",
            is_photorealistic=True,
            anti_beautification_flag=False,
            critique="Critique",
            improvements="Improvements"
        )
        
        result_path = create_score_overlay(
            image_path=input_path,
            verdict=verdict,
            iteration=1
        )
        
        assert result_path.exists()
        
        img = PILImage.open(result_path)
        assert img.size[0] == 100
        assert img.size[1] > 100
