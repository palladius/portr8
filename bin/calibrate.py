#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "google-genai>=1.0.0",
#     "rich>=13.0.0",
#     "pydantic>=2.0.0",
#     "pillow>=10.0.0",
#     "python-slugify>=8.0.0",
# ]
# ///
"""portr8 calibrate — Generate N images and collect AI + human ratings.

Use this to calibrate the AI judge against human ratings.
Results are saved to calibration/ for later analysis.

Usage:
    uv run ./bin/calibrate.py -c riccardo -p "Riccardo at a cafe" --num-images 5
    uv run ./bin/calibrate.py -c riccardo -p "..." --judge-models gemini-3.5-flash,gemini-3.6-flash
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import FloatPrompt
from google import genai

from lib.generator import (
    resolve_character_images,
    upload_references_files_api,
    load_references_pil,
    generate_image,
    to_tilde_path,
)
from lib.judge import judge_image
from lib.overlay import create_score_overlay

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(description="📏 portr8 calibrate — AI judge calibration tool")
    parser.add_argument("-c", "--character", required=True)
    parser.add_argument("-p", "--prompt", required=True)
    parser.add_argument("--num-images", type=int, default=5)
    parser.add_argument("--image-model", default="gemini-3.1-flash-image-preview")
    parser.add_argument("--judge-models", default="gemini-3.5-flash",
                        help="Comma-separated judge models to compare")
    parser.add_argument("--ref-transport", choices=["files_api", "pil"], default="files_api")
    parser.add_argument("--interactive", action="store_true",
                        help="Prompt for human ratings after each image")
    return parser.parse_args()


def main():
    args = parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[bold red]❌ GEMINI_API_KEY not set[/bold red]")
        sys.exit(1)
    
    judge_models = [m.strip() for m in args.judge_models.split(",")]
    
    # Create calibration output directory
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    cal_dir = Path("calibration") / f"{timestamp}-{args.character}"
    cal_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"\n📏 [bold cyan]portr8 Calibration[/bold cyan]")
    console.print(f"  Character: {args.character}")
    console.print(f"  Images: {args.num_images}")
    console.print(f"  Judge models: {', '.join(judge_models)}")
    console.print(f"  Output: {to_tilde_path(cal_dir)}")
    
    # Resolve references
    ref_paths = resolve_character_images(args.character)
    client = genai.Client(api_key=api_key)
    
    if args.ref_transport == "files_api":
        try:
            references = upload_references_files_api(client, ref_paths)
        except Exception:
            references = load_references_pil(ref_paths)
    else:
        references = load_references_pil(ref_paths)
    
    # Results collection
    results = []  # List of dicts: {image_path, judge_model, verdict, human_score}
    
    for img_idx in range(args.num_images):
        console.print(f"\n{'='*50}")
        console.print(f"🎨 Generating image {img_idx + 1}/{args.num_images}...")
        
        img_path = cal_dir / f"cal_{img_idx + 1:02d}.png"
        generated, model_used = generate_image(
            client=client,
            prompt=args.prompt,
            references=references,
            model=args.image_model,
            output_path=img_path,
        )
        
        if generated is None:
            console.print("[red]Generation failed, skipping[/red]")
            continue
        
        # Judge with each model
        for judge_model in judge_models:
            console.print(f"\n  👨⚖️ Judging with {judge_model}...")
            try:
                verdict = judge_image(
                    client=client,
                    image_path=img_path,
                    reference_paths=ref_paths,
                    prompt=args.prompt,
                    character_name=args.character,
                    model=judge_model,
                )
                
                create_score_overlay(img_path, verdict, img_idx + 1,
                                     cal_dir / f"cal_{img_idx + 1:02d}_{judge_model}_scored.png")
                
                result = {
                    "image_idx": img_idx + 1,
                    "image_path": to_tilde_path(img_path),
                    "judge_model": judge_model,
                    "facial_similarity": verdict.facial_similarity,
                    "scene_adaptation": verdict.scene_adaptation,
                    "adherence_score": verdict.adherence_score,
                    "is_photorealistic": verdict.is_photorealistic,
                    "anti_beautification_flag": verdict.anti_beautification_flag,
                    "verdict_label": verdict.verdict_label,
                    "human_facial_similarity": None,
                    "human_adherence": None,
                    "status": "PENDING_HUMAN",
                }
                
                # Interactive human rating
                if args.interactive:
                    console.print(f"\n  👁️  Please look at: {img_path}")
                    try:
                        h_r = FloatPrompt.ask("  Human resemblance (0-10)", default=0.0)
                        h_a = FloatPrompt.ask("  Human adherence (0-10)", default=0.0)
                        result["human_resemblance"] = h_r
                        result["human_adherence"] = h_a
                        result["status"] = "RATED"
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n  [dim]Skipped human rating[/dim]")
                
                results.append(result)
                
            except Exception as e:
                console.print(f"  [red]Judge error: {e}[/red]")
    
    # Save results as JSONL
    results_path = cal_dir / "calibration.jsonl"
    with open(results_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    
    # Print summary table
    _print_calibration_summary(results, judge_models)
    
    console.print(f"\n💾 Results saved: [blue]{to_tilde_path(results_path)}[/blue]")
    console.print(f"   Edit calibration.jsonl to add human_resemblance/human_adherence scores")


def _print_calibration_summary(results, judge_models):
    """Print calibration summary table."""
    table = Table(title="📏 Calibration Summary")
    table.add_column("Judge Model")
    table.add_column("Avg R", justify="right")
    table.add_column("Avg A", justify="right")
    table.add_column("N", justify="right")
    table.add_column("Photo %", justify="right")
    
    for model in judge_models:
        model_results = [r for r in results if r["judge_model"] == model]
        if not model_results:
            continue
        avg_r = sum(r["resemblance_score"] for r in model_results) / len(model_results)
        avg_a = sum(r["adherence_score"] for r in model_results) / len(model_results)
        photo_pct = sum(1 for r in model_results if r["is_photorealistic"]) / len(model_results) * 100
        table.add_row(
            model,
            f"{avg_r:.1f}",
            f"{avg_a:.1f}",
            str(len(model_results)),
            f"{photo_pct:.0f}%",
        )
    
    console.print(table)


if __name__ == "__main__":
    main()
