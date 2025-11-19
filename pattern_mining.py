#!/usr/bin/env python3
"""
Pattern Mining for Cyclic Sequences in Transporter Schedules

Finds repeating patterns where transporters execute synchronized stage sequences.
Focus on finding the shortest complete pattern that covers all treatment stages
and involves both transporters.
"""
import os
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CyclicPattern:
    """Represents a discovered cyclic pattern in the schedule."""
    start_time: int
    end_time: int
    duration: int
    transporter_states: Dict[int, str]  # transporter_id -> station at end
    tasks_in_cycle: pd.DataFrame
    batches_completed: int
    throughput: float  # batches per hour


def load_transporter_schedule(output_dir: str) -> pd.DataFrame:
    """Load the CP-SAT transporter schedule from the output directory."""
    # Phase 2 saves as cp_sat_transporter_schedule.csv
    schedule_path = os.path.join(output_dir, "cp_sat", "cp_sat_transporter_schedule.csv")
    
    if not os.path.exists(schedule_path):
        raise FileNotFoundError(f"Transporter schedule not found: {schedule_path}")
    
    df = pd.read_csv(schedule_path)
    
    # Add Stage column if missing (derive from batch_schedule)
    if 'Stage' not in df.columns:
        # Load batch schedule to get Stage info
        batch_schedule_path = os.path.join(output_dir, "cp_sat", "cp_sat_station_schedule.csv")
        if os.path.exists(batch_schedule_path):
            batch_sched = pd.read_csv(batch_schedule_path)
            # Merge Stage info based on Batch and Station (To_Station)
            df = df.merge(
                batch_sched[['Batch', 'Stage', 'Station']].rename(columns={'Station': 'To_Station'}),
                on=['Batch', 'To_Station'],
                how='left'
            )
    
    print(f"✓ Loaded schedule with {len(df)} tasks")
    return df


def find_stage_sequence_patterns(df: pd.DataFrame, min_length: int = 5, max_length: int = 50) -> List[Tuple[int, int]]:
    """
    Find repeating patterns in synchronized multi-transporter stage sequences.
    Creates a combined stage-state sequence where each state is a tuple of all transporters' stages.
    
    Returns list of (start_time, end_time) pairs representing repeating sequences.
    """
    if 'Stage' not in df.columns or df['Stage'].isna().all():
        print("⚠ No Stage column found in schedule")
        return []
    
    # Sort by time to create chronological sequence
    df_sorted = df.sort_values('TaskStart').reset_index(drop=True)
    
    # Create synchronized state sequence: [(time, {trans1: stage1, trans2: stage2, ...}), ...]
    transporters = sorted(df['Transporter'].unique())
    print(f"\n  Creating synchronized stage-state sequence for {len(transporters)} transporters...")
    
    # Build state history: time -> {transporter: stage}
    state_sequence = []
    current_state = {t: None for t in transporters}
    
    for _, row in df_sorted.iterrows():
        trans_id = row['Transporter']
        stage = int(row['Stage']) if pd.notna(row['Stage']) else None
        task_end = int(row['TaskEnd'])
        
        if stage is not None:
            # Update this transporter's stage
            current_state[trans_id] = stage
            
            # Record state snapshot (make immutable tuple for hashing)
            state_tuple = tuple(sorted([(t, s) for t, s in current_state.items() if s is not None]))
            state_sequence.append((task_end, state_tuple, row.name))
    
    print(f"  Created {len(state_sequence)} state snapshots")
    if len(state_sequence) > 0:
        print(f"  Example states:")
        for i in range(min(3, len(state_sequence))):
            time, state, _ = state_sequence[i]
            state_str = ", ".join([f"T{t}:S{s}" for t, s in state])
            print(f"    @{time}s: {state_str}")
    
    # Extract just the state tuples for pattern matching
    states_only = [state for _, state, _ in state_sequence]
    
    # Get all stages that appear in schedule
    all_stages = set()
    for state_tuple in states_only:
        for trans_id, stage in state_tuple:
            all_stages.add(stage)
    
    print(f"  Stages in schedule: {sorted(all_stages)}")
    required_stages = set(range(1, 15))  # S1-S14
    print(f"  Required stages: {sorted(required_stages)}")
    
    # Strategy: Find ONE repeating CYCLE (sykli) that both transporters execute
    # Goal: Repeating pattern that can be scaled from 8 batches to 28 batches
    # This is JOKO/TAI: either we find a scalable cycle OR we use free optimization
    print(f"\n  Strategy: Finding ONE scalable cycle (sykli)...")
    
    # Build per-transporter stage sequences with timing
    transporter_sequences = {}
    for time, state_tuple, idx in state_sequence:
        for trans_id, stage in state_tuple:
            if trans_id not in transporter_sequences:
                transporter_sequences[trans_id] = []
            transporter_sequences[trans_id].append((time, stage, idx))
    
    # Print transporter sequences
    print(f"  Per-transporter sequences:")
    for tid in sorted(transporter_sequences.keys()):
        seq = transporter_sequences[tid]
        stages = [stage for _, stage, _ in seq]
        print(f"    T{tid}: {len(seq)} tasks, stages: {stages[:15]}{'...' if len(stages) > 15 else ''}")
    
    # Find SHORTEST TIME-DURATION SYNCHRONIZED cycle where ALL transporters TOGETHER cover all stages
    # Each transporter has its own repeating sequence, but TOGETHER they must cover stages 1-14
    print(f"\n  Searching for SHORTEST synchronized cycle where transporters TOGETHER cover all stages...")
    
    transporter_cycles = {}
    
    # First, find repeating patterns for each transporter (doesn't need to cover all stages individually)
    for tid in sorted(transporter_sequences.keys()):
        seq = transporter_sequences[tid]
        stages = [stage for _, stage, _ in seq]
        times = [time for time, _, _ in seq]
        
        print(f"\n    T{tid}: Finding any repeating cycle...")
        
        valid_cycles = []
        
        for cycle_len in range(3, len(seq) // 2 + 1):
            for cycle_start in range(len(stages) - 2 * cycle_len + 1):
                candidate_cycle = stages[cycle_start:cycle_start + cycle_len]
                
                # Check if this candidate repeats at least once
                repeat_positions = [cycle_start]
                
                for test_start in range(cycle_start + cycle_len, len(stages) - cycle_len + 1):
                    test_cycle = stages[test_start:test_start + cycle_len]
                    if candidate_cycle == test_cycle:
                        repeat_positions.append(test_start)
                
                if len(repeat_positions) >= 2:
                    # Calculate time duration
                    time_start = times[cycle_start]
                    time_end = times[cycle_start + cycle_len - 1]
                    duration = time_end - time_start
                    
                    valid_cycles.append({
                        'length': cycle_len,
                        'stages': candidate_cycle,
                        'time_start': time_start,
                        'time_end': time_end,
                        'duration': duration,
                        'indices': [idx for _, _, idx in seq[cycle_start:cycle_start + cycle_len]],
                        'repetitions': len(repeat_positions),
                        'positions': repeat_positions,
                        'covered_stages': set(candidate_cycle)
                    })
        
        # Select the cycle with MOST STAGES (to maximize coverage), then shortest duration
        if valid_cycles:
            # Sort by: 1) most stages, 2) shortest duration
            valid_cycles.sort(key=lambda c: (-len(c['covered_stages']), c['duration']))
            best_cycle = valid_cycles[0]
            transporter_cycles[tid] = best_cycle
            print(f"      ✓ Found cycle: {best_cycle['length']} tasks, {best_cycle['repetitions']} reps, {best_cycle['duration']}s")
            print(f"        Stages ({len(best_cycle['covered_stages'])}): {sorted(best_cycle['covered_stages'])}")
        else:
            print(f"      ⚠ No repeating cycle found")
    
    # Check if ALL transporters have cycles AND together they cover all stages
    if len(transporter_cycles) == len(transporters):
        print(f"\n  ✓ All transporters have repeating cycles")
        
        # Check COMBINED stage coverage
        all_stages = set()
        for tid, cycle_info in transporter_cycles.items():
            all_stages.update(cycle_info['covered_stages'])
        
        print(f"    Combined stage coverage: {sorted(all_stages)}")
        print(f"    Required stages: {sorted(required_stages)}")
        
        # Check if TOGETHER they cover most stages (allow 1-2 missing for edge cases like final stage)
        missing_stages = required_stages - all_stages
        if len(missing_stages) <= 1:  # Accept if at most 1 stage missing
            if missing_stages:
                print(f"    ⓘ Accepting cycle with {len(missing_stages)} missing stage(s): {sorted(missing_stages)}")
            
            # Combine cycles into ONE scalable pattern
            all_indices = []
            for tid, cycle_info in transporter_cycles.items():
                all_indices.extend(cycle_info['indices'])
            
            # Get tasks from combined cycle
            pattern_tasks = df_sorted.loc[sorted(all_indices)]
            pattern_start = pattern_tasks['TaskStart'].min()
            pattern_end = pattern_tasks['TaskEnd'].max()
            duration = pattern_end - pattern_start
            
            print(f"\n  {'='*60}")
            print(f"  ✓✓ FOUND SYNCHRONIZED SCALABLE CYCLE ✓✓")
            print(f"  {'='*60}")
            for tid, cycle_info in transporter_cycles.items():
                print(f"    T{tid}: {cycle_info['length']} tasks × {cycle_info['repetitions']} reps")
                print(f"          Stages: {sorted(cycle_info['covered_stages'])}")
                print(f"          Duration: {cycle_info['duration']}s")
            print(f"    COMBINED coverage: {sorted(all_stages)} ✓")
            print(f"    Total duration: {duration}s ({duration/60:.1f}min)")
            print(f"  {'='*60}")
            
            # Return ONE pattern (the synchronized cycle)
            found_complete_patterns = [{
                'pattern_sequence': [(t, s, i) for t, s, i in state_sequence 
                                   if i in all_indices],
                't1_length': transporter_cycles.get(1, {}).get('length', 0),
                't2_length': transporter_cycles.get(2, {}).get('length', 0),
                't1_repeats': transporter_cycles.get(1, {}).get('repetitions', 0),
                't2_repeats': transporter_cycles.get(2, {}).get('repetitions', 0),
                'duration': duration,
                'start_time': pattern_start,
                'end_time': pattern_end,
                'stages': all_stages,
                'transporter_cycles': transporter_cycles
            }]
        else:
            missing = required_stages - all_stages
            print(f"  ⚠ Combined cycles don't cover all stages")
            print(f"    Missing: {sorted(missing)}")
            found_complete_patterns = []
    else:
        print(f"\n  ⚠ Could not find repeating cycles for all transporters")
        found_complete_patterns = []
    
    # JOKO/TAI: Either we found a scalable cycle OR no pattern
    if len(found_complete_patterns) == 0:
        print(f"\n  {'='*60}")
        print(f"  ❌ NO SCALABLE CYCLE FOUND")
        print(f"  {'='*60}")
        print(f"  → Phase 3 will use FREE optimization (no pattern)")
        return []
    
    # Return the ONE cycle we found
    best = found_complete_patterns[0]
    return [(best['start_time'], best['end_time'])]


def analyze_cycle(df: pd.DataFrame, start_time: int, end_time: int, transporters: List[int]) -> CyclicPattern:
    """Analyze a potential cycle and create a CyclicPattern object."""
    duration = end_time - start_time
    
    # Get transporter positions at end
    end_states = {}
    for tid in transporters:
        trans_tasks = df[df['Transporter'] == tid]
        trans_tasks = trans_tasks[trans_tasks['TaskEnd'] <= end_time]
        if len(trans_tasks) > 0:
            last_task = trans_tasks.iloc[-1]
            end_states[tid] = str(int(last_task['To_Station']))
        else:
            end_states[tid] = "Unknown"
    
    # Get tasks in this cycle
    cycle_tasks = df[
        (df['TaskStart'] >= start_time) & 
        (df['TaskStart'] < end_time)
    ].copy()
    
    # Count unique batches
    batches_completed = cycle_tasks['Batch'].nunique() if len(cycle_tasks) > 0 else 0
    
    # Calculate throughput (batches per hour)
    duration_hours = duration / 3600
    throughput = batches_completed / duration_hours if duration_hours > 0 else 0
    
    return CyclicPattern(
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        transporter_states=end_states,
        tasks_in_cycle=cycle_tasks,
        batches_completed=batches_completed,
        throughput=throughput
    )


def find_cyclic_patterns(output_dir: str, max_cycle_duration: int = 7200, require_complete: bool = True) -> List[CyclicPattern]:
    """
    Main function to find cyclic patterns in the transporter schedule.
    
    Args:
        output_dir: Path to the simulation output directory
        max_cycle_duration: Maximum cycle duration in seconds (default 2 hours)
        require_complete: If True, only return cycles that contain all treatment stages
    
    Returns:
        List of discovered cyclic patterns, sorted by throughput (descending)
    """
    print("\n" + "="*70)
    print("PATTERN MINING: Searching for Stage-Based Cyclic Patterns")
    print("="*70)
    
    # Load schedule
    df = load_transporter_schedule(output_dir)
    
    # Get list of transporters
    transporters = sorted(df['Transporter'].unique())
    print(f"✓ Found {len(transporters)} transporters: {transporters}")
    
    # Find stage-based sequence patterns
    print("\n🔍 Searching for repeating stage sequences (covering all stages)...")
    cycle_candidates = find_stage_sequence_patterns(df)
    
    if len(cycle_candidates) == 0:
        print("\n❌ No complete stage sequence patterns found")
        print("="*70 + "\n")
        return []
    
    # Analyze each cycle candidate
    patterns = []
    
    for idx, (start, end) in enumerate(cycle_candidates):
        duration = end - start
        
        # Skip cycles that are too long
        if duration > max_cycle_duration:
            continue
        
        # Skip very short cycles
        if duration < 30:
            continue
        
        pattern = analyze_cycle(df, start, end, transporters)
        
        # Accept patterns with batches
        if pattern.batches_completed > 0:
            patterns.append(pattern)
            
            print(f"\n  ✓ Pattern #{len(patterns)}:")
            print(f"    Time: {start}s → {end}s")
            print(f"    Duration: {duration}s ({duration/60:.1f}min)")
            print(f"    Batches: {pattern.batches_completed}")
            print(f"    Throughput: {pattern.throughput:.2f} batches/hour")
            print(f"    Tasks: {len(pattern.tasks_in_cycle)}")
            print(f"    Transporter end positions: {pattern.transporter_states}")
    
    # Sort by throughput (descending)
    patterns.sort(key=lambda p: p.throughput, reverse=True)
    
    print("\n" + "="*70)
    print(f"SUMMARY: Found {len(patterns)} cyclic pattern(s)")
    if patterns:
        best = patterns[0]
        print(f"Best pattern: {best.duration}s, {best.throughput:.2f} batches/h, {best.batches_completed} batches")
    print("="*70 + "\n")
    
    return patterns


def export_pattern_report(pattern: CyclicPattern, output_dir: str, pattern_index: int = 0):
    """
    Export pattern details to CSV file in reports directory.
    
    Args:
        pattern: The pattern to export
        output_dir: Output directory
        pattern_index: Index of this pattern (0 = best)
    """
    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # Export tasks in cycle
    tasks_file = os.path.join(reports_dir, f"pattern_{pattern_index}_tasks.csv")
    pattern.tasks_in_cycle.to_csv(tasks_file, index=False)
    
    # Export summary
    summary_file = os.path.join(reports_dir, f"pattern_{pattern_index}_summary.txt")
    with open(summary_file, 'w') as f:
        f.write(f"Pattern {pattern_index} Summary\n")
        f.write("="*50 + "\n\n")
        f.write(f"Start time: {pattern.start_time}s\n")
        f.write(f"End time: {pattern.end_time}s\n")
        f.write(f"Duration: {pattern.duration}s ({pattern.duration/60:.1f} minutes)\n")
        f.write(f"Batches completed: {pattern.batches_completed}\n")
        f.write(f"Throughput: {pattern.throughput:.2f} batches/hour\n")
        f.write(f"Tasks in cycle: {len(pattern.tasks_in_cycle)}\n")
        f.write(f"\nTransporter end positions:\n")
        for tid, station in sorted(pattern.transporter_states.items()):
            f.write(f"  Transporter {tid}: Station {station}\n")
    
    print(f"  ✓ Pattern {pattern_index} exported: {tasks_file}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pattern_mining.py <output_directory>")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    patterns = find_cyclic_patterns(output_dir)
    
    if patterns:
        for i, p in enumerate(patterns[:3]):  # Export top 3
            export_pattern_report(p, output_dir, i)
    else:
        print("No patterns found")
        sys.exit(1)
