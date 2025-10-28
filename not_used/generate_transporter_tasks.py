import pandas as pd
import os

def generate_transporter_tasks(output_dir):
    # Oletetaan, että tarvittavat tiedot on luettu DataFrameen df
    # df:ssä sarakkeet: Batch, Stage, Lift_stat, Sink_stat, Phase_1, Phase_2, Phase_3, Phase_4, Lift_time
    # Tässä esimerkissä lasketaan Sink_time kaavalla: Lift_time + Phase_2 + Phase_3 + Phase_4
    tasks_file = os.path.join(output_dir, "Logs", "transporter_tasks_raw.csv")
    df = pd.read_csv(tasks_file)
    if not all(col in df.columns for col in ["Lift_time", "Phase_2", "Phase_3", "Phase_4"]):
        raise ValueError("Puuttuvia sarakkeita: Lift_time, Phase_2, Phase_3, Phase_4")
    df["Sink_time"] = df["Lift_time"] + df["Phase_2"] + df["Phase_3"] + df["Phase_4"]
    # Tallennus (jos halutaan)
    df.to_csv(tasks_file, index=False)
    return df

def create_transporter_tasks_final(output_dir):
    """
    Luo lopulliset nostintehtävät optimoiduista tehtävistä ja lopullisesta matriisista.
    Käyttää AINA transporter_tasks_optimized.csv jos se on olemassa.
    """
    # Lue optimoidut nostintehtävät ja lopullinen matriisi
    logs_dir = os.path.join(output_dir, "logs")
    
    # Kokeile ensin optimoituja tehtäviä
    optimized_file = os.path.join(logs_dir, "transporter_tasks_optimized.csv")
    stretched_file = os.path.join(logs_dir, "transporter_tasks_stretched.csv")
    
    # Valitse paras saatavilla oleva nostintehtävätiedosto
    if os.path.exists(optimized_file):
        transporter_file = optimized_file
        source_type = "optimized"
    elif os.path.exists(stretched_file):
        transporter_file = stretched_file
        source_type = "stretched"
    else:
        from datetime import datetime
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: Ei löydy optimoituja eikä venytettyjä nostintehtäviä")
        print("Pipeline keskeytetään. Varmista, että vaihe stretch_hoist_tasks on ajettu ennen tätä.")
        raise FileNotFoundError(f"Nostintehtävätiedostoja ei löydy: {optimized_file} tai {stretched_file}")
    
    matrix_file = os.path.join(logs_dir, "line_matrix_stretched.csv")
    final_file = os.path.join(logs_dir, "transporter_tasks_final.csv")
    
    # Tarkista, että line_matrix_stretched.csv on olemassa
    if not os.path.exists(matrix_file):
        from datetime import datetime
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: line_matrix_stretched.csv puuttuu polusta: {matrix_file}")
        print("Pipeline keskeytetään. Varmista, että vaihe generate_matrix_stretched on ajettu ennen tätä.")
        raise FileNotFoundError(f"line_matrix_stretched.csv puuttuu polusta: {matrix_file}")
    
    df_transporter = pd.read_csv(transporter_file)
    df_matrix = pd.read_csv(matrix_file)
    
    # Oletetaan, että df_transporter: Batch, Treatment_program, Stage, Lift_stat, Sink_stat, ...
    # df_matrix: Batch, Stage, Station, EntryTime, ExitTime, ...
    lift_times = []
    sink_times = []
    for idx, row in df_transporter.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        lift_stat = row["Lift_stat"]
        sink_stat = row["Sink_stat"]
        # Lift_time: line_matrix_stretched ExitTime, jossa sama Batch, Stage, Station=Lift_stat
        lift_match = df_matrix[(df_matrix["Batch"] == batch) & (df_matrix["Stage"] == stage) & (df_matrix["Station"] == lift_stat)]
        if not lift_match.empty:
            lift_time = lift_match.iloc[0]["ExitTime"]
        else:
            lift_time = None
        # Sink_time: line_matrix_stretched EntryTime, jossa sama Batch, Stage+1, Station=Sink_stat
        sink_match = df_matrix[(df_matrix["Batch"] == batch) & (df_matrix["Stage"] == stage+1) & (df_matrix["Station"] == sink_stat)]
        if not sink_match.empty:
            sink_time = sink_match.iloc[0]["EntryTime"]
        else:
            sink_time = None
        lift_times.append(lift_time)
        sink_times.append(sink_time)
    df_transporter["Lift_time"] = lift_times
    df_transporter["Sink_time"] = sink_times
    df_transporter.to_csv(final_file, index=False)
    return final_file

# Esimerkkikäyttö:
# generate_transporter_tasks("output")
# create_transporter_tasks_final("output")
