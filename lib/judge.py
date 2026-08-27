"""portr8 dual-axis judge — forensic biometric + scene adaptation + prompt adherence evaluation."""

import json
import os
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image as PILImage
from rich.console import Console

from lib.constants import DEFAULT_JUDGE_MODEL
from lib.models import JudgeVerdict

console = Console()


def build_judge_prompt(
    prompt: str,
    character_name: str,
    characters: list[str] | None = None,
    characters_metadata: dict | None = None,
    image_type: str = "photo",
    character_ref_counts: dict[str, int] | None = None,
) -> str:
    """Build the 3-axis judge prompt with multi-character support and character metadata."""
    char_list = characters if characters else [character_name]
    is_multi = len(char_list) > 1

    if image_type == "photo":
        photo_instructions = """## Photorealism Check
Set is_photorealistic=true ONLY if the image could pass as a real photograph.
Cartoon, illustration, painting, or heavily stylized = false.

CRITICAL: If any face looks smoothed, beautified, or "doll-like" compared to
the authentic reference photos, this is AI beautification. Mark
anti_beautification_flag=true and cap facial_similarity at 5.0.
Authentic skin texture with visible pores, natural lighting, and real-world
imperfections are GOOD signs."""
    elif image_type == "cartoon":
        photo_instructions = """## Style Check
This is a CARTOON image. Set is_photorealistic=false (this is expected and OK).
Set anti_beautification_flag=false (smoothing is expected in cartoons).
Instead, evaluate whether the cartoon style is consistent and high-quality."""
    else:  # illustration
        photo_instructions = """## Style Check
This is an ILLUSTRATION. Set is_photorealistic=false (this is expected and OK).
Set anti_beautification_flag=false (stylization is expected in illustrations)."""

    char_profiles_text = ""
    if characters_metadata:
        prof_lines = []
        for c_name, meta in characters_metadata.items():
            if hasattr(meta, "to_biometric_blueprint"):
                bp = meta.to_biometric_blueprint()
                if bp:
                    prof_lines.append(f"• {c_name.capitalize()}: {bp}")
        if prof_lines:
            char_profiles_text = "\n\nAUTHORITATIVE CHARACTER BLUEPRINTS (from character.yaml definitions):\n" + "\n".join(prof_lines)

    if is_multi:
        char_desc = ", ".join(f"Character {i+1}: '{name}'" for i, name in enumerate(char_list))
        multi_instructions = f"""You are evaluating an AI-generated {image_type} image containing MULTIPLE characters:
{char_desc}{char_profiles_text}

EVALUATE BIOMETRICS FOR EACH CHARACTER INDEPENDENTLY:
- Populate `character_facial_scores` with a list of floats [F1, F2, ...] matching the order of characters above.
- Populate `character_facial_rationales` with specific rationale text for each character.
- Set `facial_similarity` as the lowest (bottleneck) score among all characters."""
    else:
        multi_instructions = f"""You are evaluating an AI-generated {image_type} image of "{character_name}".{char_profiles_text}"""

    # Build image order mapping
    image_order_lines = [
        "IMAGE ORDER & REFERENCE MAPPING:",
        "- Image 1: The AI-generated target image under evaluation",
    ]
    if character_ref_counts:
        curr_idx = 2
        for char_name, count in character_ref_counts.items():
            if count == 1:
                image_order_lines.append(f"- Image {curr_idx}: Authentic reference photograph for '{char_name}'")
            elif count > 1:
                image_order_lines.append(f"- Images {curr_idx}-{curr_idx + count - 1}: Authentic reference photographs for '{char_name}'")
            curr_idx += count
    else:
        image_order_lines.append("- Subsequent images: Authentic real-life reference photographs")
    image_order_text = "\n".join(image_order_lines)

    return f"""You are an unsparing forensic biometric likeness, scene adaptation, AND prompt adherence judge.

{multi_instructions}
Scene prompt: "{prompt}"

{image_order_text}

EVALUATE THREE INDEPENDENT AXES:

## Axis 1: Facial Similarity (facial_similarity, 1.0-10.0)
Score ONLY based on FACIAL IDENTITY: face shape, bone structure, eye color and shape,
nose bridge and tip, lip shape, hair texture/color/style, skin texture, distinct facial
traits (moles, wrinkles, asymmetries), ear shape, jawline, age, body build.

Do NOT reward matching clothing, accessories, or pose from the reference photos.
The reference photos are for FACE IDENTITY comparison ONLY.

CRITICAL IDENTITY & ANTI-BEAUTIFICATION RULES:
- Compare each character STRICTLY against their assigned reference photographs above.
- A generic attractive AI face with similar hair color/styling is NOT a match (MAX SCORE 5.0).
- If a character is depicted in profile or at an angle where their facial structure cannot be conclusively verified, DO NOT award higher than 6.0-6.5.
- Look closely for distinctive biometrics: exact nose bridge/curvature, dimples, eye crinkles, facial proportions, asymmetries.
- If AI smoothing or beautification is present on ANY character, flag anti_beautification_flag=true and CAP facial_similarity at 5.0.

SCORING ANCHORS (use the FULL 1-10 scale):
- 9.0-10.0: Perfect — could fool a close friend or family member
- 8.0-8.9:  Excellent — immediately and unmistakably recognizable as this person, minor imperfections
- 7.0-7.9:  Good — strong resemblance but with noticeable differences in some features
- 5.0-6.9:  Fair — vaguely similar, some features match but others are clearly wrong
- 1.0-4.9:  Poor — different person, wrong age/hair/build

## Axis 2: Scene Adaptation (scene_adaptation, 1.0-10.0)
Does the person's/people's clothing, pose, accessories, and overall presentation match what the
PROMPT describes? Score based on how well the character has been ADAPTED to the scene:
- 9.0-10.0: Flawless scene-appropriate styling, looks completely natural
- 8.0-8.9:  Excellent adaptation, clothing and pose are highly appropriate
- 7.0-7.9:  Good adaptation, minor mismatches in attire or accessories
- 5.0-6.9:  Acceptable but clearly not ideal for the scene
- 1.0-4.9:  Wearing the SAME outfit from reference photos when the scene calls for different attire

## Axis 3: Adherence (adherence_score, 1.0-10.0)  
Does the overall scene match the prompt? Evaluate environment, actions, props, lighting, and presence of all requested characters.
- 9.0-10.0: Every element of the prompt is perfectly rendered
- 8.0-8.9:  All major elements present, minor details could improve
- 7.0-7.9:  Most elements present but some are missing or inaccurate
- 5.0-6.9:  Partially matches, significant elements missing
- 1.0-4.9:  Fundamentally different scene from what was requested

{photo_instructions}

Provide detailed rationales for ALL scores. Output strictly according to the requested JSON schema."""


def judge_image(
    client: genai.Client,
    image_path: Path,
    reference_paths: list[str],
    prompt: str,
    character_name: str,
    characters: list[str] | None = None,
    characters_metadata: dict | None = None,
    model: str = DEFAULT_JUDGE_MODEL,
    image_type: str = "photo",
    character_ref_counts: dict[str, int] | None = None,
) -> JudgeVerdict:
    """Judge a generated image on facial similarity, scene adaptation, and adherence."""
    char_list = characters if characters else ([c.strip() for c in character_name.split(",") if c.strip()] if character_name else [])
    
    # Load images: generated first, then references
    contents = []
    contents.append(PILImage.open(image_path))
    for ref_path in reference_paths:
        contents.append(PILImage.open(ref_path))
    
    # Add the judge prompt
    contents.append(
        build_judge_prompt(
            prompt,
            character_name,
            characters=char_list,
            characters_metadata=characters_metadata,
            image_type=image_type,
            character_ref_counts=character_ref_counts,
        )
    )
    
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
    
    # Ensure character_facial_scores fallback
    if not verdict.character_facial_scores and verdict.facial_similarity:
        verdict.character_facial_scores = [verdict.facial_similarity]
    elif verdict.character_facial_scores:
        verdict.facial_similarity = min(verdict.character_facial_scores)
    
    # Log the verdict with rich formatting
    _display_verdict(verdict, characters=char_list)
    
    return verdict


def _display_verdict(verdict: JudgeVerdict, characters: list[str] | None = None) -> None:
    """Display judge verdict with rich formatting."""
    from rich.panel import Panel
    from rich.table import Table
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")
    
    if verdict.character_facial_scores and len(verdict.character_facial_scores) > 1:
        for i, score in enumerate(verdict.character_facial_scores):
            c_name = characters[i] if characters and i < len(characters) else f"F{i+1}"
            f_col = "green" if score >= 8 else "yellow" if score >= 5 else "red"
            table.add_row(f"👤 F{i+1} ({c_name})", f"[{f_col}]{score:.1f}/10[/{f_col}]")
    else:
        f_color = "green" if verdict.facial_similarity >= 8 else "yellow" if verdict.facial_similarity >= 5 else "red"
        table.add_row("👤 Facial", f"[{f_color}]{verdict.facial_similarity:.1f}/10[/{f_color}]")

    s_color = "green" if verdict.scene_adaptation >= 8 else "yellow" if verdict.scene_adaptation >= 5 else "red"
    a_color = "green" if verdict.adherence_score >= 8 else "yellow" if verdict.adherence_score >= 5 else "red"
    avg_color = "green" if verdict.average_score >= 8 else "yellow" if verdict.average_score >= 6 else "red"
    
    table.add_row("👔 Scene", f"[{s_color}]{verdict.scene_adaptation:.1f}/10[/{s_color}]")
    table.add_row("🎯 Adherence", f"[{a_color}]{verdict.adherence_score:.1f}/10[/{a_color}]")
    table.add_row("📊 Average (Media)", f"[{avg_color}]{verdict.average_score:.1f}/10[/{avg_color}]")
    table.add_row("📷 Photorealistic", "YES" if verdict.is_photorealistic else "NO")
    table.add_row("🧟 Anti-beautify", "DETECTED" if verdict.anti_beautification_flag else "Clean")
    table.add_row("🏆 Verdict", verdict.verdict_label)
    
    console.print(Panel(table, title="👨⚖️ Judge Verdict", border_style="cyan"))
    console.print(f"  F: {verdict.facial_similarity_rationale[:100]}...")
    console.print(f"  S: {verdict.scene_adaptation_rationale[:80]}...")
    console.print(f"  A: {verdict.adherence_rationale[:100]}...")

