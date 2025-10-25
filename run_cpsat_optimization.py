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
    hoist_vars = {}
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
        if t_row.empty:
            continue
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        hoist_start = model.NewIntVar(0, 1000000, f'hoist_start_{batch}_{stage}')
        hoist_end = model.NewIntVar(0, 1000000, f'hoist_end_{batch}_{stage}')
        hoist_interval = model.NewIntervalVar(hoist_start, total_task_time, hoist_end, f'hoist_interval_{batch}_{stage}')
        hoist_vars[(batch, stage)] = {
            "interval": hoist_interval,
            "from_station": from_station,
            "to_station": to_station,
            "lift_time": lift_time,
            "transfer_time": transfer_time,
            "sink_time": sink_time,
            "total_task_time": total_task_time,
            "lift_start": hoist_start,
            "sink_end": hoist_end
        }
        # Synkronointi: edellisen vaiheen loppu = nostimen alku, tämän vaiheen alku = nostimen loppu
        # Poistettu tarpeettomat synkronointirajoitteet, koska nostimen reitti määrittää käsittelyajat automaattisesti
        # prev_end = process_vars[(batch, stage-1)][1]
        # this_start = process_vars[(batch, stage)][0]
        # model.Add(prev_end == hoist_start)
        # model.Add(this_start == hoist_end)

    # AddNoOverlap nostintehtäville
    if hoist_vars:
        hoist_intervals = [v["interval"] for v in hoist_vars.values()]
        model.AddNoOverlap(hoist_intervals)

    # AddNoOverlap asemille
    for station in stations_df["Number"]:
        intervals = [v[3] for (b, s), v in process_vars.items() if int(df[(df["Batch"]==b)&(df["Stage"]==s)].iloc[0]["Station"]) == station]
        if len(intervals) > 1:
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
        out_df.to_csv(output_path, index=False)
        print(f"[CP-SAT] Optimointi valmis. Tallennettu: {output_path}")
        # Tallennetaan nostintehtävien aikataulut erilliseen tiedostoon
        hoist_results = []
        for (batch, stage), hoist in hoist_vars.items():
            hoist_results.append({
                "Batch": batch,
                "Stage": stage,
                "From_Station": hoist["from_station"],
                "To_Station": hoist["to_station"],
                "Hoist_Start": solver.Value(hoist["lift_start"]),
                "Hoist_End": solver.Value(hoist["sink_end"]),
                "Total_Task_Time": hoist["total_task_time"]
            })
        if hoist_results:
            hoist_df = pd.DataFrame(hoist_results)
            hoist_df = hoist_df.sort_values(["Batch", "Hoist_Start"]).reset_index(drop=True)
            hoist_out_path = os.path.join(logs_dir, "transporter_tasks_optimized.csv")
            hoist_df.to_csv(hoist_out_path, index=False)
            print(f"[CP-SAT] Nostintehtävät tallennettu: {hoist_out_path}")
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
    hoist_vars = {}
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
        hoist_vars[(batch, stage)] = (hoist_start, hoist_end, hoist_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time)
    # Synkronoi prosessivaiheiden ja nostintehtävien aikataulut
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        # Jos vaiheelle ei ole nostintehtävää (esim. yksi erä, yksi askel), älä sido alku/loppua mihinkään nostinmuuttujaan
        has_prev_hoist = (batch, stage) in hoist_vars
        has_next_hoist = (batch, stage + 1) in hoist_vars
        if not has_prev_hoist and not has_next_hoist:
            # Vain MinTime/MaxTime rajoittaa, ei sidontoja
            continue
        if stage == 1:
            model.Add(process_vars[(batch, stage)][0] == batch_start_vars[batch])
            if has_next_hoist:
                next_hoist = hoist_vars[(batch, stage + 1)]
                model.Add(process_vars[(batch, stage)][1] == next_hoist[0])
        else:
            if has_prev_hoist:
                prev_hoist = hoist_vars[(batch, stage)]
                model.Add(process_vars[(batch, stage)][0] == prev_hoist[1] - prev_hoist[8])
            if has_next_hoist:
                next_hoist = hoist_vars[(batch, stage + 1)]
                model.Add(process_vars[(batch, stage)][1] == next_hoist[0])
    # Nostintehtävien aikataulut: nosto alkaa prosessivaiheen lopusta, päättyy ennen seuraavan vaiheen alkua
    for (batch, stage), (hoist_start, hoist_end, hoist_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time) in hoist_vars.items():
        # Nostimen nosto alkaa prosessivaiheen lopusta
        model.Add(hoist_start == process_vars[(batch, stage)][1])
        # Nostimen lasku päättyy seuraavan prosessivaiheen alkuun, jos sellainen on
        if (batch, stage + 1) in process_vars:
            model.Add(hoist_end == process_vars[(batch, stage + 1)][0] + sink_time)
        # Jos viimeinen vaihe, nostimen laskun päättymistä ei sidota
    # Tallenna AddNoOverlap ja muut muuttujat
    tasks = {idx: (process_vars[(row["Batch"], row["Stage"] )][0], process_vars[(row["Batch"], row["Stage"] )][1], process_vars[(row["Batch"], row["Stage"] )][2], process_vars[(row["Batch"], row["Stage"] )][3], row) for idx, row in df.iterrows()}
    hoist_tasks = hoist_vars

    # Pakota yksi batch alkamaan ajassa 0 (ensimmäinen erä heti)
    first_batch_start = model.NewIntVar(0, 1000000, 'first_batch_start')
    model.AddMinEquality(first_batch_start, list(batch_start_vars.values()))
    model.Add(first_batch_start == 0)

    # (Nostintehtävät ja synkronointi on jo tehty yllä)

    # Nostintehtävien no-overlap (nostin ei voi tehdä kahta siirtoa samaan aikaan)
    if hoist_tasks:
        hoist_intervals = [v[2] for v in hoist_tasks.values()]
        print("[DEBUG] AddNoOverlap nostin (intervalit):")
        for (batch, stage), v in hoist_tasks.items():
            print(f"    Hoist interval: batch={batch} stage={stage} -> {v[2]}")
        model.AddNoOverlap(hoist_intervals)
    # Estä päällekkäisyys jokaisella fyysisellä asemalla (AddNoOverlap per asema)
    for station in stations_df["Number"]:
        station_task_indices = [idx for idx, row in df.iterrows() if int(row["Station"]) == station]
        intervals = [tasks[idx][2] for idx in station_task_indices]
        if len(intervals) > 1:
            print(f"[DEBUG] AddNoOverlap asema {station} (intervalit):")
            for idx in station_task_indices:
                print(f"    Process interval: batch={df.loc[idx, 'Batch']} stage={df.loc[idx, 'Stage']} -> {tasks[idx][2]}")
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

    # Tulosta nostintehtävien muuttujat ja rajat
    print("[DEBUG] Nostintehtävien muuttujat ja rajat:")
    for (batch, stage), v in hoist_tasks.items():
        hoist_start, hoist_end, hoist_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time = v
        print(f"    Batch {batch} Stage {stage}: hoist_start={hoist_start}, hoist_end={hoist_end}, interval={hoist_interval}, total_task_time={total_task_time}, from={from_station}, to={to_station}, lift={lift_time}, transfer={transfer_time}, sink={sink_time}")

    # Tulosta synkronointirajoitteet
    print("[DEBUG] Synkronointirajoitteet:")
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        msg = f"    Batch {batch} Stage {stage}: "
        if stage == 1:
            msg += f"start=batch_start_vars[{batch}]"
            if (batch, stage + 1) in hoist_tasks:
                msg += f"; end=hoist_start[{batch},{stage+1}]"
        else:
            if (batch, stage) in hoist_tasks:
                msg += f"start=hoist_end[{batch},{stage}]-sink_time"
            if (batch, stage + 1) in hoist_tasks:
                msg += f"; end=hoist_start[{batch},{stage+1}]"
        print(msg)

    # Tavoite: minimoi makespan (kaikkien vaiheiden päättymisajan maksimi)
    makespan = model.NewIntVar(0, 1000000, 'makespan')
    model.AddMaxEquality(makespan, [tasks[idx][1] for idx in tasks])
    model.Minimize(makespan)
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
    # logs_dir ja output_path on jo alustettu
        hoist_results = []
        # 1. Lisää normaalit nostintehtävät (vaiheiden väliset siirrot)
    for (batch, stage), (hoist_start_var, hoist_end_var, hoist_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time) in hoist_tasks.items():
            # Purku 9 kenttään, käytetään vain tarvittavat tallennukseen
            # Purku 9 kenttään, käytetään vain tarvittavat tallennukseen
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
