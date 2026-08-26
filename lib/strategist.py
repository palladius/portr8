"""portr8 strategy engine — decides edit vs regenerate and augments prompts."""

from typing import Literal
from lib.models import JudgeVerdict, StrategyDecision
from rich.console import Console

console = Console()

# Style cues by image_type (Lesson #3: cartoon is too easy, photo is the real challenge)
STYLE_CUES: dict[str, str] = {
    "photo": (
        "photorealistic, authentic skin texture with visible pores, "
        "natural lighting, real-world imperfections, "
        "shot on professional DSLR camera, 85mm portrait lens"
    ),
    "cartoon": (
        "high-quality cartoon illustration, consistent character design, "
        "expressive features, clean linework, vibrant colors, "
        "professional animation studio quality"
    ),
    "illustration": (
        "detailed digital illustration, painterly style, "
        "accurate character likeness in illustrated form, "
        "professional concept art quality, consistent proportions"
    ),
}

# Keep backward compat for tests
PHOTOREALISM_CUES = STYLE_CUES["photo"]


def get_style_cues(image_type: str = "photo") -> str:
    """Get style-appropriate prompt cues for the given image type."""
    return STYLE_CUES.get(image_type, STYLE_CUES["photo"])


def decide_strategy(
    verdict: JudgeVerdict,
    original_prompt: str,
    iteration: int,
    previous_augmented_prompt: str | None = None,
    characters: list[str] | None = None,
    characters_metadata: dict | None = None,
    image_type: str = "photo",
    target_score: float = 8.0,
) -> StrategyDecision:
    """Decide whether to edit or regenerate, and build augmented prompt.
    
    Strategy logic:
    - If facial_similarity < 6.0: REGENERATE (face too far off to recover via edit)
    - If scene_adaptation < 5.0: REGENERATE (clothing/pose wrong for scene)
    - If adherence < 5.0: REGENERATE (scene is wrong)
    - If anti_beautification_flag: REGENERATE (AI smoothing is structural)
    - Otherwise: EDIT (workable likeness to refine)
    - If iteration == 0: always REGENERATE (no previous image to edit)
    """
    feedback_points = []
    min_facial = min(verdict.character_facial_scores) if verdict.character_facial_scores else verdict.facial_similarity
    
    # Determine strategy
    if iteration == 0:
        strategy = "regenerate"
        feedback_points.append("Initial generation")
    elif verdict.anti_beautification_flag:
        strategy = "regenerate"
        feedback_points.append("AI beautification detected — regenerating to avoid structural smoothing")
    elif min_facial < 6.0:
        strategy = "regenerate"
        feedback_points.append(f"Facial likeness bottleneck ({min_facial:.1f} < 6.0) — regenerating from scratch with refined biometric guidance")
    elif verdict.scene_adaptation < 5.0:
        strategy = "regenerate"
        feedback_points.append(f"Scene adaptation too low ({verdict.scene_adaptation:.1f}) — clothing/pose doesn't match scene, regenerating")
    elif verdict.adherence_score < 5.0:
        strategy = "regenerate"
        feedback_points.append(f"Adherence too low ({verdict.adherence_score:.1f}) — scene needs full redo")
    else:
        strategy = "edit"
        feedback_points.append(f"Scores are workable (F:{min_facial:.1f} S:{verdict.scene_adaptation:.1f} A:{verdict.adherence_score:.1f}) — refining via edit")
    
    # Build augmented prompt
    augmented = _augment_prompt(
        original_prompt, verdict, feedback_points, previous_augmented_prompt,
        characters=characters,
        characters_metadata=characters_metadata,
        image_type=image_type,
        target_score=target_score,
    )
    
    # Build rationale
    rationale = f"Strategy: {strategy}. " + "; ".join(feedback_points)
    
    decision = StrategyDecision(
        strategy=strategy, # type: ignore
        augmented_prompt=augmented,
        rationale=rationale,
        feedback_incorporated=feedback_points,
    )
    
    _display_decision(decision)
    return decision


def _augment_prompt(
    original_prompt: str,
    verdict: JudgeVerdict,
    feedback_points: list[str],
    previous_augmented: str | None,
    characters: list[str] | None = None,
    characters_metadata: dict | None = None,
    image_type: str = "photo",
    target_score: float = 8.0,
) -> str:
    """Build an augmented prompt incorporating SPECIFIC judge feedback and character blueprints."""
    parts = [original_prompt.rstrip(".")]
    
    # 1. Add character blueprints from character.yaml if available
    if characters_metadata:
        for char_name, meta in characters_metadata.items():
            if hasattr(meta, "to_biometric_blueprint"):
                blueprint = meta.to_biometric_blueprint()
                if blueprint:
                    parts.append(f"Character '{char_name.capitalize()}' profile: {blueprint}")
    
    # 2. Always add style-appropriate cues
    parts.append(get_style_cues(image_type))
    
    # 3. Specific per-character facial corrections
    if verdict.character_facial_rationales and len(verdict.character_facial_rationales) > 1:
        char_list = characters if characters else [f"Person {i+1}" for i in range(len(verdict.character_facial_rationales))]
        facial_corrections = []
        for i, rat in enumerate(verdict.character_facial_rationales):
            c_name = char_list[i] if i < len(char_list) else f"Person {i+1}"
            score = verdict.character_facial_scores[i] if len(verdict.character_facial_scores) > i else 0.0
            if score < target_score and rat:
                facial_corrections.append(f"• {c_name.capitalize()}: {rat}")
        if facial_corrections:
            parts.append("CRITICAL FACIAL CORRECTIONS PER CHARACTER:\n" + "\n".join(facial_corrections) + "\nFix each person to precisely match their reference photographs")
    elif verdict.facial_similarity < target_score and verdict.facial_similarity_rationale:
        parts.append(
            f"CRITICAL FACIAL CORRECTION — previous attempt had this issue: "
            f"\"{verdict.facial_similarity_rationale}\". Fix this by closely matching the face in the reference photos"
        )
    
    min_facial = min(verdict.character_facial_scores) if verdict.character_facial_scores else verdict.facial_similarity
    if min_facial < 5.0:
        parts.append(
            "Every person must be an exact photographic match to their respective reference photos, "
            "preserving all unique facial features, bone structure, wrinkles, and natural skin texture"
        )
    
    # 4. Scene adaptation corrections
    if verdict.scene_adaptation < target_score and verdict.scene_adaptation_rationale:
        parts.append(
            f"SCENE ADAPTATION CORRECTION — previous issue: "
            f"\"{verdict.scene_adaptation_rationale}\". Dress the characters appropriately for the scene described in the prompt"
        )
    
    if verdict.scene_adaptation < 5.0:
        parts.append(
            "Characters should wear clothing and accessories appropriate for the described scene. "
            "Use reference photos for FACIAL IDENTITY ONLY, not for clothing"
        )
    
    # 5. Scene adherence corrections
    if verdict.adherence_score < target_score and verdict.adherence_rationale:
        parts.append(
            f"SCENE ADHERENCE CORRECTION — previous issue: "
            f"\"{verdict.adherence_rationale}\". Ensure the scene precisely matches the original description"
        )
    
    # 6. Anti-beautification reinforcement
    if verdict.anti_beautification_flag and image_type == "photo":
        parts.append(
            "Preserve authentic skin texture with visible pores, natural wrinkles, "
            "and real-world skin imperfections. The skin must look like an authentic photograph, not AI-smoothed"
        )
    
    return ". ".join(parts) + "."


def _display_decision(decision: StrategyDecision) -> None:
    """Display strategy decision with rich formatting."""
    emoji = "🔄" if decision.strategy == "regenerate" else "✂️"
    style = "yellow" if decision.strategy == "regenerate" else "green"
    
    console.print(f"  {emoji} Strategy: [{style}]{decision.strategy.upper()}[/{style}]")
    console.print(f"  📝 Rationale: {decision.rationale}")
    if len(decision.augmented_prompt) > 120:
        console.print(f"  📧 Augmented prompt: {decision.augmented_prompt[:120]}...")
    else:
        console.print(f"  📧 Augmented prompt: {decision.augmented_prompt}")
