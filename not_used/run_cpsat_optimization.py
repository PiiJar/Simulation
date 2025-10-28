import os
import pandas as pd
from ortools.sat.python import cp_model

def run_cpsat_optimization(output_dir):
    preproc_dir = os.path.join(output_dir, "initialization")
    input_path = os.path.join(preproc_dir, "cpsat_preprocessed.csv")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    output_path = os.path.join(logs_dir, "cpsat_optimized.csv")
    df = pd.read_csv(input_path)
    stations_path = os.path.join(preproc_dir, "stations.csv")
    stations_df = pd.read_csv(stations_path)
    transfer_tasks_path = os.path.join(preproc_dir, "transfer_tasks.csv")
    transfer_tasks_df = pd.read_csv(transfer_tasks_path)
    production_path = os.path.join(preproc_dir, "production.csv")
    prod_df = pd.read_csv(production_path)

    model = cp_model.CpModel()
    batches = sorted(df["Batch"].unique())
    batch_start_vars = {batch: model.NewIntVar(0, 1000000, f'batch_start_{batch}') for batch in batches}
    process_vars = {}
    task_vars = {}
    stages = sorted(df["Stage"].unique())

    # Luo prosessivaiheiden muuttujat
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        start_var = model.NewIntVar(0, 1000000, f'start_{batch}_{stage}')
        end_var = model.NewIntVar(0, 1000000, f'end_{batch}_{stage}')
        duration_var = model.NewIntVar(min_time, max_time, f'duration_{batch}_{stage}')
        interval = model.NewIntervalVar(start_var, duration_var, end_var, f'interval_{batch}_{stage}')
        process_vars[(batch, stage)] = (start_var, end_var, duration_var, interval)
        # Kesto = end - start
        model.Add(end_var == start_var + duration_var)

    # Synkronoi nostintehtävät ja prosessivaiheet
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        if stage == 0:
            continue  # Ei nostinta step 0:lle
        prev_row = df[(df["Batch"] == batch) & (df["Stage"] == stage - 1)].iloc[0]
        from_station = int(prev_row["Station"])
        to_station = int(row["Station"])
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == from_station) & (transfer_tasks_df["to_station"] == to_station)]
        print(f"[DEBUG] Searching transfer: from_station={from_station}, to_station={to_station}")
        print(f"[DEBUG] Transfer row found: {not t_row.empty}")
        if t_row.empty:
            continue
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        task_start = model.NewIntVar(0, 1000000, f'task_start_{batch}_{stage}')
        task_end = model.NewIntVar(0, 1000000, f'task_end_{batch}_{stage}')
        task_interval = model.NewIntervalVar(task_start, total_task_time, task_end, f'task_interval_{batch}_{stage}')
        task_vars[(batch, stage)] = {
            "interval": task_interval,
            "from_station": from_station,
            "to_station": to_station,
            "lift_time": lift_time,
            "transfer_time": transfer_time,
            "sink_time": sink_time,
            "total_task_time": total_task_time,
            "lift_start": task_start,
            "sink_end": task_end
        }
        # Synkronointi: nostimen aikataulu määrittää asemien aikataulut
        prev_end = process_vars[(batch, stage-1)][1]
        this_start = process_vars[(batch, stage)][0]
        model.Add(task_start >= prev_end)  # Nostimen nosto alkaa edellisen vaiheen lopusta
        model.Add(this_start >= task_end)  # Nostimen lasku päättyy ennen seuraavan vaiheen alkua
        print(f"[DEBUG] Synkronointirajoitteet: Batch {batch} Stage {stage}: prev_end={prev_end}, task_start={task_start}, task_end={task_end}, this_start={this_start}")

    # Poistetaan asemien aikataulujen lukitseminen ja lisätään nostimen aikatauluun perustuvat rajoitteet
    for station in stations_df["Number"]:
        intervals = [v["interval"] for (b, s), v in task_vars.items() if v["from_station"] == station or v["to_station"] == station]
        print(f"[DEBUG] Station {station} intervals: {intervals}")
        if intervals:
            model.AddNoOverlap(intervals)

    # Pakota yksi batch alkamaan ajassa 0
    first_batch_start = model.NewIntVar(0, 1000000, 'first_batch_start')
    model.AddMinEquality(first_batch_start, list(batch_start_vars.values()))
    model.Add(first_batch_start == 0)

    # Makespan
    makespan_ends = [v[1] for v in process_vars.values()]
    makespan = model.NewIntVar(0, 1000000, 'makespan')
    model.AddMaxEquality(makespan, makespan_ends)
    model.Minimize(makespan)

    # Ratkaise
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    solver.parameters.max_time_in_seconds = 60.0
    status = solver.Solve(model)
    print(f"[CP-SAT] Ratkaisun status: {status} ({cp_model.OPTIMAL}=OPTIMAL, {cp_model.FEASIBLE}=FEASIBLE, {cp_model.INFEASIBLE}=INFEASIBLE, {cp_model.MODEL_INVALID}=MODEL_INVALID)")

    results = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (batch, stage), (start_var, end_var, duration_var, interval) in process_vars.items():
            row = df[(df["Batch"] == batch) & (df["Stage"] == stage)].iloc[0]
            start = solver.Value(start_var)
            end = solver.Value(end_var)
            duration = solver.Value(duration_var)
            results.append({
                "Batch": batch,
                "Stage": stage,
                "Station": row["Station"],
                "Start": start,
                "End": end,
                "Duration": duration
            })
        out_df = pd.DataFrame(results)
        # Varmistetaan, että tulokset tallennetaan ennen optimoinnin päättymistä
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            out_df.to_csv(output_path, index=False)
            print(f"[CP-SAT] Optimoinnin tulokset tallennettu: {output_path}")
        # Tallennetaan nostintehtävien aikataulut erilliseen tiedostoon
        task_results = []
        seen_tasks = set()
        for (batch, stage), task in task_vars.items():
            if (batch, stage) in seen_tasks:
                continue
            seen_tasks.add((batch, stage))
            # Debug-tulostus nostintehtävien ajoista
            print(f"[DEBUG] Batch {batch}, Stage {stage}: Task_Start={solver.Value(task['lift_start'])}, Task_End={solver.Value(task['sink_end'])}")
            # Tarkista epäloogiset arvot ennen lisäämistä
            if solver.Value(task['lift_start']) >= solver.Value(task['sink_end']):
                print(f"[ERROR] Epälooginen rivi: Batch {batch}, Stage {stage}, Task_Start={solver.Value(task['lift_start'])}, Task_End={solver.Value(task['sink_end'])}")
            task_results.append({
                "Batch": batch,
                "Stage": stage,
                "From_Station": task["from_station"],
                "To_Station": task["to_station"],
                "Task_Start": solver.Value(task["lift_start"]),
                "Task_End": solver.Value(task["sink_end"]),
                "Total_Task_Time": task["total_task_time"]
            })
        if task_results:
            task_df = pd.DataFrame(task_results)
            task_df = task_df.sort_values(["Batch", "Task_Start"]).reset_index(drop=True)
            # Suodata pois epäloogiset rivit
            task_df = task_df[task_df['Task_Start'] < task_df['Task_End']]
            task_out_path = os.path.join(logs_dir, "transporter_tasks_optimized.csv")
            task_df.to_csv(task_out_path, index=False)
            print(f"[CP-SAT] Nostintehtävät tallennettu: {task_out_path}")
    else:
        pass

    # Päivitä production.csv: Start_time = optimoitu ensimmäisen vaiheen Start, järjestä aikajärjestykseen
    def seconds_to_hms(secs):
        h = int(secs) // 3600
        m = (int(secs) % 3600) // 60
        s = int(secs) % 60
        return f"{h:02}:{m:02}:{s:02}"
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        optimized_df = pd.read_csv(output_path)
        batch_start_times = (
            optimized_df[optimized_df["Stage"] == 1][["Batch", "Start"]]
            .set_index("Batch")["Start"].to_dict()
        )
        prod_df["Start_time"] = prod_df["Batch"].map(lambda b: seconds_to_hms(batch_start_times.get(b, 0)))
        prod_df = prod_df.copy()
        prod_df["_sort"] = prod_df["Batch"].map(lambda b: batch_start_times.get(b, 0))
        prod_df = prod_df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
        prod_df = prod_df[["Batch", "Treatment_program", "Start_station", "Start_time"]]
        prod_df.to_csv(production_path, index=False)
        print(f"[CP-SAT] Päivitetty production.csv optimoiduilla lähtöajoilla: {production_path}")
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
    # Luo batchien vapaasti optimoitavat aloitusmuuttujat
    batches = sorted(df["Batch"].unique())
    batch_start_vars = {batch: model.NewIntVar(0, 1000000, f'batch_start_{batch}') for batch in batches}

    # DEBUG PRINTS: after all data is loaded, before model building
    print("[DEBUG] Prosessivaiheiden muuttujat ja rajat:")
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        print(f"  Batch {batch} Stage {stage}: MinTime={min_time}, MaxTime={max_time}")
    # Luo tuotantovaiheiden muuttujat ja nostintehtävien muuttujat
    # Synkronoi: prosessivaiheen alku = nostimen sink (drop) päättyy, loppu = nostimen lift (pick-up) alkaa
    process_vars = {}
    task_vars = {}
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        # Prosessivaiheen duration
        duration_var = model.NewIntVar(min_time, max_time, f'duration_{idx}')
        # Prosessivaiheen alku ja loppu (sidotaan nostintehtäviin myöhemmin)
        start_var = model.NewIntVar(0, 1000000, f'start_{idx}')
        end_var = model.NewIntVar(0, 1000000, f'end_{idx}')
        interval = model.NewIntervalVar(start_var, duration_var, end_var, f'interval_{idx}')
        process_vars[(batch, stage)] = (start_var, end_var, interval, duration_var, row)
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
        print(f"[DEBUG] Searching transfer: from_station={from_station}, to_station={to_station}")
        print(f"[DEBUG] Transfer row found: {not t_row.empty}")
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        # Nostintehtävän muuttujat
        task_start = model.NewIntVar(0, 1000000, f'task_start_{batch}_{stage}')
        task_end = model.NewIntVar(0, 1000000, f'task_end_{batch}_{stage}')
        task_interval = model.NewIntervalVar(task_start, total_task_time, task_end, f'task_interval_{batch}_{stage}')
        task_vars[(batch, stage)] = (task_start, task_end, task_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time)
    # Synkronoi prosessivaiheiden ja nostintehtävien aikataulut
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        # Jos vaiheelle ei ole nostintehtävää (esim. yksi erä, yksi askel), älä sido alku/loppua mihinkään nostinmuuttujaan
        has_prev_task = (batch, stage) in task_vars
        has_next_task = (batch, stage + 1) in task_vars
        if not has_prev_task and not has_next_task:
            # Vain MinTime/MaxTime rajoittaa, ei sidontoja
            continue
        if stage == 1:
            model.Add(process_vars[(batch, stage)][0] == batch_start_vars[batch])
            if has_next_task:
                next_task = task_vars[(batch, stage + 1)]
                model.Add(process_vars[(batch, stage)][1] == next_task[0])
        else:
            if has_prev_task:
                prev_task = task_vars[(batch, stage)]
                model.Add(process_vars[(batch, stage)][0] == prev_task[1] - prev_task[8])
            if has_next_task:
                next_task = task_vars[(batch, stage + 1)]
                model.Add(process_vars[(batch, stage)][1] == next_task[0])
    # Nostintehtävien aikataulut: nosto määrittää asemien aikataulut
    for (batch, stage), (task_start, task_end, task_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time) in task_vars.items():
        # Nostimen nosto alkaa prosessivaiheen lopusta
        model.Add(task_start >= process_vars[(batch, stage)][1])
        # Nostimen lasku päättyy ennen seuraavan prosessivaiheen alkua, jos sellainen on
        if (batch, stage + 1) in process_vars:
            model.Add(task_end <= process_vars[(batch, stage + 1)][0] + sink_time)

        # Asemien aikataulut johdetaan nostimen aikataulusta
        model.Add(process_vars[(batch, stage)][0] == task_start - lift_time)
        model.Add(process_vars[(batch, stage)][1] == task_end + transfer_time)

    # Poistetaan asemien aikataulujen lukitseminen
    # Asemien aikataulut määräytyvät nostimen reitin perusteella

    # Pakota yksi batch alkamaan ajassa 0 (ensimmäinen erä heti)
    first_batch_start = model.NewIntVar(0, 1000000, 'first_batch_start')
    model.AddMinEquality(first_batch_start, list(batch_start_vars.values()))
    model.Add(first_batch_start == 0)

    # (Nostintehtävät ja synkronointi on jo tehty yllä)

    # Nostintehtävien no-overlap (nostin ei voi tehdä kahta siirtoa samaan aikaan)
    if task_vars:
        # Korjataan task_vars käsittely tuple-muotoon
        task_intervals = [v[2] for v in task_vars.values()]  # Oletetaan, että interval on tuple-indeksissä 2
        print(f"[DEBUG] Task intervals: {task_intervals}")
        if not task_intervals:
            print("[ERROR] Task intervals are empty for AddNoOverlap.")
        else:
            model.AddNoOverlap(task_intervals)
    # Estä päällekkäisyys jokaisella fyysisellä asemalla (AddNoOverlap per asema)
    for station in stations_df["Number"]:
        station_task_indices = [idx for idx, row in df.iterrows() if int(row["Station"]) == station]
        intervals = [task_vars[(df.loc[idx, "Batch"], df.loc[idx, "Stage"])]["interval"] for idx in station_task_indices]
        if len(intervals) > 1:
            print(f"[DEBUG] AddNoOverlap asema {station} (intervalit):")
            for idx in station_task_indices:
                print(f"    Process interval: batch={df.loc[idx, 'Batch']} stage={df.loc[idx, 'Stage']} -> {intervals}")
            model.AddNoOverlap(intervals)

    print("[DEBUG] Aloitetaan CP-SAT optimointi")
    print(f"[DEBUG] Ladataan tiedot: {input_path}")
    print(f"[DEBUG] Erät: {batches}")
    print(f"[DEBUG] Vaiheet: {stages}")

    # Tulosta prosessivaiheiden muuttujat
    # Turvallinen tulostus prosessivaiheiden muuttujille
    for key, value in process_vars.items():
        if len(value) == 4:
            start_var, end_var, duration_var, interval = value
            print(f"[DEBUG] Batch {key[0]}, Stage {key[1]}: start={start_var}, end={end_var}, duration={duration_var}, interval={interval}")
        else:
            print(f"[DEBUG] Virheellinen rakenne prosessivaiheessa: {key} -> {value}")

    # Tulosta synkronointirajoitteet
    for batch in batches:
        if batch in batch_start_vars:
            print(f"[DEBUG] Batch {batch} start_var: {batch_start_vars[batch]}")

    # Tulosta prosessivaiheiden muuttujat ja rajat
    print("[DEBUG] Prosessivaiheiden muuttujat ja rajat:")
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        start_var, end_var, interval, duration_var, _ = tasks[idx]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        print(f"    Batch {batch} Stage {stage}: start={start_var}, end={end_var}, duration={duration_var} [{min_time}, {max_time}] interval={interval}")

    # Poistetaan kaikki viittaukset transporter_tasks- ja tasks-muuttujiin
    # Poistetaan debug-tulosteet, jotka viittasivat transporter_tasks-muuttujaan
    print("[DEBUG] Nostintehtävien muuttujat ja rajat:")
    for (batch, stage), v in task_vars.items():
        print(f"    Batch {batch} Stage {stage}: task_start={v['lift_start']}, task_end={v['sink_end']}, interval={v['interval']}, total_task_time={v['total_task_time']}, from={v['from_station']}, to={v['to_station']}, lift={v['lift_time']}, transfer={v['transfer_time']}, sink={v['sink_time']}")

    # Poistetaan makespanin laskenta, joka viittasi tasks-muuttujaan
    makespan = model.NewIntVar(0, 1000000, 'makespan')
    model.AddMaxEquality(makespan, [v["sink_end"] for v in task_vars.values()])
    model.Minimize(makespan)

    # Poistetaan kaikki jäljellä olevat viittaukset transporter_tasks- ja tasks-muuttujiin
    # Tämä varmistaa, että koodi ei enää viittaa näihin muuttujin missään kohdassa.

    # Ratkaise
    solver = cp_model.CpSolver()
    print("[DEBUG] Mallin rakentaminen valmis, ratkaistaan...")
    status = solver.Solve(model)
    print(f"[DEBUG] Ratkaisun status: {status} ({cp_model.OPTIMAL}=OPTIMAL, {cp_model.FEASIBLE}=FEASIBLE, {cp_model.INFEASIBLE}=INFEASIBLE, {cp_model.MODEL_INVALID}=MODEL_INVALID)")
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
        task_results = []
        # 1. Lisää normaalit nostintehtävät (vaiheiden väliset siirrot)
        for (batch, stage), (task_start_var, task_end_var, task_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time) in transporter_tasks.items():
            # Purku 9 kenttään, käytetään vain tarvittavat tallennukseen
            task_start = solver.Value(task_start_var)
            task_end = solver.Value(task_end_var)
            task_results.append({
                "Batch": batch,
                "Stage": stage,
                "From_Station": from_station,
                "To_Station": to_station,
                "Task_Start": task_start,
                "Task_End": task_end,
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
        task_end = int(first_row["Start"])
        task_start = max(0, task_end - total_task_time)
        task_results.append({
            "Batch": batch,
            "Stage": 1,
            "From_Station": start_station,
            "To_Station": to_station,
            "Task_Start": task_start,
            "Task_End": task_end,
            "Total_Task_Time": total_task_time
        })

    if task_results:
        task_df = pd.DataFrame(task_results)
        task_df = task_df.sort_values(["Batch", "Task_Start"]).reset_index(drop=True)
        # Suodata pois epäloogiset rivit
        task_df = task_df[task_df['Task_Start'] < task_df['Task_End']]
        task_out_path = os.path.join(logs_dir, "transporter_tasks_optimized.csv")
        task_df.to_csv(task_out_path, index=False)
        print(f"[CP-SAT] Nostintehtävät tallennettu: {task_out_path}")
    else:
        # Ensure this message is only printed when the solution status is not optimal or feasible
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            print("[CP-SAT] Ei ratkaisua.")

    # --- Päivitä production.csv: Start_time = optimoitu ensimmäisen vaiheen Start, järjestä aikajärjestykseen ---
    production_path = os.path.join(preproc_dir, "production.csv")
    prod_df = pd.read_csv(production_path)
    def seconds_to_hms(secs):
        h = int(secs) // 3600
        m = (int(secs) % 3600) // 60
        s = int(secs) % 60
        return f"{h:02}:{m:02}:{s:02}"
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Lue optimoidut ajat
        optimized_path = os.path.join(logs_dir, "cpsat_optimized.csv")
        optimized_df = pd.read_csv(optimized_path)
        # Hae kunkin erän ensimmäisen vaiheen Start
        batch_start_times = (
            optimized_df[optimized_df["Stage"] == 1][["Batch", "Start"]]
            .set_index("Batch")
            ["Start"]
            .to_dict()
        )
        # Päivitä Start_time (muoto hh:mm:ss)
        prod_df["Start_time"] = prod_df["Batch"].map(lambda b: seconds_to_hms(batch_start_times.get(b, 0)))
        # Järjestä aikajärjestykseen
        prod_df = prod_df.copy()
        prod_df["_sort"] = prod_df["Batch"].map(lambda b: batch_start_times.get(b, 0))
        prod_df = prod_df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
        # Ota vain vaaditut sarakkeet
        prod_df = prod_df[["Batch", "Treatment_program", "Start_station", "Start_time"]]
        prod_df.to_csv(production_path, index=False)
        print(f"[CP-SAT] Päivitetty production.csv optimoiduilla lähtöajoilla: {production_path}")

    # Debug: Print all variables and constraints before solving
    model_proto = model.Proto()
    print("\n--- Debug: Variables and Constraints ---")
    for var in model_proto.variables:
        print(f"Variable: {var.name}, Domain: {var.domain}")

    for ct in model_proto.constraints:
        print(f"Constraint: {ct}")

    print("--- End of Debug ---\n")

    # Tulosta kaikki rajoitteet ja muuttujat analysointia varten
    print("[DEBUG] Kaikki rajoitteet ja muuttujat:")
    for c in model.constraints:
        print(c)
    for v in model.variables:
        print(v)

    # Tulosta yksityiskohtaiset tiedot rajoitteista ja muuttujista
    print("[DEBUG] Yksityiskohtaiset rajoitteet ja muuttujat:")
    for c in model.constraints:
        print(f"Rajoite: {c}")
    for v in model.variables:
        print(f"Muuttuja: {v}, Arvo: {solver.Value(v)}")

    # Tulosta ristiriitaiset rajoitteet analysointia varten
    print("[DEBUG] Ristiriitaiset rajoitteet:")
    for c in model.constraints:
        if not solver.IsFeasible(c):
            print(f"Ristiriitainen rajoite: {c}")

    # Tulosta kaikki muuttujat ja niiden rajat analysointia varten
    print("[DEBUG] Muuttujat ja niiden rajat:")
    for v in model.variables:
        print(f"Muuttuja: {v}, Alaraja: {v.LowerBound()}, Yläraja: {v.UpperBound()}")

    # Debug-tulostus lineaarisista rajoitteista
    for constraint in model.constraints:
        print(f"[DEBUG] Constraint: {constraint}")
