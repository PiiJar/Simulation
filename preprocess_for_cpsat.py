import os
import pandas as pd

def preprocess_for_cpsat(output_dir):
    # Alustukset ja importit heti alkuun
    init_dir = os.path.join(output_dir, "initialization")
    from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time
    stations = pd.read_csv(os.path.join(init_dir, "stations.csv"))
    transporters = pd.read_csv(os.path.join(init_dir, "transporters.csv"))
    transporter_row = transporters.iloc[0]

    # Laske kaikki mahdolliset nostintehtävät (nosto + siirto + lasku)
    transfer_task_rows = []
    transfer_rows = []
    for i, from_row in stations.iterrows():
        for j, to_row in stations.iterrows():
            from_station = from_row["Number"]
            to_station = to_row["Number"]
            transfer_time = calculate_physics_transfer_time(from_row, to_row, transporter_row)
            lift_time = calculate_lift_time(from_row, transporter_row)
            sink_time = calculate_sink_time(to_row, transporter_row)
            total_task_time = lift_time + transfer_time + sink_time
            transfer_task_rows.append({
                "from_station": from_station,
                "to_station": to_station,
                "lift_time": lift_time,
                "transfer_time": transfer_time,
                "sink_time": sink_time,
                "total_task_time": total_task_time
            })
            transfer_rows.append({
                "from_station": from_station,
                "to_station": to_station,
                "transfer_time": transfer_time
            })
    transfer_task_df = pd.DataFrame(transfer_task_rows)
    transfer_task_df.to_csv(os.path.join(init_dir, "transfer_tasks.csv"), index=False)
    print(f"[CP-SAT esikäsittely] Tallennettu: {os.path.join(init_dir, 'transfer_tasks.csv')} ({len(transfer_task_df)} riviä)")
    transfer_df = pd.DataFrame(transfer_rows)
    transfer_df.to_csv(os.path.join(init_dir, "transfer_times.csv"), index=False)
    print(f"[CP-SAT esikäsittely] Tallennettu: {os.path.join(init_dir, 'transfer_times.csv')} ({len(transfer_df)} riviä)")
    """
    Yhdistää production, stations, transporters ja treatment_programs tiedot yhdeksi DataFrameksi CP-SAT-optimointia varten.
    Tallentaa tuloksen initialization-hakemistoon.
    """
    init_dir = os.path.join(output_dir, "initialization")
    production = pd.read_csv(os.path.join(init_dir, "production.csv"))
    stations = pd.read_csv(os.path.join(init_dir, "stations.csv"))
    transporters = pd.read_csv(os.path.join(init_dir, "transporters.csv"))

    # Yhdistä kaikki treatment_program tiedostot
    program_files = [f for f in os.listdir(init_dir) if f.startswith("treatment_program_") and f.endswith(".csv")]
    programs = {}
    for fname in program_files:
        prog_id = fname.split("_")[-1].split(".")[0]
        programs[prog_id] = pd.read_csv(os.path.join(init_dir, fname))

    # Luo yhdistetty lista: batch, stage, station, min_time, max_time, start_time
    rows = []
    for _, row in production.iterrows():
        batch = row["Batch"]
        prog_id = str(row["Treatment_program"]).zfill(3)
        start_time = row["Start_time_seconds"] if "Start_time_seconds" in row else 0
        if prog_id not in programs:
            continue
        prog_df = programs[prog_id].copy()
        # Lisää vaihe 0 alkuun, jos sitä ei ole
        if 0 not in prog_df["Stage"].values:
            start_station = row["Start_station"] if "Start_station" in row else prog_df.iloc[0]["MinStat"]
            # Oletus: MinTime=0, MaxTime=100:00:00
            prog_df = pd.concat([
                pd.DataFrame({
                    "Stage": [0],
                    "MinStat": [start_station],
                    "MaxStat": [start_station],
                    "MinTime": ["00:00:00"],
                    "MaxTime": ["100:00:00"]
                }),
                prog_df
            ], ignore_index=True)
        for _, stage_row in prog_df.iterrows():
            stage = stage_row["Stage"]
            min_stat = stage_row["MinStat"]
            max_stat = stage_row["MaxStat"]
            min_time = stage_row["MinTime"]
            max_time = stage_row["MaxTime"]
            # Oletetaan että station = min_stat (laajenna tarvittaessa)
            rows.append({
                "Batch": batch,
                "Stage": stage,
                "Station": min_stat,
                "MinTime": min_time,
                "MaxTime": max_time,
                "StartTime": start_time
            })
    df = pd.DataFrame(rows)
    out_path = os.path.join(init_dir, "cpsat_preprocessed.csv")
    df.to_csv(out_path, index=False)
    print(f"[CP-SAT esikäsittely] Tallennettu: {out_path} ({len(df)} riviä)")
