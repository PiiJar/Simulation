# Tämä tiedosto on uudelleennimetty generate_transporter_tasks.py → generate_tasks.py
# Sisältö siirretty sellaisenaan, jatka kehitystä tämän tiedoston pohjalta.

import pandas as pd
import os
from simulation_logger import get_logger

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

    # Jos mikään nostin ei pysty, keskeytä simulaatio yhdellä selkeällä virheilmoituksella
    raise RuntimeError(f"[ERROR] Nostintehtävälle ei löytynyt sopivaa nostinta! Nostoasema: {lift_station}, laskuasema: {sink_station}, nostoasema X: {lift_x}, laskuasema X: {sink_x}")

def generate_tasks(output_dir):
    """Luo kuljetintehtävät line_matrix_original.csv:n perusteella"""
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Call init_logger(output_dir) before using generate_tasks.")
    # STEP-tyyppinen aloitusviesti terminaaliin ja lokiin
    logger.log("STEP", "STEP 5 STARTED: GENERATE TASKS")
    matrix_file = os.path.join(output_dir, "logs", "line_matrix_original.csv")
    if not os.path.exists(matrix_file):
        logger.log_error(f"line_matrix_original.csv ei löydy: {matrix_file}")
        raise FileNotFoundError(f"line_matrix_original.csv ei löydy: {matrix_file}")
    
    # Lataa asema- ja nostintiedot nostinvalintaa varten
    stations_file = os.path.join(output_dir, "Initialization", "Stations.csv")
    transporters_file = os.path.join(output_dir, "Initialization", "Transporters.csv")
    if not os.path.exists(stations_file):
        raise FileNotFoundError(f"Stations.csv ei löydy: {stations_file}")
    if not os.path.exists(transporters_file):
        raise FileNotFoundError(f"Transporters.csv ei löydy: {transporters_file}")
    
    stations_df = pd.read_csv(stations_file)
    transporters_df = pd.read_csv(transporters_file)
    
    try:
        df = pd.read_csv(matrix_file)
        df = df.sort_values(["Batch", "Stage"]).reset_index(drop=True)
        tasks = []
        # Lue Production.csv start-asemat
        production_file = os.path.join(os.path.dirname(matrix_file), "..", "Initialization", "Production.csv")
        production_df = pd.read_csv(production_file)
        production_df["Batch"] = production_df["Batch"].astype(int)
        production_df["Treatment_program"] = production_df["Treatment_program"].astype(int)
        batch_start_station = {
            (row["Batch"], row["Treatment_program"]): int(row["Start_station"])
            for _, row in production_df.iterrows()
        }

        # --- Lisää aloitussiirto jokaiselle batchille ---
        # Etsi kaikki uniikit (Batch, Treatment_program)
        for key in batch_start_station.keys():
            batch, program = key
            # Etsi stage 1 rivi tälle batchille ja ohjelmalle
            stage1_row = df[(df["Batch"] == batch) & (df["Treatment_program"] == program) & (df["Stage"] == 1)]
            if not stage1_row.empty:
                stage1_row = stage1_row.iloc[0]
                start_station = batch_start_station[key]
                stage1_station = int(stage1_row["Station"])
                # Valitse oikea nostin tälle tehtävälle
                transporter = select_capable_transporter(
                    start_station,           # lift_station = Production Start_station
                    stage1_station,          # sink_station = Stage 1 asema
                    stations_df, 
                    transporters_df
                )
                # Hae start_time Productionista
                start_time = None
                if "Start_time" in production_df.columns:
                    # Oletetaan muoto HH:MM:SS
                    try:
                        start_time = pd.to_timedelta(production_df[(production_df["Batch"] == batch) & (production_df["Treatment_program"] == program)]["Start_time"].iloc[0]).total_seconds()
                    except Exception:
                        start_time = None
                if start_time is None and "Start_time_seconds" in production_df.columns:
                    start_time = float(production_df[(production_df["Batch"] == batch) & (production_df["Treatment_program"] == program)]["Start_time_seconds"].iloc[0])
                # Jos ei löydy, käytä stage 1 EntryTime
                if start_time is None:
                    start_time = float(stage1_row["EntryTime"])
                tasks.append({
                    "Transporter_id": int(transporter['Transporter_id']),
                    "Batch": int(batch),
                    "Treatment_program": int(program),
                    "Stage": 0,
                    "Lift_stat": start_station,
                    "Lift_time": start_time,
                    "Sink_stat": stage1_station,
                    "Sink_time": float(stage1_row["EntryTime"])
                })

        for idx, row in df.iterrows():
            # Jos stage=0, luo nostintehtävä Production.csv Start_station → Stage 1 asemalle
            if int(row["Stage"]) == 0:
                # Etsi Stage 1 rivi samalle erälle
                stage1_row = df[(df["Batch"] == row["Batch"]) & 
                               (df["Treatment_program"] == row["Treatment_program"]) & 
                               (df["Stage"] == 1)]
                
                if not stage1_row.empty:
                    stage1_row = stage1_row.iloc[0]
                    key = (int(row["Batch"]), int(row["Treatment_program"]))
                    
                    if key in batch_start_station:
                        # NOSTINTEHTÄVÄ: Production Start_station → Stage 1 asema
                        start_station = batch_start_station[key]  # Production.csv Start_station (104)
                        stage1_station = int(stage1_row["Station"])  # Stage 1 asema (107)
                        
                        # Valitse oikea nostin tälle tehtävälle
                        transporter = select_capable_transporter(
                            start_station,           # lift_station = Production Start_station
                            stage1_station,          # sink_station = Stage 1 asema
                            stations_df, 
                            transporters_df
                        )
                        
                        tasks.append({
                            "Transporter_id": int(transporter['Transporter_id']),
                            "Batch": int(row["Batch"]),
                            "Treatment_program": int(row["Treatment_program"]),
                            "Stage": 0,
                            "Lift_stat": start_station,              # Production Start_station
                            "Lift_time": float(row["ExitTime"]),     # Stage 0 ExitTime
                            "Sink_stat": stage1_station,            # Stage 1 asema
                            "Sink_time": float(stage1_row["EntryTime"])  # Stage 1 EntryTime
                        })
                continue
            # Ohita, jos seuraava rivi puuttuu, on eri batchia tai on stage = 0
            if idx + 1 >= len(df):
                continue
            next_row = df.iloc[idx + 1]
            if int(next_row["Stage"]) == 0:
                continue
            if row["Batch"] != next_row["Batch"]:
                continue
            
            # Valitse oikea nostin tälle tehtävälle (current_station -> next_station)
            transporter = select_capable_transporter(
                int(row["Station"]),           # lift_station = current_station  
                int(next_row["Station"]),      # sink_station = next_station
                stations_df, 
                transporters_df
            )
            tasks.append({
                "Transporter_id": int(transporter['Transporter_id']),  # Dynaaminen nostinvalinta
                "Batch": int(row["Batch"]),
                "Treatment_program": int(row["Treatment_program"]),
                "Stage": int(row["Stage"]),
                "Lift_stat": int(row["Station"]),
                "Lift_time": float(row["ExitTime"]),
                "Sink_stat": int(next_row["Station"]),
                "Sink_time": float(next_row["EntryTime"])
            })
        # Poista viimeinen tehtävä jokaisesta batchista (koska sillä ei ole seuraavaa vaihetta)
        tasks = [t for t in tasks if t["Sink_stat"] is not None]
        tasks_df = pd.DataFrame(tasks)
        
        # Järjestä sarakkeet niin että Transporter_id on ensimmäinen
        if "Transporter_id" in tasks_df.columns:
            columns = ["Transporter_id"] + [col for col in tasks_df.columns if col != "Transporter_id"]
            tasks_df = tasks_df[columns]
            
        # Suodata pois kaikki stage = 0 rivit, paitsi jos kyseessä on alkusiirto (nostoasema = Start_station ja laskuasema = askel 1 asema)
        def is_valid_stage0(row):
            if row["Stage"] != 0:
                return True
            key = (row["Batch"], row["Treatment_program"])
            # Etsi askel 1 asema samalle batchille ja ohjelmalle
            step1_row = df[(df["Batch"] == row["Batch"]) & (df["Treatment_program"] == row["Treatment_program"]) & (df["Stage"] == 1)]
            if (
                key in batch_start_station
                and int(row["Lift_stat"]) == batch_start_station[key]
                and not step1_row.empty
                and int(row["Sink_stat"]) == int(step1_row.iloc[0]["Station"])
            ):
                return True
            return False
        tasks_df = tasks_df[tasks_df.apply(is_valid_stage0, axis=1)].reset_index(drop=True)
        # Pakota kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
        for col in ["Transporter_id", "Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
            if col in tasks_df.columns:
                tasks_df[col] = tasks_df[col].astype(int)
        for col in ["Lift_time", "Sink_time"]:
            if col in tasks_df.columns:
                tasks_df[col] = tasks_df[col].apply(lambda x: int(round(x)))
    except Exception as e:
        logger = get_logger()
        logger.log_error(f"Kuljetintehtävien generointi epäonnistui: {e}")
        raise
    
    os.makedirs(output_dir, exist_ok=True)
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    raw_file = os.path.join(logs_dir, "transporter_tasks_raw.csv")
    # Pakota vielä ennen tallennusta kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Transporter_id", "Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
        if col in tasks_df.columns:
            tasks_df[col] = tasks_df[col].astype(int)
    for col in ["Lift_time", "Sink_time"]:
        if col in tasks_df.columns:
            tasks_df[col] = tasks_df[col].apply(lambda x: int(round(x)))
    tasks_df.to_csv(raw_file, index=False)
    
    # ⭐ KRIITTINEN KORJAUS: Järjestetään tehtävät NOSTINKOHTAISESTI aikajärjestykseen!
    ordered_df = tasks_df.sort_values(["Transporter_id", "Lift_time"]).reset_index(drop=True)
    # SÄILYTÄ Stage 0 tehtävät järjestetyssä listassa - ne ovat valideja Production Start_station → Stage 1 tehtäviä
    for col in ["Transporter_id", "Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
        if col in ordered_df.columns:
            ordered_df[col] = ordered_df[col].astype(int)
    for col in ["Lift_time", "Sink_time"]:
        if col in ordered_df.columns:
            ordered_df[col] = ordered_df[col].apply(lambda x: int(round(x)))
    ordered_file = os.path.join(logs_dir, "transporter_tasks_ordered.csv")
    ordered_df.to_csv(ordered_file, index=False)
    # STEP-tyyppinen lopetusviesti terminaaliin ja lokiin
    logger.log("STEP", "STEP 5 COMPLETED: GENERATE TASKS")
    return tasks_df, ordered_df
