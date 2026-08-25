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
    """Create a copy of the image with a floating score banner overlay.
    
    The banner is drawn ON TOP of the image at bottom center, semi-transparent.
    Output image has the SAME dimensions as the input (no size change).
    
    Banner text is minimal: #N F=X.X A=X.X S=X.X
    No emoji. No verdict label. Just the 3 scores.
    
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
    
    # Build minimal banner text: #N F=X.X A=X.X S=X.X
    banner_text = (
        f"#{iteration} "
        f"F={verdict.facial_similarity:.1f} "
        f"A={verdict.adherence_score:.1f} "
        f"S={verdict.scene_adaptation:.1f}"
    )
    
    # Load font
    banner_height = max(40, height // 20)  # ~5% of image height, min 40px
    font_size = banner_height // 2
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()
    
    # Measure text
    temp_draw = ImageDraw.Draw(img)
    bbox = temp_draw.textbbox((0, 0), banner_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create semi-transparent overlay
    overlay = PILImage.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Draw semi-transparent dark rectangle at bottom center
    padding_x = 16
    padding_y = 8
    rect_width = text_width + 2 * padding_x
    rect_height = text_height + 2 * padding_y
    rect_x = (width - rect_width) // 2
    rect_y = height - rect_height - 12  # 12px from bottom edge
    
    draw.rectangle(
        [(rect_x, rect_y), (rect_x + rect_width, rect_y + rect_height)],
        fill=(0, 0, 0, 153),  # black at 60% opacity
    )
    
    # Draw text centered in rectangle
    text_x = rect_x + padding_x
    text_y = rect_y + padding_y
    draw.text((text_x, text_y), banner_text, fill=(255, 255, 255, 255), font=font)
    
    # Composite overlay onto image
    composite = PILImage.alpha_composite(img, overlay)
    
    # Save as RGB (PNG with alpha or standard)
    composite.convert("RGB").save(output_path)
    return output_path


def create_failure_overlay(
    image_path: Path,
    verdict: JudgeVerdict,
    iteration: int,
    output_path: Path | None = None,
) -> Path:
    """Create a floating red failure overlay.
    
    Same dimensions as input. Red semi-transparent banner at bottom.
    Text: #N FAIL F=X.X A=X.X S=X.X
    """
    if output_path is None:
        output_path = image_path.parent / f"{image_path.stem}_failure{image_path.suffix}"
    
    img = PILImage.open(image_path).convert("RGBA")
    width, height = img.size
    
    # Minimal failure text
    banner_text = (
        f"#{iteration} FAIL "
        f"F={verdict.facial_similarity:.1f} "
        f"A={verdict.adherence_score:.1f} "
        f"S={verdict.scene_adaptation:.1f}"
    )
    
    banner_height = max(40, height // 20)
    font_size = banner_height // 2
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()
    
    temp_draw = ImageDraw.Draw(img)
    bbox = temp_draw.textbbox((0, 0), banner_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    overlay = PILImage.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    padding_x = 16
    padding_y = 8
    rect_width = text_width + 2 * padding_x
    rect_height = text_height + 2 * padding_y
    rect_x = (width - rect_width) // 2
    rect_y = height - rect_height - 12
    
    # Red semi-transparent background
    draw.rectangle(
        [(rect_x, rect_y), (rect_x + rect_width, rect_y + rect_height)],
        fill=(200, 0, 0, 178),  # red at 70% opacity
    )
    
    text_x = rect_x + padding_x
    text_y = rect_y + padding_y
    draw.text((text_x, text_y), banner_text, fill=(255, 255, 255, 255), font=font)
    
    composite = PILImage.alpha_composite(img, overlay)
    composite.convert("RGB").save(output_path)
    return output_path
