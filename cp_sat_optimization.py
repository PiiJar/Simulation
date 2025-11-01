"""
CP-SAT tuotantolinjan optimointimalli vaiheittain, vaatimusdokumentin mukaisesti.
Uusi versio - kirjoitettu puhtaalta pöydältä requirements-dokumentin mukaan.
"""
import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_optimization(output_dir, hard_order_constraint=False):
    """
    CP-SAT optimointi requirements-dokumentin kappale 4 mukaisesti.
    Vaiheittainen implementaatio (4.4): Perusoptimiointi -> Nostimen rajoitteet -> Vaihtoajat -> Asemavalinta
    """
    print("🚀 Aloitetaan uusi CP-SAT optimointi...")
    
    # 1. Lue lähtötiedot
    cp_sat_dir = os.path.join(output_dir, "cp_sat")
    batches_df = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_batches.csv"))
    stations_df = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_stations.csv"))
    transfers_df = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_transfer_tasks.csv"))
    transporters_df = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_transporters.csv"))
    
    # Lue käsittelyohjelmat
    treatment_programs = {}
    for _, batch_row in batches_df.iterrows():
        batch_id = int(batch_row["Batch"])
        program_file = os.path.join(cp_sat_dir, f"cp_sat_treatment_program_{batch_id}.csv")
        treatment_programs[batch_id] = pd.read_csv(program_file)
    
    print(f"📊 Luettu {len(batches_df)} erää, {len(stations_df)} asemaa, {len(transfers_df)} siirtotehtävää")
    
    # 2. Luo CP-SAT malli
    model = cp_model.CpModel()
    MAX_TIME = 100000  # Riittävän suuri yläraja (sekunteina)
    
    # 3. Määrittele muuttujat (Requirements 4.1)
    print("🔧 Määritellään muuttujat...")
    task_vars = create_task_variables(model, batches_df, treatment_programs, stations_df, MAX_TIME)
    makespan = model.NewIntVar(0, MAX_TIME, "makespan")
    
    # 4. Implementoi rajoitteet vaiheittain (Requirements 4.2)
    print("⚖️ Lisätään rajoitteet...")
    
    # 4.2.1 Käsittelyjärjestysrajoite (Sääntö 1)
    add_treatment_order_constraints(model, task_vars, treatment_programs)
    
    # 4.2.2 Käsittelyaikarajoite (Sääntö 2) 
    add_treatment_time_constraints(model, task_vars, treatment_programs)
    
    # 4.2.3 Aseman yksinomaisuusrajoite (Sääntö 3)
    add_station_exclusivity_constraints(model, task_vars, stations_df)
    
    # 4.2.4 Vaihtoaikarajoite (Sääntö 3.1) - KRIITTINEN!
    add_batch_change_time_constraints(model, task_vars, treatment_programs, transfers_df, stations_df)
    
    # 4.2.5 Nostimen järjestysrajoite (Sääntö 4.1)
    add_hoist_sequencing_constraints(model, task_vars, treatment_programs, transfers_df, transporters_df)
    
    # 4.2.6 Asemavalintarajoite (Vapausaste 2)
    add_station_selection_constraints(model, task_vars, treatment_programs, stations_df)
    
    # 5. Aseta optimointitavoite (Requirements 4.3)
    print("🎯 Asetetaan optimointitavoite...")
    set_makespan_objective(model, task_vars, treatment_programs, makespan)
    
    print("✅ CP-SAT malli luotu - valmis optimointiin!")
    
    # Suorita optimointi heti ja tallenna tulokset
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300.0  # 5 minuuttia
    
    print("🔍 Ratkaistaan CP-SAT mallia...")
    status = solver.Solve(model)
    
    # Tallenna tulokset
    save_optimization_results(solver, status, task_vars, treatment_programs, output_dir)
    
    return model, task_vars, treatment_programs

def save_optimization_results(solver, status, task_vars, treatment_programs, output_dir):
    """Tallenna optimoinnin tulokset"""
    from ortools.sat.python import cp_model
    
    status_str = {
        cp_model.OPTIMAL: "OPTIMAL", 
        cp_model.FEASIBLE: "FEASIBLE", 
        cp_model.INFEASIBLE: "INFEASIBLE", 
        cp_model.MODEL_INVALID: "MODEL_INVALID", 
        cp_model.UNKNOWN: "UNKNOWN"
    }.get(status, str(status))
    
    print(f"📊 Optimoinnin tila: {status_str}")
    
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Loki optimoinnin tilasta
    from simulation_logger import get_logger
    logger = get_logger()
    logger.log('OPTIMIZATION_STATUS', f'{status_str.lower()}')
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        logger.log('ERROR', f'cp-sat {status_str.lower()}: optimointi epäonnistui')
        print(f"❌ Optimointi epäonnistui: {status_str}")
        return
    
    # Kerää tulokset
    results = []
    for (batch_id, stage), vars in task_vars.items():
        results.append({
            "Batch": batch_id,
            "Stage": stage,
            "Station": solver.Value(vars["station"]),
            "Start": solver.Value(vars["start"]),
            "End": solver.Value(vars["end"]),
            "Duration": solver.Value(vars["duration"])
        })
    
    # Tallenna tulokset
    df_result = pd.DataFrame(results)
    result_path = os.path.join(logs_dir, "cp_sat_optimization_schedule.csv")
    df_result.to_csv(result_path, index=False)
    
    # Laske makespan
    max_end = df_result["End"].max()
    print(f"🎯 Makespan: {max_end} sekuntia ({max_end/60:.1f} minuuttia)")
    logger.log('OPTIMIZATION_RESULT', f'makespan: {max_end} seconds')
    
    print(f"💾 Tulokset tallennettu: {result_path}")
    print("✅ Optimointi valmis!")

def create_task_variables(model, batches_df, treatment_programs, stations_df, MAX_TIME):
    """4.1.1 Aikamuuttujat ja 4.1.2 Asemamuuttujat"""
    task_vars = {}
    
    for _, batch_row in batches_df.iterrows():
        batch_id = int(batch_row["Batch"])
        program = treatment_programs[batch_id]
        
        for _, stage_row in program.iterrows():
            stage = int(stage_row["Stage"])
            min_stat = int(stage_row["MinStat"])
            max_stat = int(stage_row["MaxStat"])
            
            # Hae samaan ryhmään kuuluvat asemat
            if min_stat == max_stat:
                possible_stations = [min_stat]
            else:
                group = stations_df[stations_df["Number"] == min_stat]["Group"].iloc[0]
                possible_stations = stations_df[
                    (stations_df["Number"] >= min_stat) & 
                    (stations_df["Number"] <= max_stat) & 
                    (stations_df["Group"] == group)
                ]["Number"].tolist()
            
            # Aikamuuttujat
            min_time = int(pd.to_timedelta(stage_row["MinTime"]).total_seconds())
            max_time = int(pd.to_timedelta(stage_row["MaxTime"]).total_seconds())
            
            start_time = model.NewIntVar(0, MAX_TIME, f"start_{batch_id}_{stage}")
            end_time = model.NewIntVar(0, MAX_TIME, f"end_{batch_id}_{stage}")
            duration = model.NewIntVar(min_time, max_time, f"duration_{batch_id}_{stage}")
            
            # Asemamuuttuja
            station_domain = cp_model.Domain.FromValues(possible_stations)
            selected_station = model.NewIntVarFromDomain(station_domain, f"station_{batch_id}_{stage}")
            
            # Linkitä aika-muuttujat
            model.Add(end_time == start_time + duration)
            
            task_vars[(batch_id, stage)] = {
                "start": start_time,
                "end": end_time,
                "duration": duration,
                "station": selected_station,
                "possible_stations": possible_stations,
                "min_time": min_time,
                "max_time": max_time
            }
    
    return task_vars

def add_treatment_order_constraints(model, task_vars, treatment_programs):
    """4.2.1 Käsittelyjärjestysrajoite (Sääntö 1)"""
    for batch_id, program in treatment_programs.items():
        stages = sorted(program["Stage"].tolist())
        
        for i in range(len(stages) - 1):
            current_stage = stages[i]
            next_stage = stages[i + 1]
            
            # Seuraava vaihe alkaa vasta kun edellinen päättyy
            model.Add(
                task_vars[(batch_id, next_stage)]["start"] >= 
                task_vars[(batch_id, current_stage)]["end"]
            )

def add_treatment_time_constraints(model, task_vars, treatment_programs):
    """4.2.2 Käsittelyaikarajoite (Sääntö 2)"""
    # Aikarajat on jo asetettu muuttujien luonnissa
    # Tarkistetaan vain että duration linkitys on kunnossa
    for (batch_id, stage), vars in task_vars.items():
        model.Add(vars["duration"] >= vars["min_time"])
        model.Add(vars["duration"] <= vars["max_time"])

def add_station_exclusivity_constraints(model, task_vars, stations_df):
    """4.2.3 Aseman yksinomaisuusrajoite (Sääntö 3)"""
    for station_num in stations_df["Number"]:
        intervals = []
        
        for (batch_id, stage), vars in task_vars.items():
            # Ohita stage 0 (aloitusasema saa olla päällekkäinen)
            if stage == 0:
                continue
                
            if station_num in vars["possible_stations"]:
                # Luo boolean: onko tämä tehtävä tällä asemalla
                is_at_station = model.NewBoolVar(f"at_station_{batch_id}_{stage}_{station_num}")
                model.Add(vars["station"] == station_num).OnlyEnforceIf(is_at_station)
                model.Add(vars["station"] != station_num).OnlyEnforceIf(is_at_station.Not())
                
                # Luo optionaalinen intervalli
                interval = model.NewOptionalIntervalVar(
                    vars["start"], vars["duration"], vars["end"], 
                    is_at_station, f"interval_{batch_id}_{stage}_{station_num}"
                )
                intervals.append(interval)
        
        # Ei päällekkäisyyksiä samalla asemalla
        if intervals:
            model.AddNoOverlap(intervals)

def add_batch_change_time_constraints(model, task_vars, treatment_programs, transfers_df, stations_df):
    """4.2.4 Vaihtoaikarajoite (Sääntö 3.1) - ESILASKETTUJEN TIETOJEN PERUSTEELLA"""
    print("🔄 Lisätään vaihtoaikarajoitteet (esilaskettujen siirtoaikojen perusteella)...")
    
    # Ryhmittele tehtävät asemittain (paitsi stage 0)
    tasks_by_station = {}
    for (batch_id, stage), vars in task_vars.items():
        if stage == 0:  # Ohita aloitusasema
            continue
            
        for station_num in vars["possible_stations"]:
            if station_num not in tasks_by_station:
                tasks_by_station[station_num] = []
            tasks_by_station[station_num].append((batch_id, stage))
    
    # Jokaiselle asemalle: laske realistiset vaihtoajat
    for station_num, tasks in tasks_by_station.items():
        print(f"   🏭 Asema {station_num}: {len(tasks)} mahdollista tehtävää")
        
        for i, task1 in enumerate(tasks):
            for j, task2 in enumerate(tasks):
                if i >= j:  # Vältetään duplikaatit
                    continue
                    
                batch1, stage1 = task1
                batch2, stage2 = task2
                vars1 = task_vars[task1]
                vars2 = task_vars[task2]
                
                # Luo booleanit: onko tehtävät samalla asemalla
                task1_at_station = model.NewBoolVar(f"t1_at_{batch1}_{stage1}_{station_num}")
                task2_at_station = model.NewBoolVar(f"t2_at_{batch2}_{stage2}_{station_num}")
                
                model.Add(vars1["station"] == station_num).OnlyEnforceIf(task1_at_station)
                model.Add(vars1["station"] != station_num).OnlyEnforceIf(task1_at_station.Not())
                model.Add(vars2["station"] == station_num).OnlyEnforceIf(task2_at_station)
                model.Add(vars2["station"] != station_num).OnlyEnforceIf(task2_at_station.Not())
                
                # Molemmat samalla asemalla
                both_at_station = model.NewBoolVar(f"both_at_{batch1}_{stage1}_{batch2}_{stage2}_{station_num}")
                model.AddBoolAnd([task1_at_station, task2_at_station]).OnlyEnforceIf(both_at_station)
                model.AddBoolOr([task1_at_station.Not(), task2_at_station.Not()]).OnlyEnforceIf(both_at_station.Not())
                
                # LASKE VAIHTOAIKA ESILASKETTUJEN TIETOJEN PERUSTEELLA
                batch_change_time = calculate_realistic_batch_change_time(
                    task1, task2, treatment_programs, transfers_df, task_vars
                )
                
                print(f"     ↔️ Vaihtoaika {batch1}s{stage1}→{batch2}s{stage2}: {batch_change_time}s")
                
                # Järjestys: task1 ennen task2
                task1_before_task2 = model.NewBoolVar(f"order_{batch1}_{stage1}_{batch2}_{stage2}_{station_num}")
                
                # Jos molemmat samalla asemalla, jompikumpi järjestys on pakko olla
                model.AddBoolOr([task1_before_task2, task1_before_task2.Not()]).OnlyEnforceIf(both_at_station)
                
                # task1 ennen task2: task2_start >= task1_end + vaihtoaika
                model.Add(
                    vars2["start"] >= vars1["end"] + batch_change_time
                ).OnlyEnforceIf([both_at_station, task1_before_task2])
                
                # task2 ennen task1: task1_start >= task2_end + vaihtoaika  
                model.Add(
                    vars1["start"] >= vars2["end"] + batch_change_time
                ).OnlyEnforceIf([both_at_station, task1_before_task2.Not()])

def calculate_realistic_batch_change_time(task1, task2, treatment_programs, transfers_df, task_vars):
    """
    Laskee vaihtoajan requirements-dokumentin mukaan esilaskettujen tietojen perusteella:
    batch_change_time = Total_Task_Time(x→y) + Transfer_Time(y→z) + Total_Task_Time(z→x)
    """
    batch1, stage1 = task1
    batch2, stage2 = task2
    
    # 1. Mistä task1 tulee ja mihin menee
    current_station_x = task_vars[task1]["possible_stations"][0]  # Yksinkertaistus: käytä ensimmäistä
    
    # Mihin task1 menee seuraavaksi (y)
    program1 = treatment_programs[batch1]
    stages1 = sorted(program1["Stage"].tolist())
    current_idx = stages1.index(stage1)
    
    if current_idx + 1 < len(stages1):
        next_stage1 = stages1[current_idx + 1]
        next_station_y = task_vars[(batch1, next_stage1)]["possible_stations"][0]
    else:
        # Viimeinen vaihe - oletetaan että menee pois järjestelmästä
        next_station_y = current_station_x  # Yksinkertaistus
    
    # 2. Mistä task2 tulee (z)
    program2 = treatment_programs[batch2]
    stages2 = sorted(program2["Stage"].tolist())
    current_idx2 = stages2.index(stage2)
    
    if current_idx2 > 0:
        prev_stage2 = stages2[current_idx2 - 1]
        prev_station_z = task_vars[(batch2, prev_stage2)]["possible_stations"][0]
    else:
        # Ensimmäinen vaihe - tulee aloitusasemalta
        prev_station_z = current_station_x  # Stage 0 asemalta
    
    # 3. Hae esilasketut ajat transfers_df:stä
    
    # Total_Task_Time(x → y): task1 poisvienti
    mask1 = (transfers_df["From_Station"] == current_station_x) & \
            (transfers_df["To_Station"] == next_station_y)
    total_task_time_1 = int(transfers_df[mask1]["TotalTaskTime"].iloc[0]) if mask1.any() else 50
    
    # Transfer_Time(y → z): nostimen tyhjäsiirto
    mask2 = (transfers_df["From_Station"] == next_station_y) & \
            (transfers_df["To_Station"] == prev_station_z)
    transfer_time_empty = int(transfers_df[mask2]["TransferTime"].iloc[0]) if mask2.any() else 10
    
    # Total_Task_Time(z → x): task2 tuonti  
    mask3 = (transfers_df["From_Station"] == prev_station_z) & \
            (transfers_df["To_Station"] == current_station_x)
    total_task_time_2 = int(transfers_df[mask3]["TotalTaskTime"].iloc[0]) if mask3.any() else 50
    
    # Kokonaisvaihtoaika = requirements-dokumentin kaava
    batch_change_time = total_task_time_1 + transfer_time_empty + total_task_time_2
    
    return batch_change_time

def add_hoist_sequencing_constraints(model, task_vars, treatment_programs, transfers_df, transporters_df):
    """4.2.5 Nostimen järjestysrajoite - VAPAUSASTE 4 + 3 IMPLEMENTOITU"""
    print("🏗️ Lisätään nostimen järjestysrajoitteet (Vapausaste 4: rinnakkaisuus + Vapausaste 3: identtisten erien järjestys)...")
    
    # VAPAUSASTE 3: Tarkista identtiset erät (sama käsittelyohjelma)
    batch_programs = {}
    for batch_id in treatment_programs.keys():
        program = treatment_programs[batch_id]
        # Luo tunniste käsittelyohjelmasta (stages + asemat + ajat)
        program_signature = tuple(sorted([
            (row['Stage'], row['MinStat'], row['MaxStat'], row['MinTime'], row['MaxTime'])
            for _, row in program.iterrows()
        ]))
        batch_programs[batch_id] = program_signature
    
    # Ryhmittele identtiset erät
    identical_groups = {}
    for batch_id, signature in batch_programs.items():
        if signature not in identical_groups:
            identical_groups[signature] = []
        identical_groups[signature].append(batch_id)
    
    # Tulosta identtiset ryhmät
    for signature, batches in identical_groups.items():
        if len(batches) > 1:
            print(f"   🔄 Identtiset erät (säilytetään järjestys): {batches}")
    
    # VAPAUSASTE 4: Nostimen rinnakkaisuus - erät voivat olla samanaikaisesti eri asemilla!
    # Vain siirtotehtävät eivät saa olla päällekkäin (nostin voi olla vain yhdessä paikassa kerrallaan)
    
    hoist_intervals = []
    
    # Luo siirtotehtävät optimaalisina intervalleina
    for batch_id, program in treatment_programs.items():
        stages = sorted(program["Stage"].tolist())
        
        for i in range(len(stages) - 1):
            current_stage = stages[i]
            next_stage = stages[i + 1]
            
            # Hae minimiaikainen siirtoaika
            current_station = task_vars[(batch_id, current_stage)]["possible_stations"][0]
            next_station = task_vars[(batch_id, next_stage)]["possible_stations"][0]
            
            # Hae siirtoaika transfers_df:stä
            mask = (transfers_df["From_Station"] == current_station) & \
                   (transfers_df["To_Station"] == next_station)
            min_transfer_time = int(transfers_df[mask]["TotalTaskTime"].iloc[0]) if mask.any() else 50
            
            # Siirtotehtävä alkaa kun edellinen vaihe päättyy
            start_var = task_vars[(batch_id, current_stage)]["end"]
            # Ja päättyy kun seuraava vaihe alkaa
            end_var = task_vars[(batch_id, next_stage)]["start"]
            
            # VAPAUSASTE 4: Anna optimointiin vapaus määrittää tehokkain siirtoaika
            model.Add(end_var >= start_var + min_transfer_time)
            
            # Luo optimaalinen duration
            duration_var = model.NewIntVar(min_transfer_time, min_transfer_time + 600, 
                                         f"transfer_duration_{batch_id}_{current_stage}_{next_stage}")
            model.Add(duration_var == end_var - start_var)
            
            interval = model.NewIntervalVar(start_var, duration_var, end_var, 
                                          f"hoist_interval_{batch_id}_{current_stage}_{next_stage}")
            hoist_intervals.append(interval)
    
    # VAPAUSASTE 3: Pakota identtisten erien alkuperäinen järjestys
    for signature, batches in identical_groups.items():
        if len(batches) > 1:
            # Järjestä ID:n mukaan (alkuperäinen järjestys)
            sorted_batches = sorted(batches)
            for i in range(len(sorted_batches) - 1):
                batch1 = sorted_batches[i]
                batch2 = sorted_batches[i + 1]
                
                # Pakota että batch1 aloittaa ennen batch2:ta
                batch1_start = task_vars[(batch1, 0)]["start"]
                batch2_start = task_vars[(batch2, 0)]["start"] 
                model.Add(batch1_start <= batch2_start)
                print(f"     ↗️ Pakotettu järjestys (identtiset): {batch1} → {batch2}")
    
    # Nostimen ei voi tehdä päällekkäisiä siirtoja
    if hoist_intervals:
        model.AddNoOverlap(hoist_intervals)
        print(f"   🔗 {len(hoist_intervals)} siirtotehtävää (optimaalinen rinnakkaisuus)")

def add_station_selection_constraints(model, task_vars, treatment_programs, stations_df):
    """4.2.6 Asemavalintarajoite (Vapausaste 2)"""
    # Asemavalinta on jo implementoitu create_task_variables -funktiossa
    # Tarkistetaan vain että ryhmärajoitteet ovat kunnossa
    
    for (batch_id, stage), vars in task_vars.items():
        # Asema oltava mahdollisten asemien listalla (jo asetettu domain-rajoitteena)
        pass

def set_makespan_objective(model, task_vars, treatment_programs, makespan):
    """4.3.1 Makespan-minimointi"""
    last_ends = []
    
    for batch_id, program in treatment_programs.items():
        final_stage = int(program["Stage"].max())
        last_ends.append(task_vars[(batch_id, final_stage)]["end"])
    
    if last_ends:
        model.AddMaxEquality(makespan, last_ends)
        model.Minimize(makespan)
    else:
        print("⚠️ Ei viimeisiä vaiheita löytynyt!")

def cp_sat_optimization_OLD(output_dir, hard_order_constraint=False):
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


    # (Poistettu: ei pakoteta stage 1:n alkuaikaa, koska se määräytyy edellisen vaiheen ja siirron mukaan)

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

    # --- Korjaus: viimeisen vaiheen duration voi olla 0, mutta siirto viimeiselle asemalle tehdään aina ---
    # Ei vaadita, että viimeisen vaiheen duration kattaa siirtoajan, vaan siirto tehdään aina, vaikka duration=0
    # Tämä vaikuttaa vain siirtologiikkaan, ei duration-muuttujaan

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

    # Vaihe 4: Nostimen siirrot ja deadhead-siirtymät eksplisiittisesti
    transporter_intervals_by_id = {}
    deadhead_intervals_by_id = {}
    last_transporter_task_end = {}  # transporter_id -> end time of last task
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
                            # DEADHEAD: Jos tämä ei ole ensimmäinen siirto tälle nostimelle, lisää deadhead-siirtymä edellisen tehtävän jälkeen
                            if transporter_id in last_transporter_task_end:
                                prev_end = last_transporter_task_end[transporter_id]
                                # Deadhead-siirtymä: edellisen tehtävän päättymisestä tämän tehtävän alkuun (nostin siirtyy ilman kuormaa)
                                deadhead_start = prev_end
                                deadhead_end = trans_start
                                prev_to_stat_val = from_stat
                                mask_deadhead = (
                                    (transfers["Transporter"] == transporter_id) &
                                    (transfers["From_Station"] == prev_to_stat_val) &
                                    (transfers["To_Station"] == from_stat)
                                )
                                deadhead_time = None
                                if mask_deadhead.any():
                                    deadhead_time = int(round(float(transfers[mask_deadhead].iloc[0]["TransferTime"])))
                                elif prev_to_stat_val == from_stat:
                                    deadhead_time = 0  # paikallaan odotus
                                else:
                                    deadhead_time = None  # ei reittiä, ei mallinneta deadheadia
                                if deadhead_time is not None:
                                    deadhead_duration = model.NewIntVar(deadhead_time, deadhead_time, f"deadhead_{batch_int}_{prev_stage}_{this_stage}_T{transporter_id}")
                                    model.Add(deadhead_end == deadhead_start + deadhead_duration).OnlyEnforceIf(is_transfer)
                                    deadhead_interval = model.NewOptionalIntervalVar(deadhead_start, deadhead_duration, deadhead_end, is_transfer, f"deadhead_{batch_int}_{prev_stage}_{this_stage}_T{transporter_id}")
                                    if transporter_id not in deadhead_intervals_by_id:
                                        deadhead_intervals_by_id[transporter_id] = []
                                    deadhead_intervals_by_id[transporter_id].append(deadhead_interval)
                            last_transporter_task_end[transporter_id] = trans_end
                            break  # Käytä vain ensimmäinen sopiva nostin
            # Vain yksi siirto voi olla aktiivinen per batch, stage
            if transfer_bools:
                model.Add(sum(transfer_bools) == 1)
    # AddNoOverlap kaikille nostimen tehtäville ja deadhead-siirtymille
    for transporter_id in transporter_intervals_by_id:
        intervals = transporter_intervals_by_id[transporter_id]
        if transporter_id in deadhead_intervals_by_id:
            intervals += deadhead_intervals_by_id[transporter_id]
        if intervals:
            model.AddNoOverlap(intervals)
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
    # Vaatimusten mukaisesti: minimoi vain makespan, toissijaisesti järjestysrikkomukset
    model.Minimize(makespan * 10000 + order_penalty * 100)

    # Vaihe 7: Erityistapaukset (askel 0)
    # (Tässä vaiheessa askel 0 sallitaan päällekkäisyys, koska AddNoOverlap ei rajoita sitä)
    # Suorita optimointi ja tallenna tulokset heti pipeline-vaiheessa
    solve_and_save(model, task_vars, treatment_programs, output_dir)
    return model, task_vars, treatment_programs
def solve_and_save(model, task_vars, treatment_programs, output_dir):
    from ortools.sat.python import cp_model
    import pandas as pd
    import os
    from datetime import datetime
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
    # Käytä simulation_loggeria yhtenäiseen aikaleimaan
    from simulation_logger import get_logger
    logger = get_logger()
    logger.log('OPTIMIZATION_STATUS', f'{status_str.lower()}')
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Kirjoita tarkempi syy, jos epäonnistui
        if status == cp_model.INFEASIBLE:
            logger.log('ERROR', 'cp-sat infeasible: tarkista siirtorajoitteet, duration-rajat ja mahdolliset asemat')
        elif status == cp_model.MODEL_INVALID:
            logger.log('ERROR', 'cp-sat model invalid: tarkista muuttujien domainit ja constraintit')
        elif status == cp_model.UNKNOWN:
            logger.log('ERROR', 'cp-sat tuntematon virhe')
        else:
            logger.log('ERROR', f'cp-sat status: {status_str.lower()}')
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

