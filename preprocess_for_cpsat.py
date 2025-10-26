import os
import pandas as pd

def preprocess_for_cpsat(output_dir):
    # Esikäsittelee olemassa olevat tiedot CP-SAT:lle sopivaan muotoon, mutta ei keksi mitään uutta tietoa.
    # Kaikki tiedot luetaan output_dir:stä, ja tallennetaan _cpsat.csv -päätteellä.
    import shutil
    stations = pd.read_csv(os.path.join(output_dir, "stations.csv"))
    transporters = pd.read_csv(os.path.join(output_dir, "transporters.csv"))
    production = pd.read_csv(os.path.join(output_dir, "production.csv"))
    # Luo transfer_tasks.csv aina fysiikkafunktioilla
    from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time
    transfer_tasks_path = os.path.join(output_dir, "transfer_tasks.csv")
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
    # treatment_programs-kansio sisältää ohjelmat per erä
    treatment_programs_dir = os.path.join(output_dir, "treatment_programs")

    # Muotoile ja tallenna tiedot CP-SAT:lle sopivaan muotoon (esim. pilkkuerotin, utf-8, ei indeksiä)
    stations.to_csv(os.path.join(output_dir, "stations_cpsat.csv"), index=False, encoding="utf-8")
    transporters.to_csv(os.path.join(output_dir, "transporters_cpsat.csv"), index=False, encoding="utf-8")
    transfer_tasks.to_csv(os.path.join(output_dir, "transfer_tasks_cpsat.csv"), index=False, encoding="utf-8")
    production.to_csv(os.path.join(output_dir, "production_cpsat.csv"), index=False, encoding="utf-8")

    # Treatment_programs: kopioi kaikki sellaisenaan uuteen kansioon
    dst_tprog = os.path.join(output_dir, "treatment_programs_cpsat")
    if os.path.exists(dst_tprog):
        shutil.rmtree(dst_tprog)
    shutil.copytree(treatment_programs_dir, dst_tprog)

    print("Esikäsittely valmis. Kaikki tiedot oikeassa muodossa CP-SAT:lle.")
