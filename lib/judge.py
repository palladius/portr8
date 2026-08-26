"""portr8 dual-axis judge — forensic biometric + scene adaptation + prompt adherence evaluation."""

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
    """Build the 3-axis judge prompt.
    
    CRITICAL DESIGN CONSTRAINTS (from empirical research):
    - Anti-beautification penalty: AI smoothing/doll-face = facial_similarity ≤ 5.0 (photo only)
    - Positive biometric analysis only (no negative constraints)
    - Photorealism check adapts to image_type
    - Facial similarity evaluates FACE ONLY, not clothing
    - Scene adaptation penalizes reference photo outfit copying
    """
    # Adjust photorealism instructions based on image type
    if image_type == "photo":
        photo_instructions = """## Photorealism Check
Set is_photorealistic=true ONLY if the image could pass as a real photograph.
Cartoon, illustration, painting, or heavily stylized = false.

CRITICAL: If the face looks smoothed, beautified, or "doll-like" compared to
the authentic reference photos, this is AI beautification. Mark
anti_beautification_flag=true and cap facial_similarity at 5.0.
Authentic skin texture with visible pores, natural lighting, and real-world
imperfections are GOOD signs."""
    elif image_type == "cartoon":
        photo_instructions = """## Style Check
This is a CARTOON image. Set is_photorealistic=false (this is expected and OK).
Set anti_beautification_flag=false (smoothing is expected in cartoons).
Instead, evaluate whether the cartoon style is consistent and high-quality.
Focus facial_similarity scoring on: does the cartoon version capture the DISTINCTIVE
features of the real person (face shape, hair style, eye color, unique traits)?"""
    else:  # illustration
        photo_instructions = """## Style Check
This is an ILLUSTRATION. Set is_photorealistic=false (this is expected and OK).
Set anti_beautification_flag=false (stylization is expected in illustrations).
Focus facial_similarity scoring on: does the illustrated version capture the DISTINCTIVE
features of the real person (face shape, hair style, eye color, unique traits)?"""

    return f"""You are an unsparing forensic biometric likeness, scene adaptation, AND prompt adherence judge.

You are evaluating an AI-generated {image_type} image of "{character_name}" against:
1. Authentic reference photographs of {character_name} (provided as subsequent images)
2. The original scene prompt: "{prompt}"

IMAGE ORDER:
- Image 1: The AI-generated target image under evaluation
- Subsequent images: Authentic real-life reference photographs of {character_name}

EVALUATE THREE INDEPENDENT AXES:

## Axis 1: Facial Similarity (facial_similarity, 1.0-10.0)
Score ONLY based on FACIAL IDENTITY: face shape, bone structure, eye color and shape,
nose bridge and tip, lip shape, hair texture/color/style, skin texture, distinct facial
traits (moles, wrinkles, asymmetries), ear shape, jawline, age, body build.

Do NOT reward matching clothing, accessories, or pose from the reference photos.
The reference photos are for FACE IDENTITY comparison ONLY.

SCORING ANCHORS (use the FULL 1-10 scale):
- 9.0-10.0: Perfect — could fool a close friend or family member of this person
- 8.0-8.9:  Excellent — immediately and unmistakably recognizable as this person, minor imperfections
- 7.0-7.9:  Good — strong resemblance but with noticeable differences in some features
- 5.0-6.9:  Fair — vaguely similar, some features match but others are clearly wrong
- 1.0-4.9:  Poor — different person, wrong age/hair/build

IMPORTANT: A score of 8.0 does NOT require photographic perfection. If a friend of
this person would immediately say "that's them!", score 8.0 or above. Do NOT cap scores
at 7.5 just because it's AI-generated.

IMPORTANT — Prompt Overrides: If the prompt explicitly modifies the character's appearance
(e.g., "without beard", "without glasses", "with long hair"), score based on the MODIFIED
appearance, even if ALL reference photos show the original look. The prompt is the ground
truth for intentional appearance changes.

## Axis 2: Scene Adaptation (scene_adaptation, 1.0-10.0)
Does the person's clothing, pose, accessories, and overall presentation match what the
PROMPT describes? Score based on how well the character has been ADAPTED to the scene:
- 9.0-10.0: Flawless scene-appropriate styling, looks completely natural
- 8.0-8.9:  Excellent adaptation, clothing and pose are highly appropriate
- 7.0-7.9:  Good adaptation, minor mismatches in attire or accessories
- 5.0-6.9:  Acceptable but clearly not ideal for the scene
- 1.0-4.9:  Wearing the SAME outfit from reference photos when the scene calls for different attire

## Axis 3: Adherence (adherence_score, 1.0-10.0)  
Does the overall scene match the prompt? Evaluate:
- Setting/environment accuracy
- Action/pose accuracy
- Objects mentioned in prompt present?
- Lighting/mood/style match
- Overall composition matches intent

SCORING ANCHORS:
- 9.0-10.0: Every element of the prompt is perfectly rendered
- 8.0-8.9:  All major elements present, minor details could improve
- 7.0-7.9:  Most elements present but some are missing or inaccurate
- 5.0-6.9:  Partially matches, significant elements missing
- 1.0-4.9:  Fundamentally different scene from what was requested

{photo_instructions}

Provide detailed rationales for ALL THREE scores. Be brutally honest.
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
    """Judge a generated image on facial similarity, scene adaptation, and adherence.
    
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
    
    f_color = "green" if verdict.facial_similarity >= 8 else "yellow" if verdict.facial_similarity >= 5 else "red"
    s_color = "green" if verdict.scene_adaptation >= 8 else "yellow" if verdict.scene_adaptation >= 5 else "red"
    a_color = "green" if verdict.adherence_score >= 8 else "yellow" if verdict.adherence_score >= 5 else "red"
    
    table.add_row("👤 Facial", f"[{f_color}]{verdict.facial_similarity:.1f}/10[/{f_color}]")
    table.add_row("👔 Scene", f"[{s_color}]{verdict.scene_adaptation:.1f}/10[/{s_color}]")
    table.add_row("🎯 Adherence", f"[{a_color}]{verdict.adherence_score:.1f}/10[/{a_color}]")
    table.add_row("📷 Photorealistic", "YES" if verdict.is_photorealistic else "NO")
    table.add_row("🧟 Anti-beautify", "DETECTED" if verdict.anti_beautification_flag else "Clean")
    table.add_row("🏆 Verdict", verdict.verdict_label)
    
    console.print(Panel(table, title="👨⚖️ Judge Verdict", border_style="cyan"))
    console.print(f"  F: {verdict.facial_similarity_rationale[:100]}...")
    console.print(f"  S: {verdict.scene_adaptation_rationale[:80]}...")
    console.print(f"  A: {verdict.adherence_rationale[:100]}...")
