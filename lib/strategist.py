"""portr8 strategy engine — decides edit vs regenerate and augments prompts."""

from lib.models import JudgeVerdict, StrategyDecision
from rich.console import Console

console = Console()

# Photorealism cues to ALWAYS include (Lesson #3)
PHOTOREALISM_CUES = (
    "photorealistic, authentic skin texture with visible pores, "
    "natural lighting, real-world imperfections, "
    "shot on professional DSLR camera, 85mm portrait lens"
)


def decide_strategy(
    verdict: JudgeVerdict,
    original_prompt: str,
    iteration: int,
    previous_augmented_prompt: str | None = None,
) -> StrategyDecision:
    """Decide whether to edit or regenerate, and build augmented prompt.
    
    Strategy logic:
    - If resemblance < 5.0: REGENERATE (too far off, editing won't fix it)
    - If resemblance >= 5.0 and adherence < 5.0: REGENERATE (scene is wrong)
    - If anti_beautification_flag: REGENERATE (AI smoothing is structural)
    - If resemblance >= 5.0 and adherence >= 5.0: EDIT (close enough to refine)
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
    elif verdict.resemblance_score < 5.0:
        strategy = "regenerate"
        feedback_points.append(f"Resemblance too low ({verdict.resemblance_score:.1f}) — regenerating from scratch")
    elif verdict.adherence_score < 5.0:
        strategy = "regenerate"
        feedback_points.append(f"Adherence too low ({verdict.adherence_score:.1f}) — scene needs full redo")
    else:
        strategy = "edit"
        feedback_points.append(f"Scores are workable (R:{verdict.resemblance_score:.1f} A:{verdict.adherence_score:.1f}) — refining via edit")
    
    # Build augmented prompt
    augmented = _augment_prompt(
        original_prompt, verdict, feedback_points, previous_augmented_prompt
    )
    
    # Build rationale
    rationale = f"Strategy: {strategy}. " + "; ".join(feedback_points)
    
    # The models Literal asks for regenerate/edit. So we need to make sure strategy is assigned nicely
    
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
) -> str:
    """Build an augmented prompt incorporating judge feedback.
    
    CRITICAL: Only use POSITIVE blueprinting. Never add negative constraints.
    """
    parts = [original_prompt.rstrip(".")]
    
    # Always add photorealism cues
    parts.append(PHOTOREALISM_CUES)
    
    # Add positive corrections based on resemblance feedback
    if verdict.resemblance_score < 7.0:
        # Extract useful details from rationale for positive reinforcement
        parts.append(
            "Maintain the exact facial bone structure, eye color, nose shape, "
            "and distinctive features of the person in the reference photos"
        )
    
    if verdict.resemblance_score < 5.0:
        parts.append(
            "The generated person must be an exact photographic match to the reference photos, "
            "preserving every unique facial feature, wrinkle, and skin imperfection"
        )
    
    # Add positive corrections based on adherence feedback
    if verdict.adherence_score < 7.0:
        parts.append(
            "Ensure the scene, setting, and action precisely match the original description"
        )
    
    # Anti-beautification reinforcement
    if verdict.anti_beautification_flag:
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
