"""
CP-SAT tuotantolinjan optimointimalli - YKSINKERTAINEN VERSIO DEBUGGAUSTA VARTEN
"""
import os
import pandas as pd
from ortools.sat.python import cp_model

def cp_sat_optimization(output_dir, hard_order_constraint=False):
    print("🔧 CP-SAT DEBUG: Aloitetaan yksinkertainen malli...")
    
    # 1. Lue snapshotin tiedot
    batches = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_batches.csv"))
    stations = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_stations.csv"))
    transfers = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_transfer_tasks.csv"))
    treatment_programs = {}
    for batch in batches["Batch"]:
        batch_int = int(batch)
        fname = os.path.join(output_dir, "cp_sat", f"cp_sat_treatment_program_{batch_int}.csv")
        df = pd.read_csv(fname)
        treatment_programs[batch_int] = df
    
    print(f"📊 Data: {len(batches)} erää, {len(stations)} asemaa")
    for batch_int, program in treatment_programs.items():
        print(f"   Erä {batch_int}: {len(program)} vaihetta")

    model = cp_model.CpModel()
    MAX_TIME = 100000  # Pienempi debug-arvo

    # VAIHE 1: Luo yksinkertaiset muuttujat - EI asemavalintaa vielä
    task_vars = {}
    print("🔧 Luodaan muuttujat...")
    
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        for idx, row in program.iterrows():
            stage = int(row["Stage"])
            min_stat = int(row["MinStat"])
            max_stat = int(row["MaxStat"])
            
            # DEBUG: Käytä vain ensimmäistä mahdollista asemaa
            station = min_stat  # Yksinkertainen: ei asemavalintaa
            
            min_time = int(pd.to_timedelta(row["MinTime"]).total_seconds())
            max_time = int(pd.to_timedelta(row["MaxTime"]).total_seconds())
            
            duration = model.NewIntVar(min_time, max_time, f"duration_{batch_int}_{stage}")
            start = model.NewIntVar(0, MAX_TIME, f"start_{batch_int}_{stage}")
            end = model.NewIntVar(0, MAX_TIME, f"end_{batch_int}_{stage}")
            
            model.Add(end == start + duration)
            
            task_vars[(batch_int, stage)] = {
                "start": start, 
                "end": end, 
                "duration": duration, 
                "station": station  # Kiinteä arvo
            }
            print(f"   Erä {batch_int}, Stage {stage}: Asema {station}, Aika {min_time}-{max_time}s")

    # VAIHE 2: Erän sisäinen järjestys (stages peräkkäin)
    print("🔧 Lisätään vaihejärjestys...")
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        stages = sorted([int(row["Stage"]) for _, row in program.iterrows()])
        
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            # Seuraava vaihe alkaa vasta kun edellinen päättyy
            model.Add(task_vars[(batch_int, this_stage)]["start"] >= 
                     task_vars[(batch_int, prev_stage)]["end"])
            print(f"   Erä {batch_int}: Stage {prev_stage} → {this_stage}")

    # VAIHE 3: Asemien yksikäyttöisyys (paitsi stage 0)
    print("🔧 Lisätään asemarajoitteet...")
    station_intervals = {}
    
    for (batch, stage), vars in task_vars.items():
        if stage == 0:  # Stage 0 saa olla päällekkäin
            continue
            
        station = vars["station"]
        if station not in station_intervals:
            station_intervals[station] = []
            
        interval = model.NewIntervalVar(
            vars["start"], vars["duration"], vars["end"], 
            f"interval_{batch}_{stage}_at_{station}"
        )
        station_intervals[station].append(interval)
    
    for station, intervals in station_intervals.items():
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)
            print(f"   Asema {station}: {len(intervals)} intervallia, ei päällekkäisyyttä")

    # VAIHE 4: Yksinkertainen nostimen siirto (ilman deadhead-kompleksisuutta)
    print("🔧 Lisätään yksinkertaiset siirtoajat...")
    
    # Luo lista kaikista transporter-tehtävistä (erän sisäiset siirrot)
    transporter_tasks = []
    
    for batch in batches["Batch"]:
        batch_int = int(batch)
        program = treatment_programs[batch_int]
        stages = sorted([int(row["Stage"]) for _, row in program.iterrows()])
        
        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            this_stage = stages[i]
            
            from_station = task_vars[(batch_int, prev_stage)]["station"]
            to_station = task_vars[(batch_int, this_stage)]["station"]
            
            # Hae siirtoaika
            transfer_mask = (
                (transfers["From_Station"] == from_station) & 
                (transfers["To_Station"] == to_station)
            )
            
            if transfer_mask.any():
                transfer_time = int(transfers[transfer_mask].iloc[0]["TotalTaskTime"])
                
                # Lisää tehtävä nostimen aikatauluun
                task_start = task_vars[(batch_int, prev_stage)]["end"]
                task_end = task_vars[(batch_int, this_stage)]["start"]
                
                # Seuraava vaihe alkaa vasta siirron jälkeen
                model.Add(task_end >= task_start + transfer_time)
                
                transporter_tasks.append({
                    'batch': batch_int,
                    'from_stage': prev_stage,
                    'to_stage': this_stage,
                    'from_station': from_station,
                    'to_station': to_station,
                    'start_time': task_start,
                    'end_time': task_end,
                    'transfer_time': transfer_time
                })
                
                print(f"   Siirto {from_station}→{to_station}: {transfer_time}s (Erä {batch_int}, Stage {prev_stage}→{this_stage})")
            else:
                print(f"   ⚠️ VIRHE: Ei siirtoa {from_station}→{to_station}")
                return None, None, None

    # VAIHE 4.1: Nostimen globaali järjestys (erien väliset siirtymät)
    print("🔧 Lisätään nostimen globaali järjestys...")
    
    # Luo järjestymuuttujat kaikille tehtäväpareille
    for i, task1 in enumerate(transporter_tasks):
        for j, task2 in enumerate(transporter_tasks):
            if i >= j:  # Vältä duplikaatit ja itse-viittaukset
                continue
                
            # Tehtävä 1 ennen tehtävää 2
            order_var = model.NewBoolVar(f"task_{i}_before_{j}")
            
            # Jos task1 ennen task2: task1.end + siirtoaika <= task2.start
            empty_transfer_time = 0
            if task1['to_station'] != task2['from_station']:
                # Nostimen tyhjäsiirto task1:n lopusta task2:n alkuun
                empty_mask = (
                    (transfers["From_Station"] == task1['to_station']) & 
                    (transfers["To_Station"] == task2['from_station'])
                )
                if empty_mask.any():
                    empty_transfer_time = int(transfers[empty_mask].iloc[0]["TransferTime"])
            
            # Rajoitteet järjestykselle
            model.Add(task1['end_time'] + empty_transfer_time <= task2['start_time']).OnlyEnforceIf(order_var)
            model.Add(task2['end_time'] + empty_transfer_time <= task1['start_time']).OnlyEnforceIf(order_var.Not())
            
            print(f"   Nostinjärjestys: Task {i} ↔ Task {j} (tyhjäsiirto: {empty_transfer_time}s)")

    # VAIHE 5: Identtisten erien järjestysrajoite
    print("🔧 Lisätään identtisten erien järjestysrajoite...")
    
    # Ryhmittele erät käsittelyohjelman mukaan
    batches_by_program = {}
    for batch in batches["Batch"]:
        batch_int = int(batch)
        # Käytä program tiedostoa identifiointiin
        program = treatment_programs[batch_int]
        program_signature = tuple(
            (int(row["Stage"]), int(row["MinStat"]), int(row["MaxStat"]), 
             int(pd.to_timedelta(row["MinTime"]).total_seconds()),
             int(pd.to_timedelta(row["MaxTime"]).total_seconds()))
            for _, row in program.iterrows()
        )
        
        if program_signature not in batches_by_program:
            batches_by_program[program_signature] = []
        batches_by_program[program_signature].append(batch_int)
    
    # Pakota alkuperäinen järjestys identtisille erille
    for signature, batch_list in batches_by_program.items():
        if len(batch_list) > 1:
            print(f"   Identtiset erät: {batch_list} → säilytetään järjestys")
            # Järjestä batch-ID:n mukaan (alkuperäinen järjestys)
            batch_list.sort()
            
            # Lisää rajoitteet: pienempi batch aloittaa ennen suurempaa
            for i in range(len(batch_list) - 1):
                smaller_batch = batch_list[i]
                larger_batch = batch_list[i + 1]
                
                # Pienempi erä aloittaa ennen suurempaa (stage 1, koska stage 0 voi olla päällekkäin)
                smaller_start = task_vars[(smaller_batch, 1)]["start"]
                larger_start = task_vars[(larger_batch, 1)]["start"]
                
                model.Add(smaller_start <= larger_start)
                print(f"     Erä {smaller_batch} aloittaa ennen erää {larger_batch}")

    # VAIHE 6: Optimointitavoite
    print("🔧 Asetetaan tavoite...")
    last_ends = []
    for (batch, stage), vars in task_vars.items():
        program = treatment_programs[batch]
        max_stage = int(program["Stage"].max())
        if stage == max_stage:
            last_ends.append(vars["end"])
            print(f"   Erä {batch} päättyy stage {stage}:ssa")
    
    if last_ends:
        makespan = model.NewIntVar(0, MAX_TIME, "makespan")
        model.AddMaxEquality(makespan, last_ends)
        model.Minimize(makespan)
        print(f"   Tavoite: Minimoi makespan ({len(last_ends)} erän maksimi)")

    # VAIHE 6: Ratkaise yksinkertainen malli
    print("🔧 Ratkaistaan malli...")
    solve_and_save_simple(model, task_vars, treatment_programs, output_dir)
    return model, task_vars, treatment_programs


def solve_and_save_simple(model, task_vars, treatment_programs, output_dir):
    """Yksinkertainen solver debuggausta varten"""
def solve_and_save_simple(model, task_vars, treatment_programs, output_dir):
    """Yksinkertainen solver debuggausta varten"""
    from ortools.sat.python import cp_model
    import pandas as pd
    import os
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0  # 1 minuutti riittää yksinkertaiselle mallille
    
    print("🔧 Ratkaistaan...")
    status = solver.Solve(model)
    
    status_names = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE", 
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN"
    }
    status_str = status_names.get(status, str(status))
    print(f"📊 Status: {status_str}")
    
    # Logi
    from simulation_logger import get_logger
    logger = get_logger()
    logger.log('OPTIMIZATION_STATUS', status_str.lower())
    
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if status == cp_model.INFEASIBLE:
            logger.log('ERROR', 'cp-sat infeasible (yksinkertainen malli): ongelman täytyy olla perustavissa rajoitteissa')
        else:
            logger.log('ERROR', f'cp-sat virhe: {status_str}')
        return
    
    # Tulokset
    print("📊 Ratkaisu löytyi! Tulokset:")
    results = []
    for (batch, stage), vars in task_vars.items():
        start_val = solver.Value(vars["start"])
        end_val = solver.Value(vars["end"]) 
        duration_val = solver.Value(vars["duration"])
        station_val = vars["station"]  # Kiinteä arvo
        
        results.append({
            "Batch": batch,
            "Stage": stage, 
            "Station": station_val,
            "Start": start_val,
            "End": end_val,
            "Duration": duration_val
        })
        print(f"   Erä {batch}, Stage {stage}: Asema {station_val}, {start_val}-{end_val} ({duration_val}s)")
    
    # Tallenna
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    result_path = os.path.join(logs_dir, "cp_sat_optimization_schedule.csv")
    
    df_result = pd.DataFrame(results)
    df_result.to_csv(result_path, index=False)
    print(f"💾 Tulos tallennettu: {result_path}")
    
    # Makespan
    if results:
        makespan_val = max(r["End"] for r in results)
        print(f"🎯 Makespan: {makespan_val} sekuntia ({makespan_val/60:.1f} min)")
    
    # Päivitä production.csv optimoiduilla lähtöajoilla
    print("💾 Päivitetään production.csv...")
    production_path = os.path.join(output_dir, "production.csv")
    if os.path.exists(production_path):
        production_df = pd.read_csv(production_path)
        
        # Laske todellinen optimaalinen aloitusaika kullekin erälle
        # = Ensimmäisen käsittelyvaiheen (Stage 1) alkuaika - siirtoaika alkuasemasta
        for _, result_row in df_result.iterrows():
            if result_row["Stage"] == 1:  # Ensimmäinen käsittelyvaihe
                batch_num = result_row["Batch"]
                stage1_start = result_row["Start"]  # Milloin Stage 1 alkaa
                
                # Hae siirtoaika alkuasemasta ensimmäiselle käsittelyasemalle
                # Löydetään batch:n tiedot
                batch_info = production_df[production_df["Batch"] == batch_num]
                if not batch_info.empty:
                    start_station = int(batch_info.iloc[0]["Start_station"])
                    target_station = result_row["Station"]
                    
                    # Lataa siirtoajat
                    transfers_path = os.path.join(output_dir, "cp_sat", "cp_sat_transfer_tasks.csv")
                    if os.path.exists(transfers_path):
                        transfers_df = pd.read_csv(transfers_path)
                        
                        # Hae siirtoaika (oletetaan nostin 1)
                        match = transfers_df[
                            (transfers_df["Transporter"] == 1) & 
                            (transfers_df["From_Station"] == start_station) & 
                            (transfers_df["To_Station"] == target_station)
                        ]
                        if not match.empty:
                            transport_time = float(match.iloc[0]["TotalTaskTime"])
                        else:
                            transport_time = 0
                    else:
                        transport_time = 0
                    
                    # Todellinen optimaalinen aloitusaika = Stage 1 alkuaika - siirtoaika
                    optimal_start_seconds = max(0, stage1_start - transport_time)
                    
                    # Muunna sekunnit muotoon hh:mm:ss
                    hours = int(optimal_start_seconds) // 3600
                    minutes = (int(optimal_start_seconds) % 3600) // 60
                    seconds = int(optimal_start_seconds) % 60
                    time_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    # Päivitä production.csv
                    mask = production_df["Batch"] == batch_num
                    if mask.any():
                        production_df.loc[mask, "Start_optimized"] = time_formatted
                        print(f"   Erä {batch_num}: Start_optimized = {time_formatted} (Stage 1 alkaa {stage1_start}s - siirtoaika {transport_time}s)")
        
        # Tallenna päivitetty production.csv
        production_df.to_csv(production_path, index=False)
        print(f"💾 Production.csv päivitetty: {production_path}")
    else:
        print(f"⚠️ Production.csv ei löytynyt: {production_path}")
    
    # Päivitä eräkohtaiset käsittelyohjelmat optimoiduilla ajoilla
    print("💾 Päivitetään käsittelyohjelmat...")
    optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")
    os.makedirs(optimized_dir, exist_ok=True)
    
    # Ryhmittele tulokset erittäin
    batches_results = {}
    for _, result_row in df_result.iterrows():
        batch_num = result_row["Batch"]
        if batch_num not in batches_results:
            batches_results[batch_num] = []
        batches_results[batch_num].append(result_row)
    
    # Päivitä kunkin erän käsittelyohjelma
    for batch_num, batch_rows in batches_results.items():
        # Järjestä rivit stage-järjestykseen
        batch_rows = sorted(batch_rows, key=lambda x: x["Stage"])
        
        # Lataa nostin- ja asematiedot
        stations_df = pd.read_csv(os.path.join(output_dir, "initialization", "stations.csv"))
        transporters_df = pd.read_csv(os.path.join(output_dir, "cp_sat", "cp_sat_transporters.csv"))
        
        # Luo optimoitu käsittelyohjelma (ilman stage 0)
        optimized_program = []
        for i, row in enumerate(batch_rows):
            if row["Stage"] == 0:  # Poista stage 0
                continue
                
            # Muunna sekunnit takaisin hh:mm:ss muotoon
            duration_seconds = row["Duration"]
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            seconds = duration_seconds % 60
            calc_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Valitse nostin: katso mistä asemasta tullaan
            if i > 0:
                # Edellinen asema (ei stage 0)
                prev_stations = [r for r in batch_rows if r["Stage"] == row["Stage"] - 1 and r["Stage"] > 0]
                if prev_stations:
                    from_station = prev_stations[0]["Station"]
                else:
                    # Jos ei edellistä käsittelyasemaa, käytetään alkuasemaa
                    batch_info = pd.read_csv(os.path.join(output_dir, "initialization", "production.csv"))
                    batch_data = batch_info[batch_info["Batch"] == batch_num]
                    from_station = int(batch_data.iloc[0]["Start_station"]) if not batch_data.empty else 301
            else:
                # Ensimmäinen käsittelyvaihe: tullaan alkuasemasta
                batch_info = pd.read_csv(os.path.join(output_dir, "initialization", "production.csv"))
                batch_data = batch_info[batch_info["Batch"] == batch_num]
                from_station = int(batch_data.iloc[0]["Start_station"]) if not batch_data.empty else 301
            
            to_station = row["Station"]
            
            # Valitse sopiva nostin
            def select_capable_transporter(lift_station, sink_station, stations_df, transporters_df):
                # Käy läpi nostimet järjestyksessä ja tarkista asemavälit (lift/sink)
                for _, transporter in transporters_df.iterrows():
                    min_lift = int(transporter.get('Min_Lift_Station', transporter.get('Min_lift_station', transporter.get('MinLiftStation', 0))))
                    max_lift = int(transporter.get('Max_Lift_Station', transporter.get('Max_lift_station', transporter.get('MaxLiftStation', 0))))
                    min_sink = int(transporter.get('Min_Sink_Station', transporter.get('Min_sink_station', transporter.get('MinSinkStation', 0))))
                    max_sink = int(transporter.get('Max_Sink_Station', transporter.get('Max_sink_station', transporter.get('MaxSinkStation', 0))))

                    if (min_lift <= lift_station <= max_lift) and (min_sink <= sink_station <= max_sink):
                        return int(transporter["Transporter_id"])

                # Jos mikään nostin ei pysty, palautetaan ensimmäinen
                return int(transporters_df.iloc[0]["Transporter_id"])
            
            transporter_id = select_capable_transporter(from_station, to_station, stations_df, transporters_df)
            
            # Hae alkuperäiset min/max ajat
            original_program = treatment_programs[batch_num]
            stage_info = original_program[original_program["Stage"] == row["Stage"]]
            if not stage_info.empty:
                min_time = stage_info.iloc[0]["MinTime"]
                max_time = stage_info.iloc[0]["MaxTime"]
            else:
                # Fallback arvot
                min_time = calc_time
                max_time = calc_time
            
            optimized_program.append({
                "Stage": row["Stage"],
                "Transporter": transporter_id,
                "Station": row["Station"], 
                "MinTime": min_time,
                "MaxTime": max_time,
                "CalcTime": calc_time  # Optimoitu aika
            })
        
        # Tallenna optimoitu käsittelyohjelma
        if optimized_program:
            optimized_df = pd.DataFrame(optimized_program)
            filename = f"Batch_{batch_num:03d}_Treatment_program_001.csv"
            filepath = os.path.join(optimized_dir, filename)
            optimized_df.to_csv(filepath, index=False)
            print(f"   Erä {batch_num}: {len(optimized_program)} vaihetta tallennettu → {filename}")
            print(f"     Sisältää: Stage, Transporter, Station, CalcTime kentät")
    
    print(f"💾 Käsittelyohjelmat päivitetty: {optimized_dir}")


# Poista kaikki vanha koodi alta
def validate_and_save_transfers(df_result, task_vars, logs_dir):
    pass  # Tyhjä funktio toistaiseksi


def remove_stage0_from_optimized_programs(output_dir):
    pass  # Tyhjä funktio toistaiseksi

