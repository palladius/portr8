"""portr8 convergence grapher — generates score progression PNG per run."""

from pathlib import Path
from lib.models import RunSummary


def generate_convergence_graph(summary: RunSummary, output_path: Path | None = None) -> Path:
    """Generate a convergence graph PNG showing score progression across iterations.
    
    Shows:
    - Facial similarity scores (blue line)
    - Adherence scores (green line)
    - Scene adaptation scores (orange line)
    - Target score (red dashed horizontal line)
    - Scene floor at 5.0 (orange dotted)
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
    f_scores = [it.verdict.facial_similarity for it in iterations]
    a_scores = [it.verdict.adherence_score for it in iterations]
    s_scores = [it.verdict.scene_adaptation for it in iterations]
    min_scores = [min(f, a) for f, a in zip(f_scores, a_scores)]
    target = summary.config.target_score
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Background color hint
    bg_color = "#e8f5e9" if summary.converged else "#ffebee"
    ax.set_facecolor(bg_color)
    
    # Plot scores
    ax.plot(xs, f_scores, "o-", color="#1565c0", linewidth=2.5, markersize=8, 
            label=f"Facial (best: {summary.best_facial_similarity:.1f})", zorder=3)
    ax.plot(xs, a_scores, "s-", color="#2e7d32", linewidth=2.5, markersize=8,
            label=f"Adherence (best: {max(a_scores):.1f})", zorder=3)
    ax.plot(xs, s_scores, "v-", color="#e65100", linewidth=2, markersize=7,
            label=f"Scene (best: {summary.best_scene_adaptation:.1f})", zorder=3)
    ax.plot(xs, min_scores, ":", color="#9e9e9e", linewidth=1.5, alpha=0.7,
            label="Min(F,A)", zorder=2)
    
    # Target line
    ax.axhline(y=target, color="#d32f2f", linestyle="--", linewidth=2, 
               label=f"Target: {target:.1f}", zorder=1)
    # Scene adaptation floor
    ax.axhline(y=5.0, color="#e65100", linestyle=":", linewidth=1, alpha=0.5,
               label="Scene floor: 5.0", zorder=1)
    
    # Annotate each point with score value
    for i, (x, f, a, s) in enumerate(zip(xs, f_scores, a_scores, s_scores)):
        ax.annotate(f"{f:.1f}", (x, f), textcoords="offset points", 
                    xytext=(0, 10), ha="center", fontsize=9, color="#1565c0", fontweight="bold")
        ax.annotate(f"{a:.1f}", (x, a), textcoords="offset points",
                    xytext=(0, -15), ha="center", fontsize=9, color="#2e7d32", fontweight="bold")
        ax.annotate(f"{s:.1f}", (x, s), textcoords="offset points",
                    xytext=(12, 0), ha="left", fontsize=8, color="#e65100")
    
    # Mark best iteration with a star
    best_idx = summary.best_iteration
    if best_idx < len(f_scores):
        ax.plot(best_idx + 1, f_scores[best_idx], "*", color="#ff6f00", markersize=20, zorder=4)
    
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
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    
    return output_path


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    return text[:max_len - 3] + "..." if len(text) > max_len else text
