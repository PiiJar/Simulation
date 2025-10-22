import pandas as pd
import os
from simulation_logger import get_logger

TRANSFER_TIME = 40  # sekuntia

def load_production_batches(output_dir):
    """Lataa Production.csv (päivitetty jos on, muuten alkuperäinen)"""
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    
    # Yritä ensin päivitettyä versiota
    updated_file = os.path.join(output_dir, "Production_updated.csv")
    if os.path.exists(updated_file):
        file_path = updated_file
        source = "päivitetty"
    else:
        # Jos ei päivitettyä, käytä alkuperäistä
        file_path = os.path.join(output_dir, "initialization", "production.csv")
        source = "alkuperäinen"
    
    if not os.path.exists(file_path):
        logger.log_error(f"Production.csv ei löydy: {file_path}")
        raise FileNotFoundError(f"Production.csv ei löydy: {file_path}")
    
    df = pd.read_csv(file_path)
    # Muunna Start_time sekunneiksi
    df["Start_time_seconds"] = pd.to_timedelta(df["Start_time"]).dt.total_seconds()
    logger.log_data(f"Loaded production batches from {file_path} ({source})")
    
    print(f"Käytetään {source} Production-tiedostoa")
    return df

def load_updated_program_for_batch(output_dir, batch_id):
    """Lataa päivitetyn ohjelmatiedoston tai alkuperäisen jos päivitettyä ei ole"""
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    
    batch_str = str(int(batch_id)).zfill(3)
    
    # Yritä ensin päivitettyä versiota
    file_updated = os.path.join(output_dir, "updated_programs", f"treatment_program_batch_{batch_str}_updated.csv")
    if os.path.exists(file_updated):
        df = pd.read_csv(file_updated)
        source = "päivitetty"
    else:
        # Jos ei päivitettyä, käytä alkuperäistä
        file_original = os.path.join(output_dir, "original_programs", f"treatment_program_batch_{batch_str}.csv")
        if os.path.exists(file_original):
            df = pd.read_csv(file_original)
            source = "alkuperäinen"
        else:
            logger.log_error(f"Eräohjelmaa ei löydy: {file_original}")
            raise FileNotFoundError(f"Eräohjelmaa ei löydy: {file_original}")
    
    # Muunna ajat sekunneiksi
    for col in ["MinTime", "MaxTime", "CalcTime"]:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = pd.to_timedelta(df[col]).dt.total_seconds()
    
    logger.log_data(f"Loaded program for batch {batch_id} ({source})")
    return df, source

def create_updated_processing_matrix_for_batch(prog_df, batch_id, start_time_seconds):
    """Luo päivitetyn käsittelymatriisin yhdelle erälle"""
    rows = []
    
    # 1. Lisää Loading-asema (101) ensimmäiseksi
    rows.append({
        "Batch": int(batch_id),
        "Program": 1,
        "Stage": 0,  # Loading on vaihe 0
        "Station": 101,  # Loading-asema
        "MinTime": 0,
        "MaxTime": 0,
        "CalcTime": 0,
        "EntryTime": int(start_time_seconds),
        "ExitTime": int(start_time_seconds),
        "Remaining": 0
    })
    
    # 2. Aloitetaan käsittelyvaiheet Loading-aseman jälkeen
    time = start_time_seconds + TRANSFER_TIME  # siirto Loading-asemalta
    
    for _, row in prog_df.iterrows():
        stage = int(row["Stage"])
        station = int(row["MinStat"])
        min_time = row["MinTime"]
        max_time = row["MaxTime"]
        calc_time = row["CalcTime"]  # Tämä on nyt päivitetty versio!
        
        entry = time
        exit = entry + calc_time
        time = exit + TRANSFER_TIME  # seuraava vaihe alkaa siirron jälkeen
        
        rows.append({
            "Batch": int(batch_id),
            "Program": 1,
            "Stage": stage,
            "Station": station,
            "MinTime": int(min_time),
            "MaxTime": int(max_time),
            "CalcTime": int(calc_time),
            "EntryTime": int(entry),
            "ExitTime": int(exit),
            "Remaining": int(calc_time)  # koko aika on jäljellä
        })
    
    return rows

def generate_updated_matrix(output_dir):
    """Luo päivitetyn käsittelymatriisin kaikille tuotantoerille päivitettyjen ohjelmien mukaan"""
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    
    logger.log_phase("Generating updated processing matrix started")
    print("Luodaan päivitetty käsittelymatriisi...")
    
    # Lataa tuotantoerien tiedot
    production_df = load_production_batches(output_dir)
    print(f"Käsitellään {len(production_df)} tuotantoerää")
    logger.log_data(f"Processing {len(production_df)} production batches for updated matrix")
    
    all_rows = []
    
    for _, batch_row in production_df.iterrows():
        batch_id = batch_row["Batch"]
        start_time_seconds = batch_row["Start_time_seconds"]
        
        # Lataa päivitetty eräkohtainen ohjelma
        prog_df, source = load_updated_program_for_batch(output_dir, batch_id)
        logger.log_data(f"Batch {batch_id}: using {source} program, start {batch_row['Start_time']}")
        print(f"   Erä {batch_id}: käytetään {source} ohjelma, aloitus {batch_row['Start_time']}")
        
        # Luo matriisin rivit tälle erälle
        batch_rows = create_updated_processing_matrix_for_batch(prog_df, batch_id, start_time_seconds)
        all_rows.extend(batch_rows)
    
    # Luo DataFrame ja tallenna
    matrix = pd.DataFrame(all_rows)
    
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "line_matrix_updated.csv")
    matrix.to_csv(output_file, index=False)
    
    logger.log_io(f"Saved updated processing matrix to: {output_file}")
    print(f"Päivitetty matriisi tallennettu: {output_file}")
    print(f"Yhteensä {len(matrix)} vaihetta päivitetyillä ajoilla")
    logger.log_phase("Generating updated processing matrix completed")
    
    return matrix

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    generate_updated_matrix(output_dir)
