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
"""Regenerate a portr8 report from an existing run directory."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from lib.models import RunConfig, RunSummary
from lib.ledger import Ledger
from lib.reporter import generate_report
from lib.generator import to_tilde_path

console = Console()


def main():
    parser = argparse.ArgumentParser(description="📊 Regenerate portr8 report from existing run")
    parser.add_argument("--run-dir", required=True, help="Path to run output directory")
    args = parser.parse_args()
    
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        console.print(f"[red]Run directory not found: {run_dir}[/red]")
        sys.exit(1)
    
    # Load config
    config_path = run_dir / "run_config.json"
    if not config_path.exists():
        console.print(f"[red]No run_config.json found in {run_dir}[/red]")
        sys.exit(1)
    config = RunConfig.model_validate_json(config_path.read_text())
    
    # Load ledger
    ledger = Ledger(run_dir)
    records = ledger.load()
    if not records:
        console.print(f"[red]No records in ledger[/red]")
        sys.exit(1)
    
    # Generate summary and report
    summary = ledger.to_summary(config)
    report_path = generate_report(summary, run_dir)
    
    console.print(f"\u2705 Report generated: [blue]{to_tilde_path(report_path)}[/blue]")
    console.print(f"   {len(records)} iterations, best: Iter {summary.best_iteration + 1}")


if __name__ == "__main__":
    main()
