"""
CP-SAT tuotantolinjan optimointimalli vaiheittain, vaatimusdokumentin mukaisesti.
"""
import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_stepwise(output_dir):
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

    model = cp_model.CpModel()
    MAX_TIME = 10**6

    # Vaihe 1: Käsittelyjärjestys ja muuttujat
    # Jokaiselle (batch, stage): start, end, duration, station
    task_vars = {}
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        for idx, row in program.iterrows():
            stage = int(row["Stage"])
            min_stat = int(row["MinStat"])
            max_stat = int(row["MaxStat"])
            group = stations[stations["Number"] == min_stat]["Group"].iloc[0]
            possible_stations = stations[(stations["Number"] >= min_stat) & (stations["Number"] <= max_stat) & (stations["Group"] == group)]["Number"].tolist()
            min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
            max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
            duration = model.NewIntVar(min_time, max_time, f"duration_{batch_int}_{stage}")
            start = model.NewIntVar(0, MAX_TIME, f"start_{batch_int}_{stage}")
            end = model.NewIntVar(0, MAX_TIME, f"end_{batch_int}_{stage}")
            station_domain = cp_model.Domain.FromValues(possible_stations)
            station = model.NewIntVarFromDomain(station_domain, f"station_{batch_int}_{stage}")
            model.Add(end == start + duration)
            task_vars[(batch_int, stage)] = {"start": start, "end": end, "duration": duration, "station": station, "possible_stations": possible_stations}

    # Vaihe 2: Käsittelyjärjestys constraint (vaiheiden järjestys)
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            model.Add(task_vars[(batch_int, this_stage)]["start"] >= task_vars[(batch_int, prev_stage)]["end"])

    # Vaihe 3: Aseman yksikäyttöisyys (AddNoOverlap)
    for station in stations["Number"]:
        intervals = []
        for (batch, stage), vars in task_vars.items():
            if station in vars["possible_stations"]:
                is_this_station = model.NewBoolVar(f"is_{batch}_{stage}_at_{station}")
                model.Add(vars["station"] == station).OnlyEnforceIf(is_this_station)
                model.Add(vars["station"] != station).OnlyEnforceIf(is_this_station.Not())
                interval = model.NewOptionalIntervalVar(vars["start"], vars["duration"], vars["end"], is_this_station, f"interval_{batch}_{stage}_at_{station}")
                intervals.append(interval)
        if intervals:
            model.AddNoOverlap(intervals)

    # Vaihe 4: Nostimen vaihtoajan ja siirtymien mallinnus (Sääntö 3.1)
    # Rakennetaan nostimen siirtointervallit myöhempää AddNoOverlapia varten
    transporter_intervals = []
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
                    transfer_time = int(transfers[mask].iloc[0]["total_task_time"])
                    cond_prev = model.NewBoolVar(f"prev_{batch_int}_{prev_stage}_at_{from_stat}")
                    cond_this = model.NewBoolVar(f"this_{batch_int}_{this_stage}_at_{to_stat}")
                    model.Add(prev_vars["station"] == from_stat).OnlyEnforceIf(cond_prev)
                    model.Add(prev_vars["station"] != from_stat).OnlyEnforceIf(cond_prev.Not())
                    model.Add(this_vars["station"] == to_stat).OnlyEnforceIf(cond_this)
                    model.Add(this_vars["station"] != to_stat).OnlyEnforceIf(cond_this.Not())
                    both = model.NewBoolVar(f"both_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}")
                    model.AddBoolAnd([cond_prev, cond_this]).OnlyEnforceIf(both)
                    model.AddBoolOr([cond_prev.Not(), cond_this.Not()]).OnlyEnforceIf(both.Not())
                    trans_start = prev_vars["end"]
                    trans_end = model.NewIntVar(0, MAX_TIME, f"trans_end_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}")
                    model.Add(trans_end == trans_start + transfer_time).OnlyEnforceIf(both)
                    model.Add(this_vars["start"] >= trans_end).OnlyEnforceIf(both)
                    interval = model.NewOptionalIntervalVar(trans_start, transfer_time, trans_end, both, f"trans_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}")
                    transporter_intervals.append(interval)
    # Vaihe 5: Nostimen yksikäyttöisyys (AddNoOverlap nostimelle, Sääntö 4.1)
    if transporter_intervals:
        model.AddNoOverlap(transporter_intervals)

    # Vaihe 6: Optimointikriteeri (minimoi makespan)
    last_ends = []
    for (batch, stage), vars in task_vars.items():
        program = treatment_programs[batch]
        if stage == int(program["Stage"].max()):
            last_ends.append(vars["end"])
    if last_ends:
        makespan = model.NewIntVar(0, MAX_TIME, "makespan")
        model.AddMaxEquality(makespan, last_ends)
        model.Minimize(makespan)

    # Vaihe 7: Erityistapaukset (askel 0)
    # (Tässä vaiheessa askel 0 sallitaan päällekkäisyys, koska AddNoOverlap ei rajoita sitä)
    return model, task_vars, treatment_programs
def solve_and_save(model, task_vars, treatment_programs, output_dir):
    from ortools.sat.python import cp_model
    import pandas as pd
    import os
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    status_str = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID", cp_model.UNKNOWN: "UNKNOWN"}.get(status, str(status))
    print(f"[CP-SAT] Solver status: {status} ({status_str})")
    print(f"[CP-SAT] Wall time: {solver.WallTime()}s, Conflicts: {solver.NumConflicts()}, Branches: {solver.NumBranches()}")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    result_path = os.path.join(logs_dir, "cp-sat-stepwise-schedule.csv")
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

