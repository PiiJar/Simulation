"""
Luo original_programs-kansion ja kopioi käsittelyohjelmat eräkohtaisesti Production.csv:n mukaan.
"""
import os
import pandas as pd
from datetime import datetime

def generate_batch_treatment_programs_original(output_dir):
    try:
        original_programs_dir = os.path.join(output_dir, "original_programs")
        os.makedirs(original_programs_dir, exist_ok=True)
        production_file = os.path.join(output_dir, "Initialization", "Production.csv")
        if not os.path.exists(production_file):
            raise FileNotFoundError(f"Production.csv ei löydy: {production_file}")
        production_df = pd.read_csv(production_file)
        created_files = []
        for _, row in production_df.iterrows():
            batch_id = str(row["Batch"]).zfill(3)
            treatment_program = str(row["Treatment_program"]).zfill(3)
            source_file = os.path.join(output_dir, "Initialization", f"Treatment_program_{treatment_program}.csv")
            if not os.path.exists(source_file):
                raise FileNotFoundError(f"Käsittelyohjelmaa ei löydy: {source_file}")
            program_df = pd.read_csv(source_file)
            # Varmista että MinTime löytyy
            if "MinTime" not in program_df.columns:
                raise ValueError(f"MinTime-sarake puuttuu tiedostosta: {source_file}")
            # Lisää/ylikirjoita CalcTime-sarake aina
            program_df["CalcTime"] = program_df["MinTime"]
            # Pakota sarakkeiden järjestys: Stage,MinStat,MaxStat,MinTime,MaxTime,CalcTime
            columns = ["Stage", "MinStat", "MaxStat", "MinTime", "MaxTime", "CalcTime"]
            program_df = program_df[columns]
            target_file = os.path.join(original_programs_dir, f"Batch_{batch_id}_Treatment_program_{treatment_program}.csv")
            program_df.to_csv(target_file, index=False)
            created_files.append(os.path.basename(target_file))
        logs_path = os.path.join(output_dir, "logs")
        log_file = os.path.join(logs_path, "simulation_log.csv")
        if os.path.exists(log_file):
            with open(log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp},STEP,STEP 2 STARTED: GENERATE ORIGINAL PROGRAMS\n")
                f.write(f"{timestamp},SETUP,original_programs folder created\n")
                f.write(f"{timestamp},SETUP,Treatment programs created: {len(created_files)}\n")
                for f_name in created_files:
                    f.write(f"{timestamp},SETUP,Created treatment program: {f_name}\n")
                f.write(f"{timestamp},STEP,STEP 2 COMPLETED: ORIGINAL PROGRAMS READY\n")
        return original_programs_dir
    except Exception as e:
        print(f"\nVIRHE: {e}")
        import traceback
        traceback.print_exc()
        return None
