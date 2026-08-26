#!/usr/bin/env python3
"""Multi-model LOO: Score Kate's own photos across every Gemini model.

Tests 3 Kate photos + 1 wrong person across multiple models.
Goal: find which model has the widest spread (high for Kate, low for wrong).
"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "portr8"))

from google import genai
from google.genai import types
from rich.console import Console
from rich.table import Table
from PIL import Image

from lib.judge import build_judge_prompt, JudgeVerdict

console = Console()

CHAR_DIR = Path(os.path.expanduser("~/git/portr8/data/characters/kate"))
RUN_DIR = Path(os.path.expanduser("~/git/portr8/out/20260826-1747-kate-at-a-corporate-work-meeting-in-sao"))

# Use 3 best Kate photos as targets (leave-one-out from refs)
KATE_ALL = sorted([
    p for p in list(CHAR_DIR.glob("*.jpg")) + list(CHAR_DIR.glob("*.JPG")) + list(CHAR_DIR.glob("*.png"))
    if "bad" not in str(p).lower() and "legacy" not in str(p).lower() 
       and "grid" not in str(p).lower() and "better" not in str(p).lower()
])

# Pick 3 representative Kate targets + use rest as refs
KATE_TARGETS = ["COLOR_POP.jpg", "IMG_9817.JPG", "PXL_20230106_141651928.jpg"]
WRONG_TARGET = RUN_DIR / "iter_12.png"

PROMPT = "A portrait photo of Kate"

MODELS = [
    "gemini-3.5-flash",          # current judge
    "gemini-3.7-flash",          # newest flash
    "gemini-3.6-flash",          # mid flash
    "gemini-3.1-flash-lite",     # lite
    "gemini-3.1-pro-preview",    # pro!
    "gemini-omni-flash-preview", # omni!
    "gemini-2.5-flash-lite",     # old lite
]


def judge_one(client, target_path, ref_paths, model):
    """Return facial_similarity score."""
    try:
        contents = [Image.open(rp) for rp in ref_paths]
        contents.append(Image.open(target_path))
        contents.append(build_judge_prompt(prompt=PROMPT, character_name="kate"))
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
        console.print(f"    [red]ERR: {type(e).__name__}: {str(e)[:80]}[/red]")
        return None


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]❌ GEMINI_API_KEY not set![/red]")
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    console.print(f"\n[bold]🔬 Multi-Model Kate LOO — {len(MODELS)} models[/bold]")
    console.print(f"Kate photos: {len(KATE_ALL)}, Targets: {KATE_TARGETS}")
    console.print(f"Wrong person: {WRONG_TARGET.name}\n")

    results = {}  # model -> {target: score}

    for model in MODELS:
        console.print(f"[cyan bold]📊 {model}[/cyan bold]")
        results[model] = {}

        # Kate LOO tests
        for target_name in KATE_TARGETS:
            target_path = CHAR_DIR / target_name
            if not target_path.exists():
                console.print(f"  ⚠️ {target_name} not found")
                continue
            refs = [p for p in KATE_ALL if p.name != target_name]
            score = judge_one(client, target_path, refs, model)
            results[model][target_name] = score
            sym = "✅" if score and score >= 8.0 else ("🟨" if score and score >= 7.0 else "🔴")
            console.print(f"  Kate [{target_name:30s}]: {score or 'ERR':>5} {sym}")

        # Wrong person
        if WRONG_TARGET.exists():
            score = judge_one(client, WRONG_TARGET, KATE_ALL, model)
            results[model]["WRONG"] = score
            sym = "✅" if score and score <= 2.0 else ("🟨" if score and score <= 3.5 else "🔴")
            console.print(f"  WRONG [iter_12.png              ]: {score or 'ERR':>5} {sym}")

    # Summary table
    console.print(f"\n{'='*90}")
    table = Table(title="🔬 Multi-Model Kate Self-Recognition")
    table.add_column("Model", style="cyan", max_width=28)
    for t in KATE_TARGETS:
        table.add_column(t[:12], justify="center", max_width=8)
    table.add_column("Kate Avg", justify="center", style="bold", max_width=8)
    table.add_column("WRONG", justify="center", style="bold", max_width=8)
    table.add_column("Spread", justify="center", style="bold", max_width=8)

    best_spread = 0
    best_model = ""

    for model in MODELS:
        row = [model]
        kate_scores = []
        for t in KATE_TARGETS:
            s = results[model].get(t)
            if s is not None:
                kate_scores.append(s)
                c = "green" if s >= 8.0 else ("yellow" if s >= 7.0 else "red")
                row.append(f"[{c}]{s:.1f}[/{c}]")
            else:
                row.append("[red]ERR[/red]")

        avg = sum(kate_scores) / len(kate_scores) if kate_scores else 0
        wrong = results[model].get("WRONG")
        spread = avg - wrong if wrong is not None else 0

        if spread > best_spread:
            best_spread = spread
            best_model = model

        ac = "green" if avg >= 8.5 else ("yellow" if avg >= 7.5 else "red")
        wc = "green" if wrong and wrong <= 2.0 else ("yellow" if wrong and wrong <= 3.5 else "red")
        sc = "green" if spread >= 7.0 else ("yellow" if spread >= 5.0 else "red")

        row.append(f"[{ac}]{avg:.1f}[/{ac}]")
        row.append(f"[{wc}]{wrong:.1f}[/{wc}]" if wrong is not None else "[red]ERR[/red]")
        row.append(f"[{sc}]{spread:.1f}[/{sc}]")
        table.add_row(*row)

    console.print(table)
    console.print(f"\n🏆 [bold green]Best model: {best_model} (spread={best_spread:.1f})[/bold green]")

    # Save
    out_path = Path(os.path.expanduser("~/git/portr8/out/multimodel_loo.json"))
    out_path.write_text(json.dumps(results, indent=2, default=str))
    console.print(f"💾 Saved: {out_path}")


if __name__ == "__main__":
    main()
