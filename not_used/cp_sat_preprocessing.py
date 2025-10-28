import os
import pandas as pd

def cp_sat_generate_batches(input_batches, output_dir):
    """
    Luo erien tiedoston muotoon cp-sat-batches.csv
    """
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(input_batches)
    out_path = os.path.join(output_dir, "cp-sat-batches.csv")
    df.to_csv(out_path, index=False)
    print(f"[CP-SAT] Tallennettu: {out_path}")

def cp_sat_generate_treatment_programs(input_programs_dir, output_dir):
    """
    Kopioi/muotoilee kaikki käsittelyohjelmatiedostot muotoon cp-sat-treatment-program-BATCH.csv
    """
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(input_programs_dir):
        if fname.endswith(".csv"):
            df = pd.read_csv(os.path.join(input_programs_dir, fname))
            batch_id = fname.split("_")[1]
            out_path = os.path.join(output_dir, f"cp-sat-treatment-program-{batch_id}.csv")
            df.to_csv(out_path, index=False)
            print(f"[CP-SAT] Tallennettu: {out_path}")

def cp_sat_generate_stations(input_stations, output_dir):
    """
    Luo asematiedoston muotoon cp-sat-stations.csv
    """
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(input_stations)
    out_path = os.path.join(output_dir, "cp-sat-stations.csv")
    df.to_csv(out_path, index=False)
    print(f"[CP-SAT] Tallennettu: {out_path}")

def cp_sat_generate_transfer_tasks(input_transfers, output_dir):
    """
    Luo siirtymäaikojen tiedoston muotoon cp-sat-transfer-tasks.csv
    """
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(input_transfers)
    out_path = os.path.join(output_dir, "cp-sat-transfer-tasks.csv")
    df.to_csv(out_path, index=False)
    print(f"[CP-SAT] Tallennettu: {out_path}")

def cp_sat_generate_transporters(input_transporters, output_dir):
    """
    Luo nostimien aloituspaikkatiedoston muotoon cp-sat-transporters.csv
    """
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(input_transporters)
    out_path = os.path.join(output_dir, "cp-sat-transporters.csv")
    df.to_csv(out_path, index=False)
    print(f"[CP-SAT] Tallennettu: {out_path}")
