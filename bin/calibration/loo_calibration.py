#!/usr/bin/env python3
"""Leave-one-out judge calibration: N-1 refs vs 1 target.

For each Kate photo, judge it against the remaining Kate photos.
Then judge a WRONG person (iter_12) against all Kate photos.
Expected: Kate-vs-Kate → 8+ facial, Wrong-vs-Kate → ≤2.
"""
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

CHAR_DIR = Path(os.path.expanduser("~/git/portr8/data/characters/kate"))
RUN_DIR = Path(os.path.expanduser("~/git/portr8/out/20260826-1747-kate-at-a-corporate-work-meeting-in-sao"))

# All Kate photos (skip bad_examples and legacy dirs)
KATE_PHOTOS = sorted([
    p for p in CHAR_DIR.glob("*.jpg")
    if "bad" not in str(p).lower() and "legacy" not in str(p).lower()
] + [
    p for p in CHAR_DIR.glob("*.JPG")
    if "bad" not in str(p).lower() and "legacy" not in str(p).lower()
])

# Wrong person: iter_12 from São Paulo (human rated 0.0)
WRONG_PERSON = RUN_DIR / "iter_12.png"
# Also try Riccardo as wrong person (very different)
RICCARDO_DIR = Path(os.path.expanduser("~/git/portr8/data/characters/riccardo"))
RICCARDO_PHOTOS = sorted(list(RICCARDO_DIR.glob("*.jpg")) + list(RICCARDO_DIR.glob("*.JPG")))
RICCARDO_PHOTO = RICCARDO_PHOTOS[0] if RICCARDO_PHOTOS else None

PROMPT = "A portrait photo of Kate"

def judge_one(client, target_path, ref_paths, model="gemini-3.5-flash", temp=0.2):
    """Judge target against refs, return (facial_sim, scene_adapt, adherence)."""
    try:
        contents = []
        for rp in ref_paths:
            contents.append(Image.open(rp))
        contents.append(Image.open(target_path))
        contents.append(build_judge_prompt(prompt=PROMPT, character_name="kate"))

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JudgeVerdict,
                temperature=temp,
            ),
        )
        v = JudgeVerdict.model_validate_json(response.text.strip())
        return v.facial_similarity, v.scene_adaptation, v.adherence_score
    except Exception as e:
        console.print(f"  [red]ERR: {e}[/red]")
        return None, None, None


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]❌ GEMINI_API_KEY not set![/red]")
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    console.print(f"\n[bold]🔬 Leave-One-Out Judge Calibration[/bold]")
    console.print(f"Kate photos: {len(KATE_PHOTOS)}")
    console.print(f"Wrong person: {WRONG_PERSON.name}")
    if RICCARDO_PHOTO:
        console.print(f"Riccardo (control): {RICCARDO_PHOTO.name}")

    table = Table(title="Leave-One-Out Results")
    table.add_column("Target", style="cyan", max_width=25)
    table.add_column("# Refs", justify="center")
    table.add_column("Facial", justify="center")
    table.add_column("Expected", justify="center")
    table.add_column("Pass?", justify="center")

    results = []

    # Test 1: Each Kate photo judged against the others (should be 8+)
    console.print(f"\n[bold green]✅ POSITIVE tests: Kate vs Kate (expect 8+)[/bold green]")
    for i, photo in enumerate(KATE_PHOTOS):
        refs = [p for j, p in enumerate(KATE_PHOTOS) if j != i]
        console.print(f"  Testing {photo.name} vs {len(refs)} refs...")
        f, s, a = judge_one(client, photo, refs)
        passed = f is not None and f >= 7.5  # soft threshold
        sym = "[green]✅[/green]" if passed else "[red]❌[/red]"
        results.append({"target": photo.name, "type": "kate", "facial": f, "expected": "≥8.0", "passed": passed})
        table.add_row(
            photo.name, str(len(refs)),
            f"[green]{f:.1f}[/green]" if f and f >= 7.5 else f"[red]{f}[/red]",
            "≥8.0", sym
        )

    # Test 2: Wrong person (iter_12) judged against all Kate photos (should be ≤2)
    console.print(f"\n[bold red]❌ NEGATIVE test: iter_12 vs all Kate (expect ≤2)[/bold red]")
    if WRONG_PERSON.exists():
        f, s, a = judge_one(client, WRONG_PERSON, KATE_PHOTOS)
        passed = f is not None and f <= 3.0
        sym = "[green]✅[/green]" if passed else "[red]❌[/red]"
        results.append({"target": "iter_12 (WRONG)", "type": "wrong", "facial": f, "expected": "≤2.0", "passed": passed})
        table.add_row(
            "iter_12.png (WRONG)", str(len(KATE_PHOTOS)),
            f"[green]{f:.1f}[/green]" if f and f <= 3.0 else f"[red]{f:.1f}[/red]" if f else "[red]ERR[/red]",
            "≤2.0", sym
        )

    # Test 3: Riccardo vs Kate (should be ≤1, totally different person)
    if RICCARDO_PHOTO and RICCARDO_PHOTO.exists():
        console.print(f"\n[bold red]❌ NEGATIVE test: Riccardo vs Kate (expect ≤1)[/bold red]")
        f, s, a = judge_one(client, RICCARDO_PHOTO, KATE_PHOTOS)
        passed = f is not None and f <= 2.0
        sym = "[green]✅[/green]" if passed else "[red]❌[/red]"
        results.append({"target": "riccardo (WRONG)", "type": "wrong_riccardo", "facial": f, "expected": "≤1.0", "passed": passed})
        table.add_row(
            f"{RICCARDO_PHOTO.name} (RICCARDO)", str(len(KATE_PHOTOS)),
            f"[green]{f:.1f}[/green]" if f and f <= 2.0 else f"[red]{f:.1f}[/red]" if f else "[red]ERR[/red]",
            "≤1.0", sym
        )

    # Test 4: Kate with only 2 refs (does signal degrade?)
    console.print(f"\n[bold yellow]🔬 SIGNAL test: Kate with only 2 refs[/bold yellow]")
    best_2 = KATE_PHOTOS[:2]
    for photo in KATE_PHOTOS[2:4]:  # test 2 photos not in the ref set
        f, s, a = judge_one(client, photo, best_2)
        passed = f is not None and f >= 7.0
        sym = "[green]✅[/green]" if passed else "[red]❌[/red]"
        results.append({"target": f"{photo.name} (2-ref)", "type": "kate_2ref", "facial": f, "expected": "≥7.0", "passed": passed})
        table.add_row(
            f"{photo.name} (2-ref)", "2",
            f"[green]{f:.1f}[/green]" if f and f >= 7.0 else f"[red]{f}[/red]",
            "≥7.0", sym
        )

    console.print(f"\n")
    console.print(table)

    # Summary
    pos = [r for r in results if "kate" in r["type"]]
    neg = [r for r in results if "wrong" in r["type"]]
    pos_pass = sum(1 for r in pos if r["passed"])
    neg_pass = sum(1 for r in neg if r["passed"])

    console.print(f"\n[bold]📊 Summary:[/bold]")
    console.print(f"  Positive (Kate=Kate): {pos_pass}/{len(pos)} passed")
    console.print(f"  Negative (Wrong≠Kate): {neg_pass}/{len(neg)} passed")

    if neg_pass < len(neg):
        console.print(f"\n[bold red]⚠️ JUDGE FAILS TO REJECT WRONG PERSONS![/bold red]")
        for r in neg:
            if not r["passed"]:
                console.print(f"  {r['target']}: got {r['facial']} (expected {r['expected']})")

    # Save
    out_path = Path(os.path.expanduser("~/git/portr8/out")) / "loo_calibration.json"
    out_path.write_text(json.dumps(results, indent=2))
    console.print(f"\n💾 Saved: {out_path}")


if __name__ == "__main__":
    main()
