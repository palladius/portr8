"""portr8 score overlay — stamps score banners on generated images."""

from pathlib import Path
from PIL import Image as PILImage, ImageDraw, ImageFont
from lib.models import JudgeVerdict


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
    """Create a copy of the image with a score banner overlay.
    
    The banner shows:
    - Iteration number
    - Resemblance and adherence scores
    - Italian verdict label
    - Photorealism status
    - Color-coded by verdict (green/blue/amber/red)
    
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
    
    img = PILImage.open(image_path)
    width, height = img.size
    
    # Create banner
    banner_height = max(60, height // 12)  # ~8% of image height, min 60px
    banner = PILImage.new('RGB', (width, banner_height), get_verdict_color(verdict.verdict_label))
    draw = ImageDraw.Draw(banner)
    
    # Build banner text
    photo_str = "✅" if verdict.is_photorealistic else "❌"
    beautify_str = " ⚠️ BEAUTIFIED" if verdict.anti_beautification_flag else ""
    banner_text = (
        f"Iter {iteration} | "
        f"R:{verdict.resemblance_score:.1f} A:{verdict.adherence_score:.1f} | "
        f"{verdict.verdict_label} | "
        f"Photo:{photo_str}{beautify_str}"
    )
    
    # Use default font (no external font dependency)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", banner_height // 3)
    except (IOError, OSError):
        font = ImageFont.load_default()
    
    # Center text in banner
    bbox = draw.textbbox((0, 0), banner_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = max(10, (width - text_width) // 2)
    text_y = (banner_height - text_height) // 2
    draw.text((text_x, text_y), banner_text, fill=(255, 255, 255), font=font)
    
    # Composite: original image + banner at bottom
    composite = PILImage.new('RGB', (width, height + banner_height))
    composite.paste(img, (0, 0))
    composite.paste(banner, (0, height))
    
    composite.save(output_path)
    return output_path


def create_failure_overlay(
    image_path: Path,
    verdict: JudgeVerdict,
    iteration: int,
    output_path: Path | None = None,
) -> Path:
    """Create a red-bordered failure overlay for convergence failures.
    
    Similar to score overlay but with a thick red border and ':failure' text.
    """
    if output_path is None:
        output_path = image_path.parent / f"{image_path.stem}_failure{image_path.suffix}"
    
    img = PILImage.open(image_path)
    width, height = img.size
    
    border = 8
    banner_height = max(80, height // 10)
    
    # Red banner
    banner = PILImage.new('RGB', (width + 2*border, banner_height), (200, 0, 0))
    draw = ImageDraw.Draw(banner)
    
    banner_text = (
        f":failure | Iter {iteration} | "
        f"R:{verdict.resemblance_score:.1f} A:{verdict.adherence_score:.1f} | "
        f"{verdict.verdict_label}"
    )
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", banner_height // 3)
    except (IOError, OSError):
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), banner_text, font=font)
    text_x = max(10, (width + 2*border - (bbox[2] - bbox[0])) // 2)
    text_y = (banner_height - (bbox[3] - bbox[1])) // 2
    draw.text((text_x, text_y), banner_text, fill=(255, 255, 255), font=font)
    
    # Red-bordered composite
    composite = PILImage.new('RGB', (width + 2*border, height + 2*border + banner_height), (200, 0, 0))
    composite.paste(img, (border, border))
    composite.paste(banner, (0, height + 2*border))
    
    composite.save(output_path)
    return output_path
