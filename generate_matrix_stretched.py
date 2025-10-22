import os
import pandas as pd
from datetime import datetime
from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time

def load_stations(output_dir):
    """Lataa Stations.csv tiedoston"""
    stations_file = os.path.join(output_dir, "initialization", "stations.csv")
    if not os.path.exists(stations_file):
        raise FileNotFoundError(f"Stations.csv ei löydy: {stations_file}")
    return pd.read_csv(stations_file)

def select_capable_transporter(lift_station, sink_station, stations_df, transporters_df):
    """
    Valitsee sopivan nostimen tehtävälle stations ja transporters tietojen perusteella.
    Kopioi alkuperäisen logiikan generate_matrix_original.py:stä.
    """
    # Hae asemien x-koordinaatit
    lift_x = stations_df[stations_df['Number'] == lift_station]['X Position'].iloc[0]
    sink_x = stations_df[stations_df['Number'] == sink_station]['X Position'].iloc[0]
    
    # Käy läpi nostimet järjestyksessä
    for _, transporter in transporters_df.iterrows():
        min_x = transporter['Min_x_position']
        max_x = transporter['Max_x_Position']
        
        # Tarkista että molemmat asemat ovat nostimen alueella
        if min_x <= lift_x <= max_x and min_x <= sink_x <= max_x:
            return transporter
    
    # Jos mikään nostin ei pysty, palautetaan ensimmäinen (virhetilanne)
    return transporters_df.iloc[0]

def select_available_station(min_stat, max_stat, station_reservations, entry_time, exit_time):
    """
    Valitsee ensimmäisen vapaan aseman MinStat-MaxStat väliltä numerojärjestyksessä.
    Yksinkertaistettu versio alkuperäisestä - ei kirjaa konflikteja.
    """
    for station in range(min_stat, max_stat + 1):
        if station not in station_reservations:
            station_reservations[station] = []
        
        # Tarkista onko asema vapaa haluttuna aikana
        is_available = True
        for reservation in station_reservations[station]:
            res_start, res_end = reservation[:2]
            # Jos aikavälit menevät päällekkäin
            latest_start = max(entry_time, res_start)
            earliest_end = min(exit_time, res_end)
            if earliest_end > latest_start:  # Päällekkäisyys löytyi
                is_available = False
                break
        
        if is_available:
            return station
    
    # Jos mikään ei ole vapaa, palauta ensimmäinen
    return min_stat

def load_production_batches_stretched(output_dir):
    """Lataa Production.csv ja palauttaa tuotantoerien tiedot päivitetyillä lähtöajoilla"""
    file_path = os.path.join(output_dir, "initialization", "production.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Production.csv ei löydy: {file_path}")
    df = pd.read_csv(file_path)
    
    # KORJAUS: Muunna päivitetty Start_time sekunteiksi (ohittaa vanhan Start_time_seconds sarakkeen)
    df["Start_time_seconds"] = pd.to_timedelta(df["Start_time"]).dt.total_seconds()
    
    return df

def load_batch_program_optimized(programs_dir, batch_id, treatment_program):
    """
    Lataa eräkohtainen ohjelmatiedosto optimized_programs kansiosta.
    """
    batch_str = str(batch_id).zfill(3)
    program_str = str(treatment_program).zfill(3)
    
    # Käytä aina optimized_programs kansiota
    file_path = os.path.join(programs_dir, f"Batch_{batch_str}_Treatment_program_{program_str}.csv")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Eräohjelmaa ei löydy: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Muunna ajat sekunteiksi
    df["MinTime"] = pd.to_timedelta(df["MinTime"]).dt.total_seconds()
    df["MaxTime"] = pd.to_timedelta(df["MaxTime"]).dt.total_seconds()
    
    if "CalcTime" in df.columns:
        df["CalcTime"] = pd.to_timedelta(df["CalcTime"]).dt.total_seconds()
    else:
        df["CalcTime"] = df["MinTime"]
    
    return df


def generate_matrix_stretched_pure(output_dir):
    """
    Luo lopullisen matriisin päivitetyn Production.csv:n ja optimoitujen ohjelmien perusteella.
    EI ratkaise konflikteja, EI päivitä Production.csv:ää.
    
    LOGIIKKA:
    1. Käyttää päivitettyä Production.csv Start_time kenttää (muuntaa sekunteiksi)
    2. Käyttää AINA optimoituja ohjelmia (optimized_programs/) 
    3. Laskee EntryTime/ExitTime peräkkäisesti ohjelman vaiheiden mukaan
    4. Huomioi rinnakkaiset asemat (MinStat-MaxStat) asemavarausten kanssa
    5. Laskee nostimen fysiikan (Phase_1, Phase_2, Phase_3, Phase_4)
    """
    logs_dir = os.path.join(output_dir, "logs")
    optimized_dir = os.path.join(output_dir, "optimized_programs")
    output_file = os.path.join(logs_dir, "line_matrix_stretched.csv")
    
    # Lataa lähtötiedot - päivitetty Production.csv jossa Start_time ON oikein
    production_df = load_production_batches_stretched(output_dir)
    stations_df = load_stations(output_dir)
    transporters_df = pd.read_csv(os.path.join(output_dir, "initialization", "transporters.csv"))
    
    # Asemavaraukset rinnakkaisten asemien hallintaan
    station_reservations = {}
    
    all_rows = []
    
    # Käy läpi jokainen erä
    for _, batch_row in production_df.iterrows():
        batch_id = int(batch_row["Batch"])
        start_station = int(batch_row["Start_station"])
        treatment_program = int(batch_row["Treatment_program"])
        start_time_seconds = float(batch_row["Start_time_seconds"])

        prog_df = load_batch_program_optimized(optimized_dir, batch_id, treatment_program)

        # if batch_id == 1:
        #     print(f"[DEBUG MATRIX] Ensimmäinen erä: batch={batch_id}, start_station={start_station}, start_time_seconds={start_time_seconds}")
        all_rows.append({
            "Batch": batch_id,
            "Program": treatment_program,
            "Treatment_program": treatment_program,
            "Stage": 0,
            "Station": start_station,
            "MinTime": 0,
            "MaxTime": 0,
            "CalcTime": 0,
            "EntryTime": int(start_time_seconds),
            "ExitTime": int(start_time_seconds),
            "Phase_1": 0.0,
            "Phase_2": 0.0,
            "Phase_3": 0.0,
            "Phase_4": 0.0
        })

        if start_station not in station_reservations:
            station_reservations[start_station] = []
        station_reservations[start_station].append((start_time_seconds, start_time_seconds))

        previous_sink_stat = start_station
        previous_exit = start_time_seconds

        for i, (_, prog_row) in enumerate(prog_df.iterrows()):
            stage = int(prog_row["Stage"])
            min_time = prog_row["MinTime"]
            max_time = prog_row["MaxTime"]
            calc_time = prog_row["CalcTime"]
            min_stat = int(prog_row["MinStat"])
            max_stat = int(prog_row["MaxStat"])

            if i == 0:
                lift_stat = start_station
            else:
                lift_stat = previous_sink_stat

            temp_entry = int(previous_exit)
            temp_exit = temp_entry + int(calc_time)
            sink_stat = select_available_station(min_stat, max_stat, station_reservations, temp_entry, temp_exit)

            transporter = select_capable_transporter(lift_stat, sink_stat, stations_df, transporters_df)
            lift_station_row = stations_df[stations_df['Number'] == lift_stat].iloc[0]
            sink_station_row = stations_df[stations_df['Number'] == sink_stat].iloc[0]

            if i == 0:
                phase_1 = 0.0
            else:
                prev_station_row = stations_df[stations_df['Number'] == previous_sink_stat].iloc[0]
                phase_1 = calculate_physics_transfer_time(prev_station_row, lift_station_row, transporter)

            phase_2 = calculate_lift_time(lift_station_row, transporter)
            phase_3 = calculate_physics_transfer_time(lift_station_row, sink_station_row, transporter)
            phase_4 = calculate_sink_time(sink_station_row, transporter)

            transport_time = phase_2 + phase_3 + phase_4
            entry_time = int(previous_exit + transport_time)
            exit_time = entry_time + int(calc_time)

            # Täsmädebug: Tulosta väliarvot erän 1, vaiheen 1 kohdalla
            # if batch_id == 1 and stage == 1:
            #     print(f"[DEBUG MATRIX] batch=1, stage=1, previous_exit={previous_exit}, phase_2={phase_2}, phase_3={phase_3}, phase_4={phase_4}, transport_time={transport_time}, entry_time={entry_time}")

            if sink_stat not in station_reservations:
                station_reservations[sink_stat] = []
            station_reservations[sink_stat].append((entry_time, exit_time))

            all_rows.append({
                "Batch": batch_id,
                "Program": treatment_program,
                "Treatment_program": treatment_program,
                "Stage": stage,
                "Station": sink_stat,
                "MinTime": int(min_time),
                "MaxTime": int(max_time),
                "CalcTime": int(calc_time),
                "EntryTime": entry_time,
                "ExitTime": exit_time,
                "Phase_1": round(phase_1, 2),
                "Phase_2": round(phase_2, 2),
                "Phase_3": round(phase_3, 2),
                "Phase_4": round(phase_4, 2)
            })



            previous_sink_stat = sink_stat
            previous_exit = exit_time
    
    # Luo DataFrame ja tallenna
    matrix = pd.DataFrame(all_rows)
    
    # Pyöristä float-sarakkeet
    for col in matrix.select_dtypes(include=['float']).columns:
        matrix[col] = matrix[col].round(2)
    
    # Tallenna matriisi
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    matrix.to_csv(output_file, index=False)
    
    # Lokita toiminta
    log_file = os.path.join(logs_dir, "simulation_log.csv")
    if os.path.exists(log_file):
        with open(log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp},TASK,Stretched matrix generated (pure): {os.path.basename(output_file)}\n")
            f.write(f"{timestamp},TASK,Rows in stretched matrix: {len(matrix)}\n")
    
    return matrix

def generate_matrix_stretched(output_dir):
    """Wrapper-funktio yhteensopivuuden vuoksi"""
    return generate_matrix_stretched_pure(output_dir)

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    generate_matrix_stretched(output_dir)
