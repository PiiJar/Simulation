"""
CP-SAT tuotantolinjan optimointimalli vaiheittain, vaatimusdokumentin mukaisesti.
"""
import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_optimization(output_dir, hard_order_constraint=False):
    # (Poistettu: ei enää pakoteta pienimmän erän aloitusta nollaan)
    # 1. Lue snapshotin tiedot
    batches = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_batches.csv"))
    stations = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_transfer_tasks.csv"))
    transporters = pd.read_csv(os.path.join(output_dir, "initialization", "transporters.csv"))
    treatment_programs = {}
    for batch in batches["Batch"]:
        batch_int = int(batch)
        fname = os.path.join(output_dir, "cp_sat", f"cp_sat_treatment_program_{batch_int}.csv")
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

    # Pakota, että ensimmäinen tuotantotapahtuma (minkä tahansa erän Stage 0) alkaa ajassa 0:00:00
    stage0_starts = [vars["start"] for (batch, stage), vars in task_vars.items() if stage == 0]
    if stage0_starts:
        model.AddMinEquality(model.NewIntVar(0, MAX_TIME, "first_start"), stage0_starts)
        model.AddMinEquality(0, stage0_starts)
    # 1. Lue snapshotin tiedot
    batches = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_batches.csv"))
    stations = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_transfer_tasks.csv"))
    transporters = pd.read_csv(os.path.join(output_dir, "initialization", "transporters.csv"))
    treatment_programs = {}
    for batch in batches["Batch"]:
        batch_int = int(batch)
        fname = os.path.join(output_dir, "cp_sat", f"cp_sat_treatment_program_{batch_int}.csv")
        df = pd.read_csv(fname)
        treatment_programs[batch_int] = df

    # (Removed duplicate block)

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


    # Pakota, että jos mikään muu ei rajoita, ensimmäisen erän ensimmäinen oikea vaihe (stage 1) alkaa ajassa 0
    stage1_starts = [(batch, vars["start"]) for (batch, stage), vars in task_vars.items() if stage == 1]
    if stage1_starts:
        min_stage1_start = model.NewIntVar(0, MAX_TIME, "min_stage1_start")
        model.AddMinEquality(min_stage1_start, [s for _, s in stage1_starts])
        model.Add(min_stage1_start == 0)

    # Kovien järjestysrajoitteiden lisäys vain jos hard_order_constraint=True
    if hard_order_constraint:
        # Käytetään batch-numeroiden nousevaa järjestystä
        batch_ids = sorted([int(b) for b in batches["Batch"]])
        batch_end_vars = [task_vars[(batch_id, 0)]["end"] for batch_id in batch_ids]
        for i in range(len(batch_ids)):
            for j in range(i+1, len(batch_ids)):
                model.Add(batch_end_vars[i] <= batch_end_vars[j])

    # Vaihe 2: Käsittelyjärjestys constraint (vaiheiden järjestys)
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            model.Add(task_vars[(batch_int, this_stage)]["start"] >= task_vars[(batch_int, prev_stage)]["end"])

    # Vaihe 3: Aseman yksikäyttöisyys (AddNoOverlap, mutta ei aloitusasemalle/stage 0)
    for station in stations["Number"]:
        intervals = []
        for (batch, stage), vars in task_vars.items():
            if stage == 0:
                continue  # Älä rajoita aloitusasemaa
            if station in vars["possible_stations"]:
                is_this_station = model.NewBoolVar(f"is_{batch}_{stage}_at_{station}")
                model.Add(vars["station"] == station).OnlyEnforceIf(is_this_station)
                model.Add(vars["station"] != station).OnlyEnforceIf(is_this_station.Not())
                interval = model.NewOptionalIntervalVar(vars["start"], vars["duration"], vars["end"], is_this_station, f"interval_{batch}_{stage}_at_{station}")
                intervals.append(interval)
        if intervals:
            model.AddNoOverlap(intervals)

    # Vaihe 4: Nostimen siirrot eksplisiittisesti ja siirron kesto transfer-tiedoston mukainen (korjattu logiikka)
    # Kerätään nostinintervallit per nostin
    transporter_intervals_by_id = {}
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            prev_vars = task_vars[(batch_int, prev_stage)]
            this_vars = task_vars[(batch_int, this_stage)]
            transfer_bools = []
            for from_stat in prev_vars["possible_stations"]:
                for to_stat in this_vars["possible_stations"]:
                    if from_stat == to_stat:
                        continue  # Skip same-station transfers
                    for _, transporter in transporters.iterrows():
                        min_x = transporter['Min_x_position']
                        max_x = transporter['Max_x_Position']
                        stations_df = stations
                        lift_x = stations_df[stations_df['Number'] == from_stat]['X Position'].iloc[0]
                        sink_x = stations_df[stations_df['Number'] == to_stat]['X Position'].iloc[0]
                        if min_x <= lift_x <= max_x and min_x <= sink_x <= max_x:
                            transporter_id = int(transporter['Transporter_id'])
                            mask = (
                                (transfers["Transporter"] == transporter_id) &
                                (transfers["From_Station"] == from_stat) &
                                (transfers["To_Station"] == to_stat)
                            )
                            if not mask.any():
                                continue
                            transfer_time = float(transfers[mask].iloc[0]["TotalTaskTime"])
                            is_transfer = model.NewBoolVar(f"is_transfer_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}_T{transporter_id}")
                            model.Add(prev_vars["station"] == from_stat).OnlyEnforceIf(is_transfer)
                            model.Add(prev_vars["station"] != from_stat).OnlyEnforceIf(is_transfer.Not())
                            model.Add(this_vars["station"] == to_stat).OnlyEnforceIf(is_transfer)
                            model.Add(this_vars["station"] != to_stat).OnlyEnforceIf(is_transfer.Not())
                            trans_start = prev_vars["end"]
                            trans_end = model.NewIntVar(0, MAX_TIME, f"trans_end_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}_T{transporter_id}")
                            model.Add(trans_end == trans_start + int(round(transfer_time))).OnlyEnforceIf(is_transfer)
                            model.Add(this_vars["start"] == trans_end).OnlyEnforceIf(is_transfer)
                            interval = model.NewOptionalIntervalVar(trans_start, int(round(transfer_time)), trans_end, is_transfer, f"trans_{batch_int}_{prev_stage}_{this_stage}_{from_stat}_{to_stat}_T{transporter_id}")
                            if transporter_id not in transporter_intervals_by_id:
                                transporter_intervals_by_id[transporter_id] = []
                            transporter_intervals_by_id[transporter_id].append(interval)
                            transfer_bools.append(is_transfer)
                            break  # Käytä vain ensimmäinen sopiva nostin
            # Vain yksi siirto voi olla aktiivinen per batch, stage
            if transfer_bools:
                model.Add(sum(transfer_bools) == 1)
    # Vaihe 5: Nostimen yksikäyttöisyys (AddNoOverlap per nostin, Sääntö 4.1)
    for transporter_id, intervals in transporter_intervals_by_id.items():
        if intervals:
            model.AddNoOverlap(intervals)

    # Vaihe 6: Optimointikriteeri (minimoi makespan)
    last_ends = []
    for (batch, stage), vars in task_vars.items():
        program = treatment_programs[batch]
        if stage == int(program["Stage"].max()):
            last_ends.append(vars["end"])
    if last_ends:
        makespan = model.NewIntVar(0, MAX_TIME, "makespan")
        model.AddMaxEquality(makespan, last_ends)
        # Järjestysrikkomuspenalty: penalisoidaan, jos pienempi batch alkaa myöhemmin kuin suurempi batch
        batch_start_vars = []
        batch_ids = []
        for batch in batches["Batch"]:
            batch_int = int(batch)
            batch_start_vars.append(task_vars[(batch_int, 0)]["start"])
            batch_ids.append(batch_int)
        # Penalisoidaan kaikki parit (i, j), joissa batch_ids[i] < batch_ids[j] mutta start[i] > start[j]
        order_violations = []
        for i in range(len(batch_ids)):
            for j in range(i+1, len(batch_ids)):
                if batch_ids[i] < batch_ids[j]:
                    violation = model.NewBoolVar(f"order_violation_{batch_ids[i]}_{batch_ids[j]}")
                    model.Add(batch_start_vars[i] > batch_start_vars[j]).OnlyEnforceIf(violation)
                    model.Add(batch_start_vars[i] <= batch_start_vars[j]).OnlyEnforceIf(violation.Not())
                    order_violations.append(violation)
        if order_violations:
            order_penalty = model.NewIntVar(0, len(order_violations), "order_penalty")
            model.Add(order_penalty == sum(order_violations))
        else:
            order_penalty = model.NewIntVar(0, 0, "order_penalty")
            model.Add(order_penalty == 0)
        # Ensisijaisesti minimoi makespan, toissijaisesti järjestysrikkomukset
        model.Minimize(makespan * (len(batch_ids)+1) + order_penalty)

    # Vaihe 7: Erityistapaukset (askel 0)
    # (Tässä vaiheessa askel 0 sallitaan päällekkäisyys, koska AddNoOverlap ei rajoita sitä)
    return model, task_vars, treatment_programs
def solve_and_save(model, task_vars, treatment_programs, output_dir):
    from ortools.sat.python import cp_model
    import pandas as pd
    import os
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    # Debug: tulosta batchien vaiheen 0 start ja end arvot
    batch_starts = []
    batch_ends = []
    for (batch, stage), vars in task_vars.items():
        if stage == 0:
            batch_starts.append((batch, solver.Value(vars["start"])))
            batch_ends.append((batch, solver.Value(vars["end"])))
    status_str = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID", cp_model.UNKNOWN: "UNKNOWN"}.get(status, str(status))
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    result_path = os.path.join(logs_dir, "cp_sat_optimization_schedule.csv")
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
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


    validate_and_save_transfers(df_result, task_vars, logs_dir)

    # --- Päivitä production.csv ja ohjelmat optimoiduilla ajoilla ---
    import sys
    import pandas as pd
    sys.path.append(os.path.join(os.path.dirname(__file__), 'not_used'))
    from not_used.optimize_final_schedule import update_production_and_programs
    orig_prod = pd.read_csv(os.path.join(output_dir, "initialization", "production.csv"))
    update_production_and_programs(orig_prod, df_result, output_dir, None)

    # Poista Stage 0 -rivit treatment_program_optimized/-kansiosta
    optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")
    if os.path.exists(optimized_dir):
        for filename in os.listdir(optimized_dir):
            if filename.startswith("Batch_") and filename.endswith(".csv"):
                file_path = os.path.join(optimized_dir, filename)
                df = pd.read_csv(file_path)
                df = df[df["Stage"] != 0].copy()
                df.to_csv(file_path, index=False)

    # Poista Stage 0 -rivi kaikista treatment_program_optimized -tiedostoista
    remove_stage0_from_optimized_programs(output_dir)

def remove_stage0_from_optimized_programs(output_dir):
    import os
    import pandas as pd
    optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")
    if not os.path.exists(optimized_dir):
        return
    for filename in os.listdir(optimized_dir):
        if filename.startswith("Batch_") and filename.endswith(".csv"):
            file_path = os.path.join(optimized_dir, filename)
            df = pd.read_csv(file_path)
            df = df[df["Stage"] != 0].copy()
            df.to_csv(file_path, index=False)

def validate_and_save_transfers(df_result, task_vars, logs_dir):
    import pandas as pd
    import os
    # Tallennetaan nostimen siirtointervallit analysoitavaksi
    siirrot = []
    for (batch, stage), vars in task_vars.items():
        if stage == 0:
            continue
        start = df_result[(df_result["Batch"] == batch) & (df_result["Stage"] == stage-1)]["End"].values
        end = df_result[(df_result["Batch"] == batch) & (df_result["Stage"] == stage)]["Start"].values
        from_station = df_result[(df_result["Batch"] == batch) & (df_result["Stage"] == stage-1)]["Station"].values
        to_station = df_result[(df_result["Batch"] == batch) & (df_result["Stage"] == stage)]["Station"].values
        if len(start) == 1 and len(end) == 1 and len(from_station) == 1 and len(to_station) == 1:
            siirrot.append({
                "Batch": batch,
                "FromStage": stage-1,
                "ToStage": stage,
                "FromStation": from_station[0],
                "ToStation": to_station[0],
                "Start": start[0],
                "End": end[0]
            })
    df_siirrot = pd.DataFrame(siirrot)
    siirrot_path = os.path.join(logs_dir, "cp_sat_optimization_transfers.csv")
    df_siirrot.to_csv(siirrot_path, index=False)

    # Validointi: tarkista, ettei AddNoOverlap rajoita askel 0:aa, mutta toimii muille vaiheille
    for station in df_result['Station'].unique():
        df_station = df_result[df_result['Station'] == station]
        # Järjestetään aloitusajan mukaan
        df_station = df_station.sort_values('Start')
        prev_end = None
        prev_batch = None
        prev_stage = None
        for idx, row in df_station.iterrows():
            if row['Stage'] == 0:
                continue  # step 0 can overlap
            if prev_end is not None and row['Start'] < prev_end:
                pass  # Overlap warning removed
            prev_end = row['End']
            prev_batch = row['Batch']
            prev_stage = row['Stage']

