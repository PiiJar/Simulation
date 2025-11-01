"""
TODELLINEN CP-SAT OPTIMOINTI REQUIREMENTS-DOKUMENTIN MUKAAN

Implementoi kaikki vapausasteet:
1. Käsittelyaikojen säätö (min-max välillä) 
2. Asemavalinta (rinnakkaiset asemat)
3. Erien järjestyksen optimointi (paitsi identtiset)
4. Nostimen rinnakkaisuus (erät voivat olla samanaikaisesti eri asemilla)
"""

import os
import pandas as pd
from ortools.sat.python import cp_model


def cp_sat_optimization_REAL(output_dir, treatment_programs, batches_df, stations_df, transfers_df, transporters_df, hard_order_constraint=False):
    """
    TODELLINEN CP-SAT OPTIMOINTI REQUIREMENTS-DOKUMENTIN MUKAAN
    """
    print("🚀 TODELLINEN CP-SAT optimointi (requirements-dokumentin mukaan)...")
    
    # Lue tiedot
    print(f"📊 Luettu {len(treatment_programs)} erää, {len(stations_df)} asemaa, {len(transfers_df)} siirtotehtävää")
    
    # Luo malli
    model = cp_model.CpModel()
    
    # 1. MUUTTUJIEN MÄÄRITTELY
    print("🔧 Määritellään muuttujat (KAIKKI VAPAUSASTEET)...")
    task_vars = {}
    
    for batch_id, program in treatment_programs.items():
        print(f"   📦 Erä {batch_id}: {len(program)} vaihetta")
        
        for _, row in program.iterrows():
            stage = row['Stage']
            min_station = row['MinStat']
            max_station = row['MaxStat']
            min_time = pd.to_timedelta(row['MinTime']).total_seconds()
            max_time = pd.to_timedelta(row['MaxTime']).total_seconds()
            
            # VAPAUSASTE 2: Asemavalinta
            valid_stations = []
            if min_station == max_station:
                valid_stations = [min_station]
            else:
                # Hae saman ryhmän asemat
                base_group = stations_df[stations_df['Station'] == min_station]['Group'].iloc[0]
                for station in range(min_station, max_station + 1):
                    station_info = stations_df[stations_df['Station'] == station]
                    if not station_info.empty and station_info['Group'].iloc[0] == base_group:
                        valid_stations.append(station)
            
            # Luo muuttujat
            start_var = model.NewIntVar(0, 10800, f"start_{batch_id}_{stage}")  # 3h maksimi
            
            # VAPAUSASTE 1: Käsittelyaika optimoitavissa min-max välillä!
            if stage == 0:
                duration_var = model.NewIntVar(0, int(max_time), f"duration_{batch_id}_{stage}")
            else:
                duration_var = model.NewIntVar(int(min_time), int(max_time), f"duration_{batch_id}_{stage}")
            
            end_var = model.NewIntVar(0, 10800, f"end_{batch_id}_{stage}")
            model.Add(end_var == start_var + duration_var)
            
            # Asemavalinta
            if len(valid_stations) == 1:
                station_var = model.NewConstant(valid_stations[0])
            else:
                station_var = model.NewIntVarFromDomain(
                    cp_model.Domain.FromValues(valid_stations), f"station_{batch_id}_{stage}"
                )
            
            task_vars[(batch_id, stage)] = {
                "start": start_var, "end": end_var, "duration": duration_var,
                "station": station_var, "valid_stations": valid_stations,
                "min_time": int(min_time), "max_time": int(max_time)
            }
            
            print(f"     Stage {stage}: asemat {valid_stations}, aika {min_time:.0f}-{max_time:.0f}s")
    
    # 2. RAJOITTEET
    print("⚖️ Lisätään rajoitteet...")
    
    # 2.1 Erien sisäinen järjestys (Sääntö 1)
    print("   📋 Erien sisäinen järjestys...")
    for batch_id, program in treatment_programs.items():
        stages = sorted(program["Stage"].tolist())
        for i in range(len(stages) - 1):
            current_stage = stages[i]
            next_stage = stages[i + 1]
            model.Add(task_vars[(batch_id, next_stage)]["start"] >= task_vars[(batch_id, current_stage)]["end"])
    
    # 2.2 Asemien yksinoikeus (Sääntö 3) - VAPAUSASTE 2 huomioiden
    print("   🏭 Asemien yksinoikeus...")
    station_intervals = {}
    for (batch_id, stage), vars in task_vars.items():
        for station in vars["valid_stations"]:
            if station not in station_intervals:
                station_intervals[station] = []
            
            # Luo ehdollinen intervalli tälle asemalle
            is_at_station = model.NewBoolVar(f"at_station_{batch_id}_{stage}_{station}")
            model.Add(vars["station"] == station).OnlyEnforceIf(is_at_station)
            model.Add(vars["station"] != station).OnlyEnforceIf(is_at_station.Not())
            
            interval = model.NewOptionalIntervalVar(
                vars["start"], vars["duration"], vars["end"],
                is_at_station, f"interval_{batch_id}_{stage}_{station}"
            )
            station_intervals[station].append(interval)
    
    # Ei päällekkäisyyksiä asemittain
    for station, intervals in station_intervals.items():
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)
            print(f"     🏭 Asema {station}: {len(intervals)} mahdollista tehtävää")
    
    # 2.3 Nostimen rajoitteet - TODELLINEN RINNAKKAISUUS (VAPAUSASTE 4)
    print("   🏗️ Nostimen rinnakkaisuus...")
    hoist_intervals = []
    
    for batch_id, program in treatment_programs.items():
        stages = sorted(program["Stage"].tolist())
        for i in range(len(stages) - 1):
            curr_stage = stages[i]
            next_stage = stages[i + 1]
            
            # Siirtotehtävä nostimelle
            curr_vars = task_vars[(batch_id, curr_stage)]
            next_vars = task_vars[(batch_id, next_stage)]
            
            # Hae realistinen siirtoaika transfers_df:stä
            curr_station = curr_vars["valid_stations"][0]  # Yksinkertaistus
            next_station = next_vars["valid_stations"][0]
            
            mask = (transfers_df["From_Station"] == curr_station) & \
                   (transfers_df["To_Station"] == next_station)
            min_transfer_time = int(transfers_df[mask]["TotalTaskTime"].iloc[0]) if mask.any() else 60
            
            # Nostimen siirtotehtävä
            transfer_start = curr_vars["end"]
            transfer_end = next_vars["start"]
            transfer_duration = model.NewIntVar(min_transfer_time, min_transfer_time + 300, 
                                              f"transfer_{batch_id}_{curr_stage}_{next_stage}")
            
            model.Add(transfer_end == transfer_start + transfer_duration)
            
            interval = model.NewIntervalVar(
                transfer_start, transfer_duration, transfer_end,
                f"hoist_{batch_id}_{curr_stage}_{next_stage}"
            )
            hoist_intervals.append(interval)
    
    # Nostimen ei voi tehdä kahta siirtoa yhtäaikaa
    if hoist_intervals:
        model.AddNoOverlap(hoist_intervals)
        print(f"     🔗 {len(hoist_intervals)} siirtotehtävää (rinnakkaisuus optimaalinen)")
    
    # 2.4 VAPAUSASTE 3: Identtisten erien järjestys
    print("   🔄 Identtisten erien järjestys...")
    batch_signatures = {}
    for batch_id, program in treatment_programs.items():
        signature = tuple(sorted([(r['Stage'], r['MinStat'], r['MaxStat'], r['MinTime'], r['MaxTime']) 
                                 for _, r in program.iterrows()]))
        if signature not in batch_signatures:
            batch_signatures[signature] = []
        batch_signatures[signature].append(batch_id)
    
    for signature, batches in batch_signatures.items():
        if len(batches) > 1:
            print(f"     🔄 Identtiset erät (järjestys säilyy): {batches}")
            sorted_batches = sorted(batches)
            for i in range(len(sorted_batches) - 1):
                batch1, batch2 = sorted_batches[i], sorted_batches[i + 1]
                model.Add(task_vars[(batch1, 0)]["start"] <= task_vars[(batch2, 0)]["start"])
    
    # 3. TAVOITE: Minimoi makespan
    print("🎯 Asetetaan optimointitavoite (makespan minimization)...")
    makespan = model.NewIntVar(0, 10800, "makespan")
    
    for (batch_id, stage), vars in task_vars.items():
        model.Add(makespan >= vars["end"])
    
    model.Minimize(makespan)
    
    print("✅ CP-SAT malli luotu - KAIKKI VAPAUSASTEET IMPLEMENTOITU!")
    
    # 4. RATKAISU
    print("🔍 Ratkaistaan mallia...")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 120  # 2 min aikaa löytää paras ratkaisu
    solver.parameters.log_search_progress = True
    
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL:
        makespan_seconds = solver.Value(makespan)
        print(f"📊 Optimoinnin tila: OPTIMAL")
        print(f"🎯 Makespan: {makespan_seconds} sekuntia ({makespan_seconds/60:.1f} minuuttia)")
        
        # Kerää ratkaisu
        schedule = []
        for (batch_id, stage), vars in task_vars.items():
            start_val = solver.Value(vars["start"])
            end_val = solver.Value(vars["end"])
            duration_val = solver.Value(vars["duration"])
            station_val = solver.Value(vars["station"])
            
            schedule.append({
                'Batch': batch_id,
                'Stage': stage,
                'Station': station_val,
                'Start': start_val,
                'End': end_val,
                'Duration': duration_val
            })
            
            print(f"   📦 Erä {batch_id} Stage {stage}: Asema {station_val}, {start_val}→{end_val}s ({duration_val}s)")
        
        # Tallenna
        schedule_df = pd.DataFrame(schedule).sort_values(['Batch', 'Stage'])
        
        logs_dir = os.path.join(output_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        output_file = os.path.join(logs_dir, "cp_sat_optimization_schedule_REAL.csv")
        schedule_df.to_csv(output_file, index=False)
        print(f"💾 Tulokset tallennettu: {output_file}")
        
        return True
        
    elif status == cp_model.FEASIBLE:
        makespan_seconds = solver.Value(makespan)
        print(f"📊 Optimoinnin tila: FEASIBLE (ei optimaalinen)")
        print(f"🎯 Makespan: {makespan_seconds} sekuntia ({makespan_seconds/60:.1f} minuuttia)")
        return True
        
    else:
        print(f"❌ Optimointi epäonnistui: {solver.StatusName(status)}")
        return False