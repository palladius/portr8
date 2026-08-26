"""portr8 convergence grapher — generates high-quality score progression visual."""

from pathlib import Path
from lib.models import RunSummary


def generate_convergence_graph(summary: RunSummary, output_path: Path | None = None) -> Path:
    """Generate a beautiful, polished convergence graph PNG showing score progression.
    
    Features:
    - 4 distinct metric lines/markers (Facial, Scene, Adherence, and Bottleneck/Min)
    - Shaded Italian verdict zones (CAPOLAVORO, BUONO, COSÌ-COSÌ, SCHIFO)
    - Elegant modern card styling with clean grid and typography
    - Non-overlapping data point labels with stylish callout boxes
    - Robust handling for both single-iteration (converged fast) and multi-iteration runs
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    
    if output_path is None:
        output_path = Path(summary.output_dir.replace("~", str(Path.home()))) / "convergence.png"
    
    iterations = summary.iterations
    if not iterations:
        raise ValueError("No iterations to graph")
    
    n_iters = len(iterations)
    xs = [it.iteration for it in iterations]
    s_scores = [it.verdict.scene_adaptation for it in iterations]
    a_scores = [it.verdict.adherence_score for it in iterations]
    target = summary.config.target_score
    characters = summary.config.characters or ([summary.config.character] if summary.config.character else ["character"])
    is_multi = len(characters) > 1
    
    # Calculate min scores per iteration
    min_scores = [it.verdict.bottleneck_score for it in iterations]
    
    # Modern figure setup
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans', 'Arial', 'Helvetica'
    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=150)
    
    # Background verdict color zones (clean, no text clutter)
    ax.axhspan(8.0, 10.8, color='#e8f5e9', alpha=0.6, zorder=0, label='_nolegend_')
    ax.axhspan(7.0, 8.0, color='#f9fbe7', alpha=0.5, zorder=0, label='_nolegend_')
    ax.axhspan(5.0, 7.0, color='#fff8e1', alpha=0.5, zorder=0, label='_nolegend_')
    ax.axhspan(0.0, 5.0, color='#ffebee', alpha=0.4, zorder=0, label='_nolegend_')
    
    # Target line (dashed dark green)
    ax.axhline(y=target, color='#2e7d32', linestyle='--', linewidth=2.0, alpha=0.85,
               label=f'Target ({target:.1f})', zorder=2)
    # Scene adaptation floor line
    ax.axhline(y=5.0, color='#d32f2f', linestyle=':', linewidth=1.5, alpha=0.6,
               label='Floor (5.0)', zorder=2)

    # Plot metric curves
    colors_f = ['#1976d2', '#00acc1', '#8e24aa', '#d81b60']
    if is_multi:
        for char_idx, char_name in enumerate(characters):
            f_scores_char = [
                (it.verdict.character_facial_scores[char_idx] 
                 if len(it.verdict.character_facial_scores) > char_idx 
                 else it.verdict.facial_similarity)
                for it in iterations
            ]
            c_color = colors_f[char_idx % len(colors_f)]
            best_f = max(f_scores_char) if f_scores_char else 0.0
            ax.plot(xs, f_scores_char, marker='o', markersize=7, color=c_color, linewidth=2.2,
                    label=f'F{char_idx+1}: {char_name.capitalize()} (best: {best_f:.1f})', zorder=4)
    else:
        f_scores = [it.verdict.facial_similarity for it in iterations]
        ax.plot(xs, f_scores, marker='o', markersize=8, color='#1976d2', linewidth=2.5,
                label=f'Facial Similarity (best: {summary.best_facial_similarity:.1f})', zorder=4)

    # Scene Adaptation (Orange)
    ax.plot(xs, s_scores, marker='^', markersize=8, color='#f57c00', linewidth=2.5,
            label=f'Scene Adaptation (best: {summary.best_scene_adaptation:.1f})', zorder=4)
    # Prompt Adherence (Green)
    ax.plot(xs, a_scores, marker='s', markersize=8, color='#388e3c', linewidth=2.5,
            label=f'Prompt Adherence (best: {summary.best_adherence:.1f})', zorder=4)
    # Bottleneck / Min score (Purple dotted)
    ax.plot(xs, min_scores, marker='D', markersize=6, color='#7b1fa2', linewidth=1.8, linestyle=':',
            label=f'Bottleneck Score (min)', zorder=3)

    # Annotations
    for idx, x in enumerate(xs):
        it = iterations[idx]
        if is_multi and it.verdict.character_facial_scores:
            f_str = "/".join(f"{s:.1f}" for s in it.verdict.character_facial_scores)
            f_label = f"F: {f_str}"
        else:
            f_label = f"F: {it.verdict.facial_similarity:.1f}"
        
        ax.annotate(f_label, (x, it.verdict.facial_similarity), xytext=(-25, 12), textcoords='offset points',
                    fontsize=8, fontweight='bold', color='#1565c0',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#1976d2', alpha=0.85, linewidth=0.8))
        ax.annotate(f'S: {it.verdict.scene_adaptation:.1f}', (x, it.verdict.scene_adaptation), xytext=(10, 12), textcoords='offset points',
                    fontsize=8, fontweight='bold', color='#e65100',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#f57c00', alpha=0.85, linewidth=0.8))
        ax.annotate(f'A: {it.verdict.adherence_score:.1f}', (x, it.verdict.adherence_score), xytext=(10, -18), textcoords='offset points',
                    fontsize=8, fontweight='bold', color='#2e7d32',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#388e3c', alpha=0.85, linewidth=0.8))

    # Star the best iteration at its bottleneck score
    best_idx = summary.best_iteration
    if best_idx < len(xs):
        best_x = xs[best_idx]
        best_m = min_scores[best_idx]
        ax.plot(best_x, best_m, marker='*', markersize=22, color='#ffd700', markeredgecolor='#e65100', markeredgewidth=1.5, zorder=5)

    # Configure axes and limits
    ax.set_ylim(0, 10.8)
    if n_iters == 1:
        ax.set_xlim(0.5, 1.5)
        ax.set_xticks([1])
    else:
        ax.set_xlim(0.6, n_iters + 0.5)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    
    # Title & Labels
    status_label = "CONVERGED (GOAL REACHED)" if summary.converged else "MAX ITERATIONS REACHED"
    ax.set_title(
        f"portr8 v{summary.config.portr8_version} · {summary.config.character.upper()} — {status_label}\n"
        f'"{_truncate(summary.config.prompt, 75)}"',
        fontsize=11, fontweight='bold', color='#212121', pad=12
    )
    ax.set_xlabel("Iteration", fontsize=10, fontweight='bold', color='#424242')
    ax.set_ylabel("Judge Score (0 – 10)", fontsize=10, fontweight='bold', color='#424242')
    
    # Clean grid and borders
    ax.grid(True, linestyle='--', alpha=0.4, color='#9e9e9e', zorder=1)
    for spine in ax.spines.values():
        spine.set_color('#bdbdbd')
        spine.set_linewidth(1.0)
        
    # Legend at bottom with clean white box
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.28), ncol=3,
              fontsize=8.5, frameon=True, facecolor='white', edgecolor='#cccccc', framealpha=0.95)
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return output_path


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    return text[:max_len - 3] + "..." if len(text) > max_len else text
