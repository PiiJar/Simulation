#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YKSINKERTAINEN ALKUPERÄINEN MATRIISI

Konfliktien ratkaisu:
1. Laske erän ajat
2. Tarkista konfliktit matriisista  
3. Jos konflikti → siirrä erää, laske uudestaan
4. Jatka seuraavaan vaiheeseen
"""

import pandas as pd
import os
from simulation_logger import SimulationLogger
from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time

def time_to_seconds(time_str):
    """Muunna aika sekunneiksi"""
    if isinstance(time_str, (int, float)):
        return float(time_str)
    
    time_str = str(time_str).strip()
    if 's' in time_str:
        return float(time_str.replace('s', ''))
    
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = map(float, parts)
        return h * 3600 + m * 60 + s
    return float(time_str)

def load_production_data(output_dir):
    """Lataa tuotantodata"""
    prod_file = os.path.join(output_dir, "initialization", "Production.csv")
    df = pd.read_csv(prod_file)
    
    # Muunna Start_time sekunneiksi
    df['Start_time_seconds'] = df['Start_time'].apply(time_to_seconds)
    return df

def check_station_conflict(all_tasks, parallel_stations, entry_time, exit_time, transporters_df, stations_df, current_station):
    """
    Tarkistaa onko mikä tahansa rinnakkaisista asemista vapaa haluttuna aikana.
    Palauttaa: (valittu_asema, on_konflikti)
    """
    for test_station in parallel_stations:
        # Laske fysiikkapohjaiset siirtoajat tälle asemalle
        try:
            transporter = transporters_df.iloc[0]
        except IndexError:
            raise RuntimeError(f"VIRHE: Nostinta ei löydy Transporters.csv:stä! DataFrame: {transporters_df}")
        filtered_from = stations_df[stations_df['Number'] == current_station]
        if filtered_from.empty:
            raise RuntimeError(f"VIRHE: Asemaa {current_station} ei löydy Stations.csv:stä! Tarkista syötetiedostot ja käsittelyohjelmat. Mahdolliset asemat: {stations_df['Number'].unique()}")
        try:
            from_station_row = filtered_from.iloc[0]
        except IndexError:
            raise RuntimeError(f"VIRHE: Asemaa {current_station} ei löydy Stations.csv:stä! DataFrame: {filtered_from}")
        filtered_to = stations_df[stations_df['Number'] == test_station]
        if filtered_to.empty:
            raise RuntimeError(f"VIRHE: Asemaa {test_station} ei löydy Stations.csv:stä! Tarkista syötetiedostot ja käsittelyohjelmat. Mahdolliset asemat: {stations_df['Number'].unique()}")
        try:
            to_station_row = filtered_to.iloc[0]
        except IndexError:
            raise RuntimeError(f"VIRHE: Asemaa {test_station} ei löydy Stations.csv:stä! DataFrame: {filtered_to}")
        
        lift_time = calculate_lift_time(from_station_row, transporter)
        transfer_time = calculate_physics_transfer_time(from_station_row, to_station_row, transporter)
        sink_time = calculate_sink_time(to_station_row, transporter)
        transport_time = lift_time + transfer_time + sink_time
        
        test_entry_time = entry_time  # käytä alkuperäistä entry_time
        test_exit_time = exit_time    # käytä alkuperäistä exit_time
        
        # Tarkista konflikti TÄLLÄ asemalla
        has_conflict = False
        for existing_task in all_tasks:
            if existing_task['Station'] == test_station:
                # Realistinen vaihtoajan laskenta
                filtered_prev = stations_df[stations_df['Number'] == existing_task['Station']]
                if filtered_prev.empty:
                    raise RuntimeError(f"VIRHE: Asemaa {existing_task['Station']} (existing_task) ei löydy Stations.csv:stä! Tarkista syötetiedostot ja käsittelyohjelmat. Mahdolliset asemat: {stations_df['Number'].unique()}")
                try:
                    prev_station_row = filtered_prev.iloc[0]
                except IndexError:
                    raise RuntimeError(f"VIRHE: Asemaa {existing_task['Station']} (existing_task) ei löydy Stations.csv:stä! DataFrame: {filtered_prev}")
                prev_lift = calculate_lift_time(prev_station_row, transporter)
                prev_transfer = calculate_physics_transfer_time(prev_station_row, from_station_row, transporter)
                prev_sink = calculate_sink_time(from_station_row, transporter)
                changeover_time = (prev_lift + prev_transfer + prev_sink) + transport_time
                
                if test_entry_time < existing_task['ExitTime'] + changeover_time:
                    has_conflict = True
                    break
        
        if not has_conflict:
            # Vapaa asema löytyi!
            return test_station, False
    
    # Kaikki asemat varattu
    return parallel_stations[0], True

def load_batch_program(output_dir, batch_id, treatment_program):
    """Lataa erän käsittelyohjelma"""
    program_file = os.path.join(output_dir, "original_programs", f"Batch_{batch_id:03d}_Treatment_program_{treatment_program:03d}.csv")
    return pd.read_csv(program_file)

def load_stations_data():
    """Lataa asemadata"""
    stations_file = os.path.join("initialization", "Stations.csv")
    return pd.read_csv(stations_file)

def load_transporters_data():
    """Lataa nostimet"""
    transporters_file = os.path.join("initialization", "Transporters.csv")
    return pd.read_csv(transporters_file)

def generate_matrix_original(output_dir, step_logging=True):
    """
    YKSINKERTAINEN MATRIISIGENEROINTI
    """
    logger = SimulationLogger(output_dir)
    logger.log("MATRIX_GEN", "Starting simple matrix generation")
    
    # Lataa data
    production_df = load_production_data(output_dir)
    stations_df = load_stations_data()
    transporters_df = load_transporters_data()
    
    # Matriisi = lista tehtävistä
    all_tasks = []

    # Käsittele erä kerrallaan
    for _, batch_data in production_df.iterrows():
        batch_id = int(batch_data['Batch'])
        treatment_program = int(batch_data['Treatment_program'])
        start_time = batch_data['Start_time_seconds']
        start_station = int(batch_data['Start_station'])

        logger.log("BATCH", f"Processing batch {batch_id}")

        # Lataa käsittelyohjelma
        program_df = load_batch_program(output_dir, batch_id, treatment_program)

        # Konfliktien ratkaisu
        batch_start_time = start_time
        max_attempts = 100

        for attempt in range(max_attempts):
            tasks = []
            current_time = batch_start_time
            current_station = start_station
            conflict_found = False

            # Käy käsittelyohjelman vaiheet läpi (älä tee ylimääräistä Stage 0 -riviä)
            for stage_idx in range(len(program_df)):
                stage_row = program_df.iloc[stage_idx]
                stage_num = int(stage_row['Stage'])  # Käytä ohjelman Stage-arvoa
                min_stat = int(stage_row['MinStat'])
                max_stat = int(stage_row['MaxStat'])
                # if stage_num == 13:
                #     print(f"[DEBUG] Stage 13: MinStat={min_stat}, MaxStat={max_stat}")
                treatment_time = time_to_seconds(stage_row['CalcTime'])

                # Etsi vapaa asema rinnakkaisista asemista
                parallel_stations = list(range(min_stat, max_stat + 1))

                # Laske fysiikkapohjaiset siirtoajat (yleinen laskenta)

                try:
                    transporter = transporters_df.iloc[0]
                except IndexError:
                    raise RuntimeError(f"VIRHE: Nostinta ei löydy Transporters.csv:stä! DataFrame: {transporters_df}")
                filtered_from = stations_df[stations_df['Number'] == current_station]
                if filtered_from.empty:
                    raise RuntimeError(f"VIRHE: Asemaa {current_station} ei löydy Stations.csv:stä! Tarkista syötetiedostot ja käsittelyohjelmat. Mahdolliset asemat: {stations_df['Number'].unique()}")
                try:
                    from_station_row = filtered_from.iloc[0]
                except IndexError:
                    raise RuntimeError(f"VIRHE: Asemaa {current_station} ei löydy Stations.csv:stä! DataFrame: {filtered_from}")

                # Käytä ensimmäistä asemaa transport_time laskentaan (arvio)
                filtered_to = stations_df[stations_df['Number'] == min_stat]
                if filtered_to.empty:
                    raise RuntimeError(f"VIRHE: Asemaa {min_stat} (min_stat) ei löydy Stations.csv:stä! Tarkista syötetiedostot ja käsittelyohjelmat. Mahdolliset asemat: {stations_df['Number'].unique()}")
                try:
                    to_station_row = filtered_to.iloc[0]
                except IndexError:
                    raise RuntimeError(f"VIRHE: Asemaa {min_stat} (min_stat) ei löydy Stations.csv:stä! DataFrame: {filtered_to}")
                lift_time = calculate_lift_time(from_station_row, transporter)
                transfer_time = calculate_physics_transfer_time(from_station_row, to_station_row, transporter)
                sink_time = calculate_sink_time(to_station_row, transporter)
                transport_time = lift_time + transfer_time + sink_time

                entry_time = current_time + transport_time
                exit_time = entry_time + treatment_time

                # Tarkista konflikti KAIKISSA rinnakkaisissa asemissa
                station_found, has_conflict = check_station_conflict(
                    all_tasks, parallel_stations, entry_time, exit_time, 
                    transporters_df, stations_df, current_station
                )
                # if stage_num == 13:
                #     print(f"[DEBUG] Stage 13: Valittu asema {station_found} rinnakkaisista {parallel_stations}, konflikti={has_conflict}")

                if not has_conflict:
                    # Vapaa asema löytyi
                    tasks.append({
                        'Batch': batch_id,
                        'Stage': stage_num,  # Käytä ohjelman Stage-arvoa
                        'Station': station_found,
                        'EntryTime': entry_time,
                        'ExitTime': exit_time,
                        'CalcTime': treatment_time,
                        'Treatment_program': treatment_program
                    })
                    current_time = exit_time
                    current_station = station_found
                else:
                    # Konflikti kaikissa rinnakkaisissa asemissa
                    # Laske milloin ensimmäinen asema vapautuu
                    earliest_free = float('inf')

                    for test_station in parallel_stations:
                        station_free_time = current_time

                        for existing_task in all_tasks:
                            if existing_task['Station'] == test_station:
                                # Sama vaihtoaika-logiikka kuin check_station_conflict funktiossa

                                try:
                                    transporter = transporters_df.iloc[0]
                                except IndexError:
                                    raise RuntimeError(f"VIRHE: Nostinta ei löydy Transporters.csv:stä! DataFrame: {transporters_df}")
                                filtered_from = stations_df[stations_df['Number'] == current_station]
                                if filtered_from.empty:
                                    raise RuntimeError(f"VIRHE: Asemaa {current_station} ei löydy Stations.csv:stä! Tarkista syötetiedostot ja käsittelyohjelmat. Mahdolliset asemat: {stations_df['Number'].unique()}")
                                try:
                                    from_station_row = filtered_from.iloc[0]
                                except IndexError:
                                    raise RuntimeError(f"VIRHE: Asemaa {current_station} ei löydy Stations.csv:stä! DataFrame: {filtered_from}")
                                filtered_to = stations_df[stations_df['Number'] == test_station]
                                if filtered_to.empty:
                                    raise RuntimeError(f"VIRHE: Asemaa {test_station} ei löydy Stations.csv:stä! Tarkista syötetiedostot ja käsittelyohjelmat. Mahdolliset asemat: {stations_df['Number'].unique()}")
                                try:
                                    to_station_row = filtered_to.iloc[0]
                                except IndexError:
                                    raise RuntimeError(f"VIRHE: Asemaa {test_station} ei löydy Stations.csv:stä! DataFrame: {filtered_to}")

                                filtered_prev = stations_df[stations_df['Number'] == existing_task['Station']]
                                if filtered_prev.empty:
                                    raise RuntimeError(f"VIRHE: Asemaa {existing_task['Station']} (existing_task) ei löydy Stations.csv:stä! Tarkista syötetiedostot ja käsittelyohjelmat. Mahdolliset asemat: {stations_df['Number'].unique()}")
                                try:
                                    prev_station_row = filtered_prev.iloc[0]
                                except IndexError:
                                    raise RuntimeError(f"VIRHE: Asemaa {existing_task['Station']} (existing_task) ei löydy Stations.csv:stä! DataFrame: {filtered_prev}")
                                prev_lift = calculate_lift_time(prev_station_row, transporter)
                                prev_transfer = calculate_physics_transfer_time(prev_station_row, from_station_row, transporter)
                                prev_sink = calculate_sink_time(from_station_row, transporter)

                                lift_time_new = calculate_lift_time(from_station_row, transporter)
                                transfer_time_new = calculate_physics_transfer_time(from_station_row, to_station_row, transporter)
                                sink_time_new = calculate_sink_time(to_station_row, transporter)

                                changeover_time = (prev_lift + prev_transfer + prev_sink) + (lift_time_new + transfer_time_new + sink_time_new)
                                required_free_time = existing_task['ExitTime'] + changeover_time
                                station_free_time = max(station_free_time, required_free_time)

                        earliest_free = min(earliest_free, station_free_time)

                    # Siirrä erän alkua
                    if earliest_free == float('inf'):
                        earliest_free = current_time + 60  # Fallback

                    # Siirto perustuu todelliseen päällekkäisyyteen
                    delay = earliest_free - current_time
                    batch_start_time += delay
                    conflict_found = True
                    # logger.log("CONFLICT", f"Batch {batch_id} stage {stage_idx}: delay {delay:.1f}s")
                    logger.log("CONFLICT", f"Batch {batch_id} stage {stage_idx}: delay {delay:.1f}s")
                    break

            if not conflict_found:
                # Kaikki vaiheet ok, mutta tarkistetaan myös nostinkapasiteetti
                # Selvitä kaikki nostimet, joita tämän erän tehtävät käyttävät
                # Oletetaan että Transporter-id tulee treatment-ohjelmasta tai oletuksena 1
                # Jos Transporter ei ole taskissa, lisätään se oletuksena 1
                for t in tasks:
                    if 'Transporter' not in t:
                        t['Transporter'] = 1

                nostin_ids = set(t['Transporter'] for t in tasks)
                viivastys = None
                for nostin_id in nostin_ids:
                    era_nostintehtavat = sorted([t for t in tasks if t['Transporter'] == nostin_id], key=lambda x: x['EntryTime'])
                    if not era_nostintehtavat:
                        continue
                    jaksot = []
                    jakso = []
                    prev_exit = None
                    for t in era_nostintehtavat:
                        if not jakso:
                            jakso = [t]
                        else:
                            if prev_exit is not None and t['EntryTime'] > prev_exit + 1e-6:
                                jaksot.append(jakso)
                                jakso = [t]
                            else:
                                jakso.append(t)
                        prev_exit = t['ExitTime']
                    if jakso:
                        jaksot.append(jakso)
                    for jakso in jaksot:
                        aikaikkuna_alku = jakso[0]['EntryTime']
                        aikaikkuna_loppu = jakso[-1]['ExitTime']
                        aikaikkuna = aikaikkuna_loppu - aikaikkuna_alku
                        kaikki_nostimen_tehtavat = [
                            t for t in all_tasks + tasks
                            if t['Transporter'] == nostin_id
                            and t['EntryTime'] < aikaikkuna_loppu and t['ExitTime'] > aikaikkuna_alku
                            and 1 <= int(t.get('Stage', 0)) <= 4
                        ]
                        tehtava_aika_summa = sum(
                            min(t['ExitTime'], aikaikkuna_loppu) - max(t['EntryTime'], aikaikkuna_alku)
                            for t in kaikki_nostimen_tehtavat
                            if max(t['EntryTime'], aikaikkuna_alku) < min(t['ExitTime'], aikaikkuna_loppu)
                        )
                        if tehtava_aika_summa > aikaikkuna:
                            erotus = tehtava_aika_summa - aikaikkuna
                            viivastys = max(viivastys or 0, erotus)
                            break  # Jos yksikin aikaikkuna ylittyy, keskeytä nostimen tarkistus
                    if viivastys is not None:
                        break  # Jos yksikin nostin vaatii viivästystä, keskeytä kaikkien nostimien tarkistus
                if viivastys is not None:
                    batch_start_time += viivastys
                    conflict_found = True
                    continue
                # Kaikki nostimet ok, lisää tehtävät
                all_tasks.extend(tasks)
                def seconds_to_hms(seconds):
                    h = int(seconds // 3600)
                    m = int((seconds % 3600) // 60)
                    s = int(seconds % 60)
                    return f"{h:02d}:{m:02d}:{s:02d}"
                new_hms = seconds_to_hms(batch_start_time)
                new_sec = int(round(batch_start_time))
                production_df.loc[production_df['Batch'] == batch_id, 'Start_time'] = new_hms
                production_df.loc[production_df['Batch'] == batch_id, 'Start_time_seconds'] = new_sec
                break

        if attempt >= max_attempts - 1:
            logger.log("ERROR", f"Batch {batch_id} failed after {max_attempts} attempts")
            # logger.log("ERROR", f"Batch {batch_id} failed after {max_attempts} attempts")
    # Muunna DataFrameksi
    matrix_df = pd.DataFrame(all_tasks)


    # Tallenna vain logs-kansioon vaihe 4:lle
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    logs_file = os.path.join(logs_dir, "line_matrix_original.csv")
    matrix_df.to_csv(logs_file, index=False)


    # Tallenna päivitetty production_df takaisin simulaatiokansion Production.csv
    prod_file = os.path.join(output_dir, "initialization", "Production.csv")
    os.makedirs(os.path.dirname(prod_file), exist_ok=True)
    production_df.to_csv(prod_file, index=False)

    logger.log("MATRIX_GEN", f"Matrix saved: {logs_file}")
    # logger.log("MATRIX_GEN", f"Original matrix generated: {len(matrix_df)} tasks")

    return matrix_df

if __name__ == "__main__":
    # Testi
    output_dir = "output/test"
    os.makedirs(output_dir, exist_ok=True)
    matrix = generate_matrix_original(output_dir)
    # print(matrix.head())
