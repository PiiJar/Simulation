import pandas as pd
import os
import shutil
import datetime
import math
from simulation_logger import get_logger
import numpy as np
import datetime
from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time

def get_program_step_info(batch, program, stage, lift_stat, program_cache, logger, production_cache=None):
    """
    Hakee ohjelma-askeleen tiedot cache:sta tai Production.csv:stä Stage 0:lle
    """
    info = {
        'min_stat': None, 'max_stat': None,
        'min_time': None, 'max_time': None,
        'calc_time': None, 'exists': False
    }
    
    # ⭐ STAGE 0: Production.csv data
    if int(stage) == 0:
        if production_cache is not None:
            mask = production_cache["Batch"] == batch
            if mask.any():
                row = production_cache.loc[mask].iloc[0]
                info['exists'] = True
                if "Start_time_seconds" in production_cache.columns:
                    info['calc_time'] = int(round(row["Start_time_seconds"]))
                    if pd.isna(info['calc_time']):
                        if int(batch) == 2:
                            if int(batch) == 2:
                                print(f"DEBUG: Production.csv batch={batch} row={row.to_dict()}")
                elif "Start_station_check" in production_cache.columns:
                    info['calc_time'] = int(round(pd.to_timedelta(row["Start_station_check"]).total_seconds()))
                    if pd.isna(info['calc_time']):
                        if int(batch) == 2:
                            if int(batch) == 2:
                                print(f"DEBUG: Production.csv batch={batch} row={row.to_dict()}")
                if int(batch) == 2:
                    pass  # Ei tulosteta mitään
        return info
    
    # Stage 1+: käsittelyohjelma data
    batch_str = f"{int(batch):03d}"
    program_str = f"{int(program):03d}"
    prog_filename = f"Batch_{batch_str}_Treatment_program_{program_str}.csv"
    
    if prog_filename in program_cache:
        try:
            prog_df = program_cache[prog_filename]
            # Maskaa vain Stage
            mask = (prog_df["Stage"].astype(int) == int(stage))
            # Etsi rivit, joilla lift_stat kuuluu MinStat–MaxStat-väliin
            valid_rows = prog_df[mask]
            if "MinStat" in valid_rows.columns and "MaxStat" in valid_rows.columns:
                valid_rows = valid_rows[(valid_rows["MinStat"].astype(int) <= int(lift_stat)) & (valid_rows["MaxStat"].astype(int) >= int(lift_stat))]
            if not valid_rows.empty:
                row = valid_rows.iloc[0]
                info['exists'] = True
                info['min_stat'] = int(row.get("MinStat", lift_stat))
                info['max_stat'] = int(row.get("MaxStat", lift_stat))
                if "MinTime" in prog_df.columns:
                    info['min_time'] = row["MinTime"]
                if "MaxTime" in prog_df.columns:
                    info['max_time'] = row["MaxTime"]
                if "CalcTime_seconds" in prog_df.columns:
                    info['calc_time'] = int(round(row["CalcTime_seconds"]))
                elif "CalcTime" in prog_df.columns:
                    info['calc_time'] = int(round(pd.to_timedelta(row["CalcTime"]).total_seconds()))
            else:
                pass  # Ei tulosteta mitään
    
        except Exception as e:
            if int(batch) == 2:
                logger.log_error(f"Error reading program info from cache: {e}")
    
    return info

def find_previous_tasks_same_batch(df, current_index, batch, max_count=2):
    """
    Etsii saman erän edelliset tehtävät (max 2 kpl)
    """
    previous_tasks = []
    for i in range(current_index - 1, -1, -1):
        if df.at[i, "Batch"] == batch:
            previous_tasks.append(i)
            if len(previous_tasks) >= max_count:
                break
    return previous_tasks

def calculate_physics_move_time(x1, x2, max_speed, acc_time, dec_time):
    distance = abs(x2 - x1)
    if distance == 0:
        return 0.0
    acceleration = max_speed / acc_time
    deceleration = max_speed / dec_time
        # POISTETTU: käytä vain transporter_physics.py:n funktioita

def stretch_tasks(output_dir="output", input_file=None):
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    logger.log("STEP", "STEP 5 STARTED: STRETCHING TASKS")
    # ...existing code...
    # Täsmädebug: Ensimmäisen erän ensimmäinen tehtävä (poistettu)
    def debug_first_task(df):
        pass
    # ...existing code...
    # ...koodia...
    # Kun df_stretched on alustettu (esim. pd.read_csv, tms.)
    # debug_first_task(df_stretched) tähän
    # Debug-tulostus maskin muodostuksen yhteyteen (venytystarve, erä 2, stage < 3)
    # Tämä sijoitetaan oikeaan kohtaan myöhemmin funktiossa, kun batch, stage, prog_df, jne. ovat saatavilla
    
    # --- Käsittelyohjelmien kopiointi optimized_programs kansioon ---
    orig_dir = os.path.join(output_dir, "original_programs")
    optimized_dir = os.path.join(output_dir, "optimized_programs")
    os.makedirs(optimized_dir, exist_ok=True)
    if os.path.exists(orig_dir):
        for fname in os.listdir(orig_dir):
            src = os.path.join(orig_dir, fname)
            dst = os.path.join(optimized_dir, fname)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
    else:
        logger.log_error(f"Original programs folder not found: {orig_dir}")
        raise FileNotFoundError(f"Original programs folder not found: {orig_dir}")
    
    # --- UUSI: Lataa kaikki käsittelyohjelmat muistiin ---
    program_cache = {}
    production_cache = None
    
    # Lataa Production.csv
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    if os.path.exists(production_file):
        production_cache = pd.read_csv(production_file)
        # Luo Start_time_seconds sarakkeeseen Start_station_check-arvot sekunneiksi
        if "Start_station_check" in production_cache.columns:
            production_cache["Start_time_seconds"] = pd.to_timedelta(production_cache["Start_station_check"]).dt.total_seconds()
    
    # Lataa kaikki käsittelyohjelmat
    for fname in os.listdir(optimized_dir):
        if fname.endswith('.csv') and fname.startswith('Batch_'):
            prog_file = os.path.join(optimized_dir, fname)
            prog_df = pd.read_csv(prog_file)
            # Muunna CalcTime HH:MM:SS sekunneiksi uuteen sarakkeeseen
            if "CalcTime" in prog_df.columns:
                prog_df["CalcTime_seconds"] = pd.to_timedelta(prog_df["CalcTime"]).dt.total_seconds()
            else:
                prog_df["CalcTime_seconds"] = 0.0
            program_cache[fname] = prog_df
    
    # --- Tehtävien venytys ---
    logs_dir = os.path.join(output_dir, "logs")
    resolved_file = os.path.join(logs_dir, "transporter_tasks_resolved.csv")
    stretched_file = os.path.join(logs_dir, "transporter_tasks_stretched.csv")
    stations_file = os.path.join(output_dir, "initialization", "stations.csv")
    # Kopioi resolved-listan kaikki sarakkeet ja rivit stretched-listaan
    df = pd.read_csv(resolved_file)
    df_stretched = df.copy(deep=True)
    # debug_first_task(df_stretched)  # Poistettu debug-tulostus
    # Säilytä alkuperäinen järjestys indeksiin
    df_stretched["_orig_idx"] = range(len(df_stretched))
    # Pakota kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
        if col in df_stretched.columns:
            df_stretched[col] = df_stretched[col].astype(int)
    for col in ["Lift_time", "Sink_time"]:
        if col in df_stretched.columns:
            df_stretched[col] = df_stretched[col].apply(lambda x: int(round(x)))
    stations_df = pd.read_csv(stations_file)
    if 'Number' in stations_df.columns:
        stations_df['Number'] = stations_df['Number'].astype(int)
    station_x = dict(zip(stations_df['Number'], stations_df['X Position']))
    transporters_file = os.path.join(output_dir, "initialization", "transporters.csv")
    transp_df = pd.read_csv(transporters_file)
    transp = transp_df.iloc[0]
    max_speed = float(transp.get('Max_speed (mm/s)', 1000))
    acc_time = float(transp.get('Acceleration_time (s)', 1.0))
    dec_time = float(transp.get('Deceleration_time (s)', 1.0))
    n = len(df_stretched)
    if 'Phase_1' not in df_stretched.columns:
        df_stretched['Phase_1'] = 0.0
    i = 0
    while i < n-1:
        # Pakota kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella suoraan DataFrameen
        for col in ["Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
            if col in df_stretched.columns:
                df_stretched.at[i, col] = int(df_stretched.at[i, col])
                df_stretched.at[i+1, col] = int(df_stretched.at[i+1, col])
        for col in ["Lift_time", "Sink_time"]:
            if col in df_stretched.columns:
                df_stretched.at[i, col] = int(round(df_stretched.at[i, col]))
                df_stretched.at[i+1, col] = int(round(df_stretched.at[i+1, col]))
        sink_stat = int(df_stretched.at[i, "Sink_stat"])
        lift_stat = int(df_stretched.at[i+1, "Lift_stat"])
        sink_row = stations_df[stations_df['Number'] == sink_stat]
        lift_row = stations_df[stations_df['Number'] == lift_stat]
        transporter_id = int(df_stretched.at[i, "Transporter_id"])
        transporter_row = transp_df[transp_df['Transporter_id'] == transporter_id]
        if sink_row.empty or lift_row.empty or transporter_row.empty:
            phase_1 = None
        else:
            phase_1 = int(round(calculate_physics_transfer_time(sink_row.iloc[0], lift_row.iloc[0], transporter_row.iloc[0])))
        df_stretched.at[i+1, 'Phase_1'] = phase_1
        if phase_1 is None:
            raise RuntimeError(f"[ERROR] Liikeaikaa ei voitu laskea riville {i+1}: sink_stat={sink_stat}, lift_stat={lift_stat}, transporter_id={transporter_id}")

        # Venytys tehdään aina, jos kyseessä on sama nostin ja shift > 0
        if df_stretched.at[i, "Transporter_id"] == df_stretched.at[i+1, "Transporter_id"]:
            required_gap = phase_1 if (df_stretched.at[i, "Batch"] != df_stretched.at[i+1, "Batch"]) else 0
            shift = (df_stretched.at[i, "Sink_time"] + required_gap) - df_stretched.at[i+1, "Lift_time"]
            if shift > 0:
                shift_ceil = math.ceil(shift)
                # Päivitä käsittelyohjelman CalcTime ja/tai Production.csv kuten aiemmin
                batch_dbg = df_stretched.at[i+1, "Batch"]
                lift_stat = int(df_stretched.at[i+1, "Lift_stat"])
                stage_dbg = int(df_stretched.at[i+1, "Stage"])
                if production_cache is not None:
                    prod_mask = production_cache["Batch"] == batch_dbg
                    if prod_mask.any():
                        start_station = int(production_cache.loc[prod_mask, "Start_station"].iloc[0])
                        if lift_stat == start_station:
                            if "Start_time_seconds" in production_cache.columns:
                                old_start = production_cache.loc[prod_mask, "Start_time_seconds"].iloc[0]
                                production_cache.loc[prod_mask, "Start_time_seconds"] = old_start + shift_ceil
                if program_cache is not None:
                    prog_id = int(df_stretched.at[i+1, "Treatment_program"])
                    prog_filename = f"Batch_{int(batch_dbg):03d}_Treatment_program_{prog_id:03d}.csv"
                    if prog_filename in program_cache:
                        prog_df = program_cache[prog_filename]
                        if "MinStat" in prog_df.columns and "MaxStat" in prog_df.columns and "CalcTime_seconds" in prog_df.columns:
                            for idx_prog in prog_df.index:
                                minstat = int(prog_df.at[idx_prog, "MinStat"])
                                maxstat = int(prog_df.at[idx_prog, "MaxStat"])
                                if minstat <= lift_stat <= maxstat:
                                    old_val = prog_df.at[idx_prog, "CalcTime_seconds"]
                                    prog_df.at[idx_prog, "CalcTime_seconds"] = float(old_val) + float(shift_ceil)
                                    print(f"[DEBUG] CalcTime-päivitys: Batch={batch_dbg} Stage={prog_df.at[idx_prog, 'Stage']} Stat={lift_stat} {old_val}s -> {prog_df.at[idx_prog, 'CalcTime_seconds']}s (+{shift_ceil}s)")
                                    break
                # Siirrä seuraavaa tehtävää ja sen batchin kaikkia myöhempiä tehtäviä
                batch_next = df_stretched.at[i+1, "Batch"]
                for j in range(i+1, n):
                    if df_stretched.at[j, "Batch"] == batch_next:
                        df_stretched.at[j, "Lift_time"] += shift_ceil
                        df_stretched.at[j, "Sink_time"] += shift_ceil
        i += 1
    # --- ÄLÄ VAIHDA RIVIEN JÄRJESTYSTÄ! Järjestys pysyy kuten _resolved-listassa. ---
    
    # ⭐ KRIITTINEN: ÄLÄ muuta _resolved-listan järjestystä! Venytys vain siirtää aikoja, ei järjestä rivejä uudelleen.
    # Järjestys säilyy täsmälleen kuten _resolved-listassa.
    
    # Poista apusarakkeet ennen tallennusta
    # Palauta alkuperäinen järjestys (resolved-listan järjestys)
    if "_orig_idx" in df_stretched.columns:
        df_stretched = df_stretched.sort_values("_orig_idx").reset_index(drop=True)
        df_stretched = df_stretched.drop(columns=["_orig_idx"])
    # Pakota vielä ennen tallennusta kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
        if col in df_stretched.columns:
            df_stretched[col] = df_stretched[col].astype(int)
    for col in ["Lift_time", "Sink_time"]:
        if col in df_stretched.columns:
            df_stretched[col] = df_stretched[col].apply(lambda x: int(round(x)))
    df_stretched.to_csv(stretched_file, index=False)

    # --- UUSI: Tallenna kaikki muokatut tiedostot cache:sta takaisin levylle ---
    # ...

    # Tallenna Production.csv jos muokattu
    if production_cache is not None:
        # Konvertoi Start_time_seconds takaisin HH:MM:SS-muotoon Start_stretch-sarakkeeseen
        if "Start_time_seconds" in production_cache.columns:
            production_cache["Start_stretch"] = production_cache["Start_time_seconds"].apply(
                lambda s: f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}" if not pd.isna(s) else "00:00:00"
            )
            # Poista Start_time_seconds ennen tallennusta
            production_cache = production_cache.drop(columns=["Start_time_seconds"])
        production_file = os.path.join(output_dir, "initialization", "production.csv")
        production_cache.to_csv(production_file, index=False)
    # ...

    # Tallenna kaikki käsittelyohjelmat
    for prog_filename, prog_df in program_cache.items():
        # Konvertoi CalcTime_seconds takaisin HH:MM:SS-muotoon CalcTime-sarakkeeseen
        if "CalcTime_seconds" in prog_df.columns:
            prog_df["CalcTime"] = prog_df["CalcTime_seconds"].apply(
                lambda s: f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}" if not pd.isna(s) else "00:00:00"
            )
            prog_df = prog_df.drop(columns=["CalcTime_seconds"])
        prog_file = os.path.join(optimized_dir, prog_filename)
        prog_df.to_csv(prog_file, index=False)
    # ...

    logger.log("STEP", "STEP 5 COMPLETED: STRETCHING TASKS")
    return df_stretched
if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    stretch_tasks(output_dir)
