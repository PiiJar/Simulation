#!/usr/bin/env python3
"""
TEST STEP 5 CP-SAT: Optimize Transporter Tasks using CP-SAT
===========================================================

This script replaces the traditional greedy algorithm (generate_tasks, order_tasks,
resolve_station_conflicts, stretch_tasks) with a CP-SAT-based Job Shop Scheduling
optimization.

Input:
- output_dir/logs/line_matrix_original.csv
- output_dir/initialization/stations.csv
- output_dir/initialization/transporters.csv

Output:
- output_dir/logs/transporter_tasks_optimized.csv (replaces transporter_tasks_stretched.csv)
- Updated simulation_log.csv

Advantages:
- OPTIMAL makespan (not just "good enough")
- Automatic conflict resolution (no manual stretching)
- Global optimization (considers all tasks simultaneously)
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Import the logger from test_step1.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_step1 import SimulationLogger
from optimize_cpsat import optimize_transporter_schedule


def optimize_transporter_tasks_cpsat(output_dir, time_limit=60):
    """
    Optimoi nostintehtävät CP-SAT:lla (Job Shop Scheduling).
    
    Args:
        output_dir (str): Path to simulation output directory
        time_limit (int): Maximum time for optimization (seconds)
        
    Returns:
        tuple: (optimized_df, output_csv_path)
    """
    
    # Initialize logger
    logger = SimulationLogger(output_dir)
    
    logger.log("TASK", "Step 5 CP-SAT started: Optimize transporter tasks using CP-SAT")
    
    # Read input files
    matrix_file = os.path.join(output_dir, "logs", "line_matrix_original.csv")
    stations_file = os.path.join(output_dir, "initialization", "stations.csv")
    transporters_file = os.path.join(output_dir, "initialization", "transporters.csv")
    
    # Validate files exist
    if not os.path.exists(matrix_file):
        error_msg = f"Original matrix file not found: {matrix_file}"
        logger.log("ERROR", error_msg)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: {error_msg}")
        return None, None
    
    if not os.path.exists(stations_file):
        error_msg = f"Stations file not found: {stations_file}"
        logger.log("ERROR", error_msg)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: {error_msg}")
        return None, None
    
    if not os.path.exists(transporters_file):
        error_msg = f"Transporters file not found: {transporters_file}"
        logger.log("ERROR", error_msg)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: {error_msg}")
        return None, None
    
    # Load data
    logger.log("READ", f"Reading input files for CP-SAT optimization")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] Ladataan syötteet...")
    
    matrix_df = pd.read_csv(matrix_file)
    stations_df = pd.read_csv(stations_file)
    transporters_df = pd.read_csv(transporters_file)
    
    logger.log("INFO", f"Matrix: {len(matrix_df)} tasks, Stations: {len(stations_df)}, Transporters: {len(transporters_df)}")
    print(f"  Matrix: {len(matrix_df)} tehtävää")
    print(f"  Stations: {len(stations_df)} asemaa")
    print(f"  Transporters: {len(transporters_df)} nostinta")
    
    # Run CP-SAT optimization
    logger.log("TASK", "Starting CP-SAT optimization...")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] Aloitetaan CP-SAT optimointi (max {time_limit}s)...")
    
    try:
        optimized_df = optimize_transporter_schedule(
            matrix_df=matrix_df,
            stations_df=stations_df,
            transporters_df=transporters_df,
            time_limit=time_limit
        )
        
        if optimized_df is None:
            error_msg = "CP-SAT optimization failed to find a solution"
            logger.log("ERROR", error_msg)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: {error_msg}")
            return None, None
        
        # Save optimized tasks
        output_csv = os.path.join(output_dir, "logs", "transporter_tasks_optimized.csv")
        optimized_df.to_csv(output_csv, index=False)
        
        logger.log("SAVE", f"Optimized tasks saved: {os.path.basename(output_csv)}")
        logger.log("INFO", f"Optimized {len(optimized_df)} transporter tasks")
        
        # Calculate makespan
        makespan = optimized_df['Sink_time'].max()
        logger.log("INFO", f"Final makespan: {makespan} seconds ({makespan/60:.1f} minutes)")
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] ✅ Optimointi valmis!")
        print(f"  Makespan: {makespan} s ({makespan/60:.1f} min)")
        print(f"  Tallennettu: {output_csv}")
        
        logger.log("TASK", "Step 5 CP-SAT completed: Transporter tasks optimization successful")
        
        return optimized_df, output_csv
        
    except Exception as e:
        error_msg = f"CP-SAT optimization error: {str(e)}"
        logger.log("ERROR", error_msg)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: {error_msg}")
        import traceback
        traceback.print_exc()
        return None, None


def test_step_5_cpsat(output_dir):
    """
    VAIHE 5 CP-SAT: Nostimien tehtävien optimointi
    
    Korvaa vanhan VAIHE 5:n (generate_tasks, order_tasks, resolve_station_conflicts, stretch_tasks)
    yhdellä CP-SAT-optimoinnilla.
    """
    from datetime import datetime
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 5 CP-SAT - OPTIMOINTI - ALKAA")
    
    # Alusta logger
    from simulation_logger import init_logger
    init_logger(output_dir)
    
    import traceback
    try:
        optimized_df, output_csv = optimize_transporter_tasks_cpsat(output_dir)
        
        if optimized_df is None:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] ⚠️ VAROITUS: Optimointi ei tuottanut tulosta")
            raise RuntimeError("CP-SAT optimization failed")
        
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        print(f"[{end}] VAIHE 5 CP-SAT - OPTIMOINTI - VALMIS")
        
        return optimized_df
        
    except Exception as e:
        print(f"❌ VIRHE vaiheessa 5 CP-SAT: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Testaus: Hae viimeisin output-kansio
    import sys
    
    output_root = "output"
    if not os.path.exists(output_root):
        print("Ei output-kansiota!")
        sys.exit(1)
    
    # Hae viimeisin logs-kansio
    logs_dirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
    if not logs_dirs:
        print("Ei logs-kansioita!")
        sys.exit(1)
    
    latest_dir = sorted(logs_dirs)[-1]
    output_dir = os.path.join(output_root, latest_dir)
    
    print(f"Käytetään output-kansiota: {output_dir}\n")
    
    # Aja VAIHE 5 CP-SAT
    test_step_5_cpsat(output_dir)
