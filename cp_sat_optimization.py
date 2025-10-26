import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_optimize(output_dir):
    task_vars = {}
    virheet = []
    # ...existing code...
    # task_vars täyttö (olemassa jo alempana)
    # ...existing code...
    if virheet:
        print("\n".join(virheet))
        print("[CP-SAT] Optimointi keskeytetty virheiden vuoksi.")
        return
    if not task_vars:
        print("[CP-SAT] VIRHE: Yhtään vaihetta ei voitu mallintaa. Tarkista käsittelyohjelmat ja asemat.")
        return
    # DEBUG: Tulosta kaikki task_vars-avaimet ja järjestysparit task_vars-täytön jälkeen
    print("[DEBUG] task_vars.keys():", list(task_vars.keys()))
    for batch in batches["Batch"]:
        program = treatment_programs[batch]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        print(f"[DEBUG] batch {batch} stages: {stages}")
    # Yläraja-arvo muuttujille
    MAX_TIME = 10**6
    # --- Mallinnus alkaa ---
    # Kaikki muuttujien ja rajoitteiden luonti tapahtuu tässä, EI solver.Solve(model) ennen tätä!
    # ...mallin muuttujat ja rajoitteet...
    """
    Suorittaa CP-SAT-optimoinnin requirements-tiedoston vaatimusten mukaisesti.
    Käyttää esikäsiteltyjä tiedostoja (cp-sat-alkuiset) ja tallentaa tulokset logs-hakemistoon.
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
            if not possible_stations:
                print(f"[CP-SAT] VIRHE: Ei mahdollisia asemia batchille {batch}, vaihe {stage}: MinStat={min_stat}, MaxStat={max_stat}")
                print(f"  Tarkista cp-sat-treatment-program-{batch}.csv ja cp-sat-stations.csv")
                print(f"  Ohjelman rivi: {row}")
                continue

            duration_var = model.NewIntVar(min_time, max_time, f"duration_{batch}_{stage}")
            start_var = model.NewIntVar(0, MAX_TIME, f"start_{batch}_{stage}")
            end_var = model.NewIntVar(0, MAX_TIME, f"end_{batch}_{stage}")
    # Pakotetaan kaikille oikeille vaiheille (ei dummy/ei viimeinen nollakestoinen) Start/End < MAX_TIME
    for (batch, stage), vars in task_vars.items():
        # Dummy-vaihe (alku) ja viimeinen nollakestoinen vaihe ohitetaan
        is_dummy = vars['duration'].Proto().domain == [0, 0] and stage == 0
        is_last = vars.get('is_last', False)
        if not is_dummy and not (is_last and vars['duration'].Proto().domain == [0, 0]):
            model.Add(vars['start'] < MAX_TIME)
            model.Add(vars['end'] < MAX_TIME)
            station_domain = cp_model.Domain.FromValues(possible_stations)
            station_var = model.NewIntVarFromDomain(station_domain, f"station_{batch}_{stage}")
            station_bools = []
            intervals = []
            for s in possible_stations:
            # Täytetään task_vars ensin
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
            if idx == last_idx and prev_end_var is not None:
                model.Add(start_var == prev_end_var)
                model.Add(end_var == prev_end_var)

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

    # Sääntö 1: Vaiheiden järjestys
    for batch in batches["Batch"]:
        program = treatment_programs[batch]
        stages = [int(row["Stage"]) for _, row in program.iterrows()]
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            model.Add(task_vars[(batch, this_stage)]["start"] >= task_vars[(batch, prev_stage)]["end"])

    # Sääntö 2: Käsittelyaikojen min/max (sisältyy duration_varin rajoihin)

    # Sääntö 3: Asemalla vain yksi erä kerrallaan (AddNoOverlap per asema)
    for station in stations["Number"]:
        station_intervals = []
        for (batch, stage), vars in task_vars.items():
            for s, interval, is_this_station, *_ in vars["intervals"]:
                if s == station:
                    station_intervals.append(interval)
        if station_intervals:
            model.AddNoOverlap(station_intervals)

    # Sääntö 4: Nostimen siirtoajat (fysiikkaan perustuvat, haetaan transfers-taulukosta)
    for batch in batches["Batch"]:
        program = treatment_programs[batch]
        for idx in range(1, len(program)):
            prev_stage = int(program.iloc[idx-1]["Stage"])
            this_stage = int(program.iloc[idx]["Stage"])
            prev_vars = task_vars[(batch, prev_stage)]
            this_vars = task_vars[(batch, this_stage)]
            # Jos seuraava vaihe on viimeinen, ei mallinneta siirtoa pois asemalta (vapautus tapahtuu automaattisesti)
            if this_vars.get("is_last", False):
                continue
            transfer_time_vars = []
            for i, from_stat in enumerate(prev_vars["possible_stations"]):
                for j, to_stat in enumerate(this_vars["possible_stations"]):
                    if from_stat == to_stat:
                        total_time = 0
                    else:
                        mask = (transfers["from_station"] == from_stat) & (transfers["to_station"] == to_stat)
                        if not mask.any():
                            raise ValueError(f"Siirtymäaika puuttuu: {from_stat} -> {to_stat}")
                        total_time = int(transfers[mask].iloc[0]["total_task_time"])
                    cond = model.NewBoolVar(f"trans_{batch}_{prev_stage}_{from_stat}_to_{this_stage}_{to_stat}")
                    model.AddImplication(cond, prev_vars["station_bools"][i])
                    model.AddImplication(cond, this_vars["station_bools"][j])
                    model.Add(this_vars["start"] >= prev_vars["end"] + total_time).OnlyEnforceIf(cond)
                    transfer_time_vars.append(cond)
            model.AddBoolOr(transfer_time_vars)

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
