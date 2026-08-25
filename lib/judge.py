"""portr8 dual-axis judge — forensic biometric + prompt adherence evaluation."""

import json
import os
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image as PILImage
from rich.console import Console

from lib.models import JudgeVerdict

console = Console()

# Default judge model (empirically best — see docs/SPECS.md Lesson #12)
DEFAULT_JUDGE_MODEL = "gemini-3.5-flash"


def build_judge_prompt(prompt: str, character_name: str, image_type: str = "photo") -> str:
    """Build the dual-axis judge prompt.
    
    CRITICAL DESIGN CONSTRAINTS (from empirical research):
    - Anti-beautification penalty: AI smoothing/doll-face = resemblance ≤ 5.0 (photo only)
    - Positive biometric analysis only (no negative constraints)
    - Photorealism check adapts to image_type
    """
    # Adjust photorealism instructions based on image type
    if image_type == "photo":
        photo_instructions = """## Photorealism Check
Set is_photorealistic=true ONLY if the image could pass as a real photograph.
Cartoon, illustration, painting, or heavily stylized = false.

CRITICAL: If the face looks smoothed, beautified, or "doll-like" compared to
the authentic reference photos, this is AI beautification. Mark
anti_beautification_flag=true and cap resemblance_score at 5.0.
Authentic skin texture with visible pores, natural lighting, and real-world
imperfections are GOOD signs."""
    elif image_type == "cartoon":
        photo_instructions = """## Style Check
This is a CARTOON image. Set is_photorealistic=false (this is expected and OK).
Set anti_beautification_flag=false (smoothing is expected in cartoons).
Instead, evaluate whether the cartoon style is consistent and high-quality.
Focus resemblance scoring on: does the cartoon version capture the DISTINCTIVE
features of the real person (face shape, hair style, eye color, unique traits)?"""
    else:  # illustration
        photo_instructions = """## Style Check
This is an ILLUSTRATION. Set is_photorealistic=false (this is expected and OK).
Set anti_beautification_flag=false (stylization is expected in illustrations).
Focus resemblance scoring on: does the illustrated version capture the DISTINCTIVE
features of the real person (face shape, hair style, eye color, unique traits)?"""

    return f"""You are an unsparing forensic biometric likeness AND scene accuracy judge.

You are evaluating an AI-generated {image_type} image of "{character_name}" against:
1. Authentic reference photographs of {character_name} (provided as subsequent images)
2. The original scene prompt: "{prompt}"

IMAGE ORDER:
- Image 1: The AI-generated target image under evaluation
- Subsequent images: Authentic real-life reference photographs of {character_name}

EVALUATE TWO INDEPENDENT AXES:

## Axis 1: Resemblance (biometric_resemblance_score, 1.0-10.0)
Scrutinize: facial bone structure, eye color and shape, nose bridge and tip,
lip shape, hair texture/color/style, skin texture, distinct facial traits
(moles, wrinkles, asymmetries), ear shape, jawline.

## Axis 2: Adherence (adherence_score, 1.0-10.0)  
Does the scene match the prompt? Evaluate:
- Setting/environment accuracy
- Action/pose accuracy
- Objects mentioned in prompt present?
- Lighting/mood/style match
- Overall composition matches intent

{photo_instructions}

Provide detailed rationales for both scores. Be brutally honest.
Output strictly according to the requested JSON schema."""


def judge_image(
    client: genai.Client,
    image_path: Path,
    reference_paths: list[str],
    prompt: str,
    character_name: str,
    model: str = DEFAULT_JUDGE_MODEL,
    image_type: str = "photo",
) -> JudgeVerdict:
    """Judge a generated image on resemblance and adherence.
    
    Args:
        client: genai.Client instance
        image_path: Path to the generated image to evaluate
        reference_paths: Paths to character reference photos
        prompt: The original scene prompt
        character_name: Name of the character being evaluated
        model: Judge model to use (default: gemini-3.5-flash)
        image_type: Type of image (photo/cartoon/illustration)
    
    Returns:
        JudgeVerdict with scores, rationales, and flags
    """
    # Load images: generated first, then references
    contents = []
    contents.append(PILImage.open(image_path))
    for ref_path in reference_paths:
        contents.append(PILImage.open(ref_path))
    
    # Add the judge prompt
    contents.append(build_judge_prompt(prompt, character_name, image_type=image_type))
    
    console.print(f"  👨⚖️ Judging with [cyan]{model}[/cyan] (temp=0.2)...")
    
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JudgeVerdict,
            temperature=0.2,
        ),
    )
    
    verdict = JudgeVerdict.model_validate_json(response.text.strip())
    
    # Log the verdict with rich formatting
    _display_verdict(verdict)
    
    return verdict


def _display_verdict(verdict: JudgeVerdict) -> None:
    """Display judge verdict with rich formatting."""
    from rich.panel import Panel
    from rich.table import Table
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")
    
    r_color = "green" if verdict.resemblance_score >= 8 else "yellow" if verdict.resemblance_score >= 5 else "red"
    a_color = "green" if verdict.adherence_score >= 8 else "yellow" if verdict.adherence_score >= 5 else "red"
    
    table.add_row("👤 Resemblance", f"[{r_color}]{verdict.resemblance_score:.1f}/10[/{r_color}]")
    table.add_row("🎯 Adherence", f"[{a_color}]{verdict.adherence_score:.1f}/10[/{a_color}]")
    table.add_row("📷 Photorealistic", "✅" if verdict.is_photorealistic else "❌")
    table.add_row("🧟 Anti-beautify", "⚠️ DETECTED" if verdict.anti_beautification_flag else "✅ Clean")
    table.add_row("🏆 Verdict", verdict.verdict_label)
    
    console.print(Panel(table, title="👨⚖️ Judge Verdict", border_style="cyan"))
    console.print(f"  📝 R: {verdict.resemblance_rationale[:100]}...")
    console.print(f"  📝 A: {verdict.adherence_rationale[:100]}...")
