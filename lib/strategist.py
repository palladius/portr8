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
    image_type: str = "photo",
    target_score: float = 8.0,
) -> StrategyDecision:
    """Decide whether to edit or regenerate, and build augmented prompt.
    
    Strategy logic:
    - If facial_similarity < 5.0: REGENERATE (face too far off)
    - If scene_adaptation < 5.0: REGENERATE (clothing/pose wrong for scene)
    - If adherence < 5.0: REGENERATE (scene is wrong)
    - If anti_beautification_flag: REGENERATE (AI smoothing is structural)
    - Otherwise: EDIT (close enough to refine)
    - If iteration == 0: always REGENERATE (no previous image to edit)
    """
    feedback_points = []
    
    # Determine strategy
    if iteration == 0:
        strategy = "regenerate"
        feedback_points.append("Initial generation")
    elif verdict.anti_beautification_flag:
        strategy = "regenerate"
        feedback_points.append("AI beautification detected — regenerating to avoid structural smoothing")
    elif verdict.facial_similarity < 5.0:
        strategy = "regenerate"
        feedback_points.append(f"Facial similarity too low ({verdict.facial_similarity:.1f}) — regenerating from scratch")
    elif verdict.scene_adaptation < 5.0:
        strategy = "regenerate"
        feedback_points.append(f"Scene adaptation too low ({verdict.scene_adaptation:.1f}) — clothing/pose doesn't match scene, regenerating")
    elif verdict.adherence_score < 5.0:
        strategy = "regenerate"
        feedback_points.append(f"Adherence too low ({verdict.adherence_score:.1f}) — scene needs full redo")
    else:
        strategy = "edit"
        feedback_points.append(f"Scores are workable (F:{verdict.facial_similarity:.1f} S:{verdict.scene_adaptation:.1f} A:{verdict.adherence_score:.1f}) — refining via edit")
    
    # Build augmented prompt
    augmented = _augment_prompt(
        original_prompt, verdict, feedback_points, previous_augmented_prompt,
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
    image_type: str = "photo",
    target_score: float = 8.0,
) -> str:
    """Build an augmented prompt incorporating SPECIFIC judge feedback.
    
    CRITICAL: Only use POSITIVE blueprinting. Never add negative constraints.
    Key change from v0.4.1: we now extract specific issues from judge rationale
    and include them, so the prompt EVOLVES each iteration.
    """
    parts = [original_prompt.rstrip(".")]
    
    # Always add style-appropriate cues
    parts.append(get_style_cues(image_type))
    
    # --- FACIAL SIMILARITY FEEDBACK (specific, from rationale) ---
    if verdict.facial_similarity < target_score:
        # Extract and forward the SPECIFIC rationale so the model knows what to fix
        rationale = verdict.facial_similarity_rationale
        if rationale:
            # Reframe as a positive correction directive
            parts.append(
                f"CRITICAL FACIAL CORRECTION — the previous attempt had this issue: "
                f"\"{rationale}\". Fix this by closely matching the face in the reference photos"
            )
    
    if verdict.facial_similarity < 5.0:
        parts.append(
            "The generated person must be an exact photographic match to the reference photos, "
            "preserving every unique facial feature, wrinkle, and skin imperfection"
        )
    
    # --- SCENE ADAPTATION FEEDBACK (specific, from rationale) ---
    if verdict.scene_adaptation < target_score:
        rationale = verdict.scene_adaptation_rationale
        if rationale:
            parts.append(
                f"SCENE ADAPTATION CORRECTION — previous issue: "
                f"\"{rationale}\". Dress the person appropriately for the scene described in the prompt"
            )
    
    if verdict.scene_adaptation < 5.0:
        parts.append(
            "The person should wear clothing and accessories appropriate for the described scene. "
            "Use reference photos for FACIAL IDENTITY ONLY, not for clothing or accessories"
        )
    
    # --- ADHERENCE FEEDBACK (specific, from rationale) ---
    if verdict.adherence_score < target_score:
        rationale = verdict.adherence_rationale
        if rationale:
            parts.append(
                f"SCENE ADHERENCE CORRECTION — previous issue: "
                f"\"{rationale}\". Ensure the scene precisely matches the original description"
            )
    
    # Anti-beautification reinforcement (only for photo — cartoon IS beautified by nature)
    if verdict.anti_beautification_flag and image_type == "photo":
        parts.append(
            "Preserve authentic skin texture with visible pores, natural wrinkles, "
            "and real-world skin imperfections. The skin must look like a real photograph"
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
