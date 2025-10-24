#!/usr/bin/env python3
"""
CP-SAT Optimizer for Transporter Task Scheduling
================================================

This module uses Google OR-Tools CP-SAT solver to optimize transporter task scheduling
as a Job Shop Scheduling Problem (JSSP).

Problem mapping:
- Jobs = Batches (erät)
- Machines = Stations (asemat) + Transporters (nostimet)
- Operations = Treatment stages (käsittelyvaiheet)
- Durations = CalcTime (käsittelyaika) + Transfer time (siirtoaika)

Input:
- line_matrix_original.csv (batches, stages, stations, treatment times)
- stations.csv (station locations)
- transporters.csv (transporter parameters)

Output:
- Optimized schedule with minimal makespan
- Same format as transporter_tasks_stretched.csv
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from ortools.sat.python import cp_model
from transporter_physics import calculate_physics_transfer_time


def precalculate_transfer_times(matrix_df, stations_df, transporters_df):
    """
    Esilaskee kaikki siirtoajat asemien välillä.
    
    CP-SAT tarvitsee kaikki kestot etukäteen, koska se ei voi kutsua
    funktioita optimoinnin aikana.
    
    Args:
        matrix_df: line_matrix_original.csv DataFrame
        stations_df: stations.csv DataFrame
        transporters_df: transporters.csv DataFrame
        
    Returns:
        dict: {(from_station, to_station, transporter_id): transfer_time_seconds}
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Esilasketaan siirtoajat...")
    
    transfer_times = {}
    
    # Luo station_map numero -> rivi
    station_map = {int(row['Number']): row for _, row in stations_df.iterrows()}
    transporter_map = {int(row['Transporter_id']): row for _, row in transporters_df.iterrows()}
    
    # Käy läpi kaikki mahdolliset siirrot
    unique_stations = matrix_df['Station'].unique()
    unique_transporters = transporters_df['Transporter_id'].unique()
    
    for from_station in unique_stations:
        for to_station in unique_stations:
            for transporter_id in unique_transporters:
                if from_station == to_station:
                    # Ei siirtoa, jos sama asema
                    transfer_times[(from_station, to_station, transporter_id)] = 0
                else:
                    from_row = station_map[from_station]
                    to_row = station_map[to_station]
                    trans_row = transporter_map[transporter_id]
                    
                    transfer_time = calculate_physics_transfer_time(from_row, to_row, trans_row)
                    transfer_times[(from_station, to_station, transporter_id)] = int(transfer_time)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Laskettu {len(transfer_times)} siirtoaikaa")
    return transfer_times


def build_cpsat_model(matrix_df, transfer_times, transporters_df, stations_df):
    """
    Rakentaa CP-SAT Job Shop Scheduling -mallin.
    
    Args:
        matrix_df: line_matrix_original.csv DataFrame
        transfer_times: Esilasketut siirtoajat
        transporters_df: transporters.csv DataFrame
        
    Returns:
        tuple: (model, variables_dict)
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Rakennetaan CP-SAT-mallia...")
    
    model = cp_model.CpModel()
    
    # Hae kaikki erät ja vaiheet
    batches = sorted(matrix_df['Batch'].unique())
    
    # Luo horizon (maksimiaika): konservatiivinen yläraja
    max_calc_time = matrix_df['CalcTime'].sum() + 10000  # Lisää puskuria siirroille
    horizon = int(max_calc_time)
    
    print(f"  Erät: {batches}")
    print(f"  Horizon: {horizon} s")
    
    # Rinnakkaiset asemat: Group -> lista asemia
    station_groups = {}
    for _, row in matrix_df.iterrows():
        station_id = int(row['Station'])
        group = row.get('Group', None)
        if group is None:
            group = station_id  # fallback: yksittäinen asema
        if group not in station_groups:
            station_groups[group] = set()
        station_groups[group].add(station_id)

    # Muuttujat: Jokaisen vaiheen start, end, interval, station_assignment
    task_vars = {}

    for batch in batches:
        batch_tasks = matrix_df[matrix_df['Batch'] == batch].sort_values('Stage')
        for _, task in batch_tasks.iterrows():
            batch_id = int(task['Batch'])
            stage = int(task['Stage'])
            group = task.get('Group', None)
            if group is None:
                group = int(task['Station'])
            group_stations = list(station_groups[group])
            calc_time = int(task['CalcTime'])
            transporter = int(task['Transporter'])

            # Assignment: mille asemalle vaihe menee ryhmässä
            station_assignment = model.NewIntVarFromDomain(cp_model.Domain.FromValues(group_stations), f'station_b{batch_id}_s{stage}')
            start = model.NewIntVar(0, horizon, f'start_b{batch_id}_s{stage}')
            end = model.NewIntVar(0, horizon, f'end_b{batch_id}_s{stage}')
            interval = model.NewIntervalVar(start, calc_time, end, f'interval_b{batch_id}_s{stage}')

            model.Add(end == start + calc_time)

            task_vars[(batch_id, stage)] = {
                'start': start,
                'end': end,
                'interval': interval,
                'station_assignment': station_assignment,
                'calc_time': calc_time,
                'transporter': transporter
            }
    
    # RAJOITE 1: Vaiheiden järjestys samassa erässä
    print(f"  Lisätään precedence-rajoitteet...")
    for batch in batches:
        batch_tasks = matrix_df[matrix_df['Batch'] == batch].sort_values('Stage')
        stages = batch_tasks['Stage'].tolist()
        for i in range(len(stages) - 1):
            curr_stage = int(stages[i])
            next_stage = int(stages[i + 1])
            curr_task = task_vars[(batch, curr_stage)]
            next_task = task_vars[(batch, next_stage)]
            transporter_id = curr_task['transporter']
            # Siirtoaika: käytetään aseman assignment-muuttujaa
            from_station_id = int(matrix_df[(matrix_df['Batch']==batch) & (matrix_df['Stage']==curr_stage)]['Station'].values[0])
            to_station_id = int(matrix_df[(matrix_df['Batch']==batch) & (matrix_df['Stage']==next_stage)]['Station'].values[0])
            from_group = stations_df[stations_df['Number'] == from_station_id]['Group'].values[0] if 'Group' in stations_df.columns else from_station_id
            to_group = stations_df[stations_df['Number'] == to_station_id]['Group'].values[0] if 'Group' in stations_df.columns else to_station_id
            from_group_stations = [v for v in station_groups.get(from_group, [from_station_id])]
            to_group_stations = [v for v in station_groups.get(to_group, [to_station_id])]
            transfer_time_table = []
            for fs in from_group_stations:
                for ts in to_group_stations:
                    transfer_time_table.append(transfer_times.get((fs, ts, transporter_id), 0))
            # Siirtoaika muuttujana
            if transfer_time_table:
                transfer_time_var = model.NewIntVar(0, max(transfer_time_table), f'transfer_b{batch}_s{curr_stage}_to_s{next_stage}')
                # Rajoite: seuraava vaihe voi alkaa vasta kun edellinen on valmis + siirtoaika
                model.Add(next_task['start'] >= curr_task['end'] + transfer_time_var)
    
    # RAJOITE 2: Ei päällekkäisyyksiä rinnakkaisryhmän asemilla
    print(f"  Lisätään NoOverlap-rajoitteet rinnakkaisryhmille...")
    for group, stations_in_group in station_groups.items():
        group_intervals = []
        for (batch, stage), task in task_vars.items():
            # Jos asema kuuluu tähän groupiin
            # Käytetään assignment-muuttujaa
            group_intervals.append(task['interval'])
        if len(group_intervals) > 1:
            model.AddNoOverlap(group_intervals)
    
    # RAJOITE 3: Ei päällekkäisyyksiä samalla nostimella
    # (Yksinkertaistettu: Oletetaan että nostin voi tehdä vain yhden tehtävän kerrallaan)
    print(f"  Lisätään NoOverlap-rajoitteet nostimille...")
    transporter_intervals = {}
    
    for (batch, stage), task in task_vars.items():
        transporter = task['transporter']
        if transporter not in transporter_intervals:
            transporter_intervals[transporter] = []
        transporter_intervals[transporter].append(task['interval'])
    
    for transporter, intervals in transporter_intervals.items():
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)
    
    # TAVOITE: Minimoi makespan (viimeisen tehtävän päättymisaika)
    print(f"  Asetetaan tavoitefunktio (minimoi makespan)...")
    makespan = model.NewIntVar(0, horizon, 'makespan')
    
    for (batch, stage), task in task_vars.items():
        model.Add(makespan >= task['end'])
    
    model.Minimize(makespan)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Malli rakennettu. Muuttujia: {len(task_vars)}")
    
    return model, task_vars


def solve_cpsat_model(model, task_vars, time_limit_seconds=60):
    """
    Ratkaisee CP-SAT-mallin.
    
    Args:
        model: CP-SAT-malli
        task_vars: Muuttujat (dict)
        time_limit_seconds: Maksimiaika ratkaisuun (sekunteja)
        
    Returns:
        tuple: (status, solution_dict, makespan)
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ratkaistaan CP-SAT-mallia (max {time_limit_seconds}s)...")
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.log_search_progress = True
    
    status = solver.Solve(model)
    
    status_names = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN"
    }
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {status_names.get(status, 'UNKNOWN')}")
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        makespan = solver.ObjectiveValue()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Makespan: {makespan} s")
        
        # Pura ratkaisu
        solution = {}
        for (batch, stage), task in task_vars.items():
            solution[(batch, stage)] = {
                'start': solver.Value(task['start']),
                'end': solver.Value(task['end']),
                'station': solver.Value(task['station_assignment']),
                'calc_time': task['calc_time'],
                'transporter': task['transporter']
            }
        
        return status, solution, makespan
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ratkaisua ei löytynyt!")
        return status, None, None


def cpsat_solution_to_dataframe(solution, matrix_df, stations_df, transporters_df):
    """
    Muuntaa CP-SAT:n ratkaisun DataFrame-muotoon (yhteensopiva transporter_tasks_stretched.csv:n kanssa).
    
    Args:
        solution: Ratkaistu aikataulu (dict)
        matrix_df: Alkuperäinen line_matrix_original.csv DataFrame
        stations_df: stations.csv DataFrame
        transporters_df: transporters.csv DataFrame
        
    Returns:
        pd.DataFrame: Optimoitu aikataulu (sisältää Lift_stat, Sink_stat, Phase_1-4)
    """
    from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Muunnetaan ratkaisu DataFrame-muotoon...")
    
    # Luo station_map ja transporter_map
    station_map = {int(row['Number']): row for _, row in stations_df.iterrows()}
    transporter_map = {int(row['Transporter_id']): row for _, row in transporters_df.iterrows()}
    
    tasks = []
    
    # Järjestä tehtävät (batch, stage) mukaan
    sorted_keys = sorted(solution.keys())
    
    # Käsittele jokainen erä erikseen
    batches = sorted(set([batch for batch, _ in sorted_keys]))
    
    for batch in batches:
        batch_tasks = [(b, s) for b, s in sorted_keys if b == batch]
        batch_stages = sorted([s for _, s in batch_tasks])
        
        # STAGE 0: Aloitusasema (301)
        # Hae erän ensimmäinen käsittelyasema
        first_stage = batch_stages[0]
        first_task = solution[(batch, first_stage)]
        first_station = first_task['station']
        first_start = first_task['start']
        transporter_id = first_task['transporter']
        
        # Hae alkuperäisestä matriisista treatment_program
        orig_row = matrix_df[(matrix_df['Batch'] == batch) & (matrix_df['Stage'] == first_stage)].iloc[0]
        treatment_program = int(orig_row['Treatment_program'])
        
        # Oletetaan että aloitusasema on 301 (voidaan lukea production.csv:stä)
        start_station = 301
        
        # Laske siirtoaika aloitusasemalta ensimmäiselle käsittelyasemalle
        from_row = station_map[start_station]
        to_row = station_map[first_station]
        trans_row = transporter_map[transporter_id]
        
        phase_1 = calculate_physics_transfer_time(from_row, to_row, trans_row)
        phase_2 = calculate_lift_time(to_row, trans_row)
        phase_3 = calculate_physics_transfer_time(to_row, to_row, trans_row)  # Ei siirtoa
        phase_4 = calculate_sink_time(to_row, trans_row)
        
        # Laske Lift_time taaksepäin Start_time:sta
        lift_time = first_start - int(phase_1)
        
        # Stage 0 -rivi
        task_row_0 = {
            'Transporter_id': transporter_id,
            'Batch': batch,
            'Treatment_program': treatment_program,
            'Stage': 0,
            'Lift_stat': start_station,
            'Lift_time': lift_time,
            'Sink_stat': first_station,
            'Sink_time': first_start,
            'Phase_1': float(phase_1),
            'Phase_2': float(phase_2),
            'Phase_3': float(phase_3),
            'Phase_4': float(phase_4)
        }
        tasks.append(task_row_0)
        
        # STAGE 1-N: Käsittelyvaiheet
        for i, stage in enumerate(batch_stages):
            task = solution[(batch, stage)]
            current_station = task['station']
            
            # Hae seuraava asema (tai sama jos viimeinen)
            if i < len(batch_stages) - 1:
                next_stage = batch_stages[i + 1]
                next_task = solution[(batch, next_stage)]
                next_station = next_task['station']
            else:
                next_station = current_station
            
            # Laske vaiheajat
            curr_row = station_map[current_station]
            next_row = station_map[next_station]
            trans_row = transporter_map[transporter_id]
            
            phase_1 = calculate_physics_transfer_time(curr_row, next_row, trans_row)
            phase_2 = calculate_lift_time(curr_row, trans_row)
            phase_3 = calculate_physics_transfer_time(curr_row, curr_row, trans_row)
            phase_4 = calculate_sink_time(curr_row, trans_row)
            
            # Lift_time = käsittelyn alkuaika
            # Sink_time = käsittelyn loppuaika
            lift_time = task['start']
            sink_time = task['end']
            
            task_row = {
                'Transporter_id': transporter_id,
                'Batch': batch,
                'Treatment_program': treatment_program,
                'Stage': stage,
                'Lift_stat': current_station,
                'Lift_time': lift_time,
                'Sink_stat': next_station if i < len(batch_stages) - 1 else current_station,
                'Sink_time': sink_time,
                'Phase_1': float(phase_1),
                'Phase_2': float(phase_2),
                'Phase_3': float(phase_3),
                'Phase_4': float(phase_4)
            }
            tasks.append(task_row)
    
    df = pd.DataFrame(tasks)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Luotu {len(df)} tehtävää")
    
    return df


def optimize_transporter_schedule(matrix_df, stations_df, transporters_df, time_limit=60):
    """
    Pääfunktio: Optimoi nostimien aikataulun CP-SAT:lla.
    
    Args:
        matrix_df: line_matrix_original.csv DataFrame
        stations_df: stations.csv DataFrame
        transporters_df: transporters.csv DataFrame
        time_limit: Maksimiaika optimointiin (sekunteja)
        
    Returns:
        pd.DataFrame: Optimoitu aikataulu
    """
    print(f"\n{'='*60}")
    print(f"CP-SAT OPTIMOINTI ALKAA")
    print(f"{'='*60}\n")
    
    # Vaihe 1: Esilaskenta
    # Ota Group-sarake mukaan aseman tietoihin
    if 'Group' not in stations_df.columns:
        stations_df['Group'] = None
    transfer_times = precalculate_transfer_times(matrix_df, stations_df, transporters_df)
    
    # Vaihe 2: Mallin rakentaminen
    model, task_vars = build_cpsat_model(matrix_df, transfer_times, transporters_df, stations_df)
    
    # Vaihe 3: Ratkaiseminen
    status, solution, makespan = solve_cpsat_model(model, task_vars, time_limit)
    
    if solution is None:
        print(f"\n⚠️ VIRHE: Optimointi epäonnistui!")
        return None
    
    # Vaihe 4: Muuntaminen DataFrame-muotoon
    optimized_df = cpsat_solution_to_dataframe(solution, matrix_df, stations_df, transporters_df)
    
    print(f"\n{'='*60}")
    print(f"CP-SAT OPTIMOINTI VALMIS")
    print(f"Makespan: {makespan} s ({makespan/60:.1f} min)")
    print(f"{'='*60}\n")
    
    return optimized_df


if __name__ == "__main__":
    # Testaus: Lataa viimeisin output ja optimoi
    import sys
    
    output_root = "output"
    if not os.path.exists(output_root):
        print("Ei output-kansiota!")
        sys.exit(1)
    
    # Hae viimeisin logs-kansio
    logs_dirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
    if not logs_dirs:
        print("Ei logs-kansioita!")
        sys.exit(1)
    
    latest_dir = sorted(logs_dirs)[-1]
    output_dir = os.path.join(output_root, latest_dir)
    
    print(f"Käytetään output-kansiota: {output_dir}")
    
    # Lataa syötteet
    matrix_file = os.path.join(output_dir, "logs", "line_matrix_original.csv")
    stations_file = os.path.join(output_dir, "initialization", "stations.csv")
    transporters_file = os.path.join(output_dir, "initialization", "transporters.csv")
    
    if not os.path.exists(matrix_file):
        print(f"Virhe: {matrix_file} ei löydy!")
        sys.exit(1)
    
    matrix_df = pd.read_csv(matrix_file)
    stations_df = pd.read_csv(stations_file)
    transporters_df = pd.read_csv(transporters_file)
    
    # Optimoi
    optimized_df = optimize_transporter_schedule(matrix_df, stations_df, transporters_df)
    
    if optimized_df is not None:
        # Tallenna tulos
        output_file = os.path.join(output_dir, "logs", "transporter_tasks_cpsat.csv")
        optimized_df.to_csv(output_file, index=False)
        print(f"\n✅ Tallennettu: {output_file}")
        print(f"\nEnsimmäiset 10 riviä:")
        print(optimized_df.head(10))
