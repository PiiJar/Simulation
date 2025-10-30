import os
import pandas as pd

def preprocess_for_cpsat(output_dir):
    
    # Read data from initialization and save all preprocessed files to the cp_sat directory
    init_dir = os.path.join(output_dir, "initialization")
    cp_sat_dir = os.path.join(output_dir, "cp_sat")
    os.makedirs(cp_sat_dir, exist_ok=True)
    
    # Read production plan for batch start station lookup
    production_df = pd.read_csv(os.path.join(init_dir, "production.csv"))
    
    # For each batch, create the correct program file based on production.csv
    originals_dir = os.path.join(output_dir, "initialization", "treatment_program_originals")
    for _, row in production_df.iterrows():
        batch_num = int(row["Batch"])
        program_num = int(row["Treatment_program"])
        src = os.path.join(originals_dir, f"Batch_{batch_num:03d}_Treatment_program_{program_num:03d}.csv")
        dst = os.path.join(cp_sat_dir, f"cp_sat_treatment_program_{batch_num}.csv")
        df = pd.read_csv(src)
        # Add step 0 at the beginning
        start_station = int(row["Start_station"])
        step0 = {
            "Stage": 0,
            "MinStat": start_station,
            "MaxStat": start_station,
            "MinTime": "00:00:00",
            "MaxTime": "100:00:00",
            "CalcTime": "00:00:00"
        }
        # Varmista, että CalcTime on olemassa myös muissa riveissä
        if "CalcTime" not in df.columns:
            df["CalcTime"] = df["MinTime"]
        # Yhdistä oikeassa sarakejärjestyksessä
        columns = ["Stage", "MinStat", "MaxStat", "MinTime", "MaxTime", "CalcTime"]
        df = pd.concat([pd.DataFrame([step0], columns=columns), df[columns]], ignore_index=True)
        # Replace Stage column with running numbers (0,1,2,...)
        df["Stage"] = range(len(df))
        df.to_csv(dst, index=False, encoding="utf-8")
    
    # Create cp_sat_batches.csv (copy production.csv, but with the correct name and all columns)
    production = pd.read_csv(os.path.join(init_dir, "production.csv"))
    batches_path = os.path.join(cp_sat_dir, "cp_sat_batches.csv")
    # Säilytä kaikki sarakkeet, myös Start_optimized, jos se on olemassa
    production.to_csv(batches_path, index=False, encoding="utf-8")
    
    # Preprocesses existing data into a format suitable for CP-SAT, but does not invent any new data.
    # All data is read from output_dir and saved with _cpsat.csv suffix.
    import shutil

    stations = pd.read_csv(os.path.join(init_dir, "stations.csv"))
    transporters = pd.read_csv(os.path.join(init_dir, "transporters.csv"))
    
    from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time
    transfer_tasks_path = os.path.join(cp_sat_dir, "cp_sat_transfer_tasks.csv")
    rows = []
    # Jokaiselle nostimelle kaikki mahdolliset siirrot sen toiminta-alueella
    for _, transporter_row in transporters.iterrows():
        transporter_id = int(transporter_row["Transporter_id"])
        min_x = transporter_row["Min_x_position"]
        max_x = transporter_row["Max_x_Position"]
        stations_in_area = stations[(stations["X Position"] >= min_x) & (stations["X Position"] <= max_x)]
        station_numbers = stations_in_area["Number"].unique()
        for from_station in station_numbers:
            for to_station in station_numbers:
                lift_time = round(float(calculate_lift_time(stations[stations["Number"] == from_station].iloc[0], transporter_row)), 1)
                sink_time = round(float(calculate_sink_time(stations[stations["Number"] == to_station].iloc[0], transporter_row)), 1)
                if from_station == to_station:
                    transfer_time = 0.0
                else:
                    transfer_time = round(float(calculate_physics_transfer_time(stations[stations["Number"] == from_station].iloc[0], stations[stations["Number"] == to_station].iloc[0], transporter_row)), 1)
                total_task_time = round(lift_time + transfer_time + sink_time, 1)
                rows.append({
                    "Transporter": transporter_id,
                    "From_Station": from_station,
                    "To_Station": to_station,
                    "LiftTime": lift_time,
                    "TransferTime": transfer_time,
                    "SinkTime": sink_time,
                    "TotalTaskTime": total_task_time
                })
    transfer_tasks = pd.DataFrame(rows)
    # Järjestä sarakkeet haluttuun järjestykseen
    transfer_tasks = transfer_tasks[["Transporter", "From_Station", "To_Station", "LiftTime", "TransferTime", "SinkTime", "TotalTaskTime"]]
    transfer_tasks.to_csv(transfer_tasks_path, index=False)

    # Also save files required by CP-SAT optimization with correct names to cp_sat directory
    stations.to_csv(os.path.join(cp_sat_dir, "cp_sat_stations.csv"), index=False, encoding="utf-8")
    transporters.to_csv(os.path.join(cp_sat_dir, "cp_sat_transporters.csv"), index=False, encoding="utf-8")