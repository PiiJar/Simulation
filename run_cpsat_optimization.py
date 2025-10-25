import os
import pandas as pd
from ortools.sat.python import cp_model

def run_cpsat_optimization(output_dir):

    preproc_dir = os.path.join(output_dir, "initialization")
    # Lue nostintehtävien ajat
    transfer_tasks_path = os.path.join(preproc_dir, "transfer_tasks.csv")
    transfer_tasks_df = pd.read_csv(transfer_tasks_path)

    """
    Lukee preprocessing/cpsat_preprocessed.csv ja ajaa CP-SAT-optimoinnin.
    Tallentaa tuloksen preprocessing/cpsat_optimized.csv.
    """
    preproc_dir = os.path.join(output_dir, "initialization")
    input_path = os.path.join(preproc_dir, "cpsat_preprocessed.csv")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    output_path = os.path.join(logs_dir, "cpsat_optimized.csv")
    df = pd.read_csv(input_path)

    model = cp_model.CpModel()
    tasks = {}
    hoist_tasks = {}
    horizon = 0
    # Lue asemien kapasiteetit
    stations_path = os.path.join(preproc_dir, "stations.csv")
    stations_df = pd.read_csv(stations_path)
    # Rinnakkaisuus Groupin perusteella
    station_to_group = {}
    group_to_stations = {}
    for _, srow in stations_df.iterrows():
        num = int(srow["Number"])
        group = int(srow["Group"])
        station_to_group[num] = group
        if group not in group_to_stations:
            group_to_stations[group] = []
        group_to_stations[group].append(num)
    # Luo tuotantovaiheiden muuttujat
    for idx, row in df.iterrows():
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        duration_var = model.NewIntVar(min_time, max_time, f'duration_{idx}')
        start_var = model.NewIntVar(0, 1000000, f'start_{idx}')
        end_var = model.NewIntVar(0, 1000000, f'end_{idx}')
        interval = model.NewIntervalVar(start_var, duration_var, end_var, f'interval_{idx}')
        tasks[idx] = (start_var, end_var, interval, duration_var, row)
        horizon = max(horizon, max_time)

    # Luo nostintehtävät (siirrot vaiheiden välillä)
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        # Etsi edellinen vaihe (stage-1)
        prev_idx = df[(df["Batch"] == batch) & (df["Stage"] == stage - 1)].index
        if len(prev_idx) == 0:
            continue  # Ensimmäisellä vaiheella ei siirtoa
        prev_row = df.loc[prev_idx[0]]
        from_station = int(prev_row["Station"])
        to_station = int(row["Station"])
        # Hae siirtoajat
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == from_station) & (transfer_tasks_df["to_station"] == to_station)]
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        # Nostintehtävän muuttujat
        hoist_start = model.NewIntVar(0, 1000000, f'hoist_start_{batch}_{stage}')
        hoist_end = model.NewIntVar(0, 1000000, f'hoist_end_{batch}_{stage}')
        hoist_interval = model.NewIntervalVar(hoist_start, total_task_time, hoist_end, f'hoist_interval_{batch}_{stage}')
        hoist_tasks[(batch, stage)] = (hoist_start, hoist_end, hoist_interval, total_task_time, from_station, to_station)
        # Nostintehtävä voi alkaa vasta kun edellinen vaihe on valmis
        model.Add(hoist_start >= tasks[prev_idx[0]][1])
        # Nostintehtävä päättyy ennen seuraavan vaiheen alkua
        model.Add(hoist_end <= tasks[idx][0])

    # Nostintehtävien no-overlap (nostin ei voi tehdä kahta siirtoa samaan aikaan)
    if hoist_tasks:
        model.AddNoOverlap([v[2] for v in hoist_tasks.values()])
    # Rinnakkaisuus Groupin perusteella: AddCumulative kaikille ryhmille
    for group, station_list in group_to_stations.items():
        # Kerää kaikki tehtäväintervallit, jotka kuuluvat tähän groupiin
        intervals = [tasks[idx][2] for idx, row in df.iterrows() if station_to_group.get(int(row["Station"]), -1) == group]
        demands = [1]*len(intervals)
        cap = len(station_list)
        if len(intervals) > 0:
            if cap > 1:
                model.AddCumulative(intervals, demands, cap)
            else:
                if len(intervals) > 1:
                    model.AddNoOverlap(intervals)
    # Ratkaise
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    results = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for idx, row in df.iterrows():
            start = solver.Value(tasks[idx][0])
            end = solver.Value(tasks[idx][1])
            duration = solver.Value(tasks[idx][3])
            results.append({
                "Batch": row["Batch"],
                "Stage": row["Stage"],
                "Station": row["Station"],
                "Start": start,
                "End": end,
                "Duration": duration
            })
        out_df = pd.DataFrame(results)
        out_df.to_csv(output_path, index=False)
        print(f"[CP-SAT] Optimointi valmis. Tallennettu: {output_path}")
        # Tallennetaan nostintehtävien aikataulut erilliseen tiedostoon
    # logs_dir ja output_path on jo alustettu
        hoist_results = []
        # 1. Lisää normaalit nostintehtävät (vaiheiden väliset siirrot)
        for (batch, stage), (hoist_start_var, hoist_end_var, hoist_interval, total_task_time, from_station, to_station) in hoist_tasks.items():
            hoist_start = solver.Value(hoist_start_var)
            hoist_end = solver.Value(hoist_end_var)
            hoist_results.append({
                "Batch": batch,
                "Stage": stage,
                "From_Station": from_station,
                "To_Station": to_station,
                "Hoist_Start": hoist_start,
                "Hoist_End": hoist_end,
                "Total_Task_Time": total_task_time
            })

        # 2. Lisää erien ensimmäiset siirrot (aloituspaikasta ensimmäiselle asemalle)
        production_path = os.path.join(preproc_dir, "production.csv")
        prod_df = pd.read_csv(production_path)
        # Lue optimoidut ajat
        optimized_path = os.path.join(logs_dir, "cpsat_optimized.csv")
        optimized_df = pd.read_csv(optimized_path)
        for _, prod_row in prod_df.iterrows():
            batch = prod_row["Batch"]
            start_station = int(prod_row["Start_station"])
            # Etsi tämän erän ensimmäinen vaihe (stage==1)
            first_row = optimized_df[(optimized_df["Batch"] == batch) & (optimized_df["Stage"] == 1)]
            if first_row.empty:
                continue
            first_row = first_row.iloc[0]
            to_station = int(first_row["Station"])
            # Hae siirtoajat
            t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == start_station) & (transfer_tasks_df["to_station"] == to_station)]
            if t_row.empty:
                continue
            total_task_time = int(t_row.iloc[0]["total_task_time"])
            # Ensimmäisen vaiheen alku = tuotantovaiheen Start (optimoitu)
            hoist_end = int(first_row["Start"])
            hoist_start = max(0, hoist_end - total_task_time)
            hoist_results.append({
                "Batch": batch,
                "Stage": 1,
                "From_Station": start_station,
                "To_Station": to_station,
                "Hoist_Start": hoist_start,
                "Hoist_End": hoist_end,
                "Total_Task_Time": total_task_time
            })

        if hoist_results:
            hoist_df = pd.DataFrame(hoist_results)
            hoist_df = hoist_df.sort_values(["Batch", "Hoist_Start"]).reset_index(drop=True)
            hoist_out_path = os.path.join(logs_dir, "transporter_tasks_optimized.csv")
            hoist_df.to_csv(hoist_out_path, index=False)
            print(f"[CP-SAT] Nostintehtävät tallennettu: {hoist_out_path}")
    else:
        print("[CP-SAT] Ei ratkaisua.")
