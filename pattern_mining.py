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
    batches_completed: int  # For reference only, not accurate throughput measure


def load_transporter_schedule(output_dir: str) -> pd.DataFrame:
    """Load the CP-SAT transporter schedule from the output directory."""
    # Try Phase 1+2 directory first (quick mode), then fallback to cp_sat (normal mode)
    for subdir in ["cp_sat_phase_1_2", "cp_sat"]:
        schedule_path = os.path.join(output_dir, subdir, "cp_sat_transporter_schedule.csv")
        if os.path.exists(schedule_path):
            break
    else:
        schedule_path = os.path.join(output_dir, "cp_sat", "cp_sat_transporter_schedule.csv")
    
    if not os.path.exists(schedule_path):
        raise FileNotFoundError(f"Transporter schedule not found: {schedule_path}")
    
    df = pd.read_csv(schedule_path)
    
    # Add Stage column if missing (derive from batch_schedule)
    if 'Stage' not in df.columns:
        # Load batch schedule to get Stage info - use same subdir as schedule
        subdir = os.path.dirname(schedule_path).split(os.sep)[-1]
        batch_schedule_path = os.path.join(output_dir, subdir, "cp_sat_station_schedule.csv")
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
    
    # Strategy: Find repeating stage sequence in TIME ORDER (not per-transporter)
    # Pattern is: stages 1-14 each appear once, then this sequence repeats
    print(f"\n  Strategy: Finding repeating stage sequence in chronological order...")
    
    # Build chronological stage sequence from ALL transporters
    df_sorted_time = df_sorted.sort_values('TaskStart')
    time_ordered_stages = df_sorted_time['Stage'].astype(int).tolist()
    time_ordered_indices = df_sorted_time.index.tolist()
    
    print(f"  Chronological stage sequence ({len(time_ordered_stages)} tasks):")
    print(f"    First 30: {time_ordered_stages[:30]}")
    
    # Find repeating pattern: sequence of stages 1-14 (each once) that repeats
    print(f"\n  Searching for repeating pattern containing each stage 1-14 exactly once...")
    
    best_pattern = None
    
    # Try different pattern lengths (should be around 14 stages)
    for pattern_len in range(len(required_stages), len(time_ordered_stages) // 2 + 1):
        # Try different starting positions
        for start_pos in range(len(time_ordered_stages) - pattern_len * 2 + 1):
            # Extract candidate pattern
            candidate_stages = time_ordered_stages[start_pos:start_pos + pattern_len]
            candidate_indices = time_ordered_indices[start_pos:start_pos + pattern_len]
            
            # Check: does this pattern contain all required stages exactly once?
            if set(candidate_stages) != required_stages:
                continue
            if len(candidate_stages) != len(set(candidate_stages)):
                continue  # Has duplicates
            
            # Check: does this pattern repeat at least once?
            found_repetition = False
            for next_start in range(start_pos + pattern_len, len(time_ordered_stages) - pattern_len + 1):
                next_stages = time_ordered_stages[next_start:next_start + pattern_len]
                if next_stages == candidate_stages:
                    found_repetition = True
                    break
            
            if found_repetition:
                # Found valid repeating pattern!
                tasks = df_sorted.loc[candidate_indices]
                time_start = tasks['TaskStart'].min()
                time_end = tasks['TaskEnd'].max()
                
                best_pattern = {
                    'length': pattern_len,
                    'stages': candidate_stages,
                    'time_start': time_start,
                    'time_end': time_end,
                    'duration': time_end - time_start,
                    'indices': candidate_indices,
                    'covered_stages': set(candidate_stages)
                }
                print(f"  ✓ Found repeating pattern!")
                print(f"    Length: {pattern_len} tasks")
                print(f"    Duration: {time_end - time_start}s")
                print(f"    Stage sequence: {candidate_stages}")
                break
        
        if best_pattern:
            break
    
    # Check if we found a valid pattern
    if best_pattern and best_pattern['covered_stages'] == required_stages:
        print(f"    ✓ Pattern covers ALL required stages")
        
        # Show detailed sequence
        pattern_indices = best_pattern['indices']
        pattern_start = best_pattern['time_start']
        pattern_end = best_pattern['time_end']
        duration = best_pattern['duration']
        
        print(f"\n  {'='*60}")
        print(f"  ✓✓ FOUND REPEATING PATTERN ✓✓")
        print(f"  {'='*60}")
        print(f"    Pattern length: {best_pattern['length']} tasks")
        print(f"    Duration: {duration}s ({duration/60:.1f}min)")
        print(f"    Stages: {sorted(best_pattern['covered_stages'])} ✓")
        print(f"\n    Detailed sequence:")
        # Show actual sequence of tasks
        pattern_df = df_sorted.loc[pattern_indices].sort_values('TaskStart')
        for idx, row in pattern_df.iterrows():
            print(f"      T{row['Transporter']} B{row['Batch']:02d} S{int(row['Stage']):02d} "
                  f"{row['TaskStart']:5d}s → {row['TaskEnd']:5d}s "
                  f"({row['TaskEnd']-row['TaskStart']:3d}s)")
        print(f"  {'='*60}")
        
        # Return ONE pattern
        found_complete_patterns = [{
            'pattern_sequence': [(t, s, i) for t, s, i in state_sequence 
                               if i in pattern_indices],
            'task_indices': pattern_indices,
            't1_length': len([i for i in pattern_indices if df_sorted.loc[i, 'Transporter'] == 1]),
            't2_length': len([i for i in pattern_indices if df_sorted.loc[i, 'Transporter'] == 2]),
            'duration': duration,
            'start_time': pattern_start,
            'end_time': pattern_end,
            'stages': best_pattern['covered_stages']
        }]
    else:
        print(f"\n  ⚠ Could not find repeating pattern")
        found_complete_patterns = []
    
    # JOKO/TAI: Either we found a scalable cycle OR no pattern
    if not found_complete_patterns:
        print(f"\n  {'='*60}")
        print(f"  ❌ NO MINIMAL PATTERN FOUND")
        print(f"  {'='*60}")
        print(f"  → Phase 3 will use FREE optimization (no pattern)")
        return []
    
    # Return the ONE cycle we found with task indices
    best = found_complete_patterns[0]
    return [(best['start_time'], best['end_time'], best['task_indices'])]


def analyze_cycle(df: pd.DataFrame, start_time: int, end_time: int, transporters: List[int], task_indices: Optional[List[int]] = None) -> CyclicPattern:
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
    
    # Get ALL tasks in this time window (from all transporters)
    # This ensures we capture both T1 and T2 tasks that happen during the cycle
    cycle_tasks = df[
        (df['TaskStart'] >= start_time) & 
        (df['TaskStart'] < end_time)
    ].copy()
    
    # Count batches involved (for reference, not accurate throughput)
    batches_in_cycle = cycle_tasks['Batch'].nunique() if len(cycle_tasks) > 0 else 0
    
    return CyclicPattern(
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        transporter_states=end_states,
        tasks_in_cycle=cycle_tasks,
        batches_completed=batches_in_cycle
    )


def find_cyclic_patterns(output_dir: str, max_cycle_duration: int = 7200, require_complete: bool = True) -> List[CyclicPattern]:
    """
    Main function to find cyclic patterns in the transporter schedule.
    
    Args:
        output_dir: Path to the simulation output directory
        max_cycle_duration: Maximum cycle duration in seconds (default 2 hours)
        require_complete: If True, only return cycles that contain all treatment stages
    
    Returns:
        List of discovered cyclic patterns, sorted by duration (ascending)
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
    
    for idx, candidate in enumerate(cycle_candidates):
        if len(candidate) == 3:
            start, end, task_indices = candidate
        else:
            start, end = candidate
            task_indices = None
        
        duration = end - start
        
        # Skip cycles that are too long
        if duration > max_cycle_duration:
            continue
        
        # Skip very short cycles
        if duration < 30:
            continue
        
        pattern = analyze_cycle(df, start, end, transporters, task_indices)
        
        # Accept patterns with batches
        if pattern.batches_completed > 0:
            patterns.append(pattern)
            
            print(f"\n  ✓ Pattern #{len(patterns)}:")
            print(f"    Time: {start}s → {end}s")
            print(f"    Duration: {duration}s ({duration/60:.1f}min)")
            print(f"    Batches: {pattern.batches_completed}")
            print(f"    Batches involved: {pattern.batches_completed}")
            print(f"    Tasks: {len(pattern.tasks_in_cycle)}")
            print(f"    Transporter end positions: {pattern.transporter_states}")
    
    # Sort by duration (ascending - prefer shorter cycles)
    patterns.sort(key=lambda p: p.duration)
    
    print("\n" + "="*70)
    print(f"SUMMARY: Found {len(patterns)} cyclic pattern(s)")
    if patterns:
        best = patterns[0]
        print(f"Best pattern: {best.duration}s ({best.duration/60:.1f}min), {best.batches_completed} batches involved")
    print("="*70 + "\n")
    
    return patterns


def create_sequence_matrix(pattern: CyclicPattern, output_dir: str) -> Optional[pd.DataFrame]:
    """
    Luo sequence_matrix.csv joka kuvaa erien liikkeet asemilla sekvenssin ajalta.
    
    Rakenne kuten line_matrix, mutta vain sekvenssin ajalta.
    Eränumerot korvataan kirjaimilla A, B, C, jne.
    
    Args:
        pattern: Löydetty pattern
        output_dir: Output directory
    
    Returns:
        DataFrame tai None
    """
    # Lataa treatment program tiedot (MinTime, MaxTime)
    treatment_program_path = os.path.join("initialization", "treatment_program_001.csv")
    if not os.path.exists(treatment_program_path):
        print(f"  ⚠ Treatment program not found: {treatment_program_path}")
        return None
    
    treatment_df = pd.read_csv(treatment_program_path)
    
    # Muunna aika-sarakkeet sekunneiksi
    for col in ['MinTime', 'MaxTime']:
        treatment_df[col] = pd.to_timedelta(treatment_df[col]).dt.total_seconds().astype(int)
    
    # Lataa station schedule saadaksemme CalcTime-tiedot
    for subdir in ["cp_sat_phase_1_2", "cp_sat"]:
        station_schedule_path = os.path.join(output_dir, subdir, "cp_sat_station_schedule.csv")
        if os.path.exists(station_schedule_path):
            break
    else:
        station_schedule_path = None
    
    if station_schedule_path and os.path.exists(station_schedule_path):
        station_df = pd.read_csv(station_schedule_path)
    else:
        print(f"  ⚠ Station schedule not found")
        return None
    
    # Sorteerataan pattern tasks ajan mukaan
    tasks = pattern.tasks_in_cycle.sort_values('TaskStart').copy()
    
    # Luodaan batch mapping: alkuperäinen batch numero -> kirjain
    unique_batches = sorted(tasks['Batch'].unique())
    batch_mapping = {batch: chr(65 + i) for i, batch in enumerate(unique_batches)}  # A, B, C, ...
    
    # Rakennetaan sequence matrix
    rows = []
    
    for _, task in tasks.iterrows():
        batch_num = int(task['Batch'])
        stage = int(task['Stage'])
        batch_letter = batch_mapping[batch_num]
        
        # Hae station station_schedule:sta
        station_row = station_df[(station_df['Batch'] == batch_num) & (station_df['Stage'] == stage)]
        if len(station_row) == 0:
            continue
        
        station_row = station_row.iloc[0]
        station = int(station_row['Station'])
        
        # Hae treatment program tiedot
        treatment_row = treatment_df[treatment_df['Stage'] == stage]
        if len(treatment_row) == 0:
            continue
        
        treatment_row = treatment_row.iloc[0]
        min_time = int(treatment_row['MinTime'])
        max_time = int(treatment_row['MaxTime'])
        
        # CalcTime asemalla
        calc_time = int(station_row['CalcTime']) if 'CalcTime' in station_row else 0
        
        # EntryTime = kun erä saapuu asemalle = kun nostimen tehtävä loppuu
        entry_time = int(task['TaskEnd'])
        
        # ExitTime = EntryTime + CalcTime
        exit_time = entry_time + calc_time
        
        # TransportTime = nostimen tehtävän kesto
        transport_time = int(task['TaskEnd'] - task['TaskStart'])
        
        # Program ja Treatment_program
        program = f"Program_{batch_letter}"
        treatment_program = "Treatment_Program_001"
        
        rows.append({
            'Batch': batch_letter,
            'Program': program,
            'Treatment_program': treatment_program,
            'Stage': stage,
            'Station': station,
            'MinTime': min_time,
            'MaxTime': max_time,
            'CalcTime': calc_time,
            'EntryTime': entry_time,
            'ExitTime': exit_time,
            'TransportTime': transport_time
        })
    
    if not rows:
        return None
    
    sequence_matrix = pd.DataFrame(rows)
    
    # Järjestä batch ja stage mukaan
    sequence_matrix = sequence_matrix.sort_values(['Batch', 'Stage'])
    
    # Normalisoi ajat alkamaan nollasta (siirrä ensimmäinen sykli alkamaan ajasta 0)
    min_time = sequence_matrix['EntryTime'].min()
    sequence_matrix['EntryTime'] = sequence_matrix['EntryTime'] - min_time
    sequence_matrix['ExitTime'] = sequence_matrix['ExitTime'] - min_time
    
    # Laske syklin todellinen kesto:
    # Viimeisen erän poistumisaika + aika että nostin on valmis aloittamaan uuden syklin
    # Pattern-objektissa on cycle duration joka sisältää tämän
    cycle_duration = pattern.duration
    
    # Toista sama sykli kolme kertaa peräkkäin
    # Nostimet tekevät saman liikesarjan, erät siirtyvät
    all_cycles = [sequence_matrix.copy()]
    
    for cycle_num in range(1, 3):
        next_cycle = sequence_matrix.copy()
        
        # Siirrä ajat syklin keston verran eteenpäin
        # Tämä huomioi myös viimeisen liikkeen jälkeisen ajan
        time_offset = cycle_duration * cycle_num
        next_cycle['EntryTime'] = next_cycle['EntryTime'] + time_offset
        next_cycle['ExitTime'] = next_cycle['ExitTime'] + time_offset
        
        all_cycles.append(next_cycle)
    
    # Yhdistä kaikki syklit
    sequence_matrix = pd.concat(all_cycles, ignore_index=True)
    sequence_matrix = sequence_matrix.sort_values(['EntryTime'])
    
    return sequence_matrix


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
        f.write(f"Batches involved: {pattern.batches_completed}\n")
        f.write(f"Tasks in cycle: {len(pattern.tasks_in_cycle)}\n")
        f.write(f"\nTransporter end positions:\n")
        for tid, station in sorted(pattern.transporter_states.items()):
            f.write(f"  Transporter {tid}: Station {station}\n")
    
    print(f"  ✓ Pattern {pattern_index} exported: {tasks_file}")
    
    # Export sequence_matrix.csv
    sequence_matrix_file = os.path.join(reports_dir, f"sequence_matrix.csv")
    sequence_matrix = create_sequence_matrix(pattern, output_dir)
    if sequence_matrix is not None:
        sequence_matrix.to_csv(sequence_matrix_file, index=False)
        print(f"  ✓ Sequence matrix exported: {sequence_matrix_file}")


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
