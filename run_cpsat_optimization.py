import os
import pandas as pd
from ortools.sat.python import cp_model

def run_cpsat_optimization(output_dir):
    # --- Lue kaikki data ennen mallin rakentamista ---
    preproc_dir = os.path.join(output_dir, "initialization")
    input_path = os.path.join(preproc_dir, "cpsat_preprocessed.csv")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    output_path = os.path.join(logs_dir, "cpsat_optimized.csv")
    df = pd.read_csv(input_path)
    # Poista rivit, joilla MinTime tai MaxTime puuttuu (NaN)
    df = df.dropna(subset=["MinTime", "MaxTime"]).copy()
    transfer_tasks_path = os.path.join(preproc_dir, "transfer_tasks.csv")
    transfer_tasks_df = pd.read_csv(transfer_tasks_path)

    # --- Lue kaikki data ennen mallin rakentamista ---
    preproc_dir = os.path.join(output_dir, "initialization")
    input_path = os.path.join(preproc_dir, "cpsat_preprocessed.csv")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    output_path = os.path.join(logs_dir, "cpsat_optimized.csv")
    df = pd.read_csv(input_path)
    # Lue transfer_tasks_df ennen debug-tulostusta
    transfer_tasks_path = os.path.join(preproc_dir, "transfer_tasks.csv")
    transfer_tasks_df = pd.read_csv(transfer_tasks_path)
    # Alusta hoist_intervals ja station_intervals debug-tulostusta varten
    hoist_intervals = []
    station_intervals = {}

    # --- CP-SAT malli: Nostin + Min/Max + synkronointi ---
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()
    # Horizon asetetaan reilusti isoksi (10x suurin mahdollinen prosessiaika)
    max_stage_time = df[["MaxTime"]].apply(lambda x: pd.to_timedelta(x).dt.total_seconds()).max().values[0]
    horizon = int(10 * max_stage_time * len(df))
    batch_start_vars = {}
    for batch in sorted(df["Batch"].unique()):
        batch_start_vars[batch] = model.NewIntVar(0, horizon, f"batch_start_{batch}")
    hoist_intervals = []
    hoist_starts = []
    hoist_ends = []
    process_starts = {}
    process_ends = {}
    for idx, row in df.iterrows():
        batch = int(row["Batch"])
        stage = int(row["Stage"])
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        # Prosessimuuttujat luodaan aina (myös stage==1)
        process_start = model.NewIntVar(0, horizon, f"process_start_{batch}_{stage}")
        process_end = model.NewIntVar(0, horizon, f"process_end_{batch}_{stage}")
        process_starts[(int(batch), int(stage))] = process_start
        process_ends[(int(batch), int(stage))] = process_end
        duration = model.NewIntVar(min_time, max_time, f"duration_{batch}_{stage}")
        model.Add(process_end - process_start == duration)
        if stage == 0:
            continue
        prev_idx = df[(df["Batch"] == batch) & (df["Stage"] == stage - 1)].index
        if len(prev_idx) == 0:
            continue
        prev_row = df.loc[prev_idx[0]]
        from_station = int(prev_row["Station"])
        to_station = int(row["Station"])
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == from_station) & (transfer_tasks_df["to_station"] == to_station)]
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        # Nostintehtävä
        hoist_start = model.NewIntVar(0, horizon, f"hoist_start_{batch}_{stage}")
        hoist_end = model.NewIntVar(0, horizon, f"hoist_end_{batch}_{stage}")
        hoist_interval = model.NewIntervalVar(hoist_start, total_task_time, hoist_end, f"hoist_interval_{batch}_{stage}")
        hoist_intervals.append(hoist_interval)
        hoist_starts.append(hoist_start)
        hoist_ends.append(hoist_end)
        # Synkronointi nostimen ja prosessin välillä
        model.Add(process_start == hoist_end - sink_time)
        # Jos tämä EI ole viimeinen vaihe tälle erälle, synkronoi prosessivaiheen loppu nostimen nostoon
        is_last_stage = (stage == df[df["Batch"] == batch]["Stage"].max())
        if not is_last_stage:
            model.Add(process_end == hoist_start + lift_time)
        # Jos viimeinen vaihe, prosessivaiheen loppu = alku + duration (vapaa MinTime–MaxTime)
    # Ensimmäisen vaiheen alku = batch_start
    for batch in sorted(df["Batch"].unique()):
        batch_int = int(batch)
        idx = df[(df["Batch"] == batch_int) & (df["Stage"] == 1)].index
        if len(idx) == 0:
            continue
        process_start = process_starts[(batch_int, 1)]
        model.Add(process_start == batch_start_vars[batch_int])
    # AddNoOverlap nostintehtäville
    model.AddNoOverlap(hoist_intervals)
    # Optimoidaan makespan
    makespan = model.NewIntVar(0, horizon, "makespan")
    model.AddMaxEquality(makespan, hoist_ends)
    model.Minimize(makespan)
    # Ratkaise
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    print(f"[DEBUG] Ratkaisun status: {status} (4=OPTIMAL, 2=FEASIBLE, 3=INFEASIBLE, 1=MODEL_INVALID)")
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print("[DEBUG] Nostintehtävien aikataulu:")
        for i, interval in enumerate(hoist_intervals):
            s = solver.Value(hoist_starts[i])
            e = solver.Value(hoist_ends[i])
            print(f"  {interval.Name()}: start={s}, end={e}")
        print(f"[DEBUG] Makespan: {solver.Value(makespan)}")
        print("[DEBUG] Batchien start-ajat:")
        for batch in sorted(df["Batch"].unique()):
            print(f"  batch_start_{batch} = {solver.Value(batch_start_vars[batch])}")
    else:
        print("[DEBUG] Ei ratkaisua!")
    return
    # --- Lue kaikki data ennen mallin rakentamista ---
    preproc_dir = os.path.join(output_dir, "initialization")
    input_path = os.path.join(preproc_dir, "cpsat_preprocessed.csv")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    output_path = os.path.join(logs_dir, "cpsat_optimized.csv")
    df = pd.read_csv(input_path)

    # --- DEBUG: Tarkista mahdolliset mahdottomat aikavälit ennen mallin rakentamista ---
    print("[DEBUG] TARKISTUS: Prosessivaiheiden minimi kesto vs. siirtojen yhteisaika")
    impossible = False
    transfer_tasks_path = os.path.join(preproc_dir, "transfer_tasks.csv")
    transfer_tasks_df = pd.read_csv(transfer_tasks_path)
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        # Etsi edellinen asema (askel 0 huomioiden)
        prev_idx = df[(df["Batch"] == batch) & (df["Stage"] == stage - 1)].index
        if len(prev_idx) == 0:
            continue
        prev_row = df.loc[prev_idx[0]]
        from_station = int(prev_row["Station"])
        to_station = int(row["Station"])
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == from_station) & (transfer_tasks_df["to_station"] == to_station)]
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        # Prosessivaiheen minimi kesto pitää olla >= 0 (tai mieluummin > 0)
        if min_time < 0:
            print(f"[VIRHE] Batch {batch} Stage {stage}: MinTime < 0!")
            impossible = True
        # Jos prosessivaiheen minimi kesto on pienempi kuin nostimen siirron kesto, se on mahdoton
        if min_time < total_task_time:
            print(f"[VIRHE] Batch {batch} Stage {stage}: MinTime ({min_time}) < siirron kesto ({total_task_time}) → MAHDOTON!")
            impossible = True
        print(f"    Batch {batch} Stage {stage}: MinTime={min_time}, MaxTime={max_time}, Siirron kesto={total_task_time}")
    if impossible:
        print("[VIRHE] Löytyi mahdottomia prosessivaiheita! Tarkista MinTime ja siirtojen kestot.")

    stations_path = os.path.join(preproc_dir, "stations.csv")
    stations_df = pd.read_csv(stations_path)

    # --- DEBUG: Tarkista mahdolliset mahdottomat aikavälit ennen mallin rakentamista ---
    print("[DEBUG] TARKISTUS: Prosessivaiheiden minimi kesto vs. siirtojen yhteisaika")
    impossible = False
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        # Etsi edellinen asema (askel 0 huomioiden)
        prev_idx = df[(df["Batch"] == batch) & (df["Stage"] == stage - 1)].index
        if len(prev_idx) == 0:
            continue
        prev_row = df.loc[prev_idx[0]]
        from_station = int(prev_row["Station"])
        to_station = int(row["Station"])
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == from_station) & (transfer_tasks_df["to_station"] == to_station)]
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        # Prosessivaiheen minimi kesto pitää olla >= 0 (tai mieluummin > 0)
        if min_time < 0:
            print(f"[VIRHE] Batch {batch} Stage {stage}: MinTime < 0!")
            impossible = True
        # Jos prosessivaiheen minimi kesto on pienempi kuin nostimen siirron kesto, se on mahdoton
        if min_time < total_task_time:
            print(f"[VIRHE] Batch {batch} Stage {stage}: MinTime ({min_time}) < siirron kesto ({total_task_time}) → MAHDOTON!")
            impossible = True
        print(f"    Batch {batch} Stage {stage}: MinTime={min_time}, MaxTime={max_time}, Siirron kesto={total_task_time}")
    if impossible:
        print("[VIRHE] Löytyi mahdottomia prosessivaiheita! Tarkista MinTime ja siirtojen kestot.")

    # --- DEBUG: Tarkista mahdolliset mahdottomat aikavälit ennen mallin rakentamista ---
    print("[DEBUG] TARKISTUS: Prosessivaiheiden minimi kesto vs. siirtojen yhteisaika")
    impossible = False
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        # Etsi edellinen asema (askel 0 huomioiden)
        prev_idx = df[(df["Batch"] == batch) & (df["Stage"] == stage - 1)].index
        if len(prev_idx) == 0:
            continue
        prev_row = df.loc[prev_idx[0]]
        from_station = int(prev_row["Station"])
        to_station = int(row["Station"])
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == from_station) & (transfer_tasks_df["to_station"] == to_station)]
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        # Prosessivaiheen minimi kesto pitää olla >= 0 (tai mieluummin > 0)
        if min_time < 0:
            print(f"[VIRHE] Batch {batch} Stage {stage}: MinTime < 0!")
            impossible = True
        # Jos prosessivaiheen minimi kesto on pienempi kuin nostimen siirron kesto, se on mahdoton
        if min_time < total_task_time:
            print(f"[VIRHE] Batch {batch} Stage {stage}: MinTime ({min_time}) < siirron kesto ({total_task_time}) → MAHDOTON!")
            impossible = True
        print(f"    Batch {batch} Stage {stage}: MinTime={min_time}, MaxTime={max_time}, Siirron kesto={total_task_time}")
    if impossible:
        print("[VIRHE] Löytyi mahdottomia prosessivaiheita! Tarkista MinTime ja siirtojen kestot.")
    # 1. Optimoidaan nostimen tehtävien (nosto, siirto, lasku) ajoitukset vapaasti.
    # 2. Jokainen nostintehtävä (batch, stage):
    #    - lift_start: milloin nostin nostaa erän asemalta
    #    - sink_end: milloin nostin laskee erän seuraavalle asemalle
    #    - Näiden väli = siirtotehtävän kokonaisaika (lift + transfer + sink)
    # 3. Prosessivaiheen alku = edellisen nostotehtävän sink_end, loppu = tämän vaiheen nostotehtävän lift_start
    #    - Prosessiaika = lift_start - sink_end ∈ [MinTime, MaxTime]
    #    - Prosessivaiheiden ajat määräytyvät nostimen liikkeiden mukaan
    # 4. AddNoOverlap nostintehtäville (nostin ei tee kahta siirtoa yhtä aikaa)
    # 5. AddNoOverlap asemille (asemalla vain yksi erä kerrallaan)
    # 6. Kaikki siirtotehtävät tehdään oikeassa järjestyksessä, makespan minimoidaan
    # 7. Optimointi etsii nostimelle nopeimman mahdollisen reitin, joka täyttää kaikki rajoitteet
    model = cp_model.CpModel()
    batches = sorted(df["Batch"].unique())
    stages = sorted(df["Stage"].unique())
    # Jokaiselle batchille vapaasti optimoitava aloitus (ensimmäisen vaiheen sink_end)
    # Ei sidota batchien järjestystä eikä startteja – kaikki vapaasti optimoitavia
    batch_start_vars = {batch: model.NewIntVar(0, 1000000, f'batch_start_{batch}') for batch in batches}
    # Nostintehtävien muuttujat: (lift_start, sink_end, interval)
    hoist_vars = {}
    # 1. Luo "virtuaalinen" nostintehtävä start_station -> ensimmäinen asema jokaiselle batchille
    production_path = os.path.join(preproc_dir, "production.csv")
    prod_df = pd.read_csv(production_path)
    for _, prod_row in prod_df.iterrows():
        batch = prod_row["Batch"]
        start_station = int(prod_row["Start_station"])
        # Etsi tämän erän ensimmäinen vaihe (stage==1)
        first_row = df[(df["Batch"] == batch) & (df["Stage"] == 1)]
        if first_row.empty:
            continue
        first_row = first_row.iloc[0]
        to_station = int(first_row["Station"])
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == start_station) & (transfer_tasks_df["to_station"] == to_station)]
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        # Ensimmäisen vaiheen alku = batch_start_vars[batch], loppu = noston alku
        lift_start = model.NewIntVar(0, 1000000, f'lift_start_{batch}_0')
        sink_end = model.NewIntVar(0, 1000000, f'sink_end_{batch}_0')
        hoist_interval = model.NewIntervalVar(lift_start, total_task_time, sink_end, f'hoist_interval_{batch}_0')
        hoist_vars[(batch, 0)] = {
            "lift_start": lift_start,
            "sink_end": sink_end,
            "interval": hoist_interval,
            "lift_time": lift_time,
            "transfer_time": transfer_time,
            "sink_time": sink_time,
            "total_task_time": total_task_time,
            "from_station": start_station,
            "to_station": to_station
        }
        # Yhdistä nostotehtävän alku/loppu siirron osiin
        lift_end = model.NewIntVar(0, 1000000, f'lift_end_{batch}_0')
        transfer_end = model.NewIntVar(0, 1000000, f'transfer_end_{batch}_0')
        model.Add(lift_end == lift_start + lift_time)
        model.Add(transfer_end == lift_end + transfer_time)
        model.Add(sink_end == transfer_end + sink_time)

    # 2. Luo varsinaiset nostintehtävät vaiheiden välillä
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        from_station = int(row["Station"])
        # Etsi seuraava vaihe (paitsi viimeinen)
        if stage == max(stages):
            continue
        next_idx = df[(df["Batch"] == batch) & (df["Stage"] == stage + 1)].index
        if len(next_idx) == 0:
            continue
        to_station = int(df.loc[next_idx[0], "Station"])
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == from_station) & (transfer_tasks_df["to_station"] == to_station)]
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        lift_start = model.NewIntVar(0, 1000000, f'lift_start_{batch}_{stage}')
        sink_end = model.NewIntVar(0, 1000000, f'sink_end_{batch}_{stage}')
        hoist_interval = model.NewIntervalVar(lift_start, total_task_time, sink_end, f'hoist_interval_{batch}_{stage}')
        hoist_vars[(batch, stage)] = {
            "lift_start": lift_start,
            "sink_end": sink_end,
            "interval": hoist_interval,
            "lift_time": lift_time,
            "transfer_time": transfer_time,
            "sink_time": sink_time,
            "total_task_time": total_task_time,
            "from_station": from_station,
            "to_station": to_station
        }
        lift_end = model.NewIntVar(0, 1000000, f'lift_end_{batch}_{stage}')
        transfer_end = model.NewIntVar(0, 1000000, f'transfer_end_{batch}_{stage}')
        model.Add(lift_end == lift_start + lift_time)
        model.Add(transfer_end == lift_end + transfer_time)
        model.Add(sink_end == transfer_end + sink_time)
    # Prosessivaiheiden alku/loppu määräytyy nostimen mukaan
    process_vars = {}
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        # Prosessivaiheen alku = edellisen noston sink_end, loppu = tämän vaiheen noston lift_start
        if stage == 1:
            prev_hoist = hoist_vars.get((batch, 0))
        else:
            prev_hoist = hoist_vars.get((batch, stage - 1))
        this_hoist = hoist_vars.get((batch, stage))
        if prev_hoist and this_hoist:
            start_var = prev_hoist["sink_end"]
            end_var = this_hoist["lift_start"]
            # Prosessivaiheen kesto määräytyy nostimen liikkeiden mukaan
            # Vain rajoite: käsittelyaika ∈ [MinTime, MaxTime]
            model.Add(end_var - start_var >= min_time)
            model.Add(end_var - start_var <= max_time)
            # Tallennetaan muuttujat tulostusta varten
            duration_var = model.NewIntVar(min_time, max_time, f'duration_{batch}_{stage}')
            interval = model.NewIntervalVar(start_var, duration_var, end_var, f'interval_{batch}_{stage}')
            process_vars[(batch, stage)] = (start_var, end_var, duration_var, interval)
    # AddNoOverlap nostintehtäville (myös stage=0)
    hoist_intervals = [v["interval"] for v in hoist_vars.values()]
    model.AddNoOverlap(hoist_intervals)
    # AddNoOverlap asemille (prosessivaiheiden intervalleille per asema) -- POISTETTU TESTIN VUOKSI
    # model.AddNoOverlap(intervals)  # POISTETTU
    # Vain yksi batch voidaan pakottaa alkamaan ajassa 0, mutta järjestys ja muut startit ovat vapaita
    first_batch_start = model.NewIntVar(0, 1000000, 'first_batch_start')
    model.AddMinEquality(first_batch_start, list(batch_start_vars.values()))
    model.Add(first_batch_start == 0)
    # Makespan
    makespan = model.NewIntVar(0, 1000000, 'makespan')
    # Käytä vain niitä (batch, stage), jotka löytyvät process_vars:sta
    makespan_ends = [v[1] for k, v in process_vars.items()]
    model.AddMaxEquality(makespan, makespan_ends)
    model.Minimize(makespan)

    # --- KATTAVA DEBUG-TULOSTUS ENNEN RATKAISUA ---

    # --- TULOSTA KAIKKI LISÄTYT RAJOITTEET ---

    # Ratkaise
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    solver.parameters.max_time_in_seconds = 60.0
    solver.parameters.search_branching = cp_model.AutomaticSearch
    print("[DEBUG] Mallin rakentaminen valmis, ratkaistaan (log_search_progress päällä, time_limit=60s)...")
    status = solver.Solve(model)
    print(f"[DEBUG] Ratkaisun status: {status} ({cp_model.OPTIMAL}=OPTIMAL, {cp_model.FEASIBLE}=FEASIBLE, {cp_model.INFEASIBLE}=INFEASIBLE, {cp_model.MODEL_INVALID}=MODEL_INVALID)")
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
            # Jos dict, käytä avaimia, muuten tuple
            if isinstance(hoist, dict):
                hoist_results.append({
                    "Batch": batch,
                    "Stage": stage,
                    "From_Station": hoist["from_station"],
                    "To_Station": hoist["to_station"],
                    "Hoist_Lift_Start": solver.Value(hoist["lift_start"]),
                    "Hoist_Sink_End": solver.Value(hoist["sink_end"]),
                    "Lift_Time": hoist["lift_time"],
                    "Transfer_Time": hoist["transfer_time"],
                    "Sink_Time": hoist["sink_time"],
                    "Total_Task_Time": hoist["total_task_time"]
                })
            else:
                (lift_start, sink_end, hoist_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time) = hoist
                hoist_results.append({
                    "Batch": batch,
                    "Stage": stage,
                    "From_Station": from_station,
                    "To_Station": to_station,
                    "Hoist_Lift_Start": solver.Value(lift_start),
                    "Hoist_Sink_End": solver.Value(sink_end),
                    "Lift_Time": lift_time,
                    "Transfer_Time": transfer_time,
                    "Sink_Time": sink_time,
                    "Total_Task_Time": total_task_time
                })
        if hoist_results:
            hoist_df = pd.DataFrame(hoist_results)
            hoist_df = hoist_df.sort_values(["Batch", "Hoist_Lift_Start"]).reset_index(drop=True)
            hoist_out_path = os.path.join(logs_dir, "transporter_tasks_optimized.csv")
            hoist_df.to_csv(hoist_out_path, index=False)
            print(f"[CP-SAT] Nostintehtävät tallennettu: {hoist_out_path}")
    else:
        print("[CP-SAT] Ei ratkaisua.")
    # ...existing code...
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
    # --- DEBUG: Tulosta nostintehtävien rakenne ja AddNoOverlap/synkronointi ---
    print("[DEBUG] Nostintehtävien rakenne (ennen mallin rakentamista):")
    temp_hoist_vars = {}
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        prev_idx = df[(df["Batch"] == batch) & (df["Stage"] == stage - 1)].index
        if len(prev_idx) == 0:
            continue
        prev_row = df.loc[prev_idx[0]]
        from_station = int(prev_row["Station"])
        to_station = int(row["Station"])
        t_row = transfer_tasks_df[(transfer_tasks_df["from_station"] == from_station) & (transfer_tasks_df["to_station"] == to_station)]
        if t_row.empty:
            continue
        lift_time = int(t_row.iloc[0]["lift_time"])
        transfer_time = int(t_row.iloc[0]["transfer_time"])
        sink_time = int(t_row.iloc[0]["sink_time"])
        total_task_time = int(t_row.iloc[0]["total_task_time"])
        temp_hoist_vars[(batch, stage)] = (from_station, to_station, lift_time, transfer_time, sink_time, total_task_time)
        print(f"  Batch {batch} Stage {stage}: {from_station}->{to_station} lift={lift_time} transfer={transfer_time} sink={sink_time} total={total_task_time}")

    print("[DEBUG] AddNoOverlap asema- ja nostinrajoitteet:")
    for station in stations_df["Number"]:
        station_task_indices = [idx for idx, row in df.iterrows() if int(row["Station"]) == station]
        print(f"  Station {station}: {len(station_task_indices)} vaihetta")
    print(f"  Nostintehtäviä: {len(temp_hoist_vars)}")

    print("[DEBUG] Synkronointilogiikka (prosessin alku/loppu, nostimen nosto/lasku):")
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        msg = f"  Batch {batch} Stage {stage}: "
        if stage == 1:
            msg += f"start=batch_start[{batch}]"
            if (batch, stage + 1) in temp_hoist_vars:
                msg += f"; end=hoist_start[{batch},{stage+1}]"
        else:
            if (batch, stage) in temp_hoist_vars:
                msg += f"start=hoist_end[{batch},{stage}]-sink"
            if (batch, stage + 1) in temp_hoist_vars:
                msg += f"; end=hoist_start[{batch},{stage+1}]"
        print(msg)
    # ...existing code...

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
    print("[DEBUG] Prosessivaiheiden muuttujat ja rajat:")
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        print(f"  Batch {batch} Stage {stage}: MinTime={min_time}, MaxTime={max_time}")
    print("[DEBUG] Asemat ja ryhmät:")
    for _, srow in stations_df.iterrows():
        print(f"  Station {srow['Number']} (Group {srow['Group']})")
    print("[DEBUG] Siirtotehtävät:")
    for _, trow in transfer_tasks_df.iterrows():
        print(f"  {trow['from_station']} -> {trow['to_station']}: lift={trow['lift_time']}, transfer={trow['transfer_time']}, sink={trow['sink_time']}, total={trow['total_task_time']}")
    print("[DEBUG] Asemat ja ryhmät:")
    for _, srow in stations_df.iterrows():
        print(f"  Station {srow['Number']} (Group {srow['Group']})")
    print("[DEBUG] Siirtotehtävät:")
    for _, trow in transfer_tasks_df.iterrows():
        print(f"  {trow['from_station']} -> {trow['to_station']}: lift={trow['lift_time']}, transfer={trow['transfer_time']}, sink={trow['sink_time']}, total={trow['total_task_time']}")
    # DEBUG PRINTS: after all data is loaded, before model building
    print("[DEBUG] Prosessivaiheiden muuttujat ja rajat:")
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
        max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
        print(f"  Batch {batch} Stage {stage}: MinTime={min_time}, MaxTime={max_time}")

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
        hoist_vars[(batch, stage)] = (hoist_start, hoist_end, hoist_interval, total_task_time, from_station, to_station, lift_time, transfer_time, sink_time)
    # Synkronoi prosessivaiheiden ja nostintehtävien aikataulut
    for idx, row in df.iterrows():
        batch = row["Batch"]
        stage = row["Stage"]
        # Ensimmäinen vaihe: alku = batch_start, loppu = seuraavan nostimen nosto (jos on)
        if stage == 1:
            model.Add(process_vars[(batch, stage)][0] == batch_start_vars[batch])
            next_hoist = hoist_vars.get((batch, stage + 1))
            if next_hoist:
                model.Add(process_vars[(batch, stage)][1] == next_hoist[0])
        else:
            prev_hoist = hoist_vars.get((batch, stage))
            if prev_hoist:
                # Prosessivaiheen alku = edellisen nostimen lasku päättyy (eli hoist_end - sink_time)
                model.Add(process_vars[(batch, stage)][0] == prev_hoist[1] - prev_hoist[8])
            next_hoist = hoist_vars.get((batch, stage + 1))
            if next_hoist:
                model.Add(process_vars[(batch, stage)][1] == next_hoist[0])
        # Jos viimeinen vaihe (ei seuraavaa hoistia), jätä loppu vapaaksi (vain kestoa rajoittaa Min/Max)
        if (batch, stage + 1) not in hoist_vars:
            # Ei sidota prosessivaiheen loppua mihinkään
            pass
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
