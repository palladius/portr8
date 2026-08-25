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
"""portr8 human_rate — Review and override AI judge scores with human ratings.

Reads a portr8 ledger.jsonl, shows each image with its AI scores,
and lets a human provide their own resemblance and adherence scores.
Outputs a new file with human overrides.

Usage:
    uv run ./bin/human_rate.py --run-dir out/20250825-1430-riccardo-eats-gelato/
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import FloatPrompt, Confirm
from lib.models import IterationRecord
from lib.generator import to_tilde_path

console = Console()


def load_ledger(ledger_path: Path) -> list[dict]:
    """Load raw JSON records from ledger."""
    records = []
    with open(ledger_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_human_ratings(records: list[dict], output_path: Path) -> None:
    """Save records with human ratings to JSONL."""
    with open(output_path, 'w') as f:
        for r in records:
            f.write(json.dumps(r) + '\n')


def main():
    import argparse
    parser = argparse.ArgumentParser(description="👤 portr8 human_rate — Override AI scores")
    parser.add_argument("--run-dir", required=True, help="Path to run output directory")
    parser.add_argument("--output", default=None, help="Output file (default: human_ratings.jsonl in run-dir)")
    args = parser.parse_args()
    
    run_dir = Path(args.run_dir)
    ledger_path = run_dir / "ledger.jsonl"
    
    if not ledger_path.exists():
        console.print(f"[red]No ledger.jsonl found in {run_dir}[/red]")
        sys.exit(1)
    
    records = load_ledger(ledger_path)
    output_path = Path(args.output) if args.output else run_dir / "human_ratings.jsonl"
    
    console.print(f"\n👤 [bold cyan]Human Rating Mode[/bold cyan]")
    console.print(f"  Run directory: {to_tilde_path(run_dir)}")
    console.print(f"  {len(records)} iterations to review")
    console.print(f"  Enter your scores (0-10) or press Enter to skip\n")
    
    for i, record in enumerate(records):
        iteration = record.get("iteration", i + 1)
        verdict = record.get("verdict", {})
        ai_r = verdict.get("facial_similarity", 0)
        ai_a = verdict.get("adherence_score", 0)
        label = verdict.get("verdict_label", "")
        img_path = record.get("image_path", "unknown")
        
        # Resolve tilde path for display
        display_path = img_path.replace("~", os.path.expanduser("~"))
        
        console.print(f"\n{'='*50}")
        console.print(f"🖼️  Iteration {iteration}: [cyan]{img_path}[/cyan]")
        console.print(f"  AI Resemblance: {ai_r:.1f}  |  AI Adherence: {ai_a:.1f}  |  {label}")
        
        # Check if image exists and suggest viewer
        if Path(display_path).exists():
            console.print(f"  👁️  View: [dim]xdg-open '{display_path}'[/dim]")
        
        try:
            h_r = FloatPrompt.ask(
                f"  Your resemblance score (0-10, Enter=skip)",
                default=-1.0
            )
            h_a = FloatPrompt.ask(
                f"  Your adherence score (0-10, Enter=skip)", 
                default=-1.0
            )
            
            if h_r >= 0:
                record.setdefault("human_eval", {})
                record["human_eval"]["facial_similarity"] = min(10.0, max(0.0, h_r))
                record["human_eval"]["status"] = "RATED"
            if h_a >= 0:
                record.setdefault("human_eval", {})
                record["human_eval"]["adherence_score"] = min(10.0, max(0.0, h_a))
                record["human_eval"]["status"] = "RATED"
            
            if h_r < 0 and h_a < 0:
                record.setdefault("human_eval", {})
                record["human_eval"]["status"] = "PENDING_HUMAN"
                console.print("  [dim]Skipped[/dim]")
            else:
                delta_r = h_r - ai_r if h_r >= 0 else 0
                delta_a = h_a - ai_a if h_a >= 0 else 0
                console.print(f"  ΔR: {delta_r:+.1f}  ΔA: {delta_a:+.1f}")
                
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[yellow]Rating interrupted. Saving progress...[/yellow]")
            break
    
    # Save
    save_human_ratings(records, output_path)
    
    # Print summary
    rated = sum(1 for r in records if r.get("human_eval", {}).get("status") == "RATED")
    pending = len(records) - rated
    
    console.print(f"\n✅ Saved: [blue]{to_tilde_path(output_path)}[/blue]")
    console.print(f"  Rated: {rated}/{len(records)} | Pending: {pending}")
    
    # Show AI vs Human comparison if we have ratings
    if rated > 0:
        _print_comparison(records)


def _print_comparison(records: list[dict]) -> None:
    """Print AI vs Human comparison table."""
    table = Table(title="👤 vs 🤖 Score Comparison")
    table.add_column("Iter", style="cyan")
    table.add_column("AI F", justify="right")
    table.add_column("Human F", justify="right")
    table.add_column("ΔF", justify="right")
    table.add_column("AI A", justify="right")
    table.add_column("Human A", justify="right")
    table.add_column("ΔA", justify="right")
    
    for r in records:
        human = r.get("human_eval", {})
        if human.get("status") != "RATED":
            continue
        
        ai_r = r.get("verdict", {}).get("facial_similarity", 0)
        ai_a = r.get("verdict", {}).get("adherence_score", 0)
        h_r = human.get("facial_similarity", 0)
        h_a = human.get("adherence_score", 0)
        
        dr = h_r - ai_r
        da = h_a - ai_a
        dr_style = "red" if abs(dr) > 2 else "yellow" if abs(dr) > 1 else "green"
        da_style = "red" if abs(da) > 2 else "yellow" if abs(da) > 1 else "green"
        
        table.add_row(
            str(r.get("iteration", "?")),
            f"{ai_r:.1f}", f"{h_r:.1f}", f"[{dr_style}]{dr:+.1f}[/{dr_style}]",
            f"{ai_a:.1f}", f"{h_a:.1f}", f"[{da_style}]{da:+.1f}[/{da_style}]",
        )
    
    console.print(table)


if __name__ == "__main__":
    main()
