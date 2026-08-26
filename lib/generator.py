"""portr8 image generator — wraps google-genai for character-consistent image generation."""

import glob
import os
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from PIL import Image as PILImage
from rich.console import Console

from lib.models import CharacterMetadata

console = Console()

# Fallback model chain (empirically proven order)
DEFAULT_MODELS = [
    "gemini-3.1-flash-image-preview",
    "gemini-3.1-flash-image",
    "gemini-2.5-flash-image",
]


def to_tilde_path(path: str | Path) -> str:
    """Convert absolute path to tilde-normalized path."""
    home = os.path.expanduser("~")
    res = str(Path(path).resolve())
    if res.startswith(home):
        return "~" + res[len(home):]
    return res


def resolve_character_images(character: str, ref_dir: str = "data/characters", max_images: int = 4) -> list[str]:
    """Find reference photos for a character, prioritizing grid_cleaned/ crops.
    
    Priority: grid_cleaned/ > root directory images
    Sorted by file size (largest first — higher resolution preferred).
    """
    char_dir = Path(ref_dir) / character.lower()
    if not char_dir.exists():
        raise FileNotFoundError(f"Character directory not found: {char_dir}")
    
    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    
    # Try grid_cleaned/ first
    grid_dir = char_dir / "grid_cleaned"
    if grid_dir.exists():
        imgs = [str(p) for p in grid_dir.iterdir() if p.suffix.lower() in valid_exts]
        if imgs:
            imgs.sort(key=lambda x: os.path.getsize(x), reverse=True)
            return imgs[:max_images]
    
    # Fallback to root directory
    imgs = [str(p) for p in char_dir.iterdir() 
            if p.is_file() and p.suffix.lower() in valid_exts]
    imgs.sort(key=lambda x: os.path.getsize(x), reverse=True)
    return imgs[:max_images]


def load_character_metadata(character: str, ref_dir: str = "data/characters") -> CharacterMetadata | None:
    """Load character.yaml metadata if it exists."""
    import yaml  # Don't add pyyaml as dep yet — make it optional
    yaml_path = Path(ref_dir) / character.lower() / "character.yaml"
    if yaml_path.exists():
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            return CharacterMetadata(**data)
        except Exception:
            return None
    return None


def upload_references_files_api(client: genai.Client, image_paths: list[str]) -> list:
    """Upload reference images via Files API (BEST quality — Lesson #1).
    
    Files API scores 8.2 human rating vs 5.2-6.0 for inline base64.
    ALWAYS use this method unless it fails.
    """
    uploaded = []
    for path in image_paths:
        console.print(f"  📡 Uploading via Files API: [cyan]{to_tilde_path(path)}[/cyan]")
        fref = client.files.upload(file=path)
        uploaded.append(fref)
    return uploaded


def load_references_pil(image_paths: list[str]) -> list[PILImage.Image]:
    """Load reference images as PIL objects (FALLBACK — lower quality)."""
    images = []
    for path in image_paths:
        im = PILImage.open(path)
        if im.mode != "RGB":
            im = im.convert("RGB")
        images.append(im)
        console.print(f"  📸 Loaded (PIL): [green]{to_tilde_path(path)}[/green]")
    return images


def generate_image(
    client: genai.Client,
    prompt: str,
    references: list,  # Files API refs or PIL images
    model: str = "gemini-3.1-flash-image-preview",
    seed: int | None = None,
    output_path: Path | None = None,
    previous_image: PILImage.Image | None = None,
) -> tuple[PILImage.Image | None, str]:
    """Generate a single image with character consistency.
    
    Returns: (PIL image or None, model name that succeeded)
    
    Uses model fallback chain if primary model fails.
    
    If previous_image is provided (edit mode), includes it in the payload
    so the model can refine from the previous iteration rather than
    generating from scratch.
    """
    models_to_try = [model] + [m for m in DEFAULT_MODELS if m != model]
    
    # Build payload: references + [previous image if edit] + prompt
    if previous_image is not None:
        # Edit mode: include previous image for refinement
        payload = references + [previous_image, f"Refine this image. {prompt}"]
        console.print(f"  📎 Including previous image for refinement (edit mode)")
    else:
        payload = references + [prompt]
    
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
    )
    if seed is not None:
        config.seed = seed
    
    for model_name in models_to_try:
        console.print(f"  ⚡ Trying: [cyan]{model_name}[/cyan]")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=payload,
                config=config,
            )
            if (response.candidates and 
                response.candidates[0].content and 
                response.candidates[0].content.parts):
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                        import io
                        out_img = PILImage.open(io.BytesIO(part.inline_data.data))
                        if output_path:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            out_img.save(output_path)
                            console.print(f"  ✅ Saved: [blue]{to_tilde_path(output_path)}[/blue]")
                        return out_img, model_name
            console.print(f"  [dim]No image data from {model_name}[/dim]")
        except Exception as e:
            console.print(f"  [red]Failed with {model_name}: {e}[/red]")
    
    return None, ""
