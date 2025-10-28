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
    originals_dir = os.path.join("initialization", "treatment_program_originals")
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
            "MaxTime": "100:00:00"
        }
        df = pd.concat([pd.DataFrame([step0]), df], ignore_index=True)
    
    # Replace Stage column with running numbers (0,1,2,...)
        df["Stage"] = range(len(df))
        df.to_csv(dst, index=False, encoding="utf-8")
    
    # Create cp_sat_batches.csv (copy production.csv, but with the correct name)
    production = pd.read_csv(os.path.join(init_dir, "production.csv"))
    batches_path = os.path.join(cp_sat_dir, "cp_sat_batches.csv")
    production.to_csv(batches_path, index=False, encoding="utf-8")
    
    # Preprocesses existing data into a format suitable for CP-SAT, but does not invent any new data.
    # All data is read from output_dir and saved with _cpsat.csv suffix.
    import shutil

    stations = pd.read_csv(os.path.join(init_dir, "stations.csv"))
    transporters = pd.read_csv(os.path.join(init_dir, "transporters.csv"))
    
    # Create only one transfer time file using physics functions, with a unified name
    from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time
    transfer_tasks_path = os.path.join(cp_sat_dir, "cp_sat_transfer_tasks.csv")
    transporter_row = transporters.iloc[0]  # Assume one hoist, extend if needed
    rows = []
    for batch_row in production.itertuples():
        batch_num = int(batch_row.Batch)
        program_num = int(batch_row.Treatment_program)
        # Lataa ohjelma
        prog_file = os.path.join(originals_dir, f"Batch_{batch_num:03d}_Treatment_program_{program_num:03d}.csv")
        prog_df = pd.read_csv(prog_file)
        prog_df["Stage"] = range(len(prog_df))
        for stage_row in prog_df.itertuples():
            stage = int(stage_row.Stage)
            from_station = int(stage_row.MinStat) if stage == 0 else int(prog_df.iloc[stage-1].MaxStat)
            to_station = int(stage_row.MaxStat)
            lift_time = calculate_lift_time(stations[stations["Number"] == from_station].iloc[0], transporter_row)
            sink_time = calculate_sink_time(stations[stations["Number"] == to_station].iloc[0], transporter_row)
            transfer_time = calculate_physics_transfer_time(stations[stations["Number"] == from_station].iloc[0], stations[stations["Number"] == to_station].iloc[0], transporter_row)
            total_task_time = lift_time + transfer_time + sink_time
            rows.append({
                "Batch": batch_num,
                "Stage": stage,
                "From_Station": from_station,
                "To_Station": to_station,
                "LiftTime": lift_time,
                "TransferTime": transfer_time,
                "SinkTime": sink_time,
                "TotalTaskTime": total_task_time
            })
    transfer_tasks = pd.DataFrame(rows)
    transfer_tasks.to_csv(transfer_tasks_path, index=False)

    # Also save files required by CP-SAT optimization with correct names to cp_sat directory
    stations.to_csv(os.path.join(cp_sat_dir, "cp_sat_stations.csv"), index=False, encoding="utf-8")
    transporters.to_csv(os.path.join(cp_sat_dir, "cp_sat_transporters.csv"), index=False, encoding="utf-8")