#!/usr/bin/env python3
"""
TEST STEP 5: Generate Transporter Tasks
=====================================

This script generates transporter tasks from the original line matrix.
Each transfer between stations becomes a transporter task with timing and priority.

Input:
- output_dir/Logs/line_matrix_original.csv

Output:
- output_dir/Logs/transporter_tasks_raw.csv
- Updated simulation_log.csv

Log Types Used:
- TASK: Task generation events
- SAVE: File save operations
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Import the logger from test_step1.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_step1 import SimulationLogger
from generate_tasks import *
from stretch_transporter_tasks import stretch_tasks
from order_tasks import order_tasks
from resolve_station_conflicts import resolve_station_conflicts

def generate_transporter_tasks(output_dir):
    """
    Generate transporter tasks from original line matrix.
    
    Args:
        output_dir (str): Path to simulation output directory
        
    Returns:
        tuple: (tasks_df, tasks_csv_path)
    """
    
    # Initialize logger
    logger = SimulationLogger(output_dir)
    
    logger.log("TASK", "Step 5 started: Generate transporter tasks from original matrix")
    
    # Read original line matrix
    matrix_file = os.path.join(output_dir, "Logs", "line_matrix_original.csv")
    if not os.path.exists(matrix_file):
        error_msg = f"Original matrix file not found: {matrix_file}"
        logger.log("ERROR", error_msg)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: {error_msg}")
        return None, None
    
    logger.log("READ", f"Reading original matrix: {os.path.basename(matrix_file)}")
    matrix_df = pd.read_csv(matrix_file)
    # Pakota kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Batch", "Program", "Stage", "Station"]:
        if col in matrix_df.columns:
            matrix_df[col] = matrix_df[col].astype(int)
    for col in ["EntryTime", "ExitTime"]:
        if col in matrix_df.columns:
            matrix_df[col] = matrix_df[col].apply(lambda x: int(round(x)))
    # Käytä generate_tasks.py:n korjattua logiikkaa
    from generate_tasks import generate_tasks
    tasks_df, _ = generate_tasks(output_dir)
    if tasks_df is None or len(tasks_df) == 0:
        logger.log("WARNING", "No transporter tasks generated from matrix")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: Ei nostintehtäviä generoitu!")
        return None, None
    logger.log("TASK", f"Generated {len(tasks_df)} transporter tasks from matrix")
    tasks_csv = os.path.join(output_dir, "Logs", "transporter_tasks_raw.csv")
    logger.log("SAVE", f"Transporter tasks saved: {os.path.basename(tasks_csv)}")
    # Järjestä tehtävät
    order_tasks(output_dir)
    # Ratkaise konfliktit
    resolve_station_conflicts(output_dir)
    # Venytys: SHIFT_GAP
    stretch_tasks(output_dir)
    logger.log("TASK", "Step 5 completed: Transporter tasks generation successful")
    return tasks_df, tasks_csv

def test_step_5(output_dir):
    """
    VAIHE 5: Nostimien tehtävien käsittely
    """
    from datetime import datetime
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 5 - NOSTIMIEN TEHTÄVIEN KÄSITTELY - ALKAA")
    # Alusta logger
    from simulation_logger import init_logger
    init_logger(output_dir)
    try:
        generate_transporter_tasks(output_dir)
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        print(f"[{end}] VAIHE 5 - NOSTIMIEN TEHTÄVIEN KÄSITTELY - VALMIS")
    except Exception as e:
        print(f"❌ VIRHE vaiheessa 5: {e}")
        raise
