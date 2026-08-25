"""portr8 report generator — creates Markdown reports from run data."""

from pathlib import Path
from lib.models import RunSummary
from lib.generator import to_tilde_path


def generate_report(summary: RunSummary, output_dir: Path) -> Path:
    """Generate a Markdown report for a portr8 run.
    
    The report includes:
    - Run configuration
    - Score progression table
    - Best/worst iterations
    - Convergence status
    - Embedded images (relative paths)
    
    Returns: Path to the generated report.md
    """
    report_path = output_dir / "report.md"
    
    lines = []
    lines.append(f"# portr8 Run Report")
    lines.append(f"")
    
    # Status banner
    if summary.converged:
        lines.append(f"> \u2705 **CONVERGED** — Target {summary.config.target_score}/10 achieved!")
    else:
        lines.append(f"> \u274c **FAILED** — Did not reach target {summary.config.target_score}/10")
    lines.append(f"")
    
    # Configuration
    lines.append(f"## Configuration")
    lines.append(f"")
    lines.append(f"| Parameter | Value |")
    lines.append(f"|:---|:---|")
    lines.append(f"| Prompt | {summary.config.prompt} |")
    lines.append(f"| Character | {summary.config.character} |")
    lines.append(f"| Target Score | {summary.config.target_score}/10 |")
    lines.append(f"| Max Iterations | {summary.config.max_iterations} |")
    lines.append(f"| Image Model | {summary.config.image_model} |")
    lines.append(f"| Judge Model | {summary.config.judge_model} |")
    lines.append(f"| Dual Strategy | {summary.config.dual_strategy} |")
    lines.append(f"| portr8 Version | {summary.config.portr8_version} |")
    lines.append(f"")
    
    # Score Progression
    lines.append(f"## Score Progression")
    lines.append(f"")
    lines.append(f"| Iter | Resemblance | Adherence | Strategy | Verdict | Time |")
    lines.append(f"|:---:|:---:|:---:|:---|:---|:---:|")
    for r in summary.iterations:
        r_emoji = "✅" if r.verdict.resemblance_score >= summary.config.target_score else "❌"
        a_emoji = "✅" if r.verdict.adherence_score >= summary.config.target_score else "❌"
        lines.append(
            f"| {r.iteration} | {r_emoji} {r.verdict.resemblance_score:.1f} "
            f"| {a_emoji} {r.verdict.adherence_score:.1f} "
            f"| {r.strategy} | {r.verdict.verdict_label} | {r.elapsed_seconds:.1f}s |"
        )
    lines.append(f"")
    
    # Best Iteration
    lines.append(f"## Best Iteration")
    lines.append(f"")
    best_idx = summary.best_iteration
    if summary.iterations:
        best = summary.iterations[best_idx]
        lines.append(f"**Iteration {best.iteration}** — {best.verdict.verdict_label}")
        lines.append(f"- Resemblance: {best.verdict.resemblance_score:.1f}/10")
        lines.append(f"- Adherence: {best.verdict.adherence_score:.1f}/10")
        lines.append(f"- Photorealistic: {'Yes' if best.verdict.is_photorealistic else 'No'}")
        lines.append(f"")
        # Embed best image if exists
        img_name = f"iter_{best.iteration:02d}.png"
        scored_name = f"iter_{best.iteration:02d}_scored.png"
        lines.append(f"![Best iteration]({scored_name})")
        lines.append(f"")
        lines.append(f"### Resemblance Rationale")
        lines.append(f"{best.verdict.resemblance_rationale}")
        lines.append(f"")
        lines.append(f"### Adherence Rationale")
        lines.append(f"{best.verdict.adherence_rationale}")
    lines.append(f"")
    
    # Summary Stats
    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"- Total iterations: {len(summary.iterations)}")
    lines.append(f"- Total time: {summary.total_elapsed:.1f}s")
    lines.append(f"- Best resemblance: {summary.best_resemblance:.1f}/10")
    lines.append(f"- Best adherence: {summary.best_adherence:.1f}/10")
    lines.append(f"- Output directory: `{to_tilde_path(summary.output_dir)}`")
    lines.append(f"")
    
    # Image Gallery
    if summary.iterations:
        lines.append(f"## All Iterations")
        lines.append(f"")
        for r in summary.iterations:
            scored_name = f"iter_{r.iteration:02d}_scored.png"
            lines.append(f"### Iteration {r.iteration}")
            lines.append(f"![Iteration {r.iteration}]({scored_name})")
            lines.append(f"")
    
    report_path.write_text("\n".join(lines))
    return report_path
