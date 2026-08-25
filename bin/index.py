#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.0.0"]
# ///
"""portr8 index generator — scans out/ and generates index.md from all summary.json files.

Usage:
    uv run ./bin/index.py              # Generate out/index.md
    uv run ./bin/index.py --format md  # Markdown (default)
    uv run ./bin/index.py --format csv # CSV output
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.models import RunSummary


def scan_runs(out_dir: Path) -> list[tuple[Path, RunSummary]]:
    """Scan out/ for all summary.json files, return sorted newest-first."""
    runs = []
    for summary_file in sorted(out_dir.glob("*/summary.json"), reverse=True):
        try:
            data = json.loads(summary_file.read_text())
            summary = RunSummary(**data)
            runs.append((summary_file.parent, summary))
        except Exception as e:
            print(f"  Skipping {summary_file}: {e}", file=sys.stderr)
    return runs


def generate_index_md(runs: list[tuple[Path, RunSummary]], out_dir: Path) -> str:
    """Generate a Markdown index of all runs."""
    lines = [
        "# portr8 — Run Index",
        "",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(runs)} runs",
        "",
        "| Date | Prompt | Character | Type | Target | Iters | Best F | Best S | Best A | Status | Links |",
        "|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    
    for run_dir, s in runs:
        date = run_dir.name[:8]  # YYYYMMDD
        date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        prompt = s.config.prompt[:40] + ("..." if len(s.config.prompt) > 40 else "")
        status = "ok" if s.converged else "fail"
        
        # Links
        links = []
        graph_file = run_dir / "convergence.png"
        if graph_file.exists():
            links.append(f"[graph]({run_dir.name}/convergence.png)")
        report_file = run_dir / "report.md"
        if report_file.exists():
            links.append(f"[report]({run_dir.name}/report.md)")
        scored = run_dir / f"iter_{s.best_iteration + 1:02d}_scored.png"
        if scored.exists():
            links.append(f"[best]({run_dir.name}/{scored.name})")
        
        links_str = " ".join(links)
        
        lines.append(
            f"| {date_fmt} | {prompt} | {s.config.character} | "
            f"{s.config.image_type} | {s.config.target_score} | "
            f"{len(s.iterations)} | {s.best_facial_similarity:.1f} | "
            f"{s.best_scene_adaptation:.1f} | "
            f"{s.best_adherence:.1f} | {status} | {links_str} |"
        )
    
    # Stats section
    total = len(runs)
    converged = sum(1 for _, s in runs if s.converged)
    if total > 0:
        lines.extend([
            "",
            "---",
            "",
            "## Stats",
            "",
            f"- **Total runs**: {total}",
            f"- **Converged**: {converged}/{total} ({100*converged/total:.0f}%)",
            f"- **Failed**: {total - converged}/{total}",
        ])
        
        # Best ever
        best_run = max(runs, key=lambda x: x[1].best_facial_similarity)
        lines.append(
            f"- **Best facial similarity**: {best_run[1].best_facial_similarity:.1f} "
            f"({best_run[0].name})"
        )
    
    return "\n".join(lines) + "\n"


def generate_index_csv(runs: list[tuple[Path, RunSummary]]) -> str:
    """Generate CSV index of all runs."""
    lines = ["date,prompt,character,image_type,target,iterations,best_f,best_s,best_a,converged,dir"]
    for run_dir, s in runs:
        prompt_csv = s.config.prompt.replace('"', '""')
        lines.append(
            f'{run_dir.name[:8]},"{prompt_csv}",{s.config.character},'
            f'{s.config.image_type},{s.config.target_score},{len(s.iterations)},'
            f'{s.best_facial_similarity:.1f},{s.best_scene_adaptation:.1f},'
            f'{s.best_adherence:.1f},{s.converged},{run_dir.name}'
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate portr8 run index")
    parser.add_argument("--format", choices=["md", "csv"], default="md", help="Output format")
    parser.add_argument("--out-dir", type=Path, default=Path("out"), help="Output directory to scan")
    args = parser.parse_args()
    
    if not args.out_dir.exists():
        print(f"Output directory not found: {args.out_dir}", file=sys.stderr)
        sys.exit(1)
    
    runs = scan_runs(args.out_dir)
    print(f"Found {len(runs)} run(s) in {args.out_dir}/")
    
    if args.format == "csv":
        content = generate_index_csv(runs)
        output_file = args.out_dir / "index.csv"
    else:
        content = generate_index_md(runs, args.out_dir)
        output_file = args.out_dir / "index.md"
    
    output_file.write_text(content)
    print(f"Index written: {output_file}")


if __name__ == "__main__":
    main()
