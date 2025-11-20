"""
CP-SAT Phase 3: Phase 2 optimization with pattern constraints

Phase 3 = Phase 2 (täydelliset rajoitteet) + pattern-based transition constraints
"""

import os
import pandas as pd
from typing import Dict, List
from cp_sat_phase_2 import CpSatPhase2Optimizer, _copy_results_to_cp_sat


def _load_pattern(output_dir: str) -> Dict[int, List[int]]:
    """
    Lataa pattern mining tulokset (reports/pattern_0_tasks.csv).
    
    Returns:
        Dict: transporter_id -> [stage1, stage2, ...] (syklinen järjestys)
    """
    pattern_path = os.path.join(output_dir, "reports", "pattern_0_tasks.csv")
    
    if not os.path.exists(pattern_path):
        return {}
    
    pattern_df = pd.read_csv(pattern_path).sort_values("TaskStart")
    
    # Ryhmitä nostimen mukaan
    pattern_per_transporter = {}
    for trans_id in pattern_df["Transporter"].unique():
        trans_tasks = pattern_df[pattern_df["Transporter"] == trans_id].copy()
        stage_sequence = trans_tasks["Stage"].tolist()
        
        # Poista duplikaatit (pidä ensimmäinen esiintymä)
        seen = set()
        unique_stages = []
        for s in stage_sequence:
            if s not in seen:
                seen.add(s)
                unique_stages.append(s)
        
        pattern_per_transporter[int(trans_id)] = unique_stages
    
    return pattern_per_transporter


def _add_pattern_constraints(optimizer: CpSatPhase2Optimizer, pattern: Dict[int, List[int]]):
    """
    Lisää pattern-pohjaiset järjestysrajoitteet.
    
    Pattern määrittää JÄRJESTYKSEN jossa nostin käsittelee vaiheensa:
    - T1: vaiheet 11→12→13→1→9→10→14 (syklisesti toistuva)
    - T2: vaiheet 7→4→8→5→2→6→3 (syklisesti toistuva)
    
    Rajoite: Kaikki batch:it noudat tätä järjestystä (ei vaihtoehtoisia polkuja).
    """
    if not pattern:
        return
    
    print(f"\n{'='*70}")
    print(f"ADDING PATTERN SEQUENCE CONSTRAINTS")
    print(f"{'='*70}")
    
    for trans_id, stages in pattern.items():
        print(f"  T{trans_id} pattern: {stages} (sequence enforced)")
    
    # Lisää rajoitteet per batch ja transporter:
    # Batch b:n vaiheet tälle nostimelle pitää tapahtua pattern-järjestyksessä
    
    constraint_count = 0
    
    for batch_row in optimizer.batches_df.itertuples():
        batch_num = int(batch_row.Batch)
        
        # Käy läpi kummankin nostimen pattern
        for trans_id, stage_sequence in pattern.items():
            # Etsi tämän batchin vaiheet jotka kuuluvat tälle nostimelle
            batch_stages_for_trans = []
            
            for stage in stage_sequence:
                key = (batch_num, stage)
                if key in optimizer.transporter_starts:
                    batch_stages_for_trans.append(stage)
            
            # Lisää järjestysrajoitteet: stage i pitää tapahtua ennen stage i+1
            for i in range(len(batch_stages_for_trans) - 1):
                stage_curr = batch_stages_for_trans[i]
                stage_next = batch_stages_for_trans[i + 1]
                
                # Nostimen tehtävä stage_next alkaa vasta kun stage_curr loppu
                key_curr = (batch_num, stage_curr)
                key_next = (batch_num, stage_next)
                
                # transporter_start(stage_next) >= transporter_end(stage_curr)
                optimizer.model.Add(
                    optimizer.transporter_starts[key_next] >= 
                    optimizer.transporter_ends[key_curr]
                )
                constraint_count += 1
    
    print(f"\n  ✓ Added {constraint_count} pattern sequence constraints")
    print(f"  Each transporter follows its pattern order for all batches")
    print(f"{'='*70}\n")


def optimize_phase_3(output_dir: str, phase_subdir: str = "cp_sat_phase_1_3"):
    """
    Run Phase 3: Phase 2 optimization + pattern constraints.
    
    Phase 3 käyttää Phase 2:n KAIKKIA rajoitteita (ei uudelleentoteutusta),
    ja lisää pattern-pohjaiset siirtymärajoitteet.
    
    Args:
        output_dir: Output directory
        phase_subdir: Subdirectory for Phase 3 (default "cp_sat_phase_1_3")
    """
    print(f"\n{'='*70}")
    print(f"PHASE 3: PHASE 2 + PATTERN CONSTRAINTS")
    print(f"{'='*70}")
    print(f"Using Phase 2 optimization with full constraints...")
    print(f"TODO: Add pattern-based transition constraints")
    print(f"{'='*70}\n")
    
    # Käytä Phase 2:ta suoraan (kaikki rajoitteet mukana)
    optimizer = CpSatPhase2Optimizer(output_dir, phase_subdir)
    
    # Lisää pattern-rajoitteet
    pattern = _load_pattern(output_dir)
    if pattern:
        _add_pattern_constraints(optimizer, pattern)
    else:
        print("⚠️  No pattern found - running without pattern constraints (same as Phase 2)")
    
    # Ratkaise
    result = optimizer.solve()
    
    # Kopioi tulokset cp_sat/ -kansioon
    if result:
        _copy_results_to_cp_sat(output_dir, phase_subdir)
    
    return optimizer


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python cp_sat_phase_3.py <output_dir> [phase_subdir]")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    phase_subdir = sys.argv[2] if len(sys.argv) > 2 else "cp_sat_phase_1_3"
    
    optimize_phase_3(output_dir, phase_subdir)
