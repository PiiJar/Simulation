import os
import pandas as pd

def preprocess_for_cpsat(output_dir):
    # Kaikki tiedot luetaan initialization-kansiosta
    init_dir = os.path.join(output_dir, "initialization")
    # Lue tuotantosuunnitelma batchien aloitusasemien hakua varten
    production_df = pd.read_csv(os.path.join(init_dir, "production.csv"))

    # Luo jokaiselle batchille oikea ohjelmatiedosto production.csv:n perusteella
    for _, row in production_df.iterrows():
        batch_num = int(row["Batch"])
        program_num = int(row["Treatment_program"])
        src = os.path.join(init_dir, f"treatment_program_{program_num:03d}.csv")
        dst = os.path.join(init_dir, f"cp-sat-treatment-program-{batch_num}.csv")
        df = pd.read_csv(src)
        # Lisää askel 0 alkuun
        start_station = int(row["Start_station"])
        step0 = {
            "Stage": 0,
            "MinStat": start_station,
            "MaxStat": start_station,
            "MinTime": "00:00:00",
            "MaxTime": "100:00:00"
        }
        df = pd.concat([pd.DataFrame([step0]), df], ignore_index=True)
        # Korvaa Stage-sarake juoksevalla numeroinnilla (0,1,2,...)
        df["Stage"] = range(len(df))
        df.to_csv(dst, index=False, encoding="utf-8")
        print(f"[Esikäsittely] Tallennettu: {dst}")

    # Luo cp-sat-batches.csv (kopioi production.csv, mutta oikealla nimellä)
    production = pd.read_csv(os.path.join(init_dir, "production.csv"))
    batches_path = os.path.join(init_dir, "cp-sat-batches.csv")
    production.to_csv(batches_path, index=False, encoding="utf-8")
    print(f"[Esikäsittely] Tallennettu: {batches_path}")
    # Esikäsittelee olemassa olevat tiedot CP-SAT:lle sopivaan muotoon, mutta ei keksi mitään uutta tietoa.
    # Kaikki tiedot luetaan output_dir:stä, ja tallennetaan _cpsat.csv -päätteellä.
    import shutil

    stations = pd.read_csv(os.path.join(init_dir, "stations.csv"))
    transporters = pd.read_csv(os.path.join(init_dir, "transporters.csv"))
    # Luo transfer_tasks.csv aina fysiikkafunktioilla
    from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time
    transfer_tasks_path = os.path.join(init_dir, "transfer_tasks.csv")
    transporter_row = transporters.iloc[0]  # Oletetaan yksi nostin, laajenna tarvittaessa
    rows = []
    for i, from_row in stations.iterrows():
        for j, to_row in stations.iterrows():
            if from_row["Number"] != to_row["Number"]:
                transfer_time = calculate_physics_transfer_time(from_row, to_row, transporter_row)
                lift_time = calculate_lift_time(from_row, transporter_row)
                sink_time = calculate_sink_time(to_row, transporter_row)
                total_task_time = lift_time + transfer_time + sink_time
                rows.append({
                    "from_station": from_row["Number"],
                    "to_station": to_row["Number"],
                    "lift_time": lift_time,
                    "transfer_time": transfer_time,
                    "sink_time": sink_time,
                    "total_task_time": total_task_time
                })
    transfer_tasks = pd.DataFrame(rows)
    transfer_tasks.to_csv(transfer_tasks_path, index=False)
    print(f"[Esikäsittely] Luotiin transfer_tasks.csv fysiikkafunktioilla ({len(transfer_tasks)} riviä)")

    # Tallennetaan myös CP-SAT-optimoinnin vaatimat tiedostot oikeilla nimillä
    stations.to_csv(os.path.join(init_dir, "cp-sat-stations.csv"), index=False, encoding="utf-8")
    transporters.to_csv(os.path.join(init_dir, "cp-sat-transporters.csv"), index=False, encoding="utf-8")
    transfer_tasks.to_csv(os.path.join(init_dir, "cp-sat-transfer-tasks.csv"), index=False, encoding="utf-8")
    # Huom: cp-sat-batches.csv tallennettiin jo aiemmin

    print("Esikäsittely valmis. Kaikki tiedot oikeassa muodossa CP-SAT:lle.")
