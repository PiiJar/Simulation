import pandas as pd
import os
from simulation_logger import get_logger
from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time

def resolve_station_conflicts(output_dir="output"):
    """Korjaa asemakonflitit järjestämällä tehtäviä uudelleen"""
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    file_in = os.path.join(output_dir, "Logs", "transporter_tasks_ordered.csv")
    if not os.path.exists(file_in):
        logger.log_error(f"transporter_tasks_ordered.csv ei löydy: {file_in}")
        raise FileNotFoundError(f"transporter_tasks_ordered.csv ei löydy: {file_in}")
    df = pd.read_csv(file_in)
    # Pakota kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
        if col in df.columns:
            df[col] = df[col].astype(int)
    for col in ["Lift_time", "Sink_time"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: int(round(x)))
    
    # ⭐ KRIITTINEN: ÄLÄ järjestä uudelleen! Säilytä nostinkohtainen aikajärjestys!
    # Alkuperäinen koodi: df = df.sort_values("Lift_time").reset_index(drop=True)
    # Tämä rikkoo nostinkohtaisen aikajärjestyksen ja aiheuttaa timeline-paradokseja!
    # ⭐ KORJATTU: Peräkkäisten rivien vaihto VAIN saman nostimen tehtävien välillä
    # Vaihto tehdään vain jos kaikki ehdot täyttyvät:
    # 1) SAMA NOSTIN (uusi ehto!)
    # 2) eri erät 
    # 3) edellisen laskuasema = seuraavan nostoasema
    # 4) edellisen laskuaika <= seuraavan nostoaika
    resolved = df.copy()
    i = 0
    while i < len(resolved) - 1:
        row_a = resolved.iloc[i]
        row_b = resolved.iloc[i+1]
        if (
            row_a["Transporter_id"] == row_b["Transporter_id"]  # ⭐ UUSI: Sama nostin!
            and row_a["Batch"] != row_b["Batch"]
            and row_a["Sink_stat"] == row_b["Lift_stat"]
            and row_a["Sink_time"] <= row_b["Lift_time"]
        ):
            resolved.iloc[i], resolved.iloc[i+1] = row_b, row_a
            if i > 0:
                i -= 1
            else:
                i += 1
        else:
            i += 1
    # Pakota vielä ennen tallennusta kaikki ohjelma-, vaihe-, asema- ja aikakentät kokonaisluvuiksi sekuntitarkkuudella
    for col in ["Batch", "Treatment_program", "Stage", "Lift_stat", "Sink_stat"]:
        if col in resolved.columns:
            resolved[col] = resolved[col].astype(int)
    for col in ["Lift_time", "Sink_time"]:
        if col in resolved.columns:
            resolved[col] = resolved[col].apply(lambda x: int(round(x)))

    # --- Lasketaan Phase_1, Phase_2, Phase_3, Phase_4 ---
    # Lue asema- ja nostintiedot
    stations_file = os.path.join(output_dir, "Initialization", "Stations.csv")
    transporters_file = os.path.join(output_dir, "Initialization", "Transporters.csv")
    stations_df = pd.read_csv(stations_file)
    if 'Number' in stations_df.columns:
        stations_df['Number'] = stations_df['Number'].astype(int)
    station_x = dict(zip(stations_df['Number'], stations_df['X Position']))
    transp_df = pd.read_csv(transporters_file)
    transp = transp_df.iloc[0]
    max_speed = float(transp.get('Max_speed (mm/s)', 1000))
    acc_time = float(transp.get('Acceleration_time (s)', 1.0))
    dec_time = float(transp.get('Deceleration_time (s)', 1.0))

    # --- Fysiikkapohjaiset pystysuunnan laskentafunktiot ---


    n = len(resolved)
    resolved['Phase_1'] = 0.0
    resolved['Phase_2'] = 0.0
    resolved['Phase_3'] = 0.0
    resolved['Phase_4'] = 0.0
    # Varmista, että sarakkeet ovat float-tyyppisiä ennen laskentaa
    for col in ['Phase_1', 'Phase_2', 'Phase_3', 'Phase_4']:
        resolved[col] = resolved[col].astype(float)

    for i in range(n):
        # Phase_1: edellisen laskuasemalta nykyisen nostoasemalle (eka rivi 0)
        if i == 0:
            resolved.at[i, 'Phase_1'] = 0.0
        else:
            prev_sink = resolved.at[i-1, 'Sink_stat']
            curr_lift = resolved.at[i, 'Lift_stat']
            prev_sink_row = stations_df[stations_df['Number'] == int(prev_sink)].iloc[0]
            curr_lift_row = stations_df[stations_df['Number'] == int(curr_lift)].iloc[0]
            phase1 = round(calculate_physics_transfer_time(prev_sink_row, curr_lift_row, transp), 2)
            resolved.at[i, 'Phase_1'] = phase1
        # Phase_2: nostoasema (nosto ylös, pystysuunta, fysiikkalaskenta)
        curr_lift = resolved.at[i, 'Lift_stat']
        curr_lift_row = stations_df[stations_df['Number'] == int(curr_lift)].iloc[0]
        phase2 = round(calculate_lift_time(curr_lift_row, transp), 2)
        resolved.at[i, 'Phase_2'] = phase2
        # Phase_3: nostoasemalta laskuasemalle (siirto)
        curr_sink = resolved.at[i, 'Sink_stat']
        curr_sink_row = stations_df[stations_df['Number'] == int(curr_sink)].iloc[0]
        phase3 = round(calculate_physics_transfer_time(curr_lift_row, curr_sink_row, transp), 2)
        resolved.at[i, 'Phase_3'] = phase3
        # Testitulostus kolmelle ensimmäiselle riville
        if i < 3:
            pass  # Poistettu debug-print
        # Phase_4: laskuasema (lasku alas, pystysuunta, fysiikkalaskenta)
        phase4 = round(calculate_sink_time(curr_sink_row, transp), 2)
        resolved.at[i, 'Phase_4'] = phase4

    # Tallennetaan CSV: float_formatilla
    os.makedirs(output_dir, exist_ok=True)
    logs_dir = os.path.join(output_dir, "Logs")
    os.makedirs(logs_dir, exist_ok=True)
    resolved_file = os.path.join(logs_dir, "transporter_tasks_resolved.csv")
    resolved.to_csv(resolved_file, index=False, float_format='%.2f')
    return resolved

    os.makedirs(output_dir, exist_ok=True)
    logs_dir = os.path.join(output_dir, "Logs")
    os.makedirs(logs_dir, exist_ok=True)
    resolved_file = os.path.join(logs_dir, "transporter_tasks_resolved.csv")
    resolved.to_csv(resolved_file, index=False)
    return resolved

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    from simulation_logger import init_logger
    init_logger(output_dir)
    resolve_station_conflicts(output_dir)
