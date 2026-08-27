# Implementation Plan: Track omega13-chimeric-fusion (P4)

## Phase 1: High-Water Mark Tracking in Ledger
- [ ] Task: Extend `lib/ledger.py` with `get_best_records_per_character(characters: list[str]) -> dict[str, IterationRecord]`
- [ ] Task: Add unit tests in `tests/test_ledger.py` for per-character historical peak extraction
- [ ] Task: Phase Verification & Checkpoint

## Phase 2: Omega 13 Strategy Trigger & Prompt Augmentation
- [ ] Task: Implement `should_trigger_omega13()` and `build_omega13_prompt()` in `lib/strategist.py`
- [ ] Task: Return `strategy="omega13"` with list of parent iteration image paths in `decide_strategy()`
- [ ] Task: Add unit tests in `tests/test_strategist.py` verifying trigger logic and prompt construction
- [ ] Task: Phase Verification & Checkpoint

## Phase 3: Multi-Source Image Editing in Generator
- [ ] Task: Update `generate_image()` in `lib/generator.py` to accept `edit_image_paths: list[Path] | None`
- [ ] Task: Adapt Files API / PIL loader to transport multiple parent edit images cleanly to Gemini
- [ ] Task: Add unit test verifying multi-image payload structure
- [ ] Task: Phase Verification & Checkpoint

## Phase 4: Integration in Main Convergence Loop & Reporting
- [ ] Task: Wire Omega 13 execution into `bin/portr8.py` main loop
- [ ] Task: Update `lib/reporter.py` and `lib/overlay.py` to handle and display `omega13` badges and summaries
- [ ] Task: Update `docs/USER_MANUAL.md` with the Omega 13 CUJ and documentation
- [ ] Task: Final End-to-End Verification & Checkpoint
