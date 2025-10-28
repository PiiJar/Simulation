import os
import shutil
import pandas as pd
from datetime import datetime

def generate_batch_treatment_programs(output_dir):
    """
    Create the original_programs folder and copy treatment programs batch-wise according to Production.csv.
    Also copy all programs to the optimized_programs folder (pipeline robustness).
    """
    # Create original treatment programs in initialization/treatment_program_originals directory
    originals_dir = os.path.join("initialization", "treatment_program_originals")
    os.makedirs(originals_dir, exist_ok=True)
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    if not os.path.exists(production_file):
        raise FileNotFoundError(f"production.csv not found: {production_file}")
    production_df = pd.read_csv(production_file)
    created_files = []
    for _, row in production_df.iterrows():
        batch_id = str(row["Batch"]).zfill(3)
        treatment_program = str(row["Treatment_program"]).zfill(3)
        source_file = os.path.join(output_dir, "initialization", f"treatment_program_{treatment_program}.csv")
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"Treatment program not found: {source_file}")
        program_df = pd.read_csv(source_file)
        
        # Ensure MinTime exists
        if "MinTime" not in program_df.columns:
            raise ValueError(f"MinTime column missing from file: {source_file}")
        
        # Add step 0 at the beginning: station = Start_station, MinTime=0, MaxTime=360000 (100h), CalcTime=0
        start_station = int(row["Start_station"])
        step0 = {
            "Stage": 0,
            "MinStat": start_station,
            "MaxStat": start_station,
            "MinTime": "00:00:00",
            "MaxTime": "100:00:00",
            "CalcTime": "00:00:00"
        }
        columns = ["Stage", "MinStat", "MaxStat", "MinTime", "MaxTime", "CalcTime"]
        program_df["CalcTime"] = program_df["MinTime"]
        program_df = program_df[columns]
        program_df = pd.concat([
            pd.DataFrame([step0], columns=columns),
            program_df
        ], ignore_index=True)
        target_file = os.path.join(originals_dir, f"Batch_{batch_id}_Treatment_program_{treatment_program}.csv")
        program_df.to_csv(target_file, index=False)
        created_files.append(os.path.basename(target_file))
    
    # Copy all programs to cp_sat/treatment_program_optimized directory
    cp_sat_dir = os.path.join(output_dir, "cp_sat")
    optimized_dir = os.path.join(cp_sat_dir, "treatment_program_optimized")
    os.makedirs(optimized_dir, exist_ok=True)
    for fname in os.listdir(originals_dir):
        if fname.endswith('.csv'):
            src = os.path.join(originals_dir, fname)
            dst = os.path.join(optimized_dir, fname)
            shutil.copyfile(src, dst)
    
    # Logging
    log_file = os.path.join(output_dir, "logs", "simulation_log.csv")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp},SETUP,original_programs and optimized_programs folders created and populated\n")
        f.write(f"{timestamp},SETUP,Treatment programs created: {len(created_files)}\n")
        for f_name in created_files:
            f.write(f"{timestamp},SETUP,Created treatment program: {f_name}\n")
    return originals_dir, optimized_dir
