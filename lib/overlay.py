"""portr8 score overlay — stamps floating score banners on generated images."""

import re
from pathlib import Path
from PIL import Image as PILImage, ImageDraw, ImageFont
from lib.models import JudgeVerdict


def _strip_emoji(text: str) -> str:
    """Remove emoji characters from text for Pillow rendering.
    
    DejaVu and most system fonts can't render emoji — they show as □.
    """
    # Remove characters outside Basic Multilingual Plane + common emoji ranges
    emoji_pattern = re.compile(
        "[\U0001F300-\U0001F9FF"   # Misc Symbols, Emoticons, etc.
        "\U00002702-\U000027B0"    # Dingbats
        "\U0000FE00-\U0000FE0F"    # Variation Selectors
        "\U0000200D"               # Zero Width Joiner
        "\U00002600-\U000026FF"    # Misc Symbols
        "\U0000231A-\U0000231B"    # Watch, Hourglass
        "\U00002B50"               # Star
        "\U0000274C"               # Cross mark
        "\U00002705"               # Check mark
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text).strip()


def get_verdict_color(verdict_label: str) -> tuple[int, int, int]:
    """Get RGB color for verdict label."""
    if "CAPOLAVORO" in verdict_label:
        return (0, 180, 0)      # Green
    elif "BUONO" in verdict_label:
        return (0, 120, 200)    # Blue  
    elif "COS\u00cc-COS\u00cc" in verdict_label:
        return (200, 160, 0)    # Yellow/amber
    else:  # SCHIFO
        return (200, 0, 0)      # Red


def create_score_overlay(
    image_path: Path,
    verdict: JudgeVerdict,
    iteration: int,
    output_path: Path | None = None,
) -> Path:
    """Create a copy of the image with floating score indicators.
    
    Two semi-transparent pills:
    - Top-left:  Big "#N" (iteration number)
    - Bottom-right: "X.X" (overall score = min of 3 axes)
    
    Output image has the SAME dimensions as the input.
    
    Args:
        image_path: Path to the source image
        verdict: JudgeVerdict with scores
        iteration: Iteration number
        output_path: Where to save (default: image_path with _scored suffix)
    
    Returns:
        Path to the scored image
    """
    if output_path is None:
        output_path = image_path.parent / f"{image_path.stem}_scored{image_path.suffix}"
    
    img = PILImage.open(image_path).convert("RGBA")
    width, height = img.size
    
    # Single overlay score = arithmetic mean (MEDIA) of all evaluated axes
    overall_score = verdict.average_score
    
    # Font sizes: iteration is BIG, score is medium (~10% smaller for perfect fit inside pill)
    iter_font_size = max(42, int(height * 0.085))
    score_font_size = max(32, int(height * 0.062))
    try:
        iter_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", iter_font_size)
        score_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", score_font_size)
    except (IOError, OSError):
        iter_font = ImageFont.load_default()
        score_font = ImageFont.load_default()
    
    # Create overlay layer
    overlay = PILImage.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    padding_x = 16
    padding_y = 10
    margin = 14
    text_color = (255, 224, 0, 255)  # Warm bright yellow for perfect readability
    
    # --- TOP-LEFT: Big "#N" ---
    iter_text = f"#{iteration}"
    bbox_iter = draw.textbbox((0, 0), iter_text, font=iter_font)
    tw_iter = bbox_iter[2] - bbox_iter[0]
    th_iter = bbox_iter[3] - bbox_iter[1]
    
    draw.rounded_rectangle(
        [(margin, margin),
         (margin + tw_iter + 2 * padding_x, margin + th_iter + 2 * padding_y)],
        radius=12,
        fill=(0, 0, 0, 165),  # 65% opacity dark
    )
    draw.text((margin + padding_x, margin + padding_y), iter_text,
              fill=text_color, font=iter_font)
    
    # --- BOTTOM-RIGHT: Score (Average) ---
    score_text = f"{overall_score:.1f}"
    bbox_score = draw.textbbox((0, 0), score_text, font=score_font)
    tw_score = bbox_score[2] - bbox_score[0]
    th_score = bbox_score[3] - bbox_score[1]
    
    score_rect_x = width - margin - tw_score - 2 * padding_x
    score_rect_y = height - margin - th_score - 2 * padding_y
    
    # Color the score pill based on quality
    if overall_score >= 8.0:
        pill_color = (0, 140, 0, 185)     # green
    elif overall_score >= 6.0:
        pill_color = (0, 0, 0, 165)       # neutral dark
    else:
        pill_color = (180, 0, 0, 185)     # red
    
    draw.rounded_rectangle(
        [(score_rect_x, score_rect_y),
         (score_rect_x + tw_score + 2 * padding_x, score_rect_y + th_score + 2 * padding_y)],
        radius=12,
        fill=pill_color,
    )
    draw.text((score_rect_x + padding_x, score_rect_y + padding_y), score_text,
              fill=text_color, font=score_font)
    
    # Composite and save
    composite = PILImage.alpha_composite(img, overlay)
    composite.convert("RGB").save(output_path)
    return output_path


def create_failure_overlay(
    image_path: Path,
    verdict: JudgeVerdict,
    iteration: int,
    output_path: Path | None = None,
) -> Path:
    """Create a floating red failure overlay.
    
    Same two-pill design as score overlay, but with red pills.
    Top-left: #N, Bottom-right: X.X (both red).
    """
    if output_path is None:
        output_path = image_path.parent / f"{image_path.stem}_failure{image_path.suffix}"
    
    img = PILImage.open(image_path).convert("RGBA")
    width, height = img.size
    
    overall_score = min(
        verdict.facial_similarity,
        verdict.adherence_score,
        verdict.scene_adaptation,
    )
    
    iter_font_size = max(42, int(height * 0.085))
    score_font_size = max(32, int(height * 0.062))
    try:
        iter_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", iter_font_size)
        score_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", score_font_size)
    except (IOError, OSError):
        iter_font = ImageFont.load_default()
        score_font = ImageFont.load_default()
    
    overlay = PILImage.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    padding_x = 16
    padding_y = 10
    margin = 14
    text_color = (255, 224, 0, 255)
    red_pill = (180, 0, 0, 185)
    
    # --- TOP-LEFT: Big "#N" (red) ---
    iter_text = f"#{iteration}"
    bbox_iter = draw.textbbox((0, 0), iter_text, font=iter_font)
    tw_iter = bbox_iter[2] - bbox_iter[0]
    th_iter = bbox_iter[3] - bbox_iter[1]
    
    draw.rounded_rectangle(
        [(margin, margin),
         (margin + tw_iter + 2 * padding_x, margin + th_iter + 2 * padding_y)],
        radius=12,
        fill=red_pill,
    )
    draw.text((margin + padding_x, margin + padding_y), iter_text,
              fill=text_color, font=iter_font)
    
    # --- BOTTOM-RIGHT: Score (red) ---
    score_text = f"{overall_score:.1f}"
    bbox_score = draw.textbbox((0, 0), score_text, font=score_font)
    tw_score = bbox_score[2] - bbox_score[0]
    th_score = bbox_score[3] - bbox_score[1]
    
    score_rect_x = width - margin - tw_score - 2 * padding_x
    score_rect_y = height - margin - th_score - 2 * padding_y
    
    draw.rounded_rectangle(
        [(score_rect_x, score_rect_y),
         (score_rect_x + tw_score + 2 * padding_x, score_rect_y + th_score + 2 * padding_y)],
        radius=12,
        fill=red_pill,
    )
    draw.text((score_rect_x + padding_x, score_rect_y + padding_y), score_text,
              fill=text_color, font=score_font)
    
    composite = PILImage.alpha_composite(img, overlay)
    composite.convert("RGB").save(output_path)
    return output_path
