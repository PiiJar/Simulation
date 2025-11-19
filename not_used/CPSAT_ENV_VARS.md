# CPSAT environment variables (Phase 1 & 2)

This document lists all CPSAT_* environment variables used by the Simulation project, with scope, defaults, accepted values, and where they are applied in code.

Notes
- Unless noted, values are read at runtime and affect only the current run.
- Boolean flags accept: 1, true, yes, on (case-insensitive) for enabled; 0, false, no, off for disabled.
- File references below use repository paths; see those files for exact logic.

## Phase 1 (cp_sat_phase_1.py)

- Name: CPSAT_PHASE1_GROUPS
  - Type: boolean
  - Default: enabled ("1")
  - Purpose: Enable station-group constraints that try to keep adjacent stages in the same Group when feasible.
  - Where: cp_sat_phase_1.py > add_station_group_constraints

- Name: CPSAT_PHASE1_MAX_TIME
  - Type: number (seconds)
  - Default: 0 (no time limit)
  - Purpose: CP-SAT time limit for Phase 1 solve.
  - Where: cp_sat_phase_1.py > solve

- Name: CPSAT_PHASE1_THREADS
  - Type: integer (>=0)
  - Default: 0 (solver decides)
  - Purpose: Number of CP-SAT search workers for Phase 1.
  - Where: cp_sat_phase_1.py > solve

- Name: CPSAT_LOG_PROGRESS
  - Type: boolean
  - Default: disabled ("0")
  - Purpose: Enable CP-SAT search progress logging in Phase 1.
  - Where: cp_sat_phase_1.py > solve

## Phase 2 (cp_sat_phase_2.py)

- Name: CPSAT_PHASE2_ANCHOR_STAGE1
  - Type: boolean
  - Default: disabled ("0")
  - Purpose: Use Phase 1 Stage 1 EntryTime as anchor for batch windows (alternatively, windows are sliding starting at 0).
  - Where: cp_sat_phase_2.py > _compute_batch_windows

- Name: CPSAT_PHASE2_WINDOW_MARGIN_SEC
  - Type: number (seconds)
  - Default: 600
  - Purpose: Margin added around Phase 1 batch-level windows for safe pruning.
  - Where: cp_sat_phase_2.py > _compute_phase1_with_margin_windows

- Name: CPSAT_PHASE2_WINDOW_STAGE_MARGIN_SEC
  - Type: number (seconds)
  - Default: 300
  - Purpose: Margin added around Phase 1 stage-level windows for pruning cross-pairs.
  - Where: cp_sat_phase_2.py > _compute_stage_windows_with_margin

- Name: CPSAT_PHASE2_OVERLAP_MODE
  - Type: enum {phase1_with_margin | anchored | sliding}
  - Default: phase1_with_margin
  - Purpose: Select which windows are used to test time window overlap when pruning candidate pairs.
  - Where: cp_sat_phase_2.py > _windows_overlap

- Name: CPSAT_PHASE2_TRANSPORTER_SAFE_MARGIN_SEC
  - Type: number (seconds)
  - Default: 600
  - Purpose: Safety margin around transporter move windows derived from Phase 1, used for conservative pruning of cross-transporter pairs.
  - Where: cp_sat_phase_2.py > _compute_transporter_windows_with_margin

- Name: CPSAT_PHASE2_AVOID_TIME_MARGIN_SEC
  - Type: number (seconds)
  - Default: 3
  - Purpose: Base temporal separation enforced between overlapping movements of different transporters (cross-transporter avoid rule).
  - Where: cp_sat_phase_2.py > add_cross_transporter_avoid_constraints; _validate_cross_transporter_collisions

- Name: CPSAT_PHASE2_AVOID_DYNAMIC_ENABLE
  - Type: boolean
  - Default: disabled ("0")
  - Purpose: Enable dynamic addition to the avoid margin proportional to the length of the spatial overlap region.
  - Where: cp_sat_phase_2.py > add_cross_transporter_avoid_constraints; _validate_cross_transporter_collisions

- Name: CPSAT_PHASE2_AVOID_DYNAMIC_PER_MM_SEC
  - Type: number (sec/mm)
  - Default: 0.0
  - Purpose: Coefficient for dynamic avoid margin = coeff * proximity_span_mm, rounded up.
  - Where: cp_sat_phase_2.py > add_cross_transporter_avoid_constraints; _validate_cross_transporter_collisions

- Name: CPSAT_PHASE2_MAX_TIME
  - Type: number (seconds)
  - Default: 300
  - Purpose: CP-SAT time limit for Phase 2 solve.
  - Where: cp_sat_phase_2.py > solve

- Name: CPSAT_PHASE2_THREADS
  - Type: integer (>=0)
  - Default: 0 (solver decides)
  - Purpose: Number of CP-SAT search workers for Phase 2.
  - Where: cp_sat_phase_2.py > solve

- Name: CPSAT_PHASE2_DECOMPOSE
  - Type: boolean
  - Default: disabled ("0")
  - Purpose: Solve Phase 2 by time components (connected batches by window overlap), appending snapshots for each component.
  - Where: cp_sat_phase_2.py > optimize_phase_2

- Name: CPSAT_PHASE2_DECOMPOSE_GUARD_SEC
  - Type: number (seconds)
  - Default: 600
  - Purpose: Guard margin to expand component windows during decomposition to ensure safe boundaries.
  - Where: cp_sat_phase_2.py > optimize_phase_2

- Name: CPSAT_PHASE2_DECOMPOSE_APPEND
  - Type: boolean (internal)
  - Default: disabled (set internally to "1" during decomposition)
  - Purpose: Controls whether Phase 2 snapshot CSVs are appended across components; set and cleared inside optimize_phase_2.
  - Where: cp_sat_phase_2.py > optimize_phase_2; _write_transporter_schedule_snapshot; _write_transporter_schedule_snapshot (station)

Logging
- Phase 2 currently forces solver.log_search_progress = True regardless of CPSAT_LOG_PROGRESS. This may change; if you want a toggle, we can wire CPSAT_LOG_PROGRESS for Phase 2 similarly to Phase 1.

## Other places

- tools/run_simulation.sh
  - Exports CPSAT_PHASE2_MAX_TIME (defaults to 300) before calling main.py.

## Quick reference (by category)

Time limits and threading
- CPSAT_PHASE1_MAX_TIME, CPSAT_PHASE2_MAX_TIME
- CPSAT_PHASE1_THREADS, CPSAT_PHASE2_THREADS

Windows and pruning (Phase 2)
- CPSAT_PHASE2_ANCHOR_STAGE1
- CPSAT_PHASE2_OVERLAP_MODE
- CPSAT_PHASE2_WINDOW_MARGIN_SEC
- CPSAT_PHASE2_WINDOW_STAGE_MARGIN_SEC
- CPSAT_PHASE2_TRANSPORTER_SAFE_MARGIN_SEC

Decomposition (Phase 2)
- CPSAT_PHASE2_DECOMPOSE
- CPSAT_PHASE2_DECOMPOSE_GUARD_SEC
- (internal) CPSAT_PHASE2_DECOMPOSE_APPEND

Cross-transporter avoid (Phase 2)
- CPSAT_PHASE2_AVOID_TIME_MARGIN_SEC
- CPSAT_PHASE2_AVOID_DYNAMIC_ENABLE
- CPSAT_PHASE2_AVOID_DYNAMIC_PER_MM_SEC

Station-grouping and logging
- CPSAT_PHASE1_GROUPS
- CPSAT_LOG_PROGRESS (Phase 1; Phase 2 currently forces logging on)

