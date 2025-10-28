import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_optimize_new(output_dir):
    # 1. Lue snapshotin tiedot
    batches = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-batches.csv"))
    stations = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-transfer-tasks.csv"))
    treatment_programs = {}
    for batch in batches["Batch"]:
        batch_int = int(batch)
        fname = os.path.join(output_dir, "initialization", f"cp-sat-treatment-program-{batch_int}.csv")
        df = pd.read_csv(fname)
        treatment_programs[batch_int] = df

    # 2. Muuttujat ja malli
    model = cp_model.CpModel()
    MAX_TIME = 10**6
    task_vars = {}  # (batch, stage): dict
    hoist_tasks = []  # (interval_var, kuvaus)

    # Luo muuttujat jokaiselle (batch, stage)
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        for idx, row in program.iterrows():
            stage = int(row["Stage"])
            min_stat = int(row["MinStat"])
            max_stat = int(row["MaxStat"])
            min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
            max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
            # Mahdolliset asemat (rinnakkaisuus)
            possible_stations = stations[(stations["Number"] >= min_stat) & (stations["Number"] <= max_stat)]["Number"].tolist()
            duration_var = model.NewIntVar(min_time, max_time, f"duration_{batch_int}_{stage}")
            start_var = model.NewIntVar(0, MAX_TIME, f"start_{batch_int}_{stage}")
            end_var = model.NewIntVar(0, MAX_TIME, f"end_{batch_int}_{stage}")
            station_domain = cp_model.Domain.FromValues(possible_stations)
            station_var = model.NewIntVarFromDomain(station_domain, f"station_{batch_int}_{stage}")
            task_vars[(batch_int, stage)] = {
                "start": start_var,
                "end": end_var,
                "duration": duration_var,
                "station": station_var,
                "possible_stations": possible_stations
            }

    # Nostimen siirtotehtävät (rakenne):
    # Jokainen siirto (from_station, to_station) batchin vaiheiden välillä
    # (Toteutus täydennetään rajoitteiden yhteydessä)

    # 3. Rajoitteet
    # Sääntö 1: Vaiheiden järjestys (end edellisessä ≤ start seuraavassa)
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            model.Add(task_vars[(batch_int, this_stage)]["start"] >= task_vars[(batch_int, prev_stage)]["end"])

    # Sääntö 2: Käsittelyaikojen min/max (sisältyy duration_varin rajoihin)
    for (batch, stage), vars in task_vars.items():
        model.Add(vars["end"] == vars["start"] + vars["duration"])

    # Sääntö 3: Asemalla vain yksi erä kerrallaan (AddNoOverlap)
    for station in stations["Number"]:
        intervals = []
        for (batch, stage), vars in task_vars.items():
            # Jokaiselle mahdolliselle asemalle luodaan OptionalIntervalVar
            if station in vars["possible_stations"]:
                is_this_station = model.NewBoolVar(f"is_{batch}_{stage}_at_{station}")
                model.Add(vars["station"] == station).OnlyEnforceIf(is_this_station)
                model.Add(vars["station"] != station).OnlyEnforceIf(is_this_station.Not())
                interval = model.NewOptionalIntervalVar(vars["start"], vars["duration"], vars["end"], is_this_station, f"interval_{batch}_{stage}_at_{station}")
                intervals.append(interval)
        if intervals:
            model.AddNoOverlap(intervals)

    # --- Nostimen vaihtoajan ja siirtojen mallinnus (Sääntö 3.1 & 4) ---
    # Jokainen nostimen tehtävä: siirrä erä asemalta toiselle (batch, stage)
    # Mallinnetaan nostimen kaikki siirrot (myös tyhjät) eksplisiittisesti
    hoist_intervals = []
    hoist_tasks = []  # (start_var, duration, end_var, from_station, to_station, batch, prev_stage, this_stage, bool_var)
    # Kerätään kaikki siirtotehtävät (kaikki erät, kaikki vaiheet, myös tyhjät siirtymät)
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            prev_vars = task_vars[(batch_int, prev_stage)]
            this_vars = task_vars[(batch_int, this_stage)]
            for from_stat in prev_vars["possible_stations"]:
                for to_stat in this_vars["possible_stations"]:
                    mask = (transfers["from_station"] == from_stat) & (transfers["to_station"] == to_stat)
                    if not mask.any():
                        continue
                    total_task_time = int(transfers[mask].iloc[0]["total_task_time"])
                    cond_prev = model.NewBoolVar(f"prev_{batch_int}_{prev_stage}_at_{from_stat}")
                    cond_this = model.NewBoolVar(f"this_{batch_int}_{this_stage}_at_{to_stat}")
                    model.Add(prev_vars["station"] == from_stat).OnlyEnforceIf(cond_prev)
                    model.Add(prev_vars["station"] != from_stat).OnlyEnforceIf(cond_prev.Not())
                    model.Add(this_vars["station"] == to_stat).OnlyEnforceIf(cond_this)
                    model.Add(this_vars["station"] != to_stat).OnlyEnforceIf(cond_this.Not())
                    both = model.NewBoolVar(f"both_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}")
                    model.AddBoolAnd([cond_prev, cond_this]).OnlyEnforceIf(both)
                    model.AddBoolOr([cond_prev.Not(), cond_this.Not()]).OnlyEnforceIf(both.Not())
                    hoist_start = prev_vars["end"]
                    hoist_end = model.NewIntVar(0, MAX_TIME, f"hoist_end_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}")
                    model.Add(hoist_end == hoist_start + total_task_time).OnlyEnforceIf(both)
                    model.Add(this_vars["start"] >= hoist_end).OnlyEnforceIf(both)
                    interval = model.NewOptionalIntervalVar(hoist_start, total_task_time, hoist_end, both, f"hoist_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}")
                    hoist_intervals.append(interval)
                    hoist_tasks.append((hoist_start, total_task_time, hoist_end, from_stat, to_stat, batch_int, prev_stage, this_stage, both))

    # Nostimen tyhjät siirtymät: järjestetään kaikki nostimen tehtävät aikajärjestykseen ja mallinnetaan siirtymät tehtävältä toiselle
    # (Tämä vaatii, että nostin ehtii siirtyä edellisen tehtävän laskupaikalta seuraavan tehtävän nostopaikalle ennen kuin uusi tehtävä voi alkaa)
    for i in range(len(hoist_tasks)):
        for j in range(len(hoist_tasks)):
            if i == j:
                continue
            # Jos tehtävä i päättyy ennen tehtävää j, ja molemmat ovat valittuja
            _, _, end_i, _, to_i, _, _, _, both_i = hoist_tasks[i]
            start_j, _, _, from_j, _, _, _, _, both_j = hoist_tasks[j]
            # Siirtymäaika nostimen pitää siirtyä to_i -> from_j
            mask = (transfers["from_station"] == to_i) & (transfers["to_station"] == from_j)
            if not mask.any():
                continue
            transfer_time = int(transfers[mask].iloc[0]["transfer_time"])
            # Jos i ja j ovat peräkkäisiä nostintehtäviä, j voi alkaa vasta kun nostin on ehtinyt siirtyä
            # (end_i + transfer_time <= start_j) jos molemmat tehtävät valittuja
            model.Add(start_j >= end_i + transfer_time).OnlyEnforceIf([both_i, both_j])

    # Nostin ei voi olla kahdessa paikassa yhtä aikaa (AddNoOverlap nostimen tehtäville)
    if hoist_intervals:
        model.AddNoOverlap(hoist_intervals)

    # --- Optimointikriteeri: minimoi makespan ---
    last_ends = []
    for (batch, stage), vars in task_vars.items():
        program = treatment_programs[batch]
        if stage == int(program["Stage"].max()):
            last_ends.append(vars["end"])
    if last_ends:
        makespan = model.NewIntVar(0, MAX_TIME, "makespan")
        model.AddMaxEquality(makespan, last_ends)
        model.Minimize(makespan)

    # 4. Optimointikriteeri
    # TODO: Minimoi makespan

    # 5. Ratkaise ja tallenna tulos
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    status_str = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID", cp_model.UNKNOWN: "UNKNOWN"}.get(status, str(status))
    print(f"[CP-SAT] Solver status: {status} ({status_str})")
    print(f"[CP-SAT] Wall time: {solver.WallTime()}s, Conflicts: {solver.NumConflicts()}, Branches: {solver.NumBranches()}")
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

# Huom: Toteuta jokainen TODO requirements-dokumentin ja snapshotin rakenteen mukaisesti.
