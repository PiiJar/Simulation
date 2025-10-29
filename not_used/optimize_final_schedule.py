#!/usr/bin/env python3
"""
Lopullisen aikataulun optimointi - korjaa asema- ja nostinkonfliktit.

TÄRKEÄ PERIAATE:
- CalcTime-arvoja voi ja pitää optimoida MinTime-MaxTime rajoissa
- Tavoite: saada enemmän eriä läpi linjasta optimoimalla käsittelyaikoja
- Lähtöaikataulun muutos on vasta viimeisin keino
"""

import pandas as pd
import os
import shutil

def detect_station_conflicts(df):
    """Tunnistaa asemakonfliktit - useita eriä samalla asemalla samaan aikaan"""
    conflicts = []
    
    # Gruppaa tehtävät asemittain
    for station in range(df['Lift_stat'].min(), df['Sink_stat'].max() + 1):
        station_tasks = []
        
        # Kerää kaikki tehtävät jotka koskettavat tätä asemaa
        for idx, row in df.iterrows():
            # Lift-vaihe
            if row['Lift_stat'] == station:
                station_tasks.append({
                    'task_id': idx,
                    'batch': row['Batch'],
                    'start_time': row['Lift_time'],
                    'end_time': row['Lift_time'],  # Nostaminen on hetkellinen
                    'type': 'lift',
                    'station': station
                })
            
            # Käsittely-vaihe (erä on asemalla Lift_time:sta Sink_time:een)
            if row['Lift_stat'] == station and row['Sink_stat'] == station:
                # Sama asema lift ja sink - erä käsitellään täällä
                station_tasks.append({
                    'task_id': idx,
                    'batch': row['Batch'],
                    'start_time': row['Lift_time'],
                    'end_time': row['Sink_time'],
                    'type': 'treatment',
                    'station': station
                })
            
            # Sink-vaihe
            if row['Sink_stat'] == station:
                station_tasks.append({
                    'task_id': idx,
                    'batch': row['Batch'],
                    'start_time': row['Sink_time'],
                    'end_time': row['Sink_time'],  # Laskeminen on hetkellinen
                    'type': 'sink',
                    'station': station
                })
        
        # Tarkista päällekkäisyydet
        station_tasks = sorted(station_tasks, key=lambda x: x['start_time'])
        for i in range(len(station_tasks)):
            for j in range(i+1, len(station_tasks)):
                task_a = station_tasks[i]
                task_b = station_tasks[j]
                
                # Eri erät samalla asemalla samaan aikaan = konflikti
                if (task_a['batch'] != task_b['batch'] and 
                    task_a['end_time'] > task_b['start_time']):
                    conflicts.append({
                        'type': 'station_conflict',
                        'station': station,
                        'task_a': task_a,
                        'task_b': task_b,
                        'overlap_time': task_a['end_time'] - task_b['start_time']
                    })
    
    return conflicts

def detect_transporter_conflicts(df):
    """Tunnistaa nostinkonfliktit - sama nostin tekemässä useita tehtäviä samaan aikaan"""
    conflicts = []
    
    for transporter_id in df['Transporter_id'].unique():
        transporter_tasks = df[df['Transporter_id'] == transporter_id].copy()
        transporter_tasks = transporter_tasks.sort_values('Lift_time').reset_index(drop=True)
        
        for i in range(len(transporter_tasks) - 1):
            current_task = transporter_tasks.iloc[i]
            next_task = transporter_tasks.iloc[i + 1]
            
            # Tarkista että edellinen tehtävä on valmis ennen seuraavan alkua
            actual_gap = next_task['Lift_time'] - current_task['Sink_time']
            
            if actual_gap < 0:
                conflicts.append({
                    'type': 'transporter_overlap',
                    'transporter_id': transporter_id,
                    'current_task': current_task.to_dict(),
                    'next_task': next_task.to_dict(),
                    'overlap_time': -actual_gap
                })
    
    return conflicts

def resolve_station_conflicts(df, conflicts, stations_df, logger):
    """Ratkaisee asemakonfliktit siirtämällä tehtäviä"""
    df_optimized = df.copy()
    total_shifts = 0
    
    for conflict in conflicts:
        if conflict['type'] != 'station_conflict':
            continue
            
        # Yksinkertainen ratkaisu: siirrä myöhäisempää tehtävää
        task_a = conflict['task_a']
        task_b = conflict['task_b']
        overlap = conflict['overlap_time']
        
        # Siirrä task_b:tä niin että konflikti ratkeaa
        shift_amount = overlap + 1  # +1s marginaali
        
        # Etsi kaikki task_b:n erän tehtävät ja siirrä niitä
        batch_mask = df_optimized['Batch'] == task_b['batch']
        df_optimized.loc[batch_mask, 'Lift_time'] += shift_amount
        df_optimized.loc[batch_mask, 'Sink_time'] += shift_amount
        
        total_shifts += shift_amount
    # logger.log_optimization removed
    
    return df_optimized

def resolve_transporter_conflicts(df, conflicts, logger):
    """Ratkaisee nostinkonfliktit siirtämällä myöhempiä tehtäviä"""
    df_optimized = df.copy()
    
    for conflict in conflicts:
        if conflict['type'] != 'transporter_overlap':
            continue
            
        transporter_id = conflict['transporter_id']
        current_task = conflict['current_task']
        next_task = conflict['next_task']
        overlap = conflict['overlap_time']
        
        # Laske tarvittava siirto
        required_move_time = 5.0  # Nostimen siirtoaika
        total_shift = overlap + required_move_time + 1.0  # +1s marginaali
        
        # Etsi kaikki myöhemmät tehtävät samalla nostimella
        shift_time_threshold = next_task['Lift_time']
        later_tasks_mask = (df_optimized['Transporter_id'] == transporter_id) & \
                          (df_optimized['Lift_time'] >= shift_time_threshold)
        
        if later_tasks_mask.any():
            shift_count = later_tasks_mask.sum()
            df_optimized.loc[later_tasks_mask, 'Lift_time'] += int(round(total_shift))
            df_optimized.loc[later_tasks_mask, 'Sink_time'] += int(round(total_shift))
            
            # logger.log_optimization removed
    
    return df_optimized

def update_production_and_programs(df_original, df_optimized, output_dir, logger):
    """
    Optimoi käsittelyohjelmat maksimaalisen läpimenonopeuden saavuttamiseksi.
    
    STRATEGIA:
    1. Ensisijaisesti optimoi CalcTime minimiin (parempi läpimeno)
    2. Vasta viimeisenä keinona siirrä lähtöaikoja Production.csv:ssä
    
    HUOM: optimized_programs/ kansio on jo olemassa venytysvaiheesta, 
    joten muokataan suoraan niitä tiedostoja.
    """
    
    # Käytä suoraan optimized_programs kansiota (ei kopiointia)
    optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")

    if not os.path.exists(optimized_dir):
        raise FileNotFoundError(f"treatment_program_optimized folder missing: {optimized_dir}")

    # OPTIMOINTISTRATEGIA: Optimoi KAIKKI CalcTime-arvot minimiinsä maksimaalisen läpimenonopeuden saavuttamiseksi
    for filename in os.listdir(optimized_dir):
        if filename.startswith("Batch_") and filename.endswith(".csv"):
            prog_file = os.path.join(optimized_dir, filename)
            prog_df = pd.read_csv(prog_file)

            # Poista Stage 0 rivi ennen tallennusta
            prog_df = prog_df[prog_df["Stage"] != 0].copy()

            optimizations_applied = 0

            for idx, row in prog_df.iterrows():
                min_time = pd.to_timedelta(row["MinTime"]).total_seconds()
                max_time = pd.to_timedelta(row["MaxTime"]).total_seconds()
                current_time = pd.to_timedelta(row["CalcTime"]).total_seconds()

                # OPTIMOI: Käytä aina minimiaika maksimaalisen läpimenonopeuden saavuttamiseksi
                if current_time > min_time:
                    optimized_time = min_time
                    prog_df.at[idx, "CalcTime"] = pd.to_datetime(optimized_time, unit='s').strftime('%H:%M:%S')

                    time_saved = current_time - optimized_time
                    optimizations_applied += 1

            # Tallenna ohjelma ilman Stage 0 -riviä
            prog_df.to_csv(prog_file, index=False)
    
    # Tarkista tarvitaanko lähtöaikojen siirtoja (vain jos CalcTime-optimointi ei riitä)
    changes = {}
    significant_shifts_needed = False
    
    # Removed Lift_time-based shift logic: not present in program files
    
    # Päivitä Production.csv: lisää/ylikirjoita Start_optimized-sarake Stage 1:n alkamisajalla
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    if os.path.exists(production_file):
        prod_df = pd.read_csv(production_file)
        schedule_file = os.path.join(output_dir, "logs", "cp_sat_optimization_schedule.csv")
        if os.path.exists(schedule_file):
            schedule_df = pd.read_csv(schedule_file)
            # Poimi Stage 1:n Start jokaiselle batchille
            start_optimized = {}
            for _, row in schedule_df.iterrows():
                if int(row["Stage"]) == 1:
                    batch = row["Batch"]
                    start_sec = int(row["Start"])
                    # Muunna sekunnit HH:MM:SS
                    start_optimized[batch] = pd.to_datetime(start_sec, unit='s').strftime('%H:%M:%S')
            # Lisää/ylikirjoita sarake, täytä tyhjät arvot tyhjällä merkkijonolla
            prod_df["Start_optimized"] = prod_df["Batch"].map(start_optimized).fillna("")
            prod_df.to_csv(production_file, index=False)
            # logger.log_optimization removed
        # logger.log_optimization removed
    # logger.log_optimization removed

def check_and_fix_calctime_violations(output_dir, logger):
    """Tarkistaa ja korjaa CalcTime-arvot jotka ylittävät MaxTime-rajoja"""
    
    stretched_dir = os.path.join(output_dir, "stretched_programs")
    optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")
    
    violations_found = 0
    fixes_applied = 0
    
    if not os.path.exists(stretched_dir):
        return violations_found, fixes_applied
    
    for filename in os.listdir(stretched_dir):
        if filename.startswith("Batch_") and filename.endswith(".csv"):
            file_path = os.path.join(stretched_dir, filename)
            prog_df = pd.read_csv(file_path)
            
            # Muunna ajat sekunneiksi
            if "CalcTime" in prog_df.columns:
                prog_df["CalcTime_seconds"] = pd.to_timedelta(prog_df["CalcTime"]).dt.total_seconds()
            if "MinTime" in prog_df.columns:
                prog_df["MinTime_seconds"] = pd.to_timedelta(prog_df["MinTime"]).dt.total_seconds()
            if "MaxTime" in prog_df.columns:
                prog_df["MaxTime_seconds"] = pd.to_timedelta(prog_df["MaxTime"]).dt.total_seconds()
            
            violations_in_file = 0
            fixes_in_file = 0
            
            # Tarkista jokainen rivi
            for idx, row in prog_df.iterrows():
                if "CalcTime_seconds" in prog_df.columns and "MaxTime_seconds" in prog_df.columns:
                    calc_time = row["CalcTime_seconds"]
                    max_time = row["MaxTime_seconds"]
                    min_time = row.get("MinTime_seconds", 0)
                    
                    # Tarkista onko CalcTime > MaxTime
                    if calc_time > max_time:
                        violations_in_file += 1
                        violations_found += 1
                        
                        new_calc_time = max_time
                        prog_df.at[idx, "CalcTime_seconds"] = new_calc_time
                        fixes_in_file += 1
                        fixes_applied += 1
                    
                    # Tarkista onko CalcTime < MinTime
                    elif calc_time < min_time:
                        violations_in_file += 1
                        violations_found += 1
                        
                        new_calc_time = min_time
                        prog_df.at[idx, "CalcTime_seconds"] = new_calc_time
                        prog_df.at[idx, "CalcTime"] = pd.to_datetime(new_calc_time, unit='s').strftime('%H:%M:%S')
                        
                        fixes_in_file += 1
                        fixes_applied += 1
                        
            
                output_path = os.path.join(optimized_dir, filename)
                
                # Poista väliaikaiset sekuntisarakkeet ennen tallennusta
                prog_df[columns_to_save].to_csv(output_path, index=False)
    
    return violations_found, fixes_applied
    return violations_found, fixes_applied

def optimize_final_schedule(output_dir="output", max_iterations=10):
    """
    Optimoi lopullisen aikataulun ratkaisemalla asema- ja nostinkonfliktit.
    
    TÄRKEÄÄ: Optimoi CalcTime-arvoja MinTime-MaxTime rajoissa maksimaalisen läpimenonopeuden saavuttamiseksi!
    
    Sijoittuu pipeline:ssä stretch_tasks() ja generate_matrix() väliin.
    """
    # logger.log_optimization and logger usage removed for silent operation

if __name__ == "__main__":
    # Testikäyttö
    optimize_final_schedule("output/latest")
