import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_optimize(output_dir):
    """
    Suorittaa CP-SAT-optimoinnin requirements-tiedoston vaatimusten mukaisesti.
    Käyttää esikäsiteltyjä tiedostoja (cp-sat-alkuiset) ja tallentaa tulokset Logs-hakemistoon.
    """
    # Lue lähtötiedot
    batches = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-batches.csv"))
    stations = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-transfer-tasks.csv"))
    transporters = pd.read_csv(os.path.join(output_dir, "initialization", "cp-sat-transporters.csv"))
    # Lue kaikki käsittelyohjelmat
    treatment_programs = {}
    for batch in batches["Batch"]:
        fname = os.path.join(output_dir, "initialization", f"cp-sat-treatment-program-{batch}.csv")
        treatment_programs[batch] = pd.read_csv(fname)

    # Luo Logs-hakemisto
    logs_dir = os.path.join(output_dir, "Logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Luo CP-SAT-malli
    model = cp_model.CpModel()

    # --- Mallinnus alkaa ---
    # Tässä vaiheessa mallinnetaan vain yksi nostin, useita eriä, kaikki vaaditut rajoitteet
    # Jokainen erä: treatment_programs[batch] sisältää vaiheet
    # Jokainen vaihe: mahdolliset asemat, min/max aika, group
    # Kaikki siirtoajat: transfers
    # Nostimen aloitus/lopetusasema: transporters

    # Esimerkkimallinnus: (täydennä oikeilla muuttujilla ja rajoitteilla)
    # 1. Luo muuttujat jokaiselle erän vaiheelle: aloitusaika, lopetusaika, asema
    # 2. Lisää rajoitteet:
    #    - Vaiheiden järjestys (edellinen päättyy ennen seuraavan alkua)
    #    - Käsittelyaikojen min/max
    #    - Asemien varaus (AddNoOverlap)
    #    - Nostimen siirtojen ajat (siirtymäaika + nostoaika + laskuaika)
    #    - Nostimen aloitus- ja lopetusasema
    #    - Jokaisella asemalla vain yksi erä kerrallaan
    # 3. Tavoite: minimoi makespan (kaikkien erien viimeisen vaiheen päättymisaika)

    # Muuttujat: (batch, stage) -> (start, end, station, interval)
    task_vars = {}
    all_intervals = []
    station_to_intervals = {s: [] for s in stations["Station"]}
    batch_stage_to_idx = {}

    for batch in batches["Batch"]:
        program = treatment_programs[batch]
        for idx, row in program.iterrows():
            stage = int(row["Stage"])
            min_stat = int(row["MinStat"])
            max_stat = int(row["MaxStat"])
            group = int(row["Group"])
            min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
            max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())

            # Vapaus: Valitse mikä tahansa asema väliltä, joka kuuluu oikeaan Groupiin
            possible_stations = stations[
                (stations["Station"] >= min_stat) &
                (stations["Station"] <= max_stat) &
                (stations["Group"] == group)
            ]["Station"].tolist()

            # Asemavalintamuuttuja
            station_var = model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(possible_stations),
                f"station_{batch}_{stage}"
            )

            # Aloitus- ja lopetusaikamuuttujat
            start_var = model.NewIntVar(0, 10**6, f"start_{batch}_{stage}")
            end_var = model.NewIntVar(0, 10**6, f"end_{batch}_{stage}")

            # Kesto
            duration_var = model.NewIntVar(min_time, max_time, f"duration_{batch}_{stage}")

            # Intervalli
            interval = model.NewIntervalVar(start_var, duration_var, end_var, f"interval_{batch}_{stage}")

            task_vars[(batch, stage)] = {
                "start": start_var,
                "end": end_var,
                "station": station_var,
                "interval": interval,
                "duration": duration_var,
                "possible_stations": possible_stations
            }
            all_intervals.append(interval)
            batch_stage_to_idx[(batch, stage)] = idx

    # Sääntö 1: Vaiheiden järjestys
    for batch in batches["Batch"]:
        program = treatment_programs[batch]
        for idx in range(1, len(program)):
            prev_stage = int(program.iloc[idx-1]["Stage"])
            this_stage = int(program.iloc[idx]["Stage"])
            model.Add(task_vars[(batch, this_stage)]["start"] >= task_vars[(batch, prev_stage)]["end"])

    # Sääntö 2: Käsittelyaikojen min/max (sisältyy duration_varin rajoihin)

    # Sääntö 3: Asemalla vain yksi erä kerrallaan (AddNoOverlap per asema)
    for station in stations["Station"]:
        station_intervals = []
        for (batch, stage), vars in task_vars.items():
            if station in vars["possible_stations"]:
                # Luo literaali: onko tämä tehtävä tällä asemalla
                is_this_station = model.NewBoolVar(f"is_{batch}_{stage}_at_{station}")
                model.Add(vars["station"] == station).OnlyEnforceIf(is_this_station)
                model.Add(vars["station"] != station).OnlyEnforceIf(is_this_station.Not())
                # Lisää intervalli vain jos asema valitaan
                station_intervals.append((vars["interval"], is_this_station))
        if station_intervals:
            model.AddNoOverlap([(iv, lit) for iv, lit in station_intervals])

    # Sääntö 4: Nostimen siirtoajat (fysiikkaan perustuvat, haetaan transfers-taulukosta)
    # Sääntö 4.1: Nostin ei voi olla kahdessa paikassa yhtä aikaa
    # (Tässä vaiheessa yksi nostin, joten siirrot mallinnetaan vaiheiden väliin)
    for batch in batches["Batch"]:
        program = treatment_programs[batch]
        for idx in range(1, len(program)):
            prev_stage = int(program.iloc[idx-1]["Stage"])
            this_stage = int(program.iloc[idx]["Stage"])
            prev_station = task_vars[(batch, prev_stage)]["station"]
            this_station = task_vars[(batch, this_stage)]["station"]
            prev_end = task_vars[(batch, prev_stage)]["end"]
            this_start = task_vars[(batch, this_stage)]["start"]

            # Siirtymäaika lookup
            transfer_time_vars = []
            for from_stat in task_vars[(batch, prev_stage)]["possible_stations"]:
                for to_stat in task_vars[(batch, this_stage)]["possible_stations"]:
                    mask = (transfers["from_station"] == from_stat) & (transfers["to_station"] == to_stat)
                    if not mask.any():
                        raise ValueError(f"Siirtymäaika puuttuu: {from_stat} -> {to_stat}")
                    total_time = int(transfers[mask].iloc[0]["total_task_time"])
                    # Jos siirtymä on mahdollinen, lisää ehto
                    cond = model.NewBoolVar(f"trans_{batch}_{prev_stage}_{from_stat}_to_{this_stage}_{to_stat}")
                    model.Add(prev_station == from_stat).OnlyEnforceIf(cond)
                    model.Add(this_station == to_stat).OnlyEnforceIf(cond)
                    model.Add(this_start >= prev_end + total_time).OnlyEnforceIf(cond)
                    model.AddBoolOr([cond.Not(), prev_station == from_stat])
                    model.AddBoolOr([cond.Not(), this_station == to_stat])
                    transfer_time_vars.append(cond)
            # Varmista että jokin siirtymä toteutuu
            model.AddBoolOr(transfer_time_vars)

    # Aloitus- ja lopetusasema
    transporter_start = int(transporters.iloc[0]["Start_station"])
    first_batch = batches["Batch"].iloc[0]
    first_stage = int(treatment_programs[first_batch].iloc[0]["Stage"])
    model.Add(task_vars[(first_batch, first_stage)]["station"] == transporter_start)
    model.Add(task_vars[(first_batch, first_stage)]["start"] == 0)
    # Lopetusasema: viimeinen vaihe viimeiselle erälle
    last_batch = batches["Batch"].iloc[-1]
    last_stage = int(treatment_programs[last_batch].iloc[-1]["Stage"])
    model.Add(task_vars[(last_batch, last_stage)]["station"] == transporter_start)

    # Tavoite: minimoi makespan (kaikkien erien viimeisen vaiheen päättymisaika)
    makespans = [task_vars[(batch, int(treatment_programs[batch].iloc[-1]["Stage"]))]["end"] for batch in batches["Batch"]]
    makespan = model.NewIntVar(0, 10**6, "makespan")
    model.AddMaxEquality(makespan, makespans)
    model.Minimize(makespan)

    # Ratkaise
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Tallenna tulokset
    result_path = os.path.join(logs_dir, "cp-sat-result-schedule.csv")
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
    print(f"[CP-SAT] Makespan: {solver.Value(makespan)} sekuntia")

# Esimerkki kutsu:
# cp_sat_optimize("output/2025-10-26_13-00-00/")
