#!/usr/bin/env python3
"""Re-judge Kate São Paulo images with different models, temps, and ref counts."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "portr8"))

from google import genai
from google.genai import types
from rich.console import Console
from rich.table import Table
from PIL import Image

from lib.judge import build_judge_prompt, JudgeVerdict

console = Console()

RUN_DIR = Path(os.path.expanduser("~/git/portr8/out/20260826-1747-kate-at-a-corporate-work-meeting-in-sao"))
CHAR_DIR = Path(os.path.expanduser("~/git/portr8/data/characters/kate"))
HUMAN_VOTE = json.loads((RUN_DIR / "human_vote.json").read_text())

KEY_ITERS = [1, 5, 7, 12, 14, 19]

CONFIGS = [
    {"model": "gemini-3.5-flash", "temp": 0.0, "label": "3.5-flash t=0.0"},
    {"model": "gemini-3.5-flash", "temp": 0.2, "label": "3.5-flash t=0.2 ★"},
    {"model": "gemini-3.5-flash", "temp": 0.5, "label": "3.5-flash t=0.5"},
    {"model": "gemini-2.5-flash", "temp": 0.0, "label": "2.5-flash t=0.0"},
    {"model": "gemini-2.5-flash", "temp": 0.2, "label": "2.5-flash t=0.2"},
    {"model": "gemini-2.5-pro",   "temp": 0.0, "label": "2.5-pro t=0.0"},
    {"model": "gemini-2.5-pro",   "temp": 0.2, "label": "2.5-pro t=0.2"},
]

# Reference sets
ALL_REFS = sorted([
    str(p) for p in CHAR_DIR.glob("*.jpg")
    if "bad" not in str(p).lower() and "legacy" not in str(p).lower()
] + [
    str(p) for p in CHAR_DIR.glob("*.JPG")
    if "bad" not in str(p).lower() and "legacy" not in str(p).lower()
])
BEST_2 = ALL_REFS[:2] if len(ALL_REFS) >= 2 else ALL_REFS

REF_SETS = [
    {"refs": ALL_REFS, "label": f"all-{len(ALL_REFS)}"},
    {"refs": BEST_2, "label": f"best-2"},
]

PROMPT = "Kate at a corporate work meeting in São Paulo, Brazil, holding a green purse, surrounded by Brazilian colleagues at a Mondelez conference room"

def judge_one(client, image_path, ref_paths, model, temp):
    """Judge a single image with given config, return facial score."""
    try:
        # Build contents: refs first, then generated, then prompt
        contents = []
        for rp in ref_paths:
            contents.append(Image.open(rp))
        contents.append(Image.open(image_path))
        contents.append(build_judge_prompt(
            prompt=PROMPT,
            character_name="kate",
        ))

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JudgeVerdict,
                temperature=temp,
            ),
        )
        verdict = JudgeVerdict.model_validate_json(response.text.strip())
        return verdict.facial_similarity
    except Exception as e:
        console.print(f"    [red]ERR: {e}[/red]")
        return None

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]❌ GEMINI_API_KEY not set![/red]")
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    human = {i: HUMAN_VOTE["ratings"][f"iter_{i:02d}"]["human_facial"] for i in KEY_ITERS}

    console.print(f"\n[bold]🗳️ Kate Re-Judging: {len(KEY_ITERS)} imgs × {len(CONFIGS)} models × {len(REF_SETS)} ref sets[/bold]")
    console.print(f"Human: {human}\nRefs available: {[Path(r).name for r in ALL_REFS]}\n")

    results = {}

    for rs in REF_SETS:
        for cfg in CONFIGS:
            key = f"{cfg['label']} | {rs['label']}"
            results[key] = {}
            console.print(f"[cyan]{key}[/cyan]")

            for it in KEY_ITERS:
                img = RUN_DIR / f"iter_{it:02d}.png"
                if not img.exists():
                    console.print(f"  iter {it}: MISSING")
                    continue

                score = judge_one(client, img, rs["refs"], cfg["model"], cfg["temp"])
                results[key][it] = score
                h = human[it]
                d = f"{score - h:+.1f}" if score is not None else "ERR"
                sym = "✅" if score and abs(score - h) <= 0.5 else ("🟨" if score and abs(score - h) <= 1.0 else "🔴")
                console.print(f"  #{it}: judge={score or 'ERR'} human={h} Δ={d} {sym}")

    # Summary
    console.print(f"\n{'='*90}")
    table = Table(title="📊 Judge vs Human — Calibration Matrix")
    table.add_column("Config", style="cyan", max_width=30)
    for i in KEY_ITERS:
        table.add_column(f"#{i}\nH={human[i]}", justify="center", max_width=6)
    table.add_column("Bias", justify="center", style="bold", max_width=6)
    table.add_column("MAE", justify="center", style="bold", max_width=6)

    best_mae = 999
    best_key = ""

    for key, scores in results.items():
        row = [key]
        biases, aes = [], []
        for i in KEY_ITERS:
            s = scores.get(i)
            h = human[i]
            if s is not None:
                b = s - h
                biases.append(b)
                aes.append(abs(b))
                c = "green" if abs(b) <= 0.5 else ("yellow" if abs(b) <= 1.0 else "red")
                row.append(f"[{c}]{s:.1f}[/{c}]")
            else:
                row.append("[red]ERR[/red]")

        avg_b = sum(biases) / len(biases) if biases else 0
        mae = sum(aes) / len(aes) if aes else 99
        if mae < best_mae:
            best_mae = mae
            best_key = key

        bc = "green" if abs(avg_b) <= 0.3 else ("yellow" if abs(avg_b) <= 0.7 else "red")
        mc = "green" if mae <= 0.7 else ("yellow" if mae <= 1.2 else "red")
        row.append(f"[{bc}]{avg_b:+.1f}[/{bc}]")
        row.append(f"[{mc}]{mae:.1f}[/{mc}]")
        table.add_row(*row)

    console.print(table)
    console.print(f"\n🏆 [bold green]Best config: {best_key} (MAE={best_mae:.2f})[/bold green]")

    # Save
    out = {"human": human, "results": {k: {str(i): v for i, v in s.items()} for k, s in results.items()}}
    (RUN_DIR / "calibration_results.json").write_text(json.dumps(out, indent=2))
    console.print(f"💾 Saved calibration_results.json")

if __name__ == "__main__":
    main()
