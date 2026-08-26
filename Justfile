set dotenv-load := true

MAX_ITER := env_var_or_default("PORTR8_MAX_ITERATIONS", "20")

# Default: list tasks
list:
    @just --list

# Run the main portr8 convergence loop
run prompt character="riccardo" max_iter=MAX_ITER:
    uv run ./bin/portr8.py -p "{{prompt}}" -c {{character}} --max-iterations {{max_iter}}

# Run with dual strategy (edit + regenerate)
run-dual prompt character="riccardo":
    uv run ./bin/portr8.py -p "{{prompt}}" -c {{character}} --dual-strategy

# Quick demo run (3 iterations)
demo:
    uv run ./bin/portr8.py -p "Riccardo eats an ice cream in the savannah surrounded by lions, photorealistic" -c riccardo --max-iterations 3

# Calibrate the AI judge against human ratings
calibrate character="riccardo":
    uv run ./bin/calibrate.py -c {{character}} -p "Test portrait of {{character}} at a cafe" --num-images 5

# Check reference photo quality for a character
check-refs character="riccardo":
    @echo "🔬 Checking reference photos for {{character}}..."
    @ls -la data/characters/{{character}}/

# Generate report from existing run
report run-id:
    uv run ./bin/report.py --run-id {{run-id}}

# Run tests
test:
    uv run python -m pytest tests/ -v

# Install dependencies
install:
    uv sync

# Show latest run status
status:
    @echo "📁 Recent runs:"
    @ls -lt out/ 2>/dev/null | head -10 || echo "No runs yet."

# Show version
version:
    @cat VERSION

# Generate run index from all out/*/summary.json
index:
    uv run ./bin/index.py

# Generate run index as CSV
index-csv:
    uv run ./bin/index.py --format csv

# Rebuild index and sync out/ to GCS via storagify
storagify:
    @just index
    storagify "{{invocation_directory()}}/out"

# Alias for storagify
sync:
    @just storagify
