#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YKSINKERTAINEN ALKUPERÄINEN MATRIISI

Matriisi = lista tehtävistä:
- Batch, Stage, Station, EntryTime, ExitTime
- Konfliktien ratkaisu: vertaa aikoja, siirrä tarvittaessa
"""

import pandas as pd
import os
from simulation_logger import SimulationLogger

def generate_matrix_original(output_dir, step_logging=True):
    """
    ALKUPERÄISEN MATRIISIN GENEROINTI
    
    Toteuttaa dokumentaation mukaan:
    documentation/alkuperaisen_matriisin_luonti.md
    
    ALGORITMI:
    1. Ensimmäinen erä erikseen (ei konfliktitarkastelua)  
    2. Loput erät konfliktienratkaisulla
    3. Erä kerrallaan, vaihe kerrallaan
    4. Nostinfysiikka: Phase_1=0, Phase_2-4 lasketaan
    5. Vaihtoaika fysiikkafunktioilla
    """
    logger = SimulationLogger(output_dir)
    logger.log("MATRIX_GEN", "Starting original matrix generation")
    
    # Lataa lähtötiedot
    production_df = load_production_data(output_dir)
    stations_df = load_stations_data()
    transporters_df = load_transporters_data()
    
    all_rows = []
    
    # 1. ENSIMMÄINEN ERÄ - erikseen ilman konfliktitarkastelua
    logger.log("BATCH", "Processing first batch (no conflict checking)")
    first_batch = production_df.iloc[0]
    first_batch_rows = process_first_batch(first_batch, output_dir, stations_df, transporters_df, logger)
    all_rows.extend(first_batch_rows)
    
    # 2. LOPUT ERÄT - konfliktienratkaisulla
    logger.log("BATCH", "Processing remaining batches (with conflict resolution)")
    for i in range(1, len(production_df)):
        batch_data = production_df.iloc[i]
        current_matrix = pd.DataFrame(all_rows)
        
        batch_rows = process_batch_with_conflicts(
            batch_data, output_dir, stations_df, transporters_df, current_matrix, logger
        )
        all_rows.extend(batch_rows)
    
    # Tallenna matriisi
    save_matrix(all_rows, output_dir, logger)
    return pd.DataFrame(all_rows)

def process_first_batch(batch_data, output_dir, stations_df, transporters_df, logger):
    """ENSIMMÄINEN ERÄ - dokumentaation mukaan ilman konfliktitarkastelua"""
    batch_id = int(batch_data['Batch'])  # KORJAUS: Batch eikä Batch_id
    treatment_program = int(batch_data['Treatment_program'])
    start_time = batch_data['Start_time_seconds']
    start_station = int(batch_data['Start_station'])
    
    # Lataa käsittelyohjelma
    program_df = load_batch_program(output_dir, batch_id, treatment_program)
    
    rows = []
    current_time = start_time
    previous_station = start_station
    
    for stage_idx, (_, stage_row) in enumerate(program_df.iterrows()):
        stage = stage_idx
        min_stat = int(stage_row['MinStat'])
        max_stat = int(stage_row['MaxStat'])
        treatment_time = time_to_seconds(stage_row['CalcTime'])  # KORJAUS: Muunna sekunneiksi
        
        # Ensimmäinen erä: käytä MinStat, ei konfliktitarkastelua
        selected_station = min_stat
        
        # NOSTINFYSIIKKA: Phase_1=0 (nostin jo asemalla)
        transporter = transporters_df.iloc[0]  # Ensimmäinen nostin
        
        lift_station_row = stations_df[stations_df['Number'] == previous_station].iloc[0]
        sink_station_row = stations_df[stations_df['Number'] == selected_station].iloc[0]
        
        phase_1 = 0.0  # Nostin jo asemalla (dokumentaation mukaan)
        phase_2 = calculate_lift_time(lift_station_row, transporter)
        phase_3 = calculate_physics_transfer_time(lift_station_row, sink_station_row, transporter)
        phase_4 = calculate_sink_time(sink_station_row, transporter)
        
        transport_time = phase_2 + phase_3 + phase_4
        entry_time = current_time + transport_time
        exit_time = entry_time + treatment_time
        
        rows.append({
            'Batch': batch_id,
            'Stage': stage,
            'Station': selected_station,
            'EntryTime': entry_time,
            'ExitTime': exit_time,
            'CalcTime': treatment_time,
            'Treatment_program': treatment_program,  # KORJAUS: Lisää puuttuva sarake
            'TaskTime': transport_time + treatment_time,
            'Phase_1': phase_1,
            'Phase_2': phase_2,
            'Phase_3': phase_3,
            'Phase_4': phase_4
        })
        
        current_time = exit_time
        previous_station = selected_station
        
        logger.log("STAGE", f"Batch {batch_id} Stage {stage} Station {selected_station} | "
                  f"Entry: {entry_time:.1f}s Exit: {exit_time:.1f}s")
    
    return rows

def process_batch_with_conflicts(batch_data, output_dir, stations_df, transporters_df, current_matrix, logger):
    """LOPUT ERÄT - konfliktienratkaisulla dokumentaation mukaan"""
    batch_id = int(batch_data['Batch'])  # KORJAUS: Batch eikä Batch_id
    treatment_program = int(batch_data['Treatment_program'])
    original_start_time = batch_data['Start_time_seconds']
    start_station = int(batch_data['Start_station'])
    
    # Lataa käsittelyohjelma
    program_df = load_batch_program(output_dir, batch_id, treatment_program)
    
    current_start_time = original_start_time
    
    # KONFLIKTIENRATKAISU: Tarkista vaihe kerrallaan
    max_iterations = 1000  # Turvakytkentä
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        rows = []
        current_time = current_start_time
        previous_station = start_station
        conflict_found = False
        
        logger.log("CONFLICT", f"Batch {batch_id} iteration {iteration}, start time: {current_start_time:.1f}s")
        
        # Vektoroitu käsittely
        for stage_idx in range(len(program_df)):
            stage_row = program_df.iloc[stage_idx]
            stage = stage_idx
            min_stat = int(stage_row['MinStat'])
            max_stat = int(stage_row['MaxStat'])
            treatment_time = time_to_seconds(stage_row['CalcTime'])  # KORJAUS: Muunna sekunneiksi
            
            # Nostinfysiikka
            transporter = transporters_df.iloc[0]
            lift_station_row = stations_df[stations_df['Number'] == previous_station].iloc[0]
            
            # Testaa kaikki rinnakkaiset asemat min_stat -> max_stat
            station_found = False
            
            for test_station in range(min_stat, max_stat + 1):
                sink_station_row = stations_df[stations_df['Number'] == test_station].iloc[0]
                
                phase_1 = 0.0  # Nostin jo asemalla (dokumentaation mukaan)
                phase_2 = calculate_lift_time(lift_station_row, transporter)
                phase_3 = calculate_physics_transfer_time(lift_station_row, sink_station_row, transporter)
                phase_4 = calculate_sink_time(sink_station_row, transporter)
                
                transport_time = phase_2 + phase_3 + phase_4
                entry_time = current_time + transport_time
                exit_time = entry_time + treatment_time
                
                # Tarkista konflikti
                if is_station_available(test_station, current_matrix, entry_time, exit_time):
                    # Vapaa asema löytyi
                    rows.append({
                        'Batch': batch_id,
                        'Stage': stage,
                        'Station': test_station,
                        'EntryTime': entry_time,
                        'ExitTime': exit_time,
                        'CalcTime': treatment_time,
                        'Treatment_program': treatment_program,  # KORJAUS: Lisää puuttuva sarake
                        'TaskTime': transport_time + treatment_time,
                        'Phase_1': phase_1,
                        'Phase_2': phase_2,
                        'Phase_3': phase_3,
                        'Phase_4': phase_4
                    })
                    
                    current_time = exit_time
                    previous_station = test_station
                    station_found = True
                    break
            
            if not station_found:
                # Konflikti löytyi - laske milloin asemat vapautuvat
                earliest_free_time = find_earliest_free_time(
                    min_stat, max_stat, current_matrix, current_time, transporters_df, stations_df
                )
                
                # Siirrä erän alkuaikaa (minimal delay)
                delay = earliest_free_time - current_time
                current_start_time = original_start_time + delay
                conflict_found = True
                
                logger.log("CONFLICT", f"Batch {batch_id} Stage {stage}: Delayed by {delay:.1f}s")
                break
        
        if not conflict_found:
            # Kaikki vaiheet menivät läpi ilman konfliktia
            break
    
    if iteration >= max_iterations:
        logger.log("ERROR", f"Batch {batch_id} exceeded max iterations ({max_iterations})")
        raise RuntimeError(f"Conflict resolution failed for batch {batch_id} after {max_iterations} iterations")
    
    return rows

def is_station_available(station, current_matrix, entry_time, exit_time):
    """Tarkista onko asema vapaa haluttuna aikana"""
    station_tasks = current_matrix[current_matrix['Station'] == station]
    
    if station_tasks.empty:
        return True
    
    # Optimoitu tarkistus ilman iterrows()
    overlaps = ~((exit_time <= station_tasks['EntryTime']) | (entry_time >= station_tasks['ExitTime']))
    return not overlaps.any()

def find_earliest_free_time(min_stat, max_stat, current_matrix, target_time, transporters_df, stations_df):
    """
    Etsi milloin rinnakkaiset asemat vapautuvat
    - KORJAUS: Riittää että YKSI asema vapautuu (min eikä max)
    - Vaihtoaika lasketaan fysiikkafunktioilla
    """
    station_free_times = []
    
    for station in range(min_stat, max_stat + 1):
        station_tasks = current_matrix[current_matrix['Station'] == station]
        
        if station_tasks.empty:
            # Asema on vapaa heti
            station_free_times.append(target_time)
        else:
            # Tarkista konfliktissa olevat tehtävät
            conflicting_tasks = station_tasks[station_tasks['ExitTime'] > target_time]
            if conflicting_tasks.empty:
                # Ei konflikteja
                station_free_times.append(target_time)
            else:
                # Ensimmäinen vapautuva + vaihtoaika
                first_exit = conflicting_tasks['ExitTime'].min()
                changeover_time = calculate_changeover_time(station, stations_df, transporters_df)
                station_free_times.append(first_exit + changeover_time)
    
    # KORJAUS: Riittää että YKSI asema vapautuu -> min()
    return min(station_free_times)

def calculate_changeover_time(station, stations_df, transporters_df):
    """
    Laskee erien vaihtoon tarvittavan ajan fysiikkafunktioilla
    Yksinkertainen arvio: nosto + siirto + lasku
    """
    transporter = transporters_df.iloc[0]
    station_row = stations_df[stations_df['Number'] == station].iloc[0]
    
    # Arvio: nosto + lyhyt siirto + lasku
    lift_time = calculate_lift_time(station_row, transporter)
    transfer_time = calculate_physics_transfer_time(station_row, station_row, transporter)
    sink_time = calculate_sink_time(station_row, transporter)
    
    return lift_time + transfer_time + sink_time

# APUFUNKTIOT

def load_production_data(output_dir):
    """Lataa Production.csv ja muunna Start_time sekunneiksi"""
    production_file = os.path.join(output_dir, "initialization", "Production.csv")
    df = pd.read_csv(production_file)
    df['Start_time_seconds'] = df['Start_time'].apply(time_to_seconds)
    return df

def load_stations_data():
    """Lataa Stations.csv"""
    stations_file = "initialization/Stations.csv"
    return pd.read_csv(stations_file)

def load_transporters_data():
    """Lataa Transporters.csv"""
    transporters_file = "initialization/Transporters.csv"
    return pd.read_csv(transporters_file)

def load_batch_program(output_dir, batch_id, treatment_program):
    """Lataa erän käsittelyohjelma"""
    program_file = os.path.join(
        output_dir, "original_programs", 
        f"Batch_{batch_id:03d}_Treatment_program_{treatment_program:03d}.csv"
    )
    return pd.read_csv(program_file)

def time_to_seconds(time_str):
    """Muunna aika sekunneiksi"""
    if pd.isna(time_str):
        return 0
    if isinstance(time_str, (int, float)):
        return float(time_str)
    
    time_str = str(time_str).strip()
    if time_str == "" or time_str == "0":
        return 0.0
    
    try:
        # Oleta muoto HH:MM:SS tai MM:SS
        parts = time_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(float, parts)
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except:
        return 0.0

def save_matrix(rows, output_dir, logger):
    """Tallenna matriisi CSV-tiedostoon"""
    os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)
    
    df = pd.DataFrame(rows)
    output_file = os.path.join(output_dir, "logs", "line_matrix_original.csv")
    df.to_csv(output_file, index=False)
    
    logger.log("SAVE", f"Matrix saved to {output_file}")
    logger.log("SAVE", f"Total batches: {df['Batch'].nunique()}")
    logger.log("SAVE", f"Total stages: {len(df)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = "output/2025-08-11_14-27-41"  # Testimaarittely
    
    generate_matrix_original(output_dir)
