#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "google-genai>=1.0.0",
#     "rich>=13.0.0",
#     "pydantic>=2.0.0",
#     "pillow>=10.0.0",
#     "python-slugify>=8.0.0",
#     "matplotlib>=3.7.0",
#     "pyyaml>=6.0.0",
# ]
# ///
"""portr8 — Iterative character-consistent portrait convergence engine.

Generates photorealistic images of a character, judges them on resemblance
and adherence, and iterates until both scores ≥ target (default 8.0).

Usage:
    uv run ./bin/portr8.py -p "Riccardo eats gelato at the beach" -c riccardo
    uv run ./bin/portr8.py -p "..." -c riccardo --max-iterations 5 --target 7.0
    uv run ./bin/portr8.py -p "..." -c riccardo --dual-strategy
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to sys.path so lib/ imports work with uv run
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from google import genai

from lib.models import RunConfig, IterationRecord, JudgeVerdict
from lib.generator import (
    resolve_character_images,
    upload_references_files_api,
    load_references_pil,
    generate_image,
    to_tilde_path,
)
from lib.judge import judge_image, DEFAULT_JUDGE_MODEL
from lib.strategist import decide_strategy
from lib.overlay import create_score_overlay, create_failure_overlay
from lib.ledger import Ledger, create_output_dir, save_run_config

console = Console()


def load_env_file() -> None:
    """Load key-value pairs from .env into os.environ if present."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v

load_env_file()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="🎯 portr8 — Iterative character-consistent portrait convergence engine"
    )
    parser.add_argument("-p", "--prompt", required=True, help="Scene/portrait prompt")
    parser.add_argument("-c", "--character", required=True, help="Character name (must exist in data/characters/)")
    parser.add_argument("--ref-dir", default=os.getenv("PORTR8_REF_DIR", "data/characters"), help="Character reference directory")
    parser.add_argument("--image-model", default=os.getenv("PORTR8_IMAGE_MODEL", "gemini-3.1-flash-image-preview"), help="Image generation model")
    parser.add_argument("--judge-model", default=os.getenv("PORTR8_JUDGE_MODEL", DEFAULT_JUDGE_MODEL), help="Judge model")
    parser.add_argument("--target", type=float, default=float(os.getenv("PORTR8_TARGET_SCORE", "8.0")), help="Target score (both axes must reach this)")
    parser.add_argument("--max-iterations", type=int, default=int(os.getenv("PORTR8_MAX_ITERATIONS", "20")), help="Maximum iterations (default: $PORTR8_MAX_ITERATIONS or 20)")
    parser.add_argument("--dual-strategy", action="store_true", help="Use dual strategy (both edit + regenerate per iteration, pick best)")
    parser.add_argument("--no-edit", action="store_true", default=False,
                        help="ALWAYS regenerate from scratch, never edit. More variability — "
                             "scores may bounce but you get N truly different faces to pick from")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--ref-transport", choices=["files_api", "pil"], default=os.getenv("PORTR8_REF_TRANSPORT", "files_api"), help="Reference transport method")
    parser.add_argument("--image-type", choices=["photo", "cartoon", "illustration"], default="photo",
                        help="Image style type (default: photo — cartoon is too easy!)")
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Check API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY")
    else:
        # Ensure google-genai doesn't accidentally prefer an unrestricted GOOGLE_API_KEY
        os.environ.pop("GOOGLE_API_KEY", None)
        
    if not api_key:
        console.print("[bold red]❌ GEMINI_API_KEY not set. Run: export GEMINI_API_KEY=your-key[/bold red]")
        sys.exit(1)
    
    # Read VERSION
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    version = version_file.read_text().strip() if version_file.exists() else "unknown"
    
    # Build config
    config = RunConfig(
        prompt=args.prompt,
        character=args.character,
        ref_dir=args.ref_dir,
        image_model=args.image_model,
        judge_model=args.judge_model,
        target_score=args.target,
        max_iterations=args.max_iterations,
        dual_strategy=args.dual_strategy,
        no_edit=args.no_edit,
        seed=args.seed,
        ref_transport=args.ref_transport,
        image_type=args.image_type,
        portr8_version=version,
    )
    
    # Print header
    console.print(Panel(
        f"[bold]🎯 portr8 v{version}[/bold]\n"
        f"📝 Prompt: [italic]{config.prompt}[/italic]\n"
        f"👤 Character: [cyan]{config.character}[/cyan]\n"
        f"🎯 Target: [green]{config.target_score}/10[/green] (both axes)\n"
        f"🔄 Max iterations: {config.max_iterations}\n"
        f"🧠 Strategy: {'Dual (edit+regenerate)' if config.dual_strategy else '🚫 NO-EDIT (always regenerate)' if config.no_edit else 'Adaptive'}\n"
        f"🖼️  Image type: {config.image_type}\n"
        f"🎨 Model: {config.image_model}",
        title="portr8",
        border_style="cyan",
    ))
    
    # Resolve character references
    try:
        ref_dict = {}
        all_ref_paths = []
        for char in config.characters:
            paths = resolve_character_images(char, config.ref_dir)
            if not paths:
                console.print(f"[bold red]❌ No reference photos found for '{char}'[/bold red]")
                sys.exit(1)
            ref_dict[char] = paths
            all_ref_paths.extend(paths)
    except FileNotFoundError as e:
        console.print(f"[bold red]❌ {e}[/bold red]")
        sys.exit(1)
    
    console.print(f"\n📸 Found {len(all_ref_paths)} total reference photo(s) for {len(config.characters)} character(s):")
    for char, paths in ref_dict.items():
        console.print(f"  • [cyan]{char.capitalize()}[/cyan]: {len(paths)} photos")
        for p in paths:
            console.print(f"    - {to_tilde_path(p)}")
    
    # Create output directory
    output_dir = create_output_dir(config.prompt)
    console.print(f"\n📁 Output: [blue]{to_tilde_path(output_dir)}[/blue]")
    
    # Save run config
    save_run_config(config, output_dir)
    
    # Initialize client and ledger
    client = genai.Client(api_key=api_key)
    ledger = Ledger(output_dir)
    
    # Load character metadata from character.yaml if available
    from lib.generator import load_characters_metadata
    characters_meta = load_characters_metadata(config.characters, config.ref_dir)
    if characters_meta:
        console.print(f"📖 Loaded YAML definitions for {len(characters_meta)} character(s):")
        for c_name, meta in characters_meta.items():
            bp = meta.to_biometric_blueprint()
            if bp:
                console.print(f"  • [cyan]{c_name.capitalize()}[/cyan]: {bp[:100]}...")

    # Upload references
    console.print(f"\n📡 Uploading references via {config.ref_transport}...")
    if config.ref_transport == "files_api":
        try:
            references = upload_references_files_api(client, all_ref_paths)
        except Exception as e:
            console.print(f"[yellow]⚠️ Files API failed: {e}. Falling back to PIL.[/yellow]")
            references = load_references_pil(all_ref_paths)
    else:
        references = load_references_pil(all_ref_paths)
    
    # === CONVERGENCE LOOP ===
    previous_image_path = None
    
    # Format initial prompt incorporating character blueprints if available
    if characters_meta:
        initial_parts = [config.prompt.rstrip(".")]
        for c_name, meta in characters_meta.items():
            bp = meta.to_biometric_blueprint()
            if bp:
                initial_parts.append(f"Character '{c_name.capitalize()}' profile: {bp}")
        augmented_prompt = ". ".join(initial_parts) + "."
    else:
        augmented_prompt = config.prompt
    
    for iteration in range(config.max_iterations):
        iter_start = time.time()
        console.print(f"\n{'='*60}")
        console.print(f"🔄 [bold cyan]Iteration {iteration + 1}/{config.max_iterations}[/bold cyan]")
        console.print(f"{'='*60}")
        
        # Determine strategy
        if iteration == 0:
            strategy = "initial"
            strategy_decision = None
        else:
            strategy_decision = decide_strategy(
                verdict=last_verdict,
                original_prompt=config.prompt,
                iteration=iteration,
                previous_augmented_prompt=augmented_prompt,
                characters=config.characters,
                characters_metadata=characters_meta,
                image_type=config.image_type,
                target_score=config.target_score,
            )
            strategy = strategy_decision.strategy
            augmented_prompt = strategy_decision.augmented_prompt
        
        # --no-edit: force regenerate, keep the smarter prompt but don't pass previous image
        if config.no_edit and strategy == "edit":
            strategy = "regenerate"
            console.print("  🚫 [yellow]--no-edit: overriding EDIT → REGENERATE (keeping feedback prompt)[/yellow]")
        
        # Generate image
        console.print(f"\n🎨 Generating image (strategy: {strategy})...")
        image_path = output_dir / f"iter_{iteration + 1:02d}.png"
        
        # For edit mode, pass previous image so the model can refine it
        # When --no-edit, prev_img stays None → always fresh generation
        prev_img = None
        if not config.no_edit and strategy == "edit" and previous_image_path and previous_image_path.exists():
            from PIL import Image as PILImage
            prev_img = PILImage.open(previous_image_path)
        
        generated_img, model_used = generate_image(
            client=client,
            prompt=augmented_prompt,
            references=references,
            model=config.image_model,
            seed=config.seed,
            output_path=image_path,
            previous_image=prev_img,
        )
        
        if generated_img is None:
            console.print("[bold red]❌ Image generation failed across all models![/bold red]")
            break
        
        # Track current image for potential edit in next iteration
        previous_image_path = image_path
        
        # Judge the image
        console.print(f"\n👨⚖️ Judging...")
        try:
            verdict = judge_image(
                client=client,
                image_path=image_path,
                reference_paths=all_ref_paths,
                prompt=config.prompt,
                character_name=config.character,
                characters=config.characters,
                characters_metadata=characters_meta,
                model=config.judge_model,
                image_type=config.image_type,
                character_ref_counts={char: len(paths) for char, paths in ref_dict.items()},
            )
        except Exception as e:
            console.print(f"[bold red]❌ Judge failed: {e}[/bold red]")
            # Create a minimal verdict so we can continue
            verdict = JudgeVerdict(
                facial_similarity=0.0,
                scene_adaptation=0.0,
                adherence_score=0.0,
                is_photorealistic=False,
                facial_similarity_rationale=f"Judge error: {e}",
                scene_adaptation_rationale=f"Judge error: {e}",
                adherence_rationale=f"Judge error: {e}",
            )
        
        last_verdict = verdict
        elapsed = time.time() - iter_start
        
        # Create score overlay
        scored_path = create_score_overlay(image_path, verdict, iteration + 1)
        
        # Record in ledger
        record = IterationRecord(
            iteration=iteration + 1,
            timestamp=datetime.now().isoformat(),
            image_path=to_tilde_path(image_path),
            scored_image_path=to_tilde_path(scored_path),
            original_prompt=config.prompt,
            augmented_prompt=augmented_prompt,
            strategy=strategy,
            seed=config.seed,
            image_model=model_used,
            judge_model=config.judge_model,
            ref_transport=config.ref_transport,
            verdict=verdict,
            strategy_decision=strategy_decision if iteration > 0 else None,
            elapsed_seconds=elapsed,
            portr8_version=version,
        )
        ledger.append(record)
        
        # Check convergence: all facial similarities & adherence >= target, scene_adaptation >= 5.0
        min_facial = min(verdict.character_facial_scores) if verdict.character_facial_scores else verdict.facial_similarity
        converged = (
            min_facial >= config.target_score
            and verdict.adherence_score >= config.target_score
            and verdict.scene_adaptation >= 5.0
        )
        if converged:
            console.print(f"\n[bold green]🏆 CONVERGED![/bold green]")
            console.print(f"   Facial bottleneck: {min_facial:.1f}")
            console.print(f"   Scene adaptation: {verdict.scene_adaptation:.1f}")
            console.print(f"   Adherence: {verdict.adherence_score:.1f}")
            console.print(f"   Average (Media): {verdict.average_score:.1f}")
            console.print(f"   Verdict: {verdict.verdict_label}")
            break
        else:
            remaining = config.max_iterations - iteration - 1
            f_display = "/".join(f"{s:.1f}" for s in verdict.character_facial_scores) if verdict.character_facial_scores else f"{verdict.facial_similarity:.1f}"
            console.print(f"\n  ⏳ Not converged (F:{f_display} S:{verdict.scene_adaptation:.1f} A:{verdict.adherence_score:.1f} Avg:{verdict.average_score:.1f}). {remaining} left.")
        
        previous_image_path = image_path
    
    # === END LOOP ===
    
    # Generate summary
    summary = ledger.to_summary(config)
    
    # Create failure overlay on best image if not converged
    best_record = ledger.best_iteration()
    if not summary.converged and best_record:
        best_path = Path(best_record.image_path.replace("~", os.path.expanduser("~")))
        if best_path.exists():
            create_failure_overlay(best_path, best_record.verdict, best_record.iteration)
    
    # Populate best_image_path
    if best_record:
        scored_stem = Path(best_record.image_path.replace("~", os.path.expanduser("~")))
        scored_path = scored_stem.parent / f"{scored_stem.stem}_scored{scored_stem.suffix}"
        summary.best_image_path = to_tilde_path(scored_path) if scored_path.exists() else best_record.image_path
    
    # Generate convergence graph
    try:
        from lib.grapher import generate_convergence_graph
        graph_path = generate_convergence_graph(summary, output_dir / "convergence.png")
        summary.graph_path = to_tilde_path(graph_path)
        console.print(f"\n📊 Graph saved: [blue]{summary.graph_path}[/blue]")
    except Exception as e:
        console.print(f"\n[yellow]⚠️ Graph generation failed: {e}[/yellow]")
    
    # Generate per-run report
    try:
        from lib.reporter import generate_report
        report_path = generate_report(summary, output_dir)
        console.print(f"📄 README saved: [blue]{to_tilde_path(report_path)}[/blue]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Report generation failed: {e}[/yellow]")
    
    # Print final summary
    _print_summary(summary)
    
    # Save summary JSON
    summary_path = output_dir / "summary.json"
    summary_path.write_text(summary.model_dump_json(indent=2))
    console.print(f"\n💾 Summary saved: [blue]{to_tilde_path(summary_path)}[/blue]")
    console.print(f"💾 Ledger saved: [blue]{to_tilde_path(ledger.ledger_path)}[/blue]")
    
    # Auto-update global out/ index
    try:
        import subprocess
        index_script = Path(__file__).parent / "index.py"
        subprocess.run([sys.executable, str(index_script), "--out-dir", str(output_dir.parent)], check=False)
        console.print(f"📑 Global index updated: [blue]{to_tilde_path(output_dir.parent / 'index.md')}[/blue]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Index update failed: {e}[/yellow]")
    
    # Exit code
    if summary.converged:
        sys.exit(0)
    else:
        console.print(f"\n[bold red]❌ Failed to converge after {len(summary.iterations)} iterations[/bold red]")
        sys.exit(1)


def _print_summary(summary) -> None:
    """Print a rich summary table."""
    table = Table(title="🎯 portr8 Run Summary")
    table.add_column("Iter", style="cyan")
    
    characters = summary.config.characters or ([summary.config.character] if summary.config.character else [])
    is_multi = len(characters) > 1
    
    if is_multi:
        for i, c in enumerate(characters):
            table.add_column(f"F{i+1} ({c.capitalize()})", justify="right")
    else:
        table.add_column("Facial", justify="right")
        
    table.add_column("Scene", justify="right")
    table.add_column("Adherence", justify="right")
    table.add_column("Media", justify="right")
    table.add_column("Strategy")
    table.add_column("Verdict")
    table.add_column("Time", justify="right")
    
    for r in summary.iterations:
        row = [str(r.iteration)]
        if is_multi:
            for i in range(len(characters)):
                s = r.verdict.character_facial_scores[i] if len(r.verdict.character_facial_scores) > i else r.verdict.facial_similarity
                col = "green" if s >= 8 else "yellow" if s >= 5 else "red"
                row.append(f"[{col}]{s:.1f}[/{col}]")
        else:
            f_style = "green" if r.verdict.facial_similarity >= 8 else "yellow" if r.verdict.facial_similarity >= 5 else "red"
            row.append(f"[{f_style}]{r.verdict.facial_similarity:.1f}[/{f_style}]")
            
        s_style = "green" if r.verdict.scene_adaptation >= 8 else "yellow" if r.verdict.scene_adaptation >= 5 else "red"
        a_style = "green" if r.verdict.adherence_score >= 8 else "yellow" if r.verdict.adherence_score >= 5 else "red"
        avg_style = "green" if r.verdict.average_score >= 8 else "yellow" if r.verdict.average_score >= 6 else "red"
        
        row.extend([
            f"[{s_style}]{r.verdict.scene_adaptation:.1f}[/{s_style}]",
            f"[{a_style}]{r.verdict.adherence_score:.1f}[/{a_style}]",
            f"[{avg_style}]{r.verdict.average_score:.1f}[/{avg_style}]",
            r.strategy,
            r.verdict.verdict_label,
            f"{r.elapsed_seconds:.1f}s",
        ])
        table.add_row(*row)
    
    console.print(table)
    
    status = "[bold green]CONVERGED[/bold green]" if summary.converged else "[bold red]FAILED[/bold red]"
    console.print(f"\nStatus: {status}")
    console.print(f"Best: Iter {summary.best_iteration + 1} (F:{summary.best_facial_similarity:.1f} S:{summary.best_scene_adaptation:.1f} A:{summary.best_adherence:.1f})")
    console.print(f"Total time: {summary.total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
