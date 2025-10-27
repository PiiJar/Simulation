import os
import pandas as pd
from ortools.sat.python import cp_model


def cp_sat_optimize(output_dir):
    # ...existing code...
    # treatment_programs-täytön jälkeen:
    treatment_programs = {}
    batches = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-batches.csv"))
    all_batches = set(int(b) for b in batches["Batch"])
    stations = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-transfer-tasks.csv"))
    for batch in batches["Batch"]:
        batch_int = int(batch)
        fname = os.path.join(output_dir, "initialization", f"cp-sat-treatment-program-{batch_int}.csv")
        if not os.path.exists(fname):
            raise FileNotFoundError(f"Käsittelyohjelmatiedostoa ei löydy: {fname}")
        df = pd.read_csv(fname)
        if "Station" not in df.columns:
            df["Station"] = df["MinStat"]
        treatment_programs[batch_int] = df

    model = cp_model.CpModel()
    MAX_TIME = 10**6
    task_vars = {}
    batches_in_task_vars = set()
    for batch in batches["Batch"]:
        batch_int = int(batch)
        print(f"\n========== [DEBUG: CP-SAT AIKARAJAT, batch={batch_int}] ==========")
        program = treatment_programs[batch_int]
        last_idx = len(program) - 1
        prev_end_var = None
        for idx, row in program.iterrows():
            stage = int(row["Stage"])
            min_stat = int(row["MinStat"])
            max_stat = int(row["MaxStat"])
            min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
            max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
            possible_stations = stations[
                (stations["Number"] >= min_stat) &
                (stations["Number"] <= max_stat)
            ]["Number"].tolist()
            print(f"[DEBUG] batch={batch_int} stage={stage} min_stat={min_stat} max_stat={max_stat} possible_stations={possible_stations} min_time={min_time} max_time={max_time}")
            if not possible_stations:
                print(f"[CP-SAT] OHITUS: batch={batch_int} stage={stage} -- Ei mahdollisia asemia (MinStat={min_stat}, MaxStat={max_stat})")
                print(f"  Tarkista cp-sat-treatment-program-{batch_int}.csv ja cp-sat-stations.csv")
                print(f"  Ohjelman rivi: {row}")
                continue
            batches_in_task_vars.add(batch_int)
            duration_var = model.NewIntVar(min_time, max_time, f"duration_{batch_int}_{stage}")
            start_var = model.NewIntVar(0, MAX_TIME, f"start_{batch_int}_{stage}")
            end_var = model.NewIntVar(0, MAX_TIME, f"end_{batch_int}_{stage}")
            station_domain = cp_model.Domain.FromValues(possible_stations)
            station_var = model.NewIntVarFromDomain(station_domain, f"station_{batch_int}_{stage}")
            station_bools = []
            intervals = []
            for s in possible_stations:
                is_this_station = model.NewBoolVar(f"is_{batch_int}_{stage}_at_{s}")
                model.Add(station_var == s).OnlyEnforceIf(is_this_station)
                model.Add(station_var != s).OnlyEnforceIf(is_this_station.Not())
                interval = model.NewOptionalIntervalVar(start_var, duration_var, end_var, is_this_station, f"interval_{batch_int}_{stage}_at_{s}")
                station_bools.append(is_this_station)
                intervals.append((s, interval, is_this_station))
            model.AddAllowedAssignments([station_var], [[s] for s in possible_stations])
            model.Add(sum(station_bools) == 1)
            model.Add(end_var == start_var + duration_var)
            task_vars[(batch_int, stage)] = {
                "start": start_var,
                "end": end_var,
                "station": station_var,
                "duration": duration_var,
                "station_bools": station_bools,
                "intervals": intervals,
                "possible_stations": possible_stations,
                "is_last": idx == last_idx
            }
            prev_end_var = end_var

    # --- DEBUG: Tulosta kaikkien muuttujien domainit ja rajoitteet ---
    print("\n========== [DEBUG: MUUTTUJIEN DOMAINIT ENNEN RATKAISUA] ==========")
    for (batch, stage), vars in task_vars.items():
        print(f"  Batch {batch} Stage {stage}: possible_stations = {vars['possible_stations']}")
        print(f"    start: 0..{MAX_TIME}, end: 0..{MAX_TIME}, duration: {vars['duration'].Proto().domain}")
    print("\n========== [DEBUG: Rajoitteet: siirrot ja asemat] ==========")
    for (batch, stage), vars in task_vars.items():
        print(f"  (batch={batch}, stage={stage})")
        print(f"    station domain: {vars['possible_stations']}")
        # Siirtoedellytykset ja asemat
        if stage > 0:
            program = treatment_programs[batch]
            prev_station = int(program.loc[stage - 1, "Station"])
            this_station = int(program.loc[stage, "Station"])
            mask = (transfers["from_station"] == prev_station) & (transfers["to_station"] == this_station)
            if mask.any():
                transfer_time = int(transfers[mask].iloc[0]["transfer_time"])
            else:
                transfer_time = 0
            print(f"    [DEBUG] Siirto: {prev_station} -> {this_station}, aika={transfer_time}")
        else:
            print(f"    [DEBUG] Ensimmäinen vaihe, ei siirtoa")
        if stage < len(treatment_programs[batch]) - 1:
            this_station = int(treatment_programs[batch].loc[stage, "Station"])
            next_station = int(treatment_programs[batch].loc[stage + 1, "Station"])
            print(f"    [DEBUG] Seuraava vaihe: {this_station} -> {next_station}")
        else:
            print(f"    [DEBUG] Viimeinen vaihe")
    print(f"Kaikki erät: {sorted(all_batches)}")
    print(f"Erät task_vars:ssa: {sorted(batches_in_task_vars)}")
    missing = all_batches - batches_in_task_vars
    if missing:
        print(f"PUUTTUVAT ERÄT: {sorted(missing)} (näille ei muodostunut tehtäviä)")
        raise Exception(f"KOKO TUOTANNON SIMULOINTI EPÄONNISTUI: Seuraaville erille ei muodostunut tehtäviä: {sorted(missing)}. Tarkista syötedata ja rajoitteet.")
    else:
        print("Kaikki erät mukana task_vars:ssa.")
    print("========== [DEBUG: ERÄT TASK_VARS:SSA] ==========")

    # --- NOSTIMEN RESURSSIRAJOIN ---
    # Mallinna kaikki nostimen siirtotehtävät interval-muuttujina (tämä tehdään vasta kun task_vars on täytetty ja kaikki muut rajoitteet on lisätty)
    hoist_tasks = []  # (interval_var, kuvaus)
    for (batch, stage), vars in task_vars.items():
        # Siirto edelliseltä asemalta tälle asemalle (paitsi ensimmäinen vaihe)
        if stage > 0:
            program = treatment_programs[batch]
            prev_station = int(program.loc[stage - 1, "Station"])
            this_station = int(program.loc[stage, "Station"])
            mask = (transfers["from_station"] == prev_station) & (transfers["to_station"] == this_station)
            if mask.any():
                transfer_time = int(transfers[mask].iloc[0]["transfer_time"])
            else:
                transfer_time = 0
            transfer_start = model.NewIntVar(0, MAX_TIME, f"hoist_transfer_start_b{batch}_s{stage}")
            transfer_end = model.NewIntVar(0, MAX_TIME, f"hoist_transfer_end_b{batch}_s{stage}")
            transfer_interval = model.NewIntervalVar(transfer_start, transfer_time, transfer_end, f"hoist_transfer_b{batch}_s{stage}")
            # Siirto päättyy, kun erä saapuu uudelle asemalle (eli vars["start"])
            model.Add(transfer_end == vars["start"])
            # Siirto alkaa transfer_time ennen vars["start"]
            model.Add(transfer_start == vars["start"] - transfer_time)
            hoist_tasks.append((transfer_interval, f"b{batch}_s{stage}_move"))
        # Vienti asemalta pois (paitsi viimeinen vaihe)
        program = treatment_programs[batch]
        if stage < len(program) - 1:
            this_station = int(program.loc[stage, "Station"])
            next_station = int(program.loc[stage + 1, "Station"])
            mask = (transfers["from_station"] == this_station) & (transfers["to_station"] == next_station)
            if mask.any():
                transfer_time = int(transfers[mask].iloc[0]["transfer_time"])
            else:
                transfer_time = 0
            transfer_start = model.NewIntVar(0, MAX_TIME, f"hoist_transferout_start_b{batch}_s{stage}")
            transfer_end = model.NewIntVar(0, MAX_TIME, f"hoist_transferout_end_b{batch}_s{stage}")
            transfer_interval = model.NewIntervalVar(transfer_start, transfer_time, transfer_end, f"hoist_transferout_b{batch}_s{stage}")
            # Siirto alkaa vars["end"]
            model.Add(transfer_start == vars["end"])
            # Siirto päättyy transfer_time myöhemmin
            model.Add(transfer_end == vars["end"] + transfer_time)
            hoist_tasks.append((transfer_interval, f"b{batch}_s{stage}_out"))
    # Nostimen resurssirajoite: ei päällekkäisiä siirtoja
    if hoist_tasks:
        model.AddNoOverlap([interval for interval, _ in hoist_tasks])

    solver = cp_model.CpSolver()
    # Makespan: viimeisen valmistuvan erän viimeisen vaiheen päättymisajan maksimi
    last_ends = []
    for (batch, stage), vars in task_vars.items():
        if vars["is_last"]:
            last_ends.append(vars["end"])
    if last_ends:
        makespan = model.NewIntVar(0, MAX_TIME, "makespan")
        model.AddMaxEquality(makespan, last_ends)
        model.Minimize(makespan)
    status = solver.Solve(model)
    status_str = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID", cp_model.UNKNOWN: "UNKNOWN"}.get(status, str(status))
    print(f"[CP-SAT] Solver status: {status} ({status_str})")
    print(f"[CP-SAT] Wall time: {solver.WallTime()}s, Conflicts: {solver.NumConflicts()}, Branches: {solver.NumBranches()}")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Sääntö 1: Vaiheiden järjestys katetaan siirtoaikarajoitteella (ei erillistä järjestysrajoitetta)

    # Sääntö 2: Käsittelyaikojen min/max (sisältyy duration_varin rajoihin)

    # Sääntö 3: Asemalla vain yksi erä kerrallaan (AddNoOverlap per asema, vain aktiiviset OptionalIntervalVar:t)
    # --- Eksplisiittinen siirtoaikarajoite: asema tyhjä ennen seuraavaa erää ---
    # Poistettu päällekkäiset järjestysrajoitteet batch-pareilta asemalla. AddNoOverlap riittää.
    for station in stations["Number"]:
        intervals = []
        for (batch, stage), vars in task_vars.items():
            for s, interval, is_this_station in vars["intervals"]:
                if s == station:
                    # Käytetään vain OptionalIntervalVar, joka on aktiivinen kun asema == station (is_this_station)
                    intervals.append(interval)
        # AddNoOverlap käyttää OptionalIntervalVar-muuttujia, jotka ovat aktiivisia vain kun asema == station
        if intervals:
            model.AddNoOverlap(intervals)

    # Sääntö 4: Nostimen siirtoajat (fysiikkaan perustuvat, haetaan transfers-taulukosta)
    # Siirto- ja järjestysrajoitteet: seuraava vaihe alkaa vasta kun edellinen päättyy + siirtoaika
    for batch in batches["Batch"]:
        program = treatment_programs[batch]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            if (batch, prev_stage) in task_vars and (batch, this_stage) in task_vars:
                prev_vars = task_vars[(batch, prev_stage)]
                this_vars = task_vars[(batch, this_stage)]
                for from_stat in prev_vars["possible_stations"]:
                    for to_stat in this_vars["possible_stations"]:
                        mask = (transfers["from_station"] == from_stat) & (transfers["to_station"] == to_stat)
                        if not mask.any():
                            continue
                        total_time = int(transfers[mask].iloc[0]["total_task_time"])
                        print(f"[DEBUG] batch={batch} prev_stage={prev_stage}({from_stat}) -> this_stage={this_stage}({to_stat}) siirtoaika={total_time}")
                        # Reifioitu ehto: prev_station==from_stat AND this_station==to_stat
                        cond_prev = model.NewBoolVar(f"prev_{batch}_{prev_stage}_at_{from_stat}")
                        cond_this = model.NewBoolVar(f"this_{batch}_{this_stage}_at_{to_stat}")
                        model.Add(prev_vars["station"] == from_stat).OnlyEnforceIf(cond_prev)
                        model.Add(prev_vars["station"] != from_stat).OnlyEnforceIf(cond_prev.Not())
                        model.Add(this_vars["station"] == to_stat).OnlyEnforceIf(cond_this)
                        model.Add(this_vars["station"] != to_stat).OnlyEnforceIf(cond_this.Not())
                        both = model.NewBoolVar(f"both_{batch}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}")
                        model.AddBoolAnd([cond_prev, cond_this]).OnlyEnforceIf(both)
                        model.AddBoolOr([cond_prev.Not(), cond_this.Not()]).OnlyEnforceIf(both.Not())
                        # Jos duration==0 (min_time==0 ja max_time==0), sidotaan start==end==prev_end+total_time
                        min_time = this_vars["duration"].Proto().domain[0]
                        max_time = this_vars["duration"].Proto().domain[-1]
                        # Jos duration voi olla nolla, reifioidaan ehto duration==0
                        if min_time == 0:
                            is_zero_duration = model.NewBoolVar(f"is_zero_duration_{batch}_{this_stage}")
                            model.Add(this_vars["duration"] == 0).OnlyEnforceIf(is_zero_duration)
                            model.Add(this_vars["duration"] != 0).OnlyEnforceIf(is_zero_duration.Not())
                            # Jos duration==0 ja both, sidotaan start==end==prev_end+total_time
                            model.Add(this_vars["start"] == prev_vars["end"] + total_time).OnlyEnforceIf([both, is_zero_duration])
                            model.Add(this_vars["end"] == prev_vars["end"] + total_time).OnlyEnforceIf([both, is_zero_duration])
                            # Jos duration>0 ja both, normaali siirtorajoite
                            model.Add(this_vars["start"] >= prev_vars["end"] + total_time).OnlyEnforceIf([both, is_zero_duration.Not()])
                        else:
                            model.Add(this_vars["start"] >= prev_vars["end"] + total_time).OnlyEnforceIf(both)

    # DEBUG: Tulosta jokaisen vaiheen station_var domain (task_vars alustuksen jälkeen, ennen rajoitteita)
    if task_vars:
        print("[DEBUG] Station variable domainit ennen ratkaisua:")
        for (batch, stage), vars in task_vars.items():
            print(f"  Batch {batch} Stage {stage}: possible_stations = {vars['possible_stations']}")

    # AddNoOverlap: asemalla vain yksi erä kerrallaan (estää päällekkäisyyden)


    # --- Sääntö 3.1 ja nostimen siirtoaika eri erien välillä samalla asemalla ---
    # Selvitetään siirron minimiaika kaikista siirroista (pois lukien nollat)
    all_transfer_times = [int(x) for x in transfers["transfer_time"] if int(x) > 0]
    min_transfer_time = min(all_transfer_times) if all_transfer_times else 1
    for station in stations["Number"]:
        tasks_at_station = [(batch, stage, vars) for (batch, stage), vars in task_vars.items() if station in vars["possible_stations"]]
        for i in range(len(tasks_at_station)):
            batch1, stage1, vars1 = tasks_at_station[i]
            for j in range(len(tasks_at_station)):
                if i == j:
                    continue
                batch2, stage2, vars2 = tasks_at_station[j]
                if batch1 == batch2:
                    continue
                # Käytetään siirtoaikaa, jos löytyy, muuten min_transfer_time
                mask = (transfers["from_station"] == station) & (transfers["to_station"] == station)
                if mask.any():
                    transfer_time = int(transfers[mask].iloc[0]["transfer_time"])
                else:
                    transfer_time = min_transfer_time
                # Jos molemmilla vain tämä asema mahdollinen, suora disjunktiivirajoite
                if vars1["possible_stations"] == [station] and vars2["possible_stations"] == [station]:
                    b1_before_b2 = model.NewBoolVar(f"b{batch1}_{stage1}_before_b{batch2}_{stage2}_at_{station}")
                    b2_before_b1 = model.NewBoolVar(f"b{batch2}_{stage2}_before_b{batch1}_{stage1}_at_{station}")
                    model.Add(vars1["end"] + transfer_time <= vars2["start"]).OnlyEnforceIf(b1_before_b2)
                    model.Add(vars2["end"] + transfer_time <= vars1["start"]).OnlyEnforceIf(b2_before_b1)
                    model.AddBoolOr([b1_before_b2, b2_before_b1])
                else:
                    # Reifioitu malli, jos asemia useampi
                    b1_at = model.NewBoolVar(f"b{batch1}_{stage1}_at_{station}")
                    b2_at = model.NewBoolVar(f"b{batch2}_{stage2}_at_{station}")
                    model.Add(vars1["station"] == station).OnlyEnforceIf(b1_at)
                    model.Add(vars1["station"] != station).OnlyEnforceIf(b1_at.Not())
                    model.Add(vars2["station"] == station).OnlyEnforceIf(b2_at)
                    model.Add(vars2["station"] != station).OnlyEnforceIf(b2_at.Not())
                    b1_before_b2 = model.NewBoolVar(f"b{batch1}_{stage1}_before_b{batch2}_{stage2}_at_{station}")
                    b2_before_b1 = model.NewBoolVar(f"b{batch2}_{stage2}_before_b{batch1}_{stage1}_at_{station}")
                    model.Add(vars1["end"] + transfer_time <= vars2["start"]).OnlyEnforceIf([b1_at, b2_at, b1_before_b2])
                    model.Add(vars2["end"] + transfer_time <= vars1["start"]).OnlyEnforceIf([b1_at, b2_at, b2_before_b1])
                    model.AddBoolOr([b1_before_b2, b2_before_b1, b1_at.Not(), b2_at.Not()])

    # Sääntö 3.1 on katettu AddNoOverlap- ja siirtorajoitteilla, kun siirtojen ajoitus on sidottu oikein.
    # --- Ratkaise ja tallenna tulokset ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    result_path = os.path.join(logs_dir, "cp-sat-result-schedule.csv")
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"[CP-SAT] Ei toteuttamiskelpoista ratkaisua! Status: {status}")
        return
    results = []
    for (batch, stage), vars in task_vars.items():
        results.append({
            "Batch": batch,
            "Stage": stage,
            "Station": solver.Value(vars["station"]),
            "Start": solver.Value(vars["start"]),
            "End": solver.Value(vars["end"]),
            "Duration": solver.Value(vars["duration"])
        })
    df_result = pd.DataFrame(results)
    df_result.to_csv(result_path, index=False)
    print(f"[CP-SAT] Optimoinnin tulokset tallennettu: {result_path}")
# cp_sat_optimize("output/2025-10-26_13-00-00/")
