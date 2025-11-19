"""
CP-SAT Phase 3: Extended optimization with optional pattern constraints

Inherits all functionality from Phase 2, with optional addition of stage sequence
constraints when a pattern is detected.
"""

import os
import pandas as pd
from typing import List, Tuple, Optional
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
        Add stage sequence constraints based on discovered pattern.
        
        Pattern defines order: (B1,S9) → (B1,S10) → (B2,S2) → ...
        Constraint: exit(task[i]) <= entry(task[i+1])
        
        This is only called if pattern_sequence is provided.
        """
        if not self.use_pattern_constraints:
            return
        
        if len(self.pattern_sequence) < 2:
            print("⚠️  Pattern sequence too short, skipping constraints")
            return
        
        # Pattern is ONE CYCLE (sykli) from 8-batch quick run
        # We use PAKKO-OHJAUS: repeat this cycle to cover all batches
        # This is JOKO/TAI: either pattern forces sequence OR free optimization
        
        print(f"\n{'='*70}")
        print(f"PAKKO-OHJAUS: Enforcing cycle repetition")
        print(f"{'='*70}")
        print(f"Pattern cycle: {len(self.pattern_sequence)} tasks from 8-batch run")
        
        # Get batches in the cycle
        cycle_batches = sorted(set(b for b, _ in self.pattern_sequence))
        batches_in_cycle = len(cycle_batches)
        
        # Get total batches we're optimizing
        total_batches = len(set(self.production_df['Batch']))
        
        # Calculate how many times to repeat cycle
        num_repetitions = (total_batches + batches_in_cycle - 1) // batches_in_cycle
        
        print(f"Cycle covers: {batches_in_cycle} batches")
        print(f"Total batches: {total_batches}")
        print(f"Repetitions needed: {num_repetitions}")
        print(f"{'='*70}\n")
        
        # Apply HARD constraints: cycle order must be preserved in each repetition
        constraint_count = 0
        
        for rep in range(num_repetitions):
            batch_offset = rep * batches_in_cycle
            
            # Enforce order within this cycle repetition
            for i in range(len(self.pattern_sequence) - 1):
                b1, s1 = self.pattern_sequence[i]
                b2, s2 = self.pattern_sequence[i + 1]
                
                # Map to actual batch numbers
                actual_b1 = b1 + batch_offset
                actual_b2 = b2 + batch_offset
                
                # Skip if beyond total batches
                if actual_b1 >= total_batches or actual_b2 >= total_batches:
                    continue
                
                key1 = (actual_b1, s1)
                key2 = (actual_b2, s2)
                
                if key1 in self.entry and key1 in self.exit and key2 in self.entry:
                    # HARD constraint: task1 must END before task2 STARTS
                    self.model.Add(self.exit[key1] <= self.entry[key2])
                    constraint_count += 1
        
        print(f"✓ Added {constraint_count} HARD pattern constraints")
        print(f"  (Pattern sequence is FORCED - PAKKO-OHJAUS active)\n")
    
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
            from config import get_cpsat_phase3_max_time
            time_limit = float(get_cpsat_phase3_max_time())
        except Exception:
            time_limit = 7200.0  # Default 2 hours
        
        self.solver.parameters.max_time_in_seconds = time_limit
        print(f" - Time limit: {time_limit}s ({time_limit/60:.1f} minutes)")
        
        # Continue with normal Phase 2 solving logic
        return super().solve()


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
