from pathlib import Path
from lib.models import IterationRecord, RunConfig, RunSummary

class Ledger:
    """Append-only JSONL ledger for portr8 iteration tracking.
    
    Each run creates a new ledger file: out/YYYYMMDD-HHMM-<slug>/ledger.jsonl
    Records are appended one per line as they complete.
    """
    
    def __init__(self, output_dir: Path):
        """Initialize ledger in the given output directory."""
        self.output_dir = output_dir
        self.ledger_path = output_dir / "ledger.jsonl"
        self.records: list[IterationRecord] = []
    
    def append(self, record: IterationRecord) -> None:
        """Append an iteration record to the ledger.
        
        Writes to disk immediately (crash-safe) AND keeps in memory.
        """
        self.records.append(record)
        with open(self.ledger_path, 'a') as f:
            f.write(record.model_dump_json() + '\n')
    
    def load(self) -> list[IterationRecord]:
        """Load all records from an existing ledger file."""
        records = []
        if self.ledger_path.exists():
            with open(self.ledger_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(IterationRecord.model_validate_json(line))
        self.records = records
        return records
    
    def best_iteration(self) -> IterationRecord | None:
        """Return the record with the highest minimum(resemblance, adherence)."""
        if not self.records:
            return None
        return max(self.records, key=lambda r: min(r.verdict.resemblance_score, r.verdict.adherence_score))
    
    def is_converged(self, target_score: float = 8.0) -> bool:
        """Check if ANY iteration has both scores >= target."""
        return any(
            r.verdict.resemblance_score >= target_score and 
            r.verdict.adherence_score >= target_score
            for r in self.records
        )
    
    def to_summary(self, config: RunConfig) -> RunSummary:
        """Generate a RunSummary from all recorded iterations."""
        best = self.best_iteration()
        best_idx = self.records.index(best) if best else 0
        return RunSummary(
            config=config,
            iterations=self.records,
            best_iteration=best_idx,
            best_resemblance=best.verdict.resemblance_score if best else 0.0,
            best_adherence=best.verdict.adherence_score if best else 0.0,
            converged=self.is_converged(config.target_score),
            total_elapsed=sum(r.elapsed_seconds for r in self.records),
            output_dir=str(self.output_dir),
        )

def create_output_dir(prompt: str, base_dir: str = "out") -> Path:
    """Create a timestamped output directory.
    
    Format: out/YYYYMMDD-HHMM-<prompt-slug>/
    The slug is derived from the first ~40 chars of the prompt.
    """
    from datetime import datetime
    from slugify import slugify
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    slug = slugify(prompt[:40], max_length=40)
    dir_name = f"{timestamp}-{slug}"
    output_dir = Path(base_dir) / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def save_run_config(config: RunConfig, output_dir: Path) -> None:
    """Save the run configuration to a JSON file."""
    config_path = output_dir / "run_config.json"
    config_path.write_text(config.model_dump_json(indent=2))
