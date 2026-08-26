import os
from pathlib import Path
from PIL import Image as PILImage
import pytest

from lib.generator import (
    to_tilde_path,
    resolve_character_images,
    load_references_pil,
    generate_image,
)

def create_test_image(path: Path, size=(10, 10)):
    """Create a tiny test image."""
    img = PILImage.new('RGB', size, color='red')
    img.save(path)

def test_to_tilde_path():
    home = os.path.expanduser("~")
    test_path = os.path.join(home, "some_dir", "file.txt")
    assert to_tilde_path(test_path) == "~/some_dir/file.txt"
    
    # Test path outside home (if possible, like /tmp)
    out_path = "/tmp/some_file.txt"
    if not out_path.startswith(home):
        assert to_tilde_path(out_path) == "/tmp/some_file.txt"

def test_resolve_character_images(tmp_path):
    char_dir = tmp_path / "jane"
    char_dir.mkdir()
    
    # Create some root images
    create_test_image(char_dir / "1.jpg")
    create_test_image(char_dir / "2.png")
    
    res = resolve_character_images("jane", ref_dir=str(tmp_path))
    assert len(res) == 2
    assert all("jane" in p for p in res)
    
    # Create grid_cleaned dir
    grid_dir = char_dir / "grid_cleaned"
    grid_dir.mkdir()
    create_test_image(grid_dir / "grid1.jpg")
    
    # Should prioritize grid_cleaned
    res2 = resolve_character_images("jane", ref_dir=str(tmp_path))
    assert len(res2) == 1
    assert "grid1.jpg" in res2[0]

def test_resolve_character_images_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_character_images("missing_char", ref_dir=str(tmp_path))

def test_load_references_pil(tmp_path):
    img_path = tmp_path / "test.jpg"
    create_test_image(img_path)
    
    imgs = load_references_pil([str(img_path)])
    assert len(imgs) == 1
    assert isinstance(imgs[0], PILImage.Image)
    assert imgs[0].mode == "RGB"

def test_generate_image_importable():
    # We just want to make sure it's importable and the signature is there.
    assert callable(generate_image)

def test_load_character_metadata(tmp_path):
    from lib.generator import load_character_metadata, load_characters_metadata
    char_dir = tmp_path / "riccardo2016"
    char_dir.mkdir()
    yaml_content = """
name: Riccardo
birth_year: 1980
appearance:
  hair: "short dark brown hair"
  facial_hair: "clean-shaven, no beard"
  face_structure: "friendly open face"
prompt_guidelines:
  must_include:
    - "casual open-collar shirt"
  must_avoid:
    - "formal suit, beard"
"""
    (char_dir / "character.yaml").write_text(yaml_content)
    
    meta = load_character_metadata("riccardo2016", ref_dir=str(tmp_path))
    assert meta is not None
    assert meta.name == "Riccardo"
    assert meta.hair == "short dark dark hair" or "dark" in meta.hair
    assert "clean-shaven" in meta.facial_hair
    
    bp = meta.to_biometric_blueprint()
    assert "Hair: short dark brown hair" in bp
    assert "Facial hair: clean-shaven, no beard" in bp
    assert "casual open-collar shirt" in bp
    
    # Test batch loading
    multi_meta = load_characters_metadata(["riccardo2016"], ref_dir=str(tmp_path))
    assert "riccardo2016" in multi_meta
