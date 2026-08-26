#!/usr/bin/env python3
"""Multi-character, multi-model LOO calibration.

For each character (kate, kate2016, riccardo):
  - LOO: judge 2 of their own photos against the rest (POSITIVE, expect 8+)
  - Cross: judge a photo from EACH OTHER character (NEGATIVE, expect ≤2)

Tests across 5+ models. Produces a comprehensive calibration matrix.
"""
import json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "portr8"))

from google import genai
from google.genai import types
from rich.console import Console
from rich.table import Table
from PIL import Image

from lib.judge import build_judge_prompt, JudgeVerdict

console = Console()

BASE = Path(os.path.expanduser("~/git/portr8/data/characters"))

CHARACTERS = {
    "kate": {
        "dir": BASE / "kate",
        "prompt": "A portrait photo of Kate",
    },
    "kate2016": {
        "dir": BASE / "kate2016",
        "prompt": "A portrait photo of Kate",
    },
    "riccardo": {
        "dir": BASE / "riccardo",
        "prompt": "A portrait photo of Riccardo",
    },
}

MODELS = [
    "gemini-3.5-flash",          # current judge
    "gemini-3.1-flash-lite",     # best self-score
    "gemini-3.1-pro-preview",    # pro
    "gemini-2.5-flash-lite",     # best spread
    "gemini-3.7-flash",          # newest
]


def get_photos(char_dir, max_photos=8):
    """Get photos from a character dir, skip subdirs and non-image files."""
    photos = []
    for ext in ["*.jpg", "*.JPG", "*.jpeg", "*.png", "*.PNG"]:
        photos.extend(char_dir.glob(ext))
    # Filter out subdirectory contents
    photos = [p for p in photos if p.parent == char_dir]
    photos = sorted(photos)[:max_photos]
    return photos


def judge_one(client, target_path, ref_paths, prompt, char_name, model):
    """Return facial_similarity score or None on error."""
    try:
        contents = [Image.open(rp) for rp in ref_paths]
        contents.append(Image.open(target_path))
        contents.append(build_judge_prompt(prompt=prompt, character_name=char_name))
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JudgeVerdict,
                temperature=0.2,
            ),
        )
        v = JudgeVerdict.model_validate_json(response.text.strip())
        return v.facial_similarity
    except Exception as e:
        console.print(f"      [red]ERR: {type(e).__name__}: {str(e)[:60]}[/red]")
        return None


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]GEMINI_API_KEY not set![/red]")
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    # Load all photos
    char_photos = {}
    for name, cfg in CHARACTERS.items():
        photos = get_photos(cfg["dir"])
        char_photos[name] = photos
        console.print(f"  {name}: {len(photos)} photos")

    results = []  # list of dicts

    for model in MODELS:
        console.print(f"\n{'='*70}")
        console.print(f"[bold cyan]📊 MODEL: {model}[/bold cyan]")
        console.print(f"{'='*70}")

        for char_name, cfg in CHARACTERS.items():
            photos = char_photos[char_name]
            if len(photos) < 3:
                console.print(f"  [yellow]⚠️ {char_name}: only {len(photos)} photos, skipping LOO[/yellow]")
                continue

            prompt = cfg["prompt"]

            # POSITIVE: LOO with first 2 photos as targets
            console.print(f"\n  [green]✅ {char_name} self-recognition (LOO)[/green]")
            for i in range(min(2, len(photos))):
                target = photos[i]
                refs = [p for j, p in enumerate(photos) if j != i]
                score = judge_one(client, target, refs, prompt, char_name, model)
                sym = "✅" if score and score >= 8.0 else ("🟨" if score and score >= 7.0 else "🔴")
                console.print(f"    {target.name[:30]:30s} → {score or 'ERR':>5} {sym}")
                results.append({
                    "model": model, "character": char_name,
                    "test_type": "positive_loo", "target": target.name,
                    "score": score, "expected": ">=8.0",
                })
                time.sleep(0.5)  # gentle rate limit

            # NEGATIVE: cross-character (use first photo from each OTHER char)
            console.print(f"  [red]❌ {char_name} vs wrong persons[/red]")
            for other_name, other_cfg in CHARACTERS.items():
                if other_name == char_name:
                    continue
                other_photos = char_photos[other_name]
                if not other_photos:
                    continue
                wrong_target = other_photos[0]
                score = judge_one(client, wrong_target, photos, prompt, char_name, model)
                sym = "✅" if score and score <= 2.0 else ("🟨" if score and score <= 3.5 else "🔴")
                console.print(f"    {other_name}({wrong_target.name[:20]:20s}) → {score or 'ERR':>5} {sym}")
                results.append({
                    "model": model, "character": char_name,
                    "test_type": "negative_cross", "target": f"{other_name}:{wrong_target.name}",
                    "score": score, "expected": "<=2.0",
                })
                time.sleep(0.5)

    # === SUMMARY TABLE ===
    console.print(f"\n\n{'='*90}")
    console.print(f"[bold]📊 GRAND SUMMARY — Multi-Character × Multi-Model Calibration[/bold]")
    console.print(f"{'='*90}\n")

    for model in MODELS:
        table = Table(title=f"🔬 {model}")
        table.add_column("Character", style="cyan", max_width=12)
        table.add_column("Self Avg", justify="center", max_width=8)
        table.add_column("vs Kate", justify="center", max_width=8)
        table.add_column("vs Kate2016", justify="center", max_width=10)
        table.add_column("vs Riccardo", justify="center", max_width=10)
        table.add_column("Best Spread", justify="center", style="bold", max_width=10)

        for char_name in CHARACTERS:
            # Self scores
            self_scores = [r["score"] for r in results
                          if r["model"] == model and r["character"] == char_name
                          and r["test_type"] == "positive_loo" and r["score"] is not None]
            self_avg = sum(self_scores) / len(self_scores) if self_scores else 0

            # Cross scores
            cross = {}
            for r in results:
                if (r["model"] == model and r["character"] == char_name
                    and r["test_type"] == "negative_cross" and r["score"] is not None):
                    other = r["target"].split(":")[0]
                    cross[other] = r["score"]

            # Worst cross (highest wrong score = worst discrimination)
            worst_cross = max(cross.values()) if cross else 99
            spread = self_avg - worst_cross if cross else 0

            row = [char_name]
            sc = "green" if self_avg >= 8.5 else ("yellow" if self_avg >= 7.0 else "red")
            row.append(f"[{sc}]{self_avg:.1f}[/{sc}]")

            for other in ["kate", "kate2016", "riccardo"]:
                if other == char_name:
                    row.append("—")
                elif other in cross:
                    v = cross[other]
                    c = "green" if v <= 2.0 else ("yellow" if v <= 3.5 else "red")
                    row.append(f"[{c}]{v:.1f}[/{c}]")
                else:
                    row.append("—")

            spc = "green" if spread >= 6.0 else ("yellow" if spread >= 4.0 else "red")
            row.append(f"[{spc}]{spread:.1f}[/{spc}]")
            table.add_row(*row)

        console.print(table)
        console.print()

    # Save
    out_path = Path(os.path.expanduser("~/git/portr8/out/multichar_calibration.json"))
    out_path.write_text(json.dumps(results, indent=2, default=str))
    console.print(f"💾 Saved: {out_path}")


if __name__ == "__main__":
    main()
