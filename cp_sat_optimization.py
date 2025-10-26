import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_optimize(output_dir):
    # Lue lähtötiedot
    batches = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-batches.csv"))
    print(f"[DEBUG] batches: {list(batches['Batch'])}")
    stations = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-transfer-tasks.csv"))
    treatment_programs = {}
    for batch in batches["Batch"]:
        fname = os.path.join(output_dir, "initialization", f"cp-sat-treatment-program-{batch}.csv")
        treatment_programs[batch] = pd.read_csv(fname)
        print(f"[DEBUG] batch={batch} treatment_program shape: {treatment_programs[batch].shape}")
    # ...existing code...
    # ...existing code...
    # Lue lähtötiedot
    batches = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-batches.csv"))
    print(f"[DEBUG] batches: {list(batches['Batch'])}")
    stations = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-transfer-tasks.csv"))
    treatment_programs = {}
    for batch in batches["Batch"]:
        fname = os.path.join(output_dir, "initialization", f"cp-sat-treatment-program-{batch}.csv")
        treatment_programs[batch] = pd.read_csv(fname)
        print(f"[DEBUG] batch={batch} treatment_program shape: {treatment_programs[batch].shape}")
    model = cp_model.CpModel()
    task_vars = {}
    MAX_TIME = 10**6

    # task_vars täytetään vain kerran yllä olevassa silmukassa
    # ... kaikki rajoitteet ja muuttujat ...
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    status_str = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID", cp_model.UNKNOWN: "UNKNOWN"}.get(status, str(status))
    print(f"[CP-SAT] Solver status: {status} ({status_str})")
    print(f"[CP-SAT] Wall time: {solver.WallTime()}s, Conflicts: {solver.NumConflicts()}, Branches: {solver.NumBranches()}")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Muuttujat: (batch, stage) -> oikeat sidotut muuttujat
    task_vars = {}
    for batch in batches["Batch"]:
        program = treatment_programs[batch]
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
            print(f"[DEBUG] batch={batch} stage={stage} min_stat={min_stat} max_stat={max_stat} possible_stations={possible_stations} min_time={min_time} max_time={max_time}")
            if not possible_stations:
                print(f"[CP-SAT] VIRHE: Ei mahdollisia asemia batchille {batch}, vaihe {stage}: MinStat={min_stat}, MaxStat={max_stat}")
                print(f"  Tarkista cp-sat-treatment-program-{batch}.csv ja cp-sat-stations.csv")
                print(f"  Ohjelman rivi: {row}")
                continue

            duration_var = model.NewIntVar(min_time, max_time, f"duration_{batch}_{stage}")
            start_var = model.NewIntVar(0, MAX_TIME, f"start_{batch}_{stage}")
            end_var = model.NewIntVar(0, MAX_TIME, f"end_{batch}_{stage}")
            station_domain = cp_model.Domain.FromValues(possible_stations)
            station_var = model.NewIntVarFromDomain(station_domain, f"station_{batch}_{stage}")
            station_bools = []
            intervals = []
            for s in possible_stations:
                is_this_station = model.NewBoolVar(f"is_{batch}_{stage}_at_{s}")
                model.Add(station_var == s).OnlyEnforceIf(is_this_station)
                model.Add(station_var != s).OnlyEnforceIf(is_this_station.Not())
                interval = model.NewOptionalIntervalVar(start_var, duration_var, end_var, is_this_station, f"interval_{batch}_{stage}_at_{s}")
                station_bools.append(is_this_station)
                intervals.append((s, interval, is_this_station))
            model.AddAllowedAssignments([station_var], [[s] for s in possible_stations])
            model.Add(sum(station_bools) == 1)
            model.Add(end_var == start_var + duration_var)

            # Jos viimeinen vaihe, sidotaan start_var ja end_var edellisen vaiheen end_variin
            # Ei sidota viimeistä vaihetta edelliseen vaiheeseen

            task_vars[(batch, stage)] = {
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

    # Sääntö 1: Vaiheiden järjestys katetaan siirtoaikarajoitteella (ei erillistä järjestysrajoitetta)

    # Sääntö 2: Käsittelyaikojen min/max (sisältyy duration_varin rajoihin)

    # Sääntö 3: Asemalla vain yksi erä kerrallaan (AddNoOverlap per asema)
    # AddNoOverlap: asemalla vain yksi erä kerrallaan
    for station in stations["Number"]:
        intervals = []
        for (batch, stage), vars in task_vars.items():
            if station in vars["possible_stations"]:
                interval = model.NewIntervalVar(vars["start"], vars["duration"], vars["end"], f"interval_{batch}_{stage}_at_{station}")
                intervals.append(interval)
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
