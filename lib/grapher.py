"""portr8 convergence grapher — generates score progression PNG per run."""

from pathlib import Path
from lib.models import RunSummary


def generate_convergence_graph(summary: RunSummary, output_path: Path | None = None) -> Path:
    """Generate a convergence graph PNG showing score progression across iterations.
    
    Shows:
    - Resemblance scores (blue line)
    - Adherence scores (green line)  
    - Target score (red dashed horizontal line)
    - Min score per iteration (gray dotted)
    - Color-coded background: green if converged, red if not
    
    Args:
        summary: RunSummary with all iteration data
        output_path: Where to save (default: output_dir/convergence.png)
        
    Returns:
        Path to the generated PNG
    """
    # Lazy import — matplotlib is only needed for graphing
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    
    if output_path is None:
        output_path = Path(summary.output_dir.replace("~", str(Path.home()))) / "convergence.png"
    
    iterations = summary.iterations
    if not iterations:
        raise ValueError("No iterations to graph")
    
    xs = [it.iteration + 1 for it in iterations]
    r_scores = [it.verdict.resemblance_score for it in iterations]
    a_scores = [it.verdict.adherence_score for it in iterations]
    min_scores = [min(r, a) for r, a in zip(r_scores, a_scores)]
    target = summary.config.target_score
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Background color hint
    bg_color = "#e8f5e9" if summary.converged else "#ffebee"
    ax.set_facecolor(bg_color)
    
    # Plot scores
    ax.plot(xs, r_scores, "o-", color="#1565c0", linewidth=2.5, markersize=8, 
            label=f"Resemblance (best: {summary.best_resemblance:.1f})", zorder=3)
    ax.plot(xs, a_scores, "s-", color="#2e7d32", linewidth=2.5, markersize=8,
            label=f"Adherence (best: {max(a_scores):.1f})", zorder=3)
    ax.plot(xs, min_scores, ":", color="#9e9e9e", linewidth=1.5, alpha=0.7,
            label="Min(R,A)", zorder=2)
    
    # Target line
    ax.axhline(y=target, color="#d32f2f", linestyle="--", linewidth=2, 
               label=f"Target: {target:.1f}", zorder=1)
    
    # Annotate each point with score value
    for i, (x, r, a) in enumerate(zip(xs, r_scores, a_scores)):
        ax.annotate(f"{r:.1f}", (x, r), textcoords="offset points", 
                    xytext=(0, 10), ha="center", fontsize=9, color="#1565c0", fontweight="bold")
        ax.annotate(f"{a:.1f}", (x, a), textcoords="offset points",
                    xytext=(0, -15), ha="center", fontsize=9, color="#2e7d32", fontweight="bold")
    
    # Mark best iteration with a star
    best_idx = summary.best_iteration
    if best_idx < len(r_scores):
        ax.plot(best_idx + 1, r_scores[best_idx], "*", color="#ff6f00", markersize=20, zorder=4)
    
    # Styling
    status = "CONVERGED" if summary.converged else "FAILED"
    status_emoji = "[ok]" if summary.converged else "[fail]"
    ax.set_title(
        f"portr8 — {summary.config.character} · {status} {status_emoji}\n"
        f'"{_truncate(summary.config.prompt, 60)}"',
        fontsize=12, fontweight="bold"
    )
    ax.set_xlabel("Iteration", fontsize=11)
    ax.set_ylabel("Score (0-10)", fontsize=11)
    ax.set_ylim(0, 10.5)
    ax.set_xlim(0.5, len(xs) + 0.5)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    return output_path


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    return text[:max_len - 3] + "..." if len(text) > max_len else text
