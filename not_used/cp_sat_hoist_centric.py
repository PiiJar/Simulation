import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_transporter_centric(output_dir):
    # Lue snapshotin tiedot
    batches = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-batches.csv"))
    stations = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-transfer-tasks.csv"))
    treatment_programs = {}
    for batch in batches["Batch"]:
        batch_int = int(batch)
        fname = os.path.join(output_dir, "initialization", f"cp-sat-treatment-program-{batch_int}.csv")
        df = pd.read_csv(fname)
        treatment_programs[batch_int] = df

    model = cp_model.CpModel()
    MAX_TIME = 10**6

    # 1. Kerää kaikki siirtotehtävät (kaikki erät, kaikki vaiheet)
    transporter_tasks = []  # (batch, prev_stage, this_stage, from_station, to_station, min_proc, max_proc)
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            prev_row = program.iloc[i-1]
            this_row = program.iloc[i]
            prev_stats = stations[(stations["Number"] >= int(prev_row["MinStat"])) & (stations["Number"] <= int(prev_row["MaxStat"]))]["Number"].tolist()
            this_stats = stations[(stations["Number"] >= int(this_row["MinStat"])) & (stations["Number"] <= int(this_row["MaxStat"]))]["Number"].tolist()
            for from_stat in prev_stats:
                for to_stat in this_stats:
                    mask = (transfers["from_station"] == from_stat) & (transfers["to_station"] == to_stat)
                    if not mask.any():
                        continue
                    total_task_time = int(transfers[mask].iloc[0]["total_task_time"])
                    transporter_tasks.append({
                        "batch": batch_int,
                        "prev_stage": prev_stage,
                        "this_stage": this_stage,
                        "from_station": from_stat,
                        "to_station": to_stat,
                        "total_task_time": total_task_time,
                        "min_proc": int(pd.to_timedelta(this_row["MinTime"]).total_seconds()),
                        "max_proc": int(pd.to_timedelta(this_row["MaxTime"]).total_seconds())
                    })

    # 2. Järjestetään nostimen tehtävät: jokainen siirto on yksi "reitti" nostimelle
    # Luodaan muuttujat jokaiselle nostimen tehtävälle
    transporter_vars = []
    for idx, task in enumerate(transporter_tasks):
        start = model.NewIntVar(0, MAX_TIME, f"transporter_start_{idx}")
        end = model.NewIntVar(0, MAX_TIME, f"transporter_end_{idx}")
        model.Add(end == start + task["total_task_time"])
        transporter_vars.append({"start": start, "end": end, "task": task})

    # 3. Nostimen tehtävien järjestys: AddNoOverlap
    intervals = [model.NewIntervalVar(var["start"], task["total_task_time"], var["end"], f"transporter_interval_{i}") for i, (var, task) in enumerate(zip(transporter_vars, transporter_tasks))]
    model.AddNoOverlap(intervals)

    # 4. Käsittelyaikaikkunat: jokaisen erän vaiheen käsittelyaika on nostimen siirron jälkeen, min/max rajoissa
    # Luodaan muuttujat jokaiselle käsittelylle
    proc_vars = {}
    for var in transporter_vars:
        task = var["task"]
        batch = task["batch"]
        stage = task["this_stage"]
        min_proc = task["min_proc"]
        max_proc = task["max_proc"]
        proc_start = var["end"]
        proc_end = model.NewIntVar(0, MAX_TIME, f"proc_end_{batch}_{stage}")
        duration = model.NewIntVar(min_proc, max_proc, f"proc_dur_{batch}_{stage}")
        model.Add(proc_end == proc_start + duration)
        proc_vars[(batch, stage)] = {"start": proc_start, "end": proc_end, "duration": duration}

    # 5. Asemien yksikäyttöisyys: AddNoOverlap jokaiselle asemalle
    for station in stations["Number"]:
        intervals = []
        for (batch, stage), vars in proc_vars.items():
            task = next((t for t in transporter_tasks if t["batch"] == batch and t["this_stage"] == stage and t["to_station"] == station), None)
            if task is not None:
                interval = model.NewIntervalVar(vars["start"], vars["duration"], vars["end"], f"station_{station}_b{batch}_s{stage}")
                intervals.append(interval)
        if intervals:
            model.AddNoOverlap(intervals)

    # 6. Optimointikriteeri: minimoi makespan
    makespan = model.NewIntVar(0, MAX_TIME, "makespan")
    last_ends = [vars["end"] for (batch, stage), vars in proc_vars.items() if stage == max([t["this_stage"] for t in transporter_tasks if t["batch"] == batch])]
    model.AddMaxEquality(makespan, last_ends)
    model.Minimize(makespan)

    # 7. Ratkaise ja tallenna tulos
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    status_str = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID", cp_model.UNKNOWN: "UNKNOWN"}.get(status, str(status))
    print(f"[CP-SAT] Solver status: {status} ({status_str})")
    print(f"[CP-SAT] Wall time: {solver.WallTime()}s, Conflicts: {solver.NumConflicts()}, Branches: {solver.NumBranches()}")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    result_path = os.path.join(logs_dir, "cp-sat-transporter-centric-schedule.csv")
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"[CP-SAT] Ei toteuttamiskelpoista ratkaisua! Status: {status}")
        return
    results = []
    for (batch, stage), vars in proc_vars.items():
        results.append({
            "Batch": batch,
            "Stage": stage,
            "Station": next((t["to_station"] for t in transporter_tasks if t["batch"] == batch and t["this_stage"] == stage), None),
            "Start": solver.Value(vars["start"]),
            "End": solver.Value(vars["end"]),
            "Duration": solver.Value(vars["duration"])
        })
    df_result = pd.DataFrame(results)
    df_result.to_csv(result_path, index=False)
    print(f"[CP-SAT] Optimoinnin tulokset tallennettu: {result_path}")
