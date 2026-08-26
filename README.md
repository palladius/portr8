# 🎯 portr8 — Iterative Character-Consistent Portrait Convergence Engine

> Converges to ≥ 8/10 on BOTH resemblance and prompt adherence — hence the name.

## What is portr8?

portr8 is a CLI tool that generates **photorealistic, character-consistent** images of real people
in an iterative feedback loop. It generates, judges, overlays scores, and refines until both
**resemblance** (does the person look like the reference photos?) and **prompt adherence**
(does the scene match the description?) hit ≥ 8/10.

## Quick Start

```bash
# Install
uv sync

# Run (will converge in ~5-10 minutes)
./bin/portr8.py \
  -p "Riccardo eats an ice cream in the savannah surrounded by lions, photorealistic" \
  -c riccardo \
  --max-iterations 20

# Or use just
just demo
```

## Setup

1. **Copy environment template**: `cp .env.dist .env` and add your `GEMINI_API_KEY`
2. **Character photos**: Symlink `data/characters/` to your character vault:
   ```bash
   ln -sf ~/your/private/characters data/characters
   ```
3. **Install deps**: `uv sync`

## Architecture

```
Generate → Judge → Overlay → Decide (edit vs regenerate) → Augment prompt → Repeat
    ↑                                                              ↓
    └──────────────────── feedback loop ──────────────────────────-┘
```

See [`docs/SPECS.md`](docs/SPECS.md) for the full specification including 13 empirical lessons
from the upstream [`gemini-tools`](https://github.com/palladius/gemini-tools) project.

## Agentic Development

This project was built using AI-assisted development with Gemini CLI (Antigravity).
See [`META-AGENTS.md`](META-AGENTS.md) for the full methodology, skill choices, and observations —
useful for articles about AI-assisted software development.

## License

MIT
