import pandas as pd
import os
from simulation_logger import get_logger
from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time

def select_capable_transporter(lift_station, sink_station, stations_df, transporters_df):
    """
    Valitsee ensimmäisen nostimen joka pystyy suorittamaan tehtävän.
    
    Args:
        lift_station (int): Nostoaseman numero
        sink_station (int): Laskuaseman numero
        stations_df (DataFrame): Asematiedot x-koordinaateilla
        transporters_df (DataFrame): Nostintiedot vastuualueilla
    
    Returns:
        pd.Series: Valittu nostin tai None jos mikään ei pysty
    """
    # Käy läpi nostimet järjestyksessä ja tarkista asemavälit (lift/sink)
    for _, transporter in transporters_df.iterrows():
        min_lift = int(transporter.get('Min_Lift_Station', transporter.get('Min_lift_station', transporter.get('MinLiftStation', 0))))
        max_lift = int(transporter.get('Max_Lift_Station', transporter.get('Max_lift_station', transporter.get('MaxLiftStation', 0))))
        min_sink = int(transporter.get('Min_Sink_Station', transporter.get('Min_sink_station', transporter.get('MinSinkStation', 0))))
        max_sink = int(transporter.get('Max_Sink_Station', transporter.get('Max_sink_station', transporter.get('MaxSinkStation', 0))))

        if (min_lift <= lift_station <= max_lift) and (min_sink <= sink_station <= max_sink):
            return transporter

    # Jos mikään nostin ei pysty, tulosta virheilmoitus ja keskeytä simulaatio
    print(f"[ERROR] Nostintehtävälle ei löytynyt sopivaa nostinta! Nostoasema: {lift_station}, laskuasema: {sink_station}")
    raise RuntimeError(f"Nostintehtävälle ei löytynyt sopivaa nostinta! Nostoasema: {lift_station}, laskuasema: {sink_station}")

def extract_transporter_tasks(output_dir):
    """
    Lukee venytetyn matriisin ja muodostaa nostintehtävälistan fysiikka-aikojen kanssa.
    
    Otsikkorivi: Transporter_id, Batch, Treatment_program, Start_Time, Lift_Stat, Sink_stat, 
                 Phase_0_start, Phase_1_start, Phase_2_start, Phase_3_start, Phase_4_start, Phase_4_stop
    """
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Call init_logger(output_dir) before using extract_transporter_tasks.")
    
    logger.log("STEP", "STEP 8.6 STARTED: EXTRACT TRANSPORTER TASKS FROM STRETCHED MATRIX")
    
    logs_dir = os.path.join(output_dir, "logs")
    matrix_file = os.path.join(logs_dir, "line_matrix.csv")
    
    if not os.path.exists(matrix_file):
        logger.log_error(f"line_matrix.csv ei löydy: {matrix_file}")
        raise FileNotFoundError(f"line_matrix.csv ei löydy: {matrix_file}")
    
    # Lataa asema- ja nostintiedot nostinvalintaa varten
    stations_file = os.path.join(output_dir, "initialization", "stations.csv")
    transporters_file = os.path.join(output_dir, "initialization", "transporters.csv")
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    start_positions_file = os.path.join(output_dir, "initialization", "transporters_start_positions.csv")
    
    if not os.path.exists(stations_file):
        raise FileNotFoundError(f"stations.csv ei löydy: {stations_file}")
    if not os.path.exists(transporters_file):
        raise FileNotFoundError(f"Transporters.csv ei löydy: {transporters_file}")
    if not os.path.exists(production_file):
        raise FileNotFoundError(f"Production.csv ei löydy: {production_file}")
    if not os.path.exists(start_positions_file):
        raise FileNotFoundError(f"Transporters_start_positions.csv ei löydy: {start_positions_file}")

    stations_df = pd.read_csv(stations_file)
    transporters_df = pd.read_csv(transporters_file)
    production_df = pd.read_csv(production_file)
    start_positions_df = pd.read_csv(start_positions_file)
    # Strip whitespace from column names to avoid KeyError due to leading spaces
    start_positions_df.columns = start_positions_df.columns.str.strip()
    
    # Luo batch-treatment_program -> start_station mapping
    production_df["Batch"] = production_df["Batch"].astype(int)
    production_df["Treatment_program"] = production_df["Treatment_program"].astype(int)
    batch_start_station = {
        (row["Batch"], row["Treatment_program"]): int(row["Start_station"])
        for _, row in production_df.iterrows()
    }

    # Lue nostimien alkupaikat tiedostosta
    transporter_start_positions = {}
    for _, row in start_positions_df.iterrows():
        # Use correct column names from CSV: 'Transporter' and 'Start_station'
        transporter_start_positions[int(row['Transporter'])] = int(row['Start_station'])
    
    try:
        # Lue venytetty matriisi
        df = pd.read_csv(matrix_file)
        df = df.sort_values(["Batch", "Treatment_program", "Stage"]).reset_index(drop=True)
        
        tasks = []
        
        for idx, row in df.iterrows():
            # Jos stage=0, tarkista pitääkö lisätä "alkunosto" 
            if int(row["Stage"]) == 0:
                # Etsi seuraava rivi, joka on samaa batchia ja stage=1
                if idx + 1 < len(df):
                    next_row = df.iloc[idx + 1]
                    if (
                        int(next_row["Stage"]) == 1
                        and row["Batch"] == next_row["Batch"]
                        and row["Treatment_program"] == next_row["Treatment_program"]
                    ):
                        key = (int(row["Batch"]), int(row["Treatment_program"]))
                        step1_row = df[(df["Batch"] == row["Batch"]) & (df["Treatment_program"] == row["Treatment_program"]) & (df["Stage"] == 1)]
                        if (
                            key in batch_start_station
                            and int(row["Station"]) == batch_start_station[key]
                            and not step1_row.empty
                            and int(next_row["Station"]) == int(step1_row.iloc[0]["Station"])
                        ):
                            transporter = select_capable_transporter(
                                int(row["Station"]),
                                int(next_row["Station"]),
                                stations_df,
                                transporters_df
                            )
                            tasks.append({
                                "Transporter_id": int(transporter['Transporter_id']),
                                "Batch": int(row["Batch"]),
                                "Treatment_program": int(row["Treatment_program"]),
                                "Stage": int(row["Stage"]),
                                "Lift_Time": float(row["ExitTime"]),
                                "Lift_Stat": int(row["Station"]),
                                "Sink_stat": int(next_row["Station"]),
                                "Sink_time": float(next_row["EntryTime"])
                            })
                continue
            # Ohita, jos seuraava rivi puuttuu, on eri batchia tai on stage = 0
            if idx + 1 >= len(df):
                continue
            next_row = df.iloc[idx + 1]
            if int(next_row["Stage"]) == 0:
                continue
            if row["Batch"] != next_row["Batch"] or row["Treatment_program"] != next_row["Treatment_program"]:
                continue
            transporter = select_capable_transporter(
                int(row["Station"]),
                int(next_row["Station"]),
                stations_df,
                transporters_df
            )
            tasks.append({
                "Transporter_id": int(transporter['Transporter_id']),
                "Batch": int(row["Batch"]),
                "Treatment_program": int(row["Treatment_program"]),
                "Stage": int(row["Stage"]),
                "Lift_Time": float(row["ExitTime"]),
                "Lift_Stat": int(row["Station"]),
                "Sink_stat": int(next_row["Station"]),
                "Sink_time": float(next_row["EntryTime"])
            })
        
        # Luo DataFrame
        tasks_df = pd.DataFrame(tasks)
        if len(tasks_df) > 0:
            # Lataa esilasketut siirtoajat (Lift/Transfer/Sink) yhdistelmälle (Transporter, From_Station, To_Station)
            cp_dir = os.path.join(output_dir, "cp_sat")
            transfers_path = os.path.join(cp_dir, "cp_sat_transfer_tasks.csv")
            transfers_map = {}
            if os.path.exists(transfers_path):
                transfers_df = pd.read_csv(transfers_path)
                # Normalisoi tyypit
                for c in ("Transporter", "From_Station", "To_Station"):
                    if c in transfers_df.columns:
                        transfers_df[c] = transfers_df[c].astype(int)
                for _, r in transfers_df.iterrows():
                    key = (int(r["Transporter"]), int(r["From_Station"]), int(r["To_Station"]))
                    transfers_map[key] = {
                        "LiftTime": int(round(float(r.get("LiftTime", 0)))),
                        "TransferTime": int(round(float(r.get("TransferTime", 0)))),
                        "SinkTime": int(round(float(r.get("SinkTime", 0)))),
                        "TotalTaskTime": int(round(float(r.get("TotalTaskTime", 0))))
                    }
            else:
                # Jos puuttuu, jatketaan fysiikkalaskennalla
                logger.log('WARN', f"Missing cp_sat_transfer_tasks.csv at {transfers_path}; falling back to physics for phase durations")

            # Yhtenäistä sarakeotsikot heti, jotta myöhemmät viittaukset toimivat
            tasks_df = tasks_df.rename(columns={
                "Lift_Stat": "Lift_stat",
                "Lift_Time": "Lift_time"
            })
            # Sink_time on jo laskettu task-dictissä, ei tarvitse täyttää uudelleen
            # Järjestä nostinkohtaisesti aikajärjestykseen
            tasks_df = tasks_df.sort_values(["Transporter_id", "Lift_time"]).reset_index(drop=True)
            # Pakota kaikki kentät kokonaisluvuiksi/float:iksi
            for col in ["Transporter_id", "Batch", "Treatment_program", "Stage", "lift_stat", "Sink_stat"]:
                if col in tasks_df.columns:
                    tasks_df[col] = tasks_df[col].astype(int)
            if "Lift_time" in tasks_df.columns:
                tasks_df["Lift_time"] = tasks_df["Lift_time"].apply(lambda x: int(round(x)))
            # Lisää fysiikka-aikojen laskenta
            transporter_last_stop = {}
            # Lisää Phase-sarakkeet (kokonaislukuina)
            tasks_df["Phase_0_start"] = 0
            tasks_df["Phase_1_start"] = 0  
            tasks_df["Phase_2_start"] = 0
            tasks_df["Phase_3_start"] = 0
            tasks_df["Phase_4_start"] = 0
            tasks_df["Phase_4_stop"] = 0
            


            väistötehtävät = []
            for idx, row in tasks_df.iterrows():
                transporter_id = row["Transporter_id"]
                batch = row["Batch"]
                lift_station = row["Lift_stat"]
                sink_station = row["Sink_stat"]
                arrival_time = row["Lift_time"]  # Tämä on erän ExitTime nostoasemalta

                # Hae asematiedot fysiikkalaskentoja varten (fallback)
                lift_station_info = stations_df[stations_df['Number'] == lift_station].iloc[0]
                sink_station_info = stations_df[stations_df['Number'] == sink_station].iloc[0]
                transporter_info = transporters_df[transporters_df['Transporter_id'] == transporter_id].iloc[0]

                # Laske fysiikka-ajat
                try:
                    # Phase 1: deadhead prev_sink -> lift OR start_position -> lift (TransferTime)
                    if transporter_id in transporter_last_stop:
                        prev_tasks = tasks_df[(tasks_df["Transporter_id"] == transporter_id) & (tasks_df.index < idx)]
                        if not prev_tasks.empty:
                            last_sink = int(prev_tasks.iloc[-1]["Sink_stat"])
                            dh_pre = transfers_map.get((int(transporter_id), last_sink, int(lift_station)), {}).get("TransferTime", None)
                            if dh_pre is not None and float(dh_pre) > 0:
                                phase_1_duration = int(round(float(dh_pre)))
                            else:
                                last_sink_info = stations_df[stations_df['Number'] == last_sink].iloc[0]
                                phase_1_duration = int(round(calculate_physics_transfer_time(last_sink_info, lift_station_info, transporter_info)))
                        else:
                            start_position = int(transporter_start_positions.get(int(transporter_id), int(lift_station)))
                            dh_pre = transfers_map.get((int(transporter_id), start_position, int(lift_station)), {}).get("TransferTime", None)
                            if dh_pre is not None and float(dh_pre) > 0:
                                phase_1_duration = int(round(float(dh_pre)))
                            else:
                                start_station_info = stations_df[stations_df['Number'] == start_position].iloc[0]
                                phase_1_duration = int(round(calculate_physics_transfer_time(start_station_info, lift_station_info, transporter_info)))
                    else:
                        start_position = int(transporter_start_positions.get(int(transporter_id), int(lift_station)))
                        dh_pre = transfers_map.get((int(transporter_id), start_position, int(lift_station)), {}).get("TransferTime", None)
                        if dh_pre is not None and float(dh_pre) > 0:
                            phase_1_duration = int(round(float(dh_pre)))
                        else:
                            start_station_info = stations_df[stations_df['Number'] == start_position].iloc[0]
                            phase_1_duration = int(round(calculate_physics_transfer_time(start_station_info, lift_station_info, transporter_info)))

                    # Phase 2: Lifting duration from precomputed LiftTime (fallback to physics if missing or <= 0)
                    lift_pre = transfers_map.get((int(transporter_id), int(lift_station), int(sink_station)), {}).get("LiftTime", None)
                    if lift_pre is not None and float(lift_pre) > 0:
                        phase_2_duration = int(round(float(lift_pre)))
                    else:
                        phase_2_duration = int(round(calculate_lift_time(lift_station_info, transporter_info)))

                    # Phase 3: Loaded transfer duration from precomputed TransferTime (fallback if <= 0)
                    trans_pre = transfers_map.get((int(transporter_id), int(lift_station), int(sink_station)), {}).get("TransferTime", None)
                    if trans_pre is not None and float(trans_pre) > 0:
                        phase_3_duration = int(round(float(trans_pre)))
                    else:
                        phase_3_duration = int(round(calculate_physics_transfer_time(lift_station_info, sink_station_info, transporter_info)))

                    # Phase 4: Sinking duration from precomputed SinkTime (fallback if <= 0)
                    sink_pre = transfers_map.get((int(transporter_id), int(lift_station), int(sink_station)), {}).get("SinkTime", None)
                    if sink_pre is not None and float(sink_pre) > 0:
                        phase_4_duration = int(round(float(sink_pre)))
                    else:
                        phase_4_duration = int(round(calculate_sink_time(sink_station_info, transporter_info)))

                except Exception as e:
                    phase_1_duration = 5
                    phase_2_duration = 5
                    phase_3_duration = 5
                    phase_4_duration = 5

                phase_2_start = arrival_time
                # Phase_0_start: Edellisen tehtävän loppu tai alustettu arvo
                if transporter_id in transporter_last_stop:
                    phase_0_start = transporter_last_stop[transporter_id]
                else:
                    phase_0_start = 0


                # Phase 1: Siirto edellisestä sijainista nostamisasemalle
                phase_1_start = phase_2_start - phase_1_duration
                phase_3_start = phase_2_start + phase_2_duration
                phase_4_start = phase_3_start + phase_3_duration
                phase_4_stop = phase_4_start + phase_4_duration

                # Tallenna arvot kokonaislukuina
                tasks_df.at[idx, "Phase_0_start"] = int(round(phase_0_start))
                tasks_df.at[idx, "Phase_1_start"] = int(round(phase_1_start))
                tasks_df.at[idx, "Phase_2_start"] = int(round(phase_2_start))
                tasks_df.at[idx, "Phase_3_start"] = int(round(phase_3_start))
                tasks_df.at[idx, "Phase_4_start"] = int(round(phase_4_start))
                tasks_df.at[idx, "Phase_4_stop"] = int(round(phase_4_stop))

                transporter_last_stop[transporter_id] = phase_4_stop
        
        # Tallenna
        output_file = os.path.join(logs_dir, "transporter_tasks_from_matrix.csv")
        columns = [
            "Transporter_id", "Batch", "Treatment_program", "Stage", "Lift_stat", "Lift_time", "Sink_stat", "Sink_time",
            "Phase_0_start", "Phase_1_start", "Phase_2_start", "Phase_3_start", "Phase_4_start", "Phase_4_stop"
        ]
        tasks_df = tasks_df[columns]
        tasks_df.to_csv(output_file, index=False)
        
        logger.log("STEP", "STEP 8.6 COMPLETED: EXTRACT TRANSPORTER TASKS FROM STRETCHED MATRIX")
        
        return tasks_df
        
    except Exception as e:
        logger.log_error(f"Nostintehtävien erottaminen epäonnistui: {e}")
        raise

def create_detailed_movements(output_dir):
    """
    Muuntaa nostintehtävät realistisiksi liikkeiksi.
    Perusmuunnos: jokainen tehtävä → 5 liikettä (Phase 0–4).
    Väistö lisätään JÄLKIKÄSITTELYSSÄ: jos Idle alkaa yhteisalueella (112–115 nykyisillä rajoilla),
    Idle jaetaan: Idle_before (0s tai >0s) → Avoid (siirto pois yhteisalueelta) → Idle_after.
    """
    logger = get_logger()
    if logger is None:
        # Alusta logger jos ei ole vielä alustettu
        from simulation_logger import init_logger
        init_logger(output_dir)
        logger = get_logger()
        if logger is None:
            raise RuntimeError("Logger initialization failed.")
    
    logger.log("STEP", "STEP 8.7 STARTED: CREATE DETAILED TRANSPORTER MOVEMENTS")
    
    logs_dir = os.path.join(output_dir, "logs")
    tasks_file = os.path.join(logs_dir, "transporter_tasks_from_matrix.csv")
    
    if not os.path.exists(tasks_file):
        logger.log_error(f"transporter_tasks_from_matrix.csv ei löydy: {tasks_file}")
        raise FileNotFoundError(f"transporter_tasks_from_matrix.csv ei löydy: {tasks_file}")
    
    # Lataa tehtävät
    tasks_df = pd.read_csv(tasks_file)
    # Yhtenäistä sarakeotsikot, jotta myöhemmät viittaukset toimivat
    tasks_df = tasks_df.rename(columns={
        "Lift_Stat": "lift_stat",
        "Lift_Time": "Lift_time"
    })
    
    # Lataa nostintiedot alkupaikkojen määrittämiseksi
    transporters_file = os.path.join(output_dir, "initialization", "transporters.csv")
    stations_file = os.path.join(output_dir, "initialization", "stations.csv")
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    
    transporters_df = pd.read_csv(transporters_file)
    stations_df = pd.read_csv(stations_file)
    production_df = pd.read_csv(production_file)
    
    # Laske nostimien alkupaikat tiedostosta (dynaaminen, ei kovakoodauksia)
    start_positions_file = os.path.join(output_dir, "initialization", "transporters_start_positions.csv")
    start_positions_df = pd.read_csv(start_positions_file)
    start_positions_df.columns = start_positions_df.columns.str.strip()
    transporter_start_positions = {}
    for _, row in start_positions_df.iterrows():
        transporter_start_positions[int(row['Transporter'])] = int(row['Start_station'])
    
    # PAKOTETUT ALOITUSPAIKAT: (POISTETTU, käytä vain CSV-tiedostoa)
    # Ei yhtään kovakoodattua nostimen alkupaikkaa – kaikki luetaan CSV:stä
    
    movements = []

    # Seuraa nostimien edellistä sijaintia (Phase 1:n lähtöpaikka)
    transporter_last_location = transporter_start_positions.copy()

    # Tuota perus 5-vaiheiset liikkeet kaikille tehtäville (ilman väistöä)
    for _, task in tasks_df.sort_values(["Transporter_id", "Phase_0_start"]).iterrows():
        transporter_id = int(task['Transporter_id'])
        phase_1_from_station = int(transporter_last_location.get(transporter_id, task.get('lift_stat', task.get('Lift_stat', 0))))
        movements.extend([
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 0,
                'Start_Time': int(task['Phase_0_start']),
                'End_Time': int(task['Phase_1_start']),
                'From_Station': phase_1_from_station,
                'To_Station': phase_1_from_station,
                'Description': 'Idle'
            },
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 1,
                'Start_Time': int(task['Phase_1_start']),
                'End_Time': int(task['Phase_2_start']),
                'From_Station': phase_1_from_station,
                'To_Station': int(task['Lift_stat']),
                'Description': 'Move to lifting station'
            },
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 2,
                'Start_Time': int(task['Phase_2_start']),
                'End_Time': int(task['Phase_3_start']),
                'From_Station': int(task['Lift_stat']),
                'To_Station': int(task['Lift_stat']),
                'Description': 'Lifting'
            },
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 3,
                'Start_Time': int(task['Phase_3_start']),
                'End_Time': int(task['Phase_4_start']),
                'From_Station': int(task['Lift_stat']),
                'To_Station': int(task['Sink_stat']),
                'Description': 'Move to sinking station'
            },
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 4,
                'Start_Time': int(task['Phase_4_start']),
                'End_Time': int(task['Phase_4_stop']),
                'From_Station': int(task['Sink_stat']),
                'To_Station': int(task['Sink_stat']),
                'Description': 'Sinking'
            }
        ])
        transporter_last_location[transporter_id] = int(task['Sink_stat'])
    
    # Lisää loppusiirrot: nostimet takaisin alkupaikoilleen
    # Etsi jokaisen nostimen viimeisen tehtävän Phase_4_stop
    transporter_final_times = {}
    for transporter_id in transporter_start_positions.keys():
        transporter_tasks = tasks_df[tasks_df['Transporter_id'] == transporter_id]
        if not transporter_tasks.empty:
            last_task = transporter_tasks.iloc[-1]
            transporter_final_times[transporter_id] = int(last_task['Phase_4_stop'])
    
    # Etsi koko simuloinnin viimeinen Phase_4_stop aika
    global_final_time = 0
    if not tasks_df.empty:
        global_final_time = int(tasks_df['Phase_4_stop'].max())
    
    # Luo loppusiirrot jokaiselle nostimelle
    from transporter_physics import calculate_physics_transfer_time
    for transporter_id in transporter_start_positions.keys():
        transporter_id = int(transporter_id)  # Varmista int-tyyppi
        if transporter_id in transporter_final_times:
            current_location = transporter_last_location[transporter_id]
            start_position = transporter_start_positions[transporter_id]
            
            # Jos nostin ei ole jo alkupaikassa
            if current_location != start_position:
                # Laske siirtoaika takaisin alkupaikkaan
                filtered_current = stations_df[stations_df['Number'] == current_location]
                filtered_start = stations_df[stations_df['Number'] == start_position]
                if filtered_current.empty:
                    msg = (
                        f"VIRHE: Nykyistä asemaa {current_location} ei löydy Stations.csv:stä!\n"
                        f"Haettu arvo: {current_location}\n"
                        f"Mahdolliset asemat: {stations_df['Number'].unique()}\n"
                        f"DataFrame: {filtered_current.to_string(index=False)}\n"
                        f"Tarkista tiedosto: Stations.csv ja käsittelyohjelmat."
                    )
                    print(msg)
                    raise RuntimeError(msg)
                if filtered_start.empty:
                    msg = (
                        f"VIRHE: Alkupaikkaa {start_position} ei löydy Stations.csv:stä!\n"
                        f"Haettu arvo: {start_position}\n"
                        f"Mahdolliset asemat: {stations_df['Number'].unique()}\n"
                        f"DataFrame: {filtered_start.to_string(index=False)}\n"
                        f"Tarkista tiedosto: Stations.csv ja käsittelyohjelmat."
                    )
                    print(msg)
                    raise RuntimeError(msg)
                try:
                    current_station_info = filtered_current.iloc[0]
                    start_station_info = filtered_start.iloc[0]
                    transporter_info = transporters_df[transporters_df['Transporter_id'] == transporter_id].iloc[0]
                except IndexError:
                    msg = (
                        f"VIRHE: Aseman ({current_location}) tai alkupaikan ({start_position}) tietoja ei löydy Stations.csv:stä!\n"
                        f"Haetut arvot: current_location={current_location}, start_position={start_position}\n"
                        f"Mahdolliset asemat: {stations_df['Number'].unique()}\n"
                        f"Tarkista tiedosto: Stations.csv ja käsittelyohjelmat."
                    )
                    print(msg)
                    raise RuntimeError(msg)

                try:
                    transfer_duration = int(round(calculate_physics_transfer_time(current_station_info, start_station_info, transporter_info)))
                except:
                    transfer_duration = 10  # Oletusaika jos fysiikkalaskenta epäonnistuu

                return_start_time = transporter_final_times[transporter_id]
                return_end_time = return_start_time + transfer_duration

                # Lisää Phase 1: Siirto alkupaikkaan
                movements.append({
                    'Transporter': transporter_id,
                    'Batch': 0,  # Ei liity mihinkään erään
                    'Phase': 1,
                    'Start_Time': return_start_time,
                    'End_Time': return_end_time,
                    'From_Station': current_location,
                    'To_Station': start_position,
                    'Description': 'Move to lifting station'
                })
                # Lisää Phase 0: Odotus alkupaikassa simuloinnin loppuun
                movements.append({
                    'Transporter': transporter_id,
                    'Batch': 0,  # Ei liity mihinkään erään
                    'Phase': 0,
                    'Start_Time': return_end_time,
                    'End_Time': max(global_final_time, return_end_time),  # Varmista ettei mene negatiiviseksi
                    'From_Station': start_position,
                    'To_Station': start_position,
                    'Description': 'Idle'
                })
            else:
                # Nostin on jo alkupaikassa, lisää vain Phase 0 odotus
                movements.append({
                    'Transporter': transporter_id,
                    'Batch': 0,  # Ei liity mihinkään erään
                    'Phase': 0,
                    'Start_Time': transporter_final_times[transporter_id],
                    'End_Time': max(global_final_time, transporter_final_times[transporter_id]),  # Varmista ettei mene negatiiviseksi
                    'From_Station': start_position,
                    'To_Station': start_position,
                    'Description': 'Idle'
                })
    
    # Tallenna DataFrame (lisätään väistö selkeästi määritellyin ehdoin)
    movements_df = pd.DataFrame(movements)

    # Väistöehdot ja injektointi:
    # - Toteuta vain movement-tasolla, ei tehtäville
    # - Ehto: Nostin on Idle-tilassa JA idlen asema on yhteisalueella
    #   Yhteisalue = [T2.Min_Lift_Station .. T1.Max_Sink_Station] (esim. 112..115)
    # - Väistökohde: T1 → lähin asema < yhteisalueen min (mieluiten common_min-1),
    #                T2 → lähin asema > yhteisalueen max (mieluiten common_max+1)
    # - Ajoitus: Alkuperäinen Idle loppuu nyt (idlen alkuhetki), siihen Avoid (Phase=1),
    #            sitten uusi Idle alkaa Avoidin lopusta ja päättyy alkuperäisen idlen loppuun.
    # - Päivitä seuraavan siirron lähtöasema kohdeasemaksi, jos se alkaa heti idlen jälkeen.

    # Selvitä yhteisalue rajat transporters.csv:stä
    t1_row = transporters_df[transporters_df['Transporter_id'] == 1].iloc[0]
    t2_row = transporters_df[transporters_df['Transporter_id'] == 2].iloc[0]
    common_min = int(t2_row['Min_Lift_Station'])
    common_max = int(t1_row['Max_Sink_Station'])

    # Lista kaikista asemista – haetaan robustisti seuraava kelvollinen asema oman alueen puolelta
    station_numbers = sorted(stations_df['Number'].astype(int).unique().tolist())

    MIN_IDLE_FOR_AVOID = 65  # sekuntia
    avoid_inserts = []
    updates = []  # (index, new_start, new_from_to)
    # Ryhmittele per nostin ja käy Idle-rivit
    for transporter_id, g in movements_df.sort_values(['Transporter', 'Start_Time', 'Phase']).groupby('Transporter'):
        g = g.reset_index()
        for i, r in g.iterrows():
            if r['Description'] != 'Idle':
                continue
            idle_start = int(r['Start_Time'])
            idle_end = int(r['End_Time'])
            if idle_end <= idle_start:
                continue
            idle_station = int(r['From_Station'])
            idle_duration = idle_end - idle_start
            # Lisäehto: alkuperäisen idlen pituus > 65s
            if idle_duration <= MIN_IDLE_FOR_AVOID:
                continue
            # Ehto: onko idlen asema yhteisalueella
            if not (common_min <= idle_station <= common_max):
                continue

            # Valitse väistökohde oman puolen lähimpään asemaan yhteisalueen ulkopuolelle
            if int(transporter_id) == 1:
                # T1 menee vasemmalle (pienempään kuin common_min)
                candidates = [s for s in station_numbers if s < common_min]
                target_station = max(candidates) if candidates else int(t1_row['Min_Lift_Station'])
            else:
                # T2 menee oikealle (suurempaan kuin common_max)
                candidates = [s for s in station_numbers if s > common_max]
                t2_fallback = int(t2_row['Max_Sink_Station']) if 'Max_Sink_Station' in t2_row else max(station_numbers)
                target_station = min(candidates) if candidates else t2_fallback

            # Laske väistön kesto fysiikalla
            cur_info = stations_df[stations_df['Number'] == idle_station].iloc[0]
            tgt_info = stations_df[stations_df['Number'] == target_station].iloc[0]
            transp_info = transporters_df[transporters_df['Transporter_id'] == int(transporter_id)].iloc[0]
            try:
                avoid_dur = int(round(calculate_physics_transfer_time(cur_info, tgt_info, transp_info)))
            except Exception:
                avoid_dur = abs(target_station - idle_station)
            avoid_dur = max(1, avoid_dur)
            avoid_start = idle_start
            avoid_end = min(idle_end, avoid_start + avoid_dur)
            if avoid_end <= avoid_start:
                continue

            # Päivitä alkuperäinen idle alkamaan väistön lopusta ja jäämään kohdeasemalle
            updates.append((r['index'], avoid_end, target_station))

            # Luo väistörivi (phase 1)
            avoid_inserts.append({
                'Transporter': int(transporter_id),
                'Batch': int(r['Batch']),
                'Phase': 1,
                'Start_Time': avoid_start,
                'End_Time': avoid_end,
                'From_Station': idle_station,
                'To_Station': target_station,
                'Description': 'Avoid'
            })

            # Päivitä seuraavan liikkeen lähtöasema, jos se alkaa heti idlen perään (alkuperäinen idle_end)
            # Etsitään rivit, joilla Start_Time == idle_end ja sama Transporter
            mask_next = (movements_df['Transporter'] == transporter_id) & (movements_df['Start_Time'] == idle_end)
            if mask_next.any():
                idxs = movements_df[mask_next].index
                for j in idxs:
                    if movements_df.at[j, 'Description'] == 'Move to lifting station':
                        movements_df.at[j, 'From_Station'] = target_station

    # Kirjoita idle-päivitykset
    for idx, new_start, new_station in updates:
        movements_df.at[idx, 'Start_Time'] = new_start
        movements_df.at[idx, 'From_Station'] = new_station
        movements_df.at[idx, 'To_Station'] = new_station

    # Lisää väistörivit
    if avoid_inserts:
        movements_df = pd.concat([movements_df, pd.DataFrame(avoid_inserts)], ignore_index=True)

    # Järjestys: samassa ajassa piirrä Avoid ennen Idleä
    def order_value(desc, phase):
        if isinstance(desc, str) and str(desc).lower().startswith('avoid'):
            return -1
        return int(phase)

    movements_df['__order'] = movements_df.apply(lambda r: order_value(r['Description'], r['Phase']), axis=1)
    movements_df = movements_df.sort_values(['Transporter', 'Start_Time', '__order', 'Phase']).reset_index(drop=True)

    # Puhdista päällekkäisyydet per nostin varmuuden vuoksi
    fixed_rows = []
    for t_id, g in movements_df.groupby('Transporter', sort=False):
        prev_end = None
        for _, r in g.iterrows():
            s, e = int(r['Start_Time']), int(r['End_Time'])
            if prev_end is not None and s < prev_end:
                s = prev_end
            if e < s:
                e = s
            r['Start_Time'] = s
            r['End_Time'] = e
            fixed_rows.append(r)
            prev_end = e
    movements_df = pd.DataFrame(fixed_rows)
    movements_df = movements_df.drop(columns=['__order'])

    # Lisää loppusiirrot alkupaikkaan väistöjen jälkeen: määritä kunkin nostimen nykyinen sijainti viimeisestä rivistä
    final_moves = []
    if not movements_df.empty:
        global_final_time = int(movements_df['End_Time'].max())
    else:
        global_final_time = 0

    for t_id, g in movements_df.groupby('Transporter'):
        g = g.sort_values(['End_Time'])
        current_location = int(g.iloc[-1]['To_Station'])
        start_position = int(transporter_start_positions[int(t_id)])
        if current_location == start_position:
            # Odotus alkupaikassa simuloinnin loppuun
            final_moves.append({
                'Transporter': int(t_id), 'Batch': 0, 'Phase': 0,
                'Start_Time': int(g.iloc[-1]['End_Time']), 'End_Time': global_final_time,
                'From_Station': start_position, 'To_Station': start_position, 'Description': 'Idle'
            })
        else:
            # Siirto alkupaikkaan + odotus
            cur_info = stations_df[stations_df['Number'] == current_location].iloc[0]
            start_info = stations_df[stations_df['Number'] == start_position].iloc[0]
            transp_info = transporters_df[transporters_df['Transporter_id'] == int(t_id)].iloc[0]
            try:
                back_dur = int(round(calculate_physics_transfer_time(cur_info, start_info, transp_info)))
            except Exception:
                back_dur = abs(start_position - current_location)
            ret_start = int(g.iloc[-1]['End_Time'])
            ret_end = ret_start + max(back_dur, 0)
            final_moves.extend([
                {
                    'Transporter': int(t_id), 'Batch': 0, 'Phase': 1,
                    'Start_Time': ret_start, 'End_Time': ret_end,
                    'From_Station': current_location, 'To_Station': start_position,
                    'Description': 'Move to lifting station'
                },
                {
                    'Transporter': int(t_id), 'Batch': 0, 'Phase': 0,
                    'Start_Time': ret_end, 'End_Time': max(global_final_time, ret_end),
                    'From_Station': start_position, 'To_Station': start_position,
                    'Description': 'Idle'
                }
            ])

    if final_moves:
        movements_df = pd.concat([movements_df, pd.DataFrame(final_moves)], ignore_index=True)

    # Lopullinen järjestys ja Movement_ID:t
    movements_df['__order'] = movements_df.apply(lambda r: order_value(r['Description'], r['Phase']), axis=1)
    movements_df = movements_df.sort_values(['Transporter', 'Start_Time', '__order', 'Phase']).reset_index(drop=True)
    movements_df = movements_df.drop(columns=['__order'])
    movements_df['Movement_ID'] = range(1, len(movements_df) + 1)

    output_file = os.path.join(logs_dir, "transporters_movement.csv")
    movements_df.to_csv(output_file, index=False)

    logger.log("STEP", "STEP 8.7 COMPLETED: CREATE DETAILED TRANSPORTER MOVEMENTS")

    return movements_df

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "movements":
            output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
            create_detailed_movements(output_dir)
        else:
            output_dir = sys.argv[1]
            extract_transporter_tasks(output_dir)
    else:
        output_dir = "output"
        extract_transporter_tasks(output_dir)
