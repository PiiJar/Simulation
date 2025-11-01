import os
import pandas as pd
from datetime import datetime

def load_production_batches_stretched(output_dir):
    """Lataa Production.csv Start_optimized kentällä"""
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    if not os.path.exists(production_file):
        raise FileNotFoundError(f"Production.csv ei löydy: {production_file}")
    
    df = pd.read_csv(production_file)
    if "Start_optimized" in df.columns and df["Start_optimized"].notna().any():
        start_field = "Start_optimized"
    else:
        raise ValueError(f"Start_optimized-kenttää ei löydy")

    df["Start_time_seconds"] = pd.to_timedelta(df[start_field]).dt.total_seconds()
    return df

def load_batch_program_optimized(programs_dir, batch_id, treatment_program):
    """
    Lataa optimoidut käsittelyohjelmat uudessa muodossa:
    Stage, Transporter, Station, CalcTime
    """
    batch_str = str(batch_id).zfill(3)
    program_str = str(treatment_program).zfill(3)
    file_path = os.path.join(programs_dir, f"Batch_{batch_str}_Treatment_program_{program_str}.csv")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Eräohjelmaa ei löydy: {file_path}")

    df = pd.read_csv(file_path)
    
    # Muunna ajat sekunteiksi vain jos ne ovat merkkijonoina
    if "MinTime" in df.columns:
        df["MinTime"] = pd.to_timedelta(df["MinTime"]).dt.total_seconds()
    if "MaxTime" in df.columns:
        df["MaxTime"] = pd.to_timedelta(df["MaxTime"]).dt.total_seconds()
    
    if "CalcTime" in df.columns:
        df["CalcTime"] = pd.to_timedelta(df["CalcTime"]).dt.total_seconds()
    else:
        df["CalcTime"] = df["MinTime"] if "MinTime" in df.columns else 0

    return df

def generate_matrix_pure(output_dir):
    """
    Luo matriisin SUORAAN CP-SAT optimoinnin tulosten pohjalta.
    EI TEE MITÄÄN OMAA OPTIMOINTIA tai valintoja!
    
    Uusi rakenne: Optimoidut käsittelyohjelmat sisältävät:
    - Stage: käsittelyvaihe
    - Transporter: CP-SAT:n valitsema nostin  
    - Station: CP-SAT:n valitsema asema
    - CalcTime: CP-SAT:n optimoima käsittelyaika
    """
    logs_dir = os.path.join(output_dir, "logs")
    optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")
    output_file = os.path.join(logs_dir, "line_matrix.csv")
    
    # Lataa production tiedot CP-SAT:n optimoiduilla aloitusajoilla
    production_df = load_production_batches_stretched(output_dir)
    
    # Lue siirtoajat referenssiksi
    transfers_path = os.path.join(output_dir, "cp_sat", "cp_sat_transfer_tasks.csv")
    if not os.path.exists(transfers_path):
        raise FileNotFoundError(f"Transfer times file not found: {transfers_path}")
    transfers_df = pd.read_csv(transfers_path)
    transfers_df["Transporter"] = transfers_df["Transporter"].astype(int)
    transfers_df["From_Station"] = transfers_df["From_Station"].astype(int)
    transfers_df["To_Station"] = transfers_df["To_Station"].astype(int)
    
    print(f"📊 Luodaan matriisi SUORAAN optimoiduista käsittelyohjelmista")
    
    all_rows = []
    production_df_sorted = production_df.sort_values('Start_time_seconds').reset_index(drop=True)
    
    for _, batch_row in production_df_sorted.iterrows():
        batch_id = int(batch_row["Batch"])
        treatment_program = int(batch_row["Treatment_program"])
        start_time_seconds = float(batch_row["Start_time_seconds"])

        # Lataa optimoidut käsittelyohjelmat (sisältää nyt Transporter, Station, CalcTime)
        prog_df = load_batch_program_optimized(optimized_dir, batch_id, treatment_program)
        
        current_time = start_time_seconds
        previous_station = int(batch_row["Start_station"])
        
        # Stage 0: Alkuasema
        all_rows.append({
            "Batch": batch_id,
            "Program": treatment_program,
            "Treatment_program": treatment_program,
            "Stage": 0,
            "Station": previous_station,
            "MinTime": 0,
            "MaxTime": 0,
            "CalcTime": 0,
            "EntryTime": int(current_time),
            "ExitTime": int(current_time),
            "TransportTime": 0
        })
        
        # Käy läpi optimoidut käsittelyvaiheet
        for _, stage_row in prog_df.iterrows():
            stage = int(stage_row["Stage"])
            transporter_id = int(stage_row["Transporter"])
            station = int(stage_row["Station"])
            calc_time_seconds = stage_row["CalcTime"]
            min_time = int(stage_row["MinTime"]) if "MinTime" in stage_row else calc_time_seconds
            max_time = int(stage_row["MaxTime"]) if "MaxTime" in stage_row else calc_time_seconds
            
            # Hae siirtoaika edellisestä asemasta
            match = transfers_df[(transfers_df["Transporter"] == transporter_id) & 
                                (transfers_df["From_Station"] == previous_station) & 
                                (transfers_df["To_Station"] == station)]
            
            if not match.empty:
                transport_time = float(match.iloc[0]["TotalTaskTime"])
            else:
                transport_time = 0  # Fallback
                print(f"⚠️ Siirtoaikaa ei löydy: Transporter={transporter_id}, {previous_station}→{station}")
            
            # Yksinkertainen aikajana: edellinen loppu + siirtoaika + käsittelyaika
            entry_time = int(current_time + transport_time)
            exit_time = entry_time + int(calc_time_seconds)
            
            all_rows.append({
                "Batch": batch_id,
                "Program": treatment_program,
                "Treatment_program": treatment_program,
                "Stage": stage,
                "Station": station,
                "MinTime": min_time,
                "MaxTime": max_time,
                "CalcTime": int(calc_time_seconds),
                "EntryTime": entry_time,
                "ExitTime": exit_time,
                "TransportTime": transport_time
            })
            
            # Päivitä seuraavaa vaihetta varten
            current_time = exit_time
            previous_station = station
    
    # Tallenna
    matrix = pd.DataFrame(all_rows)
    for col in matrix.select_dtypes(include=['float']).columns:
        matrix[col] = matrix[col].round(2)
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    matrix.to_csv(output_file, index=False)
    
    print(f"✅ Matrix luotu optimoiduista käsittelyohjelmista: {len(matrix)} riviä")
    print(f"   Käyttää CP-SAT:n valitsemia nostimia ja asemia suoraan")
    return matrix

def generate_matrix(output_dir):
    """Wrapper-funktio"""
    return generate_matrix_pure(output_dir)

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    generate_matrix(output_dir)
