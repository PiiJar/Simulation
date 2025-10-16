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

    # Jos mikään nostin ei pysty, tulosta virheilmoitus ja keskeytä simulaatio
    print(f"[ERROR] Nostintehtävälle ei löytynyt sopivaa nostinta! Nostoasema: {lift_station}, laskuasema: {sink_station}, nostoasema X: {lift_x}, laskuasema X: {sink_x}")
    raise RuntimeError(f"Nostintehtävälle ei löytynyt sopivaa nostinta! Nostoasema: {lift_station}, laskuasema: {sink_station}, nostoasema X: {lift_x}, laskuasema X: {sink_x}")

def extract_transporter_tasks(output_dir):
    """
    Lukee venytetyn matriisin ja muodostaa nostintehtävälistan fysiikka-aikojen kanssa.
    
    Otsikkorivi: Transporter, Batch, Start_Time, Lift_Stat, Sink_stat, 
                 Phase_0_start, Phase_1_start, Phase_2_start, Phase_3_start, Phase_4_stop
    """
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Call init_logger(output_dir) before using extract_transporter_tasks.")
    
    logger.log("STEP", "STEP 8.6 STARTED: EXTRACT TRANSPORTER TASKS FROM STRETCHED MATRIX")
    
    logs_dir = os.path.join(output_dir, "logs")
    matrix_file = os.path.join(logs_dir, "line_matrix_stretched.csv")
    
    if not os.path.exists(matrix_file):
        logger.log_error(f"line_matrix_stretched.csv ei löydy: {matrix_file}")
        raise FileNotFoundError(f"line_matrix_stretched.csv ei löydy: {matrix_file}")
    
    # Lataa asema- ja nostintiedot nostinvalintaa varten
    stations_file = os.path.join(output_dir, "Initialization", "Stations.csv")
    transporters_file = os.path.join(output_dir, "Initialization", "Transporters.csv")
    production_file = os.path.join(output_dir, "Initialization", "Production.csv")
    
    if not os.path.exists(stations_file):
        raise FileNotFoundError(f"Stations.csv ei löydy: {stations_file}")
    if not os.path.exists(transporters_file):
        raise FileNotFoundError(f"Transporters.csv ei löydy: {transporters_file}")
    if not os.path.exists(production_file):
        raise FileNotFoundError(f"Production.csv ei löydy: {production_file}")
    
    stations_df = pd.read_csv(stations_file)
    transporters_df = pd.read_csv(transporters_file)
    production_df = pd.read_csv(production_file)
    
    # Luo batch-treatment_program -> start_station mapping
    production_df["Batch"] = production_df["Batch"].astype(int)
    production_df["Treatment_program"] = production_df["Treatment_program"].astype(int)
    batch_start_station = {
        (row["Batch"], row["Treatment_program"]): int(row["Start_station"])
        for _, row in production_df.iterrows()
    }
    
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
                        # Onko tämä Production.csv:n start_station ja onko laskuasema käsittelyohjelman askel 1 asema?
                        key = (int(row["Batch"]), int(row["Treatment_program"]))
                        # Etsi askel 1 asema samalle batchille ja ohjelmalle
                        step1_row = df[(df["Batch"] == row["Batch"]) & (df["Treatment_program"] == row["Treatment_program"]) & (df["Stage"] == 1)]
                        if (
                            key in batch_start_station
                            and int(row["Station"]) == batch_start_station[key]
                            and not step1_row.empty
                            and int(next_row["Station"]) == int(step1_row.iloc[0]["Station"])
                        ):
                            # Valitse oikea nostin tälle tehtävälle (start_station -> step1_station)
                            transporter = select_capable_transporter(
                                int(row["Station"]),           # lift_station = start_station
                                int(next_row["Station"]),      # sink_station = step1_station
                                stations_df, 
                                transporters_df
                            )
                            tasks.append({
                                "Transporter": int(transporter['Transporter_id']),
                                "Batch": int(row["Batch"]),
                                "Start_Time": float(row["ExitTime"]),  # Käytä ExitTime, ei EntryTime
                                "Lift_Stat": int(row["Station"]),
                                "Sink_stat": int(next_row["Station"])
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
            
            # Valitse oikea nostin tälle tehtävälle (current_station -> next_station)
            transporter = select_capable_transporter(
                int(row["Station"]),           # lift_station = current_station  
                int(next_row["Station"]),      # sink_station = next_station
                stations_df, 
                transporters_df
            )
            
            tasks.append({
                "Transporter": int(transporter['Transporter_id']),
                "Batch": int(row["Batch"]),
                "Start_Time": float(row["ExitTime"]),  # Käytä ExitTime, ei EntryTime
                "Lift_Stat": int(row["Station"]),
                "Sink_stat": int(next_row["Station"])
            })
        
        # Luo DataFrame
        tasks_df = pd.DataFrame(tasks)
        
        if len(tasks_df) > 0:
            # Järjestä nostinkohtaisesti aikajärjestykseen
            tasks_df = tasks_df.sort_values(["Transporter", "Start_Time"]).reset_index(drop=True)
            
            # Pakota kaikki kentät kokonaisluvuiksi/float:iksi
            for col in ["Transporter", "Batch", "Lift_Stat", "Sink_stat"]:
                if col in tasks_df.columns:
                    tasks_df[col] = tasks_df[col].astype(int)
            if "Start_Time" in tasks_df.columns:
                tasks_df["Start_Time"] = tasks_df["Start_Time"].apply(lambda x: int(round(x)))
            
            # Lisää fysiikka-aikojen laskenta
            
            # Seuraa jokaisen nostimen viimeistä Phase_4_stop aikaa
            transporter_last_stop = {}
            
            # Laske nostimien alkupaikat - PAKOTETUT ARVOT
            transporter_start_positions = {}
            
            # PAKOTETUT ALOITUSPAIKAT:
            transporter_start_positions[1] = 101  # Nostin 1 -> asema 101
            transporter_start_positions[2] = 113  # Nostin 2 -> asema 113  
            transporter_start_positions[3] = 126  # Nostin 3 -> asema 126
            transporter_start_positions[4] = 137  # Nostin 4 -> asema 137
            
            # Lisää Phase-sarakkeet (kokonaislukuina)
            tasks_df["Phase_0_start"] = 0
            tasks_df["Phase_1_start"] = 0  
            tasks_df["Phase_2_start"] = 0
            tasks_df["Phase_3_start"] = 0
            tasks_df["Phase_4_start"] = 0
            tasks_df["Phase_4_stop"] = 0
            
            for idx, row in tasks_df.iterrows():
                transporter_id = row["Transporter"]
                lift_station = row["Lift_Stat"]
                sink_station = row["Sink_stat"]
                arrival_time = row["Start_Time"]  # Tämä on erän ExitTime nostoasemalta
                
                # Hae asematiedot fysiikkalaskentoja varten
                lift_station_info = stations_df[stations_df['Number'] == lift_station].iloc[0]
                sink_station_info = stations_df[stations_df['Number'] == sink_station].iloc[0]
                transporter_info = transporters_df[transporters_df['Transporter_id'] == transporter_id].iloc[0]
                
                # NOSTIMEN TEHTÄVÄN LOGIIKKA:
                # Start_Time = Phase_2_start = erän ExitTime nostoasemalta (LUKITTU)
                # Phase 0 ja 1 lasketaan taaksepäin, Phase 3 ja 4 eteenpäin
                
                # phase_2_start = arrival_time  # Tämä on erän ExitTime = nostimen tehtävän alku
                
                # Laske fysiikka-ajat
                try:
                    # Phase 1: Siirto edellisestä sijainista nostoasemalle
                    if transporter_id in transporter_last_stop:
                        # Etsi edellinen tehtävä samalta nostimelta
                        prev_tasks = tasks_df[(tasks_df["Transporter"] == transporter_id) & (tasks_df.index < idx)]
                        if not prev_tasks.empty:
                            last_sink = prev_tasks.iloc[-1]["Sink_stat"]
                            last_sink_info = stations_df[stations_df['Number'] == last_sink].iloc[0]
                            phase_1_duration = int(round(calculate_physics_transfer_time(last_sink_info, lift_station_info, transporter_info)))
                        else:
                            # Ensimmäinen tehtävä: alkupaikasta nostoasemalle
                            start_position = transporter_start_positions[transporter_id]
                            start_station_info = stations_df[stations_df['Number'] == start_position].iloc[0]
                            phase_1_duration = int(round(calculate_physics_transfer_time(start_station_info, lift_station_info, transporter_info)))
                    else:
                        # Ensimmäinen tehtävä: alkupaikasta nostoasemalle
                        start_position = transporter_start_positions[transporter_id]
                        start_station_info = stations_df[stations_df['Number'] == start_position].iloc[0]
                        phase_1_duration = int(round(calculate_physics_transfer_time(start_station_info, lift_station_info, transporter_info)))
                    
                    # Phase 2: Nostoaika nostoasemalla
                    phase_2_duration = int(round(calculate_lift_time(lift_station_info, transporter_info)))
                    
                    # Phase 3: Siirtoaika nostoasemalta laskuasemalle (kuormalla)
                    phase_3_duration = int(round(calculate_physics_transfer_time(lift_station_info, sink_station_info, transporter_info)))
                    
                    # Phase 4: Laskuaika laskuasemalla
                    phase_4_duration = int(round(calculate_sink_time(sink_station_info, transporter_info)))
                    
                except Exception as e:
                    phase_1_duration = 5  # Siirtoaika
                    phase_2_duration = 5  # Nostoaika
                    phase_3_duration = 5  # Siirtoaika kuormalla
                    phase_4_duration = 5  # Laskuaika
                
                # Laske fysiikka-ajat - LUOTA MATRIISIN LASKENTAAN:
                # Phase_2_start = Start_Time (erän ExitTime) - EHDOTTOMASTI LUKITTU
                # EI TEHDÄ MITÄÄN KORJAUKSIA - jos menee pieleen, vika on matriisin laskennassa
                
                phase_2_start = arrival_time  # LUKITTU - ei korjauksia
                
                # Phase_0_start: Edellisen tehtävän loppu tai alustettu arvo
                if transporter_id in transporter_last_stop:
                    phase_0_start = transporter_last_stop[transporter_id]
                else:
                    phase_0_start = 0
                
                # Phase 1: Siirto edellisestä sijainista nostamisasemalle
                phase_1_start = phase_2_start - phase_1_duration  # Taaksepäin
                phase_3_start = phase_2_start + phase_2_duration  # Eteenpäin  
                phase_4_start = phase_3_start + phase_3_duration  # Eteenpäin
                phase_4_stop = phase_4_start + phase_4_duration   # Eteenpäin
                
                # Tallenna arvot kokonaislukuina
                tasks_df.at[idx, "Phase_0_start"] = int(round(phase_0_start))
                tasks_df.at[idx, "Phase_1_start"] = int(round(phase_1_start))
                tasks_df.at[idx, "Phase_2_start"] = int(round(phase_2_start))  # Lukittu = Start_Time
                tasks_df.at[idx, "Phase_3_start"] = int(round(phase_3_start))
                tasks_df.at[idx, "Phase_4_start"] = int(round(phase_4_start))
                tasks_df.at[idx, "Phase_4_stop"] = int(round(phase_4_stop))
                
                # Päivitä nostimen viimeinen lopetusaika
                transporter_last_stop[transporter_id] = phase_4_stop
        
        # Tallenna
        output_file = os.path.join(logs_dir, "transporter_tasks_from_matrix.csv")
        tasks_df.to_csv(output_file, index=False)
        
        logger.log("STEP", "STEP 8.6 COMPLETED: EXTRACT TRANSPORTER TASKS FROM STRETCHED MATRIX")
        
        return tasks_df
        
    except Exception as e:
        logger.log_error(f"Nostintehtävien erottaminen epäonnistui: {e}")
        raise

def create_detailed_movements(output_dir):
    """
    Muuntaa nostintehtävät realistisiksi liikkeiksi.
    Jokainen tehtävä muuntuu TÄSMÄLLEEN 5 liikkeeksi (Phase 0-4).
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
    
    # Lataa nostintiedot alkupaikkojen määrittämiseksi
    transporters_file = os.path.join(output_dir, "Initialization", "Transporters.csv")
    stations_file = os.path.join(output_dir, "Initialization", "Stations.csv")
    production_file = os.path.join(output_dir, "Initialization", "Production.csv")
    
    transporters_df = pd.read_csv(transporters_file)
    stations_df = pd.read_csv(stations_file)
    production_df = pd.read_csv(production_file)
    
    # Laske nostimien alkupaikat - PAKOTETUT ARVOT
    transporter_start_positions = {}
    
    # PAKOTETUT ALOITUSPAIKAT:
    transporter_start_positions[1] = 101  # Nostin 1 -> asema 101
    transporter_start_positions[2] = 113  # Nostin 2 -> asema 113  
    transporter_start_positions[3] = 126  # Nostin 3 -> asema 126
    transporter_start_positions[4] = 130  # Nostin 4 -> asema 130
    transporter_start_positions[5] = 140  # Nostin 5 -> asema 140
    
    movements = []
    
    # Seuraa nostimien viimeisiä sijainteja Phase 1:tä varten
    transporter_last_location = transporter_start_positions.copy()
    
    # Käsittele tehtävät lineaarisesti
    for _, task in tasks_df.iterrows():
        transporter_id = int(task['Transporter'])
        
        # Phase 1:n lähtöpaikka on nostimen edellinen sijainti
        phase_1_from_station = transporter_last_location[transporter_id]
        
        # Luo täsmälleen 5 liikettä per tehtävä (Phase 0-4)
        # Stop-ajat lasketaan: prev_stop = next_start (paitsi Phase_4_stop)
        movements.extend([
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 0,
                'Start_Time': int(task['Phase_0_start']),
                'End_Time': int(task['Phase_1_start']),  # prev_stop = next_start
                'From_Station': phase_1_from_station,
                'To_Station': phase_1_from_station,
                'Description': 'Odotus/paikoillaan'
            },
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 1,
                'Start_Time': int(task['Phase_1_start']),
                'End_Time': int(task['Phase_2_start']),  # prev_stop = next_start
                'From_Station': phase_1_from_station,
                'To_Station': int(task['Lift_Stat']),
                'Description': 'Siirto nostoasemalle'
            },
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 2,
                'Start_Time': int(task['Phase_2_start']),
                'End_Time': int(task['Phase_3_start']),  # prev_stop = next_start
                'From_Station': int(task['Lift_Stat']),
                'To_Station': int(task['Lift_Stat']),
                'Description': 'Nostaminen'
            },
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 3,
                'Start_Time': int(task['Phase_3_start']),
                'End_Time': int(task['Phase_4_start']),  # prev_stop = next_start
                'From_Station': int(task['Lift_Stat']),
                'To_Station': int(task['Sink_stat']),
                'Description': 'Siirto laskuasemalle'
            },
            {
                'Transporter': transporter_id,
                'Batch': int(task['Batch']),
                'Phase': 4,
                'Start_Time': int(task['Phase_4_start']),
                'End_Time': int(task['Phase_4_stop']),  # Ainoa jolla on erillinen stop-aika
                'From_Station': int(task['Sink_stat']),
                'To_Station': int(task['Sink_stat']),
                'Description': 'Laskeminen'
            }
        ])
        
        # Päivitä nostimen viimeinen sijainti seuraavaa tehtävää varten
        transporter_last_location[transporter_id] = int(task['Sink_stat'])
    
    # Lisää loppusiirrot: nostimet takaisin alkupaikoilleen
    # Etsi jokaisen nostimen viimeisen tehtävän Phase_4_stop
    transporter_final_times = {}
    for transporter_id in transporter_start_positions.keys():
        transporter_tasks = tasks_df[tasks_df['Transporter'] == transporter_id]
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
                current_station_info = stations_df[stations_df['Number'] == current_location].iloc[0]
                start_station_info = stations_df[stations_df['Number'] == start_position].iloc[0]
                transporter_info = transporters_df[transporters_df['Transporter_id'] == transporter_id].iloc[0]
                
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
                    'Description': 'Siirto alkupaikkaan'
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
                    'Description': 'Odotus simuloinnin lopussa'
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
                    'Description': 'Odotus simuloinnin lopussa'
                })
    
    # Tallenna DataFrame
    movements_df = pd.DataFrame(movements)
    
    # Järjestä oikein: Transporter -> Start_Time -> Phase
    movements_df = movements_df.sort_values(['Transporter', 'Start_Time', 'Phase']).reset_index(drop=True)
    
    # Päivitä Movement_ID peräkkäiseksi
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
