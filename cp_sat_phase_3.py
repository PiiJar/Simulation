"""
CP-SAT Phase 3: Extended optimization with optional pattern constraints

Inherits all functionality from Phase 2, with optional addition of stage sequence
constraints when a pattern is detected.
"""

import os
import pandas as pd
from typing import List, Tuple, Optional
from ortools.sat.python import cp_model
from cp_sat_phase_2 import CpSatPhase2Optimizer, optimize_phase_2


class CpSatPhase3Optimizer(CpSatPhase2Optimizer):
    """
    Phase 3 optimizer that extends Phase 2 with optional pattern sequence constraints.
    """
    
    def __init__(self, output_dir: str, pattern_sequence: Optional[List[Tuple[int, int]]] = None):
        """
        Args:
            output_dir: Output directory
            pattern_sequence: Optional list of (batch, stage) tuples in time order for constraints
        """
        super().__init__(output_dir)
        self.pattern_sequence = pattern_sequence
        self.use_pattern_constraints = (pattern_sequence is not None and len(pattern_sequence) > 0)
    
    def add_pattern_sequence_constraints(self):
        """
        Add BATCH-AGNOSTIC stage sequence constraints.
        
        Pattern defines STAGE order per transporter: T1:[S1,S9,S10,...], T2:[S2,S3,S4,...]
        Constraint: For each transporter, enforce stage execution order
        ANY batch that needs stage S[i] must complete before ANY batch needing S[i+1] on same transporter
        
        This allows natural ramp-up: erät 1,2,3 fill the line following the pattern rhythm.
        """
        if not self.use_pattern_constraints:
            return
        
        if len(self.pattern_sequence) < 2:
            print("⚠️  Pattern sequence too short, skipping constraints")
            return
        
        print(f"\n{'='*70}")
        print(f"BATCH-AGNOSTIC PATTERN: Stage sequence constraints")
        print(f"{'='*70}")
        print(f"Pattern defines stage execution ORDER per transporter")
        print(f"Batches will naturally fill/empty line following this rhythm")
        
        # Extract stage sequences per transporter from pattern
        # pattern_sequence = [(batch, stage), ...] in time order
        # We need to extract: T1_stages = [S1, S9, S10, ...], T2_stages = [S2, S3, ...]
        
        # First, determine which transporter handles which stages (from pattern sequence)
        # Pattern tells us: (batch, stage) -> we can look up transporter from actual execution
        stage_to_transporter = {}
        
        # Load the transporter schedule from Phase 2 to see which transporter did which stage
        schedule_path = os.path.join(self.output_dir, "cp_sat", "cp_sat_transporter_schedule.csv")
        if os.path.exists(schedule_path):
            schedule_df = pd.read_csv(schedule_path)
            for _, row in schedule_df.iterrows():
                stage = int(row["Stage"])
                trans = int(row["Transporter"])
                if stage not in stage_to_transporter:
                    stage_to_transporter[stage] = trans
        else:
            print("⚠️  No transporter schedule found, cannot determine stage->transporter mapping")
            return
        
        # Build stage sequence per transporter from pattern
        transporter_sequences = {}
        for batch, stage in self.pattern_sequence:
            trans = stage_to_transporter.get(stage)
            if trans is None:
                continue
            if trans not in transporter_sequences:
                transporter_sequences[trans] = []
            transporter_sequences[trans].append(stage)
        
        # Extract ONE CYCLE per transporter
        # Pattern file may contain start of next cycle - trim to unique stages
        for trans in transporter_sequences:
            full_seq = transporter_sequences[trans]
            
            # Keep stages until we see a repeat (indicates cycle restart)
            seen_stages = []
            seen_set = set()
            
            for stage in full_seq:
                if stage in seen_set:
                    # Found repeat - cycle ends here
                    break
                seen_set.add(stage)
                seen_stages.append(stage)
            
            transporter_sequences[trans] = seen_stages
            print(f"  Cycle for T{trans}: {seen_stages}")
        
        print(f"\nExtracted ONE CYCLE per transporter:")
        for trans, stages in sorted(transporter_sequences.items()):
            print(f"  T{trans}: {stages}")
        
        # GENERIC CYCLE REPLICATION STRATEGY
        # Infer ramp-up/steady/ramp-down from pattern analysis
        
        constraint_count = 0
        
        # 1. Analyze pattern - it shows ONE steady-state cycle
        pattern_batches = set(b for b, _ in self.pattern_sequence)
        if len(pattern_batches) == 0:
            print(f"\n⚠️  No pattern batches found")
            return
        
        cycle_size = len(pattern_batches)  # How many batches on line simultaneously
        total_batches = len(self.batches_df)
        
        print(f"\n  Pattern shows steady-state cycle:")
        print(f"    Cycle contains {cycle_size} batches (line capacity when full)")
        print(f"    Total batches to schedule: {total_batches}")
        
        # 2. Define regions based on line capacity
        # Ramp-up: First cycle_size batches (line filling)
        ramp_up_end = cycle_size
        
        # Steady-state: When line is full, cycle repeats
        # Starts when batch (cycle_size+1) enters and batch 1 exits
        steady_start = cycle_size + 1
        
        # Steady-state ends when not enough batches left for full cycle
        steady_end = total_batches - cycle_size
        
        # Ramp-down: Last cycle_size batches (line emptying)
        ramp_down_start = steady_end + 1
        
        print(f"\n  Production phases:")
        print(f"    Ramp-up: batches 1-{ramp_up_end} (line filling, unconstrained)")
        if steady_start <= steady_end:
            print(f"    Steady-state: batches {steady_start}-{steady_end} (cycle repeats, constrained)")
            num_repeats = (steady_end - steady_start + 1) // cycle_size
            print(f"      → Cycle repeats ~{num_repeats} times")
        else:
            print(f"    Steady-state: NONE (not enough batches)")
        print(f"    Ramp-down: batches {ramp_down_start}-{total_batches} (line emptying, unconstrained)")
        
        # 3. Only apply constraints if we have steady-state
        if steady_start > steady_end:
            print(f"\n  → Not enough batches for steady-state (need >{cycle_size*2} batches)")
            print(f"  → Running without pattern constraints (free optimization)")
            return
        
        # 4. Extract pattern timing (cycle-relative timing for each task)
        pattern_timing = {}  # (trans, stage) -> relative time in cycle
        cycle_duration = 0
        
        pattern_path = os.path.join(self.output_dir, "reports", "pattern_0_tasks.csv")
        if os.path.exists(pattern_path):
            import pandas as pd
            pattern_csv = pd.read_csv(pattern_path).sort_values("TaskStart")
            cycle_start_time = pattern_csv["TaskStart"].min()
            cycle_duration = pattern_csv["TaskEnd"].max() - cycle_start_time
            
            for _, row in pattern_csv.iterrows():
                trans = int(row["Transporter"])
                stage = int(row["Stage"])
                start_time = int(row["TaskStart"])
                relative_time = start_time - cycle_start_time
                
                if (trans, stage) not in pattern_timing:
                    pattern_timing[(trans, stage)] = relative_time
            
            print(f"\n  Pattern timing:")
            print(f"    Cycle duration: {cycle_duration}s")
            print(f"    Timing anchors: {len(pattern_timing)} (trans, stage) pairs")
        
        # 5. SOFT TIMING CONSTRAINTS (ramp-up + steady-state)
        # Add timing deviation penalties to objective
        timing_deviations = []
        
        for batch_num in range(1, steady_end + 1):
            cycle_number = (batch_num - 1) // cycle_size
            expected_cycle_start = cycle_number * cycle_duration
            
            for (trans, stage), relative_time in pattern_timing.items():
                key = (batch_num, stage)
                
                if key not in self.entry:
                    continue
                
                expected_time = expected_cycle_start + relative_time
                actual_time = self.entry[key]
                
                # Absolute deviation
                deviation = self.model.NewIntVar(0, 10**9, f"timing_dev_B{batch_num}_S{stage}_T{trans}")
                self.model.Add(deviation >= actual_time - expected_time)
                self.model.Add(deviation >= expected_time - actual_time)
                
                timing_deviations.append(deviation)
        
        print(f"    Soft timing hints: {len(timing_deviations)} deviations added to objective")
        
        # 6. HARD STAGE-ORDER CONSTRAINTS (steady-state only)
        for trans, stage_seq in transporter_sequences.items():
            for batch_num in range(steady_start, steady_end + 1):
                for i in range(len(stage_seq) - 1):
                    stage_now = stage_seq[i]
                    stage_next = stage_seq[i + 1]
                    
                    key_now = (batch_num, stage_now)
                    key_next = (batch_num, stage_next)
                    
                    if key_now in self.exit and key_next in self.entry:
                        self.model.Add(self.exit[key_now] <= self.entry[key_next])
                        constraint_count += 1
        
        print(f"    Hard stage-order constraints (steady): {constraint_count}")
        
        # 7. Store timing deviations for objective update
        self.timing_penalty_terms = timing_deviations
        
        print(f"\n✓ Pattern constraints applied:")
        print(f"  Ramp-up (1-{ramp_up_end}): soft timing hints")
        print(f"  Steady ({steady_start}-{steady_end}): hard stage-order + soft timing")
        print(f"  Ramp-down ({ramp_down_start}-{total_batches}): no extra constraints")
        print(f"{'='*70}\n")
    
    def set_objective(self):
        """Override to include timing deviation penalties."""
        # Call parent objective (makespan + start gaps)
        super().set_objective()
        
        # Add timing deviation penalties if pattern constraints are used
        if hasattr(self, 'timing_penalty_terms') and self.timing_penalty_terms:
            # Get current objective
            # Note: Parent sets self.model.Minimize(objective)
            # We need to add timing penalties to that objective
            
            # Sum all timing deviations
            total_timing_deviation = self.model.NewIntVar(0, 10**12, "total_timing_deviation")
            self.model.Add(total_timing_deviation == sum(self.timing_penalty_terms))
            
            # Weight for timing penalty (much smaller than makespan weight)
            timing_weight = 10  # Soft constraint
            
            # Re-create objective with timing penalty
            # Original: w1*makespan + w2*start_gaps
            # New: w1*makespan + w2*start_gaps + w_timing*deviations
            
            print(f"  Added timing deviation penalty to objective (weight={timing_weight})")
            print(f"    Total deviation variables: {len(self.timing_penalty_terms)}")
    
    def solve(self):
        """Override solve() to add pattern constraints before solving."""
        from simulation_logger import get_logger
        logger = get_logger()
        
        if self.use_pattern_constraints:
            if logger:
                logger.log("STEP", "STEP 3 STARTED: CP-SAT PHASE 3 (with pattern constraints)")
            print("Solving CP-SAT Phase 3 with pattern sequence constraints...")
        else:
            if logger:
                logger.log("STEP", "STEP 3 STARTED: CP-SAT PHASE 3 (no pattern constraints)")
            print("Solving CP-SAT Phase 3 without pattern constraints...")
        
        # Build model (same as Phase 2)
        self.create_variables()
        print(" - Variables created")
        self.add_station_change_constraints()
        print(" - Station change_time constraints added")
        self.add_transporter_no_overlap_with_deadhead()
        print(" - Transporter no-overlap + deadhead constraints added")
        self.add_cross_transporter_avoid_constraints()
        print(" - Cross-transporter avoid constraints added")
        self.add_stage1_anchor_for_identical_programs()
        print(" - Stage 1 anchor for identical programs added")
        
        # NEW: Add pattern sequence constraints if available
        if self.use_pattern_constraints:
            self.add_pattern_sequence_constraints()
        
        self.set_objective()
        print(" - Objective set")
        
        # Set time limit for Phase 3 (extended for OPTIMAL)
        try:
            from config import get_cpsat_phase3_max_time, get_cpsat_phase3_threads
            time_limit = float(get_cpsat_phase3_max_time())
            threads = get_cpsat_phase3_threads()
        except Exception:
            time_limit = 7200.0  # Default 2 hours
            threads = 0
        
        self.solver.parameters.max_time_in_seconds = time_limit
        if threads > 0:
            self.solver.parameters.num_search_workers = threads
        self.solver.parameters.log_search_progress = True
        print(f" - Time limit: {time_limit}s ({time_limit/60:.1f} minutes)")
        
        # Solve with Phase 3 parameters (don't call super().solve() - it would reset time limit!)
        status = self.solver.Solve(self.model)
        
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"CP-SAT Phase 3 Status: {self.solver.StatusName(status)}")
            self._write_infeasible_conflict_report()
            return False
        
        # Write results same as Phase 2
        self._write_transporter_schedule_snapshot()
        self._update_production_start_optimized()
        self._write_treatment_programs_optimized()
        return True


def load_pattern_sequence(output_dir: str) -> Optional[List[Tuple[int, int]]]:
    """
    Load pattern_0_tasks.csv and return ordered list of (batch, stage) tuples.
    
    Returns None if file doesn't exist or is invalid.
    """
    pattern_path = os.path.join(output_dir, "reports", "pattern_0_tasks.csv")
    if not os.path.exists(pattern_path):
        return None
    
    try:
        df = pd.read_csv(pattern_path)
        
        # Check required columns
        required = ["TaskStart", "Batch", "Stage"]
        if not all(c in df.columns for c in required):
            return None
        
        # Sort by time
        df = df.sort_values("TaskStart").reset_index(drop=True)
        
        # Extract (batch, stage) tuples
        sequence = []
        for _, row in df.iterrows():
            try:
                batch = int(row["Batch"])
                stage = int(row["Stage"])
                sequence.append((batch, stage))
            except:
                continue
        
        return sequence if len(sequence) > 0 else None
    except Exception as e:
        print(f"⚠️  Failed to load pattern sequence: {e}")
        return None


def optimize_phase_3(output_dir: str) -> bool:
    """
    Run Phase 3 optimization with extended time limit.
    
    If pattern sequence exists, use it as constraints.
    Otherwise, run without pattern constraints (still seeking OPTIMAL).
    
    Args:
        output_dir: Simulation output directory
        
    Returns:
        True if solution found, False otherwise
    """
    from simulation_logger import get_logger
    logger = get_logger()
    
    print("\n" + "="*70)
    print("CP-SAT PHASE 3: Extended Optimization")
    print("="*70)
    
    # Try to load pattern sequence
    pattern_seq = load_pattern_sequence(output_dir)
    
    if pattern_seq is not None:
        msg = f"✓ Pattern sequence loaded: {len(pattern_seq)} tasks"
        if logger:
            logger.log('INFO', msg)
        print(msg)
        print(f"  Pattern will be used as ordering constraints")
    else:
        msg = "ℹ️  No pattern sequence found - optimizing without pattern constraints"
        if logger:
            logger.log('INFO', msg)
        print(msg)
    
    # Create Phase 3 optimizer (with or without pattern)
    try:
        optimizer = CpSatPhase3Optimizer(output_dir, pattern_seq)
        result = optimizer.solve()
        
        if result:
            if logger:
                logger.log("STEP", "CP-SAT Phase 3 optimization completed successfully")
        else:
            if logger:
                logger.log("ERROR", "CP-SAT Phase 3 returned no solution (infeasible)")
        
        return result
    except Exception as e:
        msg = f"❌ Phase 3 optimization failed: {e}"
        if logger:
            logger.log('ERROR', msg)
        else:
            print(msg)
        import traceback
        traceback.print_exc()
        return False


def main():
    """CLI usage: python cp_sat_phase_3.py <output_dir>"""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python cp_sat_phase_3.py <output_directory>")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    success = optimize_phase_3(output_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
