#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
#     "python-slugify>=8.0.0",
#     "rich>=13.0.0",
# ]
# ///
"""portr8 index generator — scans out/ and generates index.md and index.csv.

Features:
- Analyzes all subfolders in out/
- Auto-generates missing README.md/report files from ledger/summary data
- Produces clean, uncluttered markdown table with direct subfolder links
- Tracks statistics (convergence rate, character breakdown, best scores)

Usage:
    uv run ./bin/index.py              # Generate out/index.md and out/index.csv
    uv run ./bin/index.py --format md  # Markdown only
    uv run ./bin/index.py --format csv # CSV only
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.models import RunConfig, RunSummary, IterationRecord, JudgeVerdict
from lib.ledger import Ledger
from lib.reporter import generate_report


def format_character(char_name: str) -> str:
    """Format character with a friendly emoji."""
    c = (char_name or "").lower()
    if "riccardo" in c:
        return f"{char_name} 🧔"
    elif "kate" in c:
        return f"{char_name} 👩"
    return char_name


def ensure_run_artifacts(run_dir: Path) -> RunSummary | None:
    """Ensure summary.json and README.md exist for a run directory."""
    summary_file = run_dir / "summary.json"
    readme_file = run_dir / "README.md"
    report_file = run_dir / "report.md"
    config_file = run_dir / "run_config.json"
    ledger_file = run_dir / "ledger.jsonl"

    summary: RunSummary | None = None

    # 1. Try to load existing summary.json
    if summary_file.exists():
        try:
            data = json.loads(summary_file.read_text())
            summary = RunSummary(**data)
        except Exception as e:
            print(f"  Warning: failed to load {summary_file}: {e}", file=sys.stderr)

    # 2. If no summary, try to reconstruct from ledger + config
    if not summary and ledger_file.exists() and config_file.exists():
        try:
            config = RunConfig.model_validate_json(config_file.read_text())
            ledger = Ledger(run_dir)
            summary = ledger.to_summary(config)
            summary_file.write_text(summary.model_dump_json(indent=2))
        except Exception as e:
            print(f"  Warning: failed to reconstruct summary for {run_dir}: {e}", file=sys.stderr)

    # 3. If still no summary, try fallback from config_file alone (partial/incomplete run)
    if not summary and config_file.exists():
        try:
            config = RunConfig.model_validate_json(config_file.read_text())
            scored_images = sorted(run_dir.glob("iter_*_scored.png"))
            summary = RunSummary(
                config=config,
                iterations=[],
                best_iteration=0,
                best_facial_similarity=0.0,
                best_scene_adaptation=0.0,
                best_adherence=0.0,
                converged=False,
                total_elapsed=0.0,
                output_dir=run_dir.name,
                best_image_path=scored_images[0].name if scored_images else "",
            )
            summary_file.write_text(summary.model_dump_json(indent=2))
        except Exception as e:
            print(f"  Warning: failed fallback summary for {run_dir}: {e}", file=sys.stderr)

    # 4. Ensure README.md exists if we have a summary or report.md
    if not readme_file.exists():
        if report_file.exists():
            readme_file.write_text(report_file.read_text())
        elif summary:
            try:
                generate_report(summary, run_dir)
            except Exception as e:
                print(f"  Warning: failed to generate README.md for {run_dir}: {e}", file=sys.stderr)

    return summary


def scan_runs(out_dir: Path) -> list[tuple[Path, RunSummary]]:
    """Scan all subdirectories in out/, ensure artifacts, return sorted newest-first."""
    runs = []
    subdirs = [p for p in out_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
    
    for run_dir in sorted(subdirs, reverse=True):
        summary = ensure_run_artifacts(run_dir)
        if summary:
            runs.append((run_dir, summary))
    return runs


def parse_version(v_str: str | None) -> tuple[int, ...]:
    """Parse semver string into comparable tuple."""
    if not v_str:
        return (0, 0, 0)
    clean = v_str.lstrip("v").strip()
    parts = []
    for x in clean.split("."):
        if x.isdigit():
            parts.append(int(x))
        else:
            digits = "".join(c for c in x if c.isdigit())
            parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0, 0, 0)


def get_score_badge(score: float) -> str:
    """Return a clean badge/emoji for a score."""
    if score >= 8.0:
        return "🏆"
    elif score >= 7.0:
        return "👍"
    elif score >= 5.0:
        return "😐"
    else:
        return "🤮"


def generate_index_md(runs: list[tuple[Path, RunSummary]], out_dir: Path, min_version: str | None = None) -> str:
    """Generate a clean, uncluttered Markdown index of all runs with subfolder links and version info."""
    lines = [
        "# 🎯 portr8 — Run Index & Gallery",
        "",
        f"> Generated: **{datetime.now().strftime('%Y-%m-%d %H:%M')}** · **{len(runs)} runs cataloged**"
        + (f" · *Filtered: ≥ v{min_version}*" if min_version else ""),
        "",
        "| Run / Folder | Ver | Character | Scenario / Prompt | Iters | Score | Status | Artifacts |",
        "|:---|:---:|:---:|:---|:---:|:---:|:---:|:---|",
    ]
    
    for run_dir, s in runs:
        # Subfolder link (explicit index.html for reliable GCS hosting)
        folder_link = f"[`📁 {run_dir.name}`]({run_dir.name}/index.html)"
        ver_tag = f"`v{s.config.portr8_version}`"
        char_badge = format_character(s.config.character)
        prompt = s.config.prompt[:50] + ("..." if len(s.config.prompt) > 50 else "")
        status = "✅ **Converged**" if s.converged else "❌ Reached Max"
        
        # Single score: bottleneck (minimum across axes)
        worst_score = min(s.best_facial_similarity, s.best_scene_adaptation, s.best_adherence)
        badge = get_score_badge(worst_score)
        score_str = f"**{worst_score:.1f}** {badge}"
        
        # Links
        links = []
        graph_file = run_dir / "convergence.png"
        if graph_file.exists():
            links.append(f"[📊 Graph]({run_dir.name}/convergence.png)")
        
        readme_file = run_dir / "README.md"
        report_file = run_dir / "report.md"
        if readme_file.exists():
            links.append(f"[📄 Report]({run_dir.name}/README.md)")
        elif report_file.exists():
            links.append(f"[📄 Report]({run_dir.name}/report.md)")
            
        scored = run_dir / f"iter_{s.best_iteration + 1:02d}_scored.png"
        if not scored.exists():
            scored_candidates = sorted(run_dir.glob("iter_*_scored.png"))
            if scored_candidates:
                scored = scored_candidates[-1]
        if scored.exists():
            links.append(f"[🖼️ Best Image]({run_dir.name}/{scored.name})")
        
        links_str = " · ".join(links) if links else "-"
        iters_count = len(s.iterations)
        
        lines.append(
            f"| {folder_link} | {ver_tag} | {char_badge} | {prompt} | {iters_count} | {score_str} | {status} | {links_str} |"
        )
    
    # Stats section
    total = len(runs)
    converged = sum(1 for _, s in runs if s.converged)
    
    if total > 0:
        # Group by character
        chars: dict[str, dict[str, int]] = {}
        versions: dict[str, dict[str, int]] = {}
        for _, s in runs:
            c = s.config.character
            v = s.config.portr8_version or "unknown"
            
            if c not in chars:
                chars[c] = {"total": 0, "converged": 0}
            chars[c]["total"] += 1
            if s.converged:
                chars[c]["converged"] += 1
                
            if v not in versions:
                versions[v] = {"total": 0, "converged": 0}
            versions[v]["total"] += 1
            if s.converged:
                versions[v]["converged"] += 1

        best_facial_run = max(runs, key=lambda x: x[1].best_facial_similarity)
        best_adherence_run = max(runs, key=lambda x: x[1].best_adherence)
        
        lines.extend([
            "",
            "---",
            "",
            "## 📊 Summary Statistics",
            "",
            f"- **Total Runs**: {total}",
            f"- **Overall Convergence Rate**: {converged}/{total} ({100*converged/total:.0f}%)",
            "",
            "### 🏷️ Breakdown by portr8 Version",
            "",
        ])
        
        for v_name, v_data in sorted(versions.items(), key=lambda x: parse_version(x[0]), reverse=True):
            v_conv = v_data["converged"]
            v_tot = v_data["total"]
            pct = 100 * v_conv / v_tot if v_tot else 0
            lines.append(f"- **v{v_name}**: {v_conv}/{v_tot} converged ({pct:.0f}%)")

        lines.extend([
            "",
            "### 👥 Breakdown by Character",
            "",
        ])
        
        for c_name, c_data in sorted(chars.items()):
            c_conv = c_data["converged"]
            c_tot = c_data["total"]
            pct = 100 * c_conv / c_tot if c_tot else 0
            lines.append(f"- **{format_character(c_name)}**: {c_conv}/{c_tot} converged ({pct:.0f}%)")
            
        lines.extend([
            "",
            "### 🏆 Top Scores",
            "",
            f"- **Best Facial Similarity**: **{best_facial_run[1].best_facial_similarity:.1f}/10** ([{best_facial_run[0].name}]({best_facial_run[0].name}/index.html))",
            f"- **Best Prompt Adherence**: **{best_adherence_run[1].best_adherence:.1f}/10** ([{best_adherence_run[0].name}]({best_adherence_run[0].name}/index.html))",
            "",
            "> *Score = bottleneck rating (minimum of Facial Similarity, Scene Adaptation, and Adherence). 🏆 ≥ 8.0 · 👍 ≥ 7.0 · 😐 ≥ 5.0 · 🤮 < 5.0*",
            "",
        ])
    
    return "\n".join(lines) + "\n"


def generate_index_csv(runs: list[tuple[Path, RunSummary]]) -> str:
    """Generate CSV index of all runs."""
    lines = ["date,version,folder,character,prompt,iterations,best_facial,best_scene,best_adherence,converged"]
    for run_dir, s in runs:
        prompt_csv = s.config.prompt.replace('"', '""')
        lines.append(
            f'{run_dir.name[:8]},{s.config.portr8_version},{run_dir.name},{s.config.character},'
            f'"{prompt_csv}",{len(s.iterations)},'
            f'{s.best_facial_similarity:.1f},{s.best_scene_adaptation:.1f},'
            f'{s.best_adherence:.1f},{s.converged}'
        )
    return "\n".join(lines) + "\n"


def generate_catalog_json(runs: list[tuple[Path, RunSummary]], out_dir: Path) -> str:
    """Generate a comprehensive JSON catalog of all runs and their iterations."""
    catalog = {
        "generated_at": datetime.now().isoformat(),
        "total_runs": len(runs),
        "converged_runs": sum(1 for _, s in runs if s.converged),
        "runs": [s.model_dump() for _, s in runs],
    }
    return json.dumps(catalog, indent=2)


def update_index(out_dir: Path | str = "out", min_version: str | None = None) -> tuple[Path, Path]:
    """Scans out_dir and updates index.md, index.csv, and catalog.json."""
    out_path = Path(out_dir)
    if not out_path.exists():
        out_path.mkdir(parents=True, exist_ok=True)
        
    all_runs = scan_runs(out_path)
    if min_version:
        target_v = parse_version(min_version)
        runs = [(p, s) for p, s in all_runs if parse_version(s.config.portr8_version) >= target_v]
    else:
        runs = all_runs

    print(f"📊 Processed {len(runs)}/{len(all_runs)} run(s) in {out_path}/")
    
    md_content = generate_index_md(runs, out_path, min_version=min_version)
    md_file = out_path / "index.md"
    md_file.write_text(md_content)
    readme_file = out_path / "README.md"
    readme_file.write_text(md_content)
    print(f"  ✅ Written: {md_file}")
    print(f"  ✅ Written: {readme_file}")
    
    csv_content = generate_index_csv(runs)
    csv_file = out_path / "index.csv"
    csv_file.write_text(csv_content)
    print(f"  ✅ Written: {csv_file}")
    
    catalog_content = generate_catalog_json(runs, out_path)
    catalog_file = out_path / "catalog.json"
    catalog_file.write_text(catalog_content)
    print(f"  ✅ Written: {catalog_file}")
    
    return md_file, csv_file


def main():
    parser = argparse.ArgumentParser(description="Generate portr8 run index and catalog from JSON data")
    parser.add_argument("--format", choices=["all", "md", "csv", "json"], default="all", help="Output format (default: all)")
    parser.add_argument("--out-dir", type=Path, default=Path("out"), help="Output directory to scan")
    parser.add_argument("--since-version", "--min-version", dest="min_version", default=None, help="Filter runs since version (e.g. 0.4.0)")
    args = parser.parse_args()
    
    if not args.out_dir.exists():
        print(f"Output directory not found: {args.out_dir}", file=sys.stderr)
        sys.exit(1)
    
    all_runs = scan_runs(args.out_dir)
    if args.min_version:
        target_v = parse_version(args.min_version)
        runs = [(p, s) for p, s in all_runs if parse_version(s.config.portr8_version) >= target_v]
        print(f"🔍 Filtered {len(runs)}/{len(all_runs)} run(s) >= v{args.min_version} in {args.out_dir}/")
    else:
        runs = all_runs
        print(f"🔍 Found {len(runs)} run(s) in {args.out_dir}/")
    
    if args.format in ("all", "md"):
        content = generate_index_md(runs, args.out_dir, min_version=args.min_version)
        output_file = args.out_dir / "index.md"
        output_file.write_text(content)
        readme_file = args.out_dir / "README.md"
        readme_file.write_text(content)
        print(f"  ✅ Markdown index written: {output_file} & {readme_file}")
        
    if args.format in ("all", "csv"):
        content = generate_index_csv(runs)
        output_file = args.out_dir / "index.csv"
        output_file.write_text(content)
        print(f"  ✅ CSV index written: {output_file}")

    if args.format in ("all", "json"):
        content = generate_catalog_json(runs, args.out_dir)
        output_file = args.out_dir / "catalog.json"
        output_file.write_text(content)
        print(f"  ✅ JSON catalog written: {output_file}")


if __name__ == "__main__":
    main()
