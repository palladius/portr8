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


def test_create_score_overlay_same_size():
    """Overlay should NOT change image dimensions — banner is drawn ON TOP."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.png"
        output_path = Path(tmpdir) / "output.png"
        
        create_test_image(input_path, size=(200, 200))
        
        verdict = JudgeVerdict(
            facial_similarity=7.0,
            scene_adaptation=7.0,
            adherence_score=7.5,
            is_photorealistic=True,
            facial_similarity_rationale="Good",
            scene_adaptation_rationale="Good scene match",
            adherence_rationale="Good",
        )
        
        result_path = create_score_overlay(
            image_path=input_path,
            verdict=verdict,
            iteration=1,
            output_path=output_path
        )
        
        assert result_path.exists()
        
        # Image dimensions should be EXACTLY the same (floating overlay, not appended)
        img = PILImage.open(result_path)
        assert img.size == (200, 200)


def test_create_score_overlay_default_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.png"
        create_test_image(input_path)
        
        verdict = JudgeVerdict(
            facial_similarity=4.0,
            scene_adaptation=6.0,
            adherence_score=4.5,
            is_photorealistic=False,
            facial_similarity_rationale="Bad",
            scene_adaptation_rationale="Ok scene",
            adherence_rationale="Bad",
            anti_beautification_flag=True,
        )
        
        result_path = create_score_overlay(
            image_path=input_path,
            verdict=verdict,
            iteration=1
        )
        
        assert result_path.exists()
        assert result_path.name == "test_scored.png"


def test_create_failure_overlay():
    """Failure overlay should have same size + red-tinted banner."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.png"
        create_test_image(input_path, size=(200, 200))
        
        verdict = JudgeVerdict(
            facial_similarity=4.0,
            scene_adaptation=3.0,
            adherence_score=4.0,
            is_photorealistic=True,
            facial_similarity_rationale="Fail",
            scene_adaptation_rationale="Bad scene",
            adherence_rationale="Fail",
        )
        
        result_path = create_failure_overlay(
            image_path=input_path,
            verdict=verdict,
            iteration=5
        )
        
        assert result_path.exists()
        assert result_path.name == "test_failure.png"
        
        # Same dimensions — floating overlay
        img = PILImage.open(result_path)
        assert img.size == (200, 200)


@pytest.mark.parametrize("label", [
    "CAPOLAVORO",
    "BUONO",
    "COSÌ-COSÌ",
    "SCHIFO"
])
def test_overlay_all_verdicts(label):
    """All verdict labels should produce valid overlays with same dimensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.png"
        create_test_image(input_path, size=(300, 200))
        
        verdict = JudgeVerdict(
            facial_similarity=6.0,
            scene_adaptation=7.0,
            adherence_score=6.0,
            is_photorealistic=True,
            facial_similarity_rationale="Rational",
            scene_adaptation_rationale="Good scene match",
            adherence_rationale="Rational",
        )
        
        result_path = create_score_overlay(
            image_path=input_path,
            verdict=verdict,
            iteration=1
        )
        
        assert result_path.exists()
        
        img = PILImage.open(result_path)
        assert img.size == (300, 200)
