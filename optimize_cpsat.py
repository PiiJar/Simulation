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
        tuple: (transfer_times, lift_times, sink_times)
    """
    from transporter_physics import calculate_lift_time, calculate_sink_time
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Esilasketaan siirtoajat, lift- ja sink-ajat...")
    
    transfer_times = {}
    lift_times = {}
    sink_times = {}
    
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
    
    # Esilaskenta: lift- ja sink-ajat
    for station_id in unique_stations:
        for transporter_id in unique_transporters:
            station_row = station_map[station_id]
            trans_row = transporter_map[transporter_id]
            lift_times[(station_id, transporter_id)] = int(calculate_lift_time(station_row, trans_row))
            sink_times[(station_id, transporter_id)] = int(calculate_sink_time(station_row, trans_row))
    
    # STAGE 0 AJAT: Siirto aloitusasemalta (301) ensimmäisille käsittelyasemille
    stage0_times = {}  # {(first_station, transporter): (phase_1, phase_2, phase_4)}
    start_station = 301  # Aloitusasema
    if start_station in station_map:
        start_row = station_map[start_station]
        for first_station in unique_stations:
            if first_station == start_station:
                continue
            first_row = station_map[first_station]
            for transporter_id in unique_transporters:
                trans_row = transporter_map[transporter_id]
                phase_1 = calculate_physics_transfer_time(start_row, first_row, trans_row)
                phase_2 = calculate_lift_time(start_row, trans_row)
                phase_4 = calculate_sink_time(first_row, trans_row)
                stage0_times[(first_station, transporter_id)] = (int(phase_1), int(phase_2), int(phase_4))
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Laskettu {len(transfer_times)} siirtoaikaa, {len(lift_times)} lift-aikaa, {len(sink_times)} sink-aikaa")
    return transfer_times, lift_times, sink_times, stage0_times


def build_cpsat_model(matrix_df, transfer_times, lift_times, sink_times, stage0_times, transporters_df, stations_df, treatment_programs_df):
    """
    Rakentaa CP-SAT Job Shop Scheduling -mallin jossa optimoidaan:
    - Erien järjestys (implisiittisesti start-aikojen kautta)
    - Alkuajat (production.csv Start_original)
    - CalcTime-arvot (MinTime ≤ CalcTime ≤ MaxTime)
    
    Args:
        matrix_df: line_matrix_original.csv DataFrame
        transfer_times: Esilasketut siirtoajat
        lift_times: Esilasketut lift-ajat
        sink_times: Esilasketut sink-ajat
        transporters_df: transporters.csv DataFrame
        stations_df: stations.csv DataFrame
        treatment_programs_df: dict {program_id: DataFrame} treatment_program CSVs
        
    Returns:
        tuple: (model, variables_dict)
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Rakennetaan CP-SAT-mallia (optimoi järjestys, alkuajat, CalcTime)...")
    
    model = cp_model.CpModel()
    
    # Hae kaikki erät ja vaiheet
    batches = sorted(matrix_df['Batch'].unique())
    
    # Luo horizon: käytetään MaxTime-arvoja ylärajana
    max_possible_time = 0
    for batch in batches:
        batch_rows = matrix_df[matrix_df['Batch'] == batch]
        for _, row in batch_rows.iterrows():
            program_id = int(row['Treatment_program'])
            stage = int(row['Stage'])
            if program_id in treatment_programs_df:
                prog_df = treatment_programs_df[program_id]
                stage_row = prog_df[prog_df['Stage'] == stage]
                if not stage_row.empty:
                    max_time_str = stage_row['MaxTime'].values[0]
                    max_time_sec = pd.to_timedelta(max_time_str).total_seconds()
                    max_possible_time += max_time_sec
    horizon = int(max_possible_time * 2 + 10000)  # Konservatiivinen yläraja
    
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

    # Muuttujat: Jokaisen vaiheen start, end, calc_time, station_assignment
    task_vars = {}
    # Optional intervals kullekin asemalle
    station_optional_intervals = {}

    for batch in batches:
        batch_tasks = matrix_df[matrix_df['Batch'] == batch].sort_values('Stage')
        for _, task in batch_tasks.iterrows():
            batch_id = int(task['Batch'])
            stage = int(task['Stage'])
            program_id = int(task['Treatment_program'])
            group = task.get('Group', None)
            if group is None:
                group = int(task['Station'])
            group_stations = list(station_groups[group])
            transporter = int(task['Transporter'])

            # Hae MinTime ja MaxTime treatment_program-tiedostosta
            if program_id in treatment_programs_df:
                prog_df = treatment_programs_df[program_id]
                stage_row = prog_df[prog_df['Stage'] == stage]
                if not stage_row.empty:
                    min_time_str = stage_row['MinTime'].values[0]
                    max_time_str = stage_row['MaxTime'].values[0]
                    min_time = int(pd.to_timedelta(min_time_str).total_seconds())
                    max_time = int(pd.to_timedelta(max_time_str).total_seconds())
                else:
                    # Fallback jos ei löydy
                    min_time = int(task['CalcTime'])
                    max_time = int(task['CalcTime'])
            else:
                min_time = int(task['CalcTime'])
                max_time = int(task['CalcTime'])

            # OPTIMOITAVA MUUTTUJA: CalcTime (MinTime ≤ CalcTime ≤ MaxTime)
            calc_time_var = model.NewIntVar(min_time, max_time, f'calc_time_b{batch_id}_s{stage}')

            # Laske aseman kokonaisvarausaika: sink + calc + lift
            max_sink_time = max([sink_times.get((s, transporter), 0) for s in group_stations])
            max_lift_time = max([lift_times.get((s, transporter), 0) for s in group_stations])
            
            # Kokonaisaika asemalla: sink + calc_time_var + lift
            total_station_time_min = max_sink_time + min_time + max_lift_time
            total_station_time_max = max_sink_time + max_time + max_lift_time

            # Assignment: mille asemalle vaihe menee ryhmässä
            station_assignment = model.NewIntVarFromDomain(cp_model.Domain.FromValues(group_stations), f'station_b{batch_id}_s{stage}')
            
            # OPTIMOITAVA MUUTTUJA: Start-aika (ei kiinteä)
            start = model.NewIntVar(0, horizon, f'start_b{batch_id}_s{stage}')
            end = model.NewIntVar(0, horizon, f'end_b{batch_id}_s{stage}')
            
            # Interval: kesto riippuu calc_time_var:sta
            duration = model.NewIntVar(total_station_time_min, total_station_time_max, f'duration_b{batch_id}_s{stage}')
            model.Add(duration == max_sink_time + calc_time_var + max_lift_time)
            
            interval = model.NewIntervalVar(start, duration, end, f'interval_b{batch_id}_s{stage}')

            # Luo optional interval kullekin mahdolliselle asemalle
            optional_intervals = {}
            for station_id in group_stations:
                # Presence-muuttuja: onko tehtävä tällä asemalla
                presence = model.NewBoolVar(f'presence_b{batch_id}_s{stage}_stat{station_id}')
                # Linkitä presence station_assignment-muuttujaan
                model.Add(station_assignment == station_id).OnlyEnforceIf(presence)
                model.Add(station_assignment != station_id).OnlyEnforceIf(presence.Not())
                
                # Optional interval tälle asemalle
                opt_interval = model.NewOptionalIntervalVar(start, duration, end, presence, f'opt_interval_b{batch_id}_s{stage}_stat{station_id}')
                optional_intervals[station_id] = opt_interval
                
                # Lisää aseman NoOverlap-listaan
                if station_id not in station_optional_intervals:
                    station_optional_intervals[station_id] = []
                station_optional_intervals[station_id].append(opt_interval)

            task_vars[(batch_id, stage)] = {
                'start': start,
                'end': end,
                'interval': interval,
                'station_assignment': station_assignment,
                'optional_intervals': optional_intervals,
                'calc_time': calc_time_var,  # OPTIMOITAVA
                'min_time': min_time,
                'max_time': max_time,
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
    
    # RAJOITE 2: Ei päällekkäisyyksiä yksittäisillä asemilla
    # HUOM: Tämä tehdään RAJOITE 4:ssä disjunktiivisilla rajoitteilla (tarkempi!)
    # Optional intervals -versio ei toimi oikein rinnakkaisten asemien kanssa
    print(f"  Ohitetaan NoOverlap asemille (käytetään RAJOITE 4:ää sen sijaan)...")
    # for station_id, intervals in station_optional_intervals.items():
    #     if len(intervals) > 1:
    #         print(f"    DEBUG: Asema {station_id}: {len(intervals)} intervalia")
    #         model.AddNoOverlap(intervals)
    
    # RAJOITE 3: Ei päällekkäisyyksiä samalla nostimella
    # TÄRKEÄ: Intervalien pitää vastata TÄSMÄLLEEN cpsat_solution_to_dataframe() -laskennan aikoja!
    # Stage 0: lift_time laskenta monimutkaisempi
    # Stage 1+: lift_time = curr_task['end'] - phase_2, sink_time = next_task['start'] + phase_4
    print(f"  Lisätään NoOverlap-rajoitteet nostimille...")
    transporter_intervals = {}
    transporter_task_vars = {}  # Tallennetaan lift_start ja sink_end muuttujat
    
    # Luo nostimen intervallit per erä (mukaan lukien STAGE 0!)
    for batch in batches:
        batch_tasks = matrix_df[matrix_df['Batch'] == batch].sort_values('Stage')
        stages = batch_tasks['Stage'].tolist()
        
        if len(stages) == 0:
            continue
            
        # Ensimmäisen vaiheen transporter ja asema
        first_stage = int(stages[0])
        first_task = task_vars[(batch, first_stage)]
        transporter = first_task['transporter']
        first_station = int(matrix_df[(matrix_df['Batch']==batch) & (matrix_df['Stage']==first_stage)]['Station'].values[0])
        
        if transporter not in transporter_intervals:
            transporter_intervals[transporter] = []
        
        # STAGE 0: Siirto aloitusasemalta (301) ensimmäiselle käsittelyasemalle
        # Laskenta: cpsat_solution_to_dataframe() rivit 518-535
        # Käytetään esilaskettuja stage0_times-arvoja
        
        stage0_key = (first_station, transporter)
        if stage0_key in stage0_times:
            phase_1_s0, phase_2_s0, phase_4_s0 = stage0_times[stage0_key]
        else:
            # Fallback: oletusarvot
            phase_1_s0 = 16
            phase_2_s0 = 5
            phase_4_s0 = 17
        
        # lift_time = max(0, first_start - phase_1 - phase_2 - phase_4)
        # sink_time = first_start (jos lift_time > 0) tai lift_time + phase_1 + phase_2 + phase_4 (jos 0)
        stage0_lift_start = model.NewIntVar(0, horizon, f'trans_b{batch}_s0_lift_start')
        stage0_sink_end = model.NewIntVar(0, horizon, f'trans_b{batch}_s0_sink_end')
        
        # ideal_lift_time = first_task['start'] - phase_1 - phase_2 - phase_4
        # lift_time = max(0, ideal_lift_time)
        ideal_lift = model.NewIntVar(-horizon, horizon, f'trans_b{batch}_s0_ideal_lift')
        model.Add(ideal_lift == first_task['start'] - phase_1_s0 - phase_2_s0 - phase_4_s0)
        
        # lift_start = max(0, ideal_lift)
        model.AddMaxEquality(stage0_lift_start, [ideal_lift, 0])
        
        # Jos lift_start == 0:
        #   sink_end = lift_start + phase_1 + phase_2 + phase_4
        # Muuten:
        #   sink_end = first_task['start']
        # Tämä on hankalaa CP-SAT:ssä, käytetään yksinkertaisempaa:
        # sink_end = max(first_task['start'], phase_1 + phase_2 + phase_4)
        model.AddMaxEquality(stage0_sink_end, [
            first_task['start'],
            phase_1_s0 + phase_2_s0 + phase_4_s0
        ])
        
        stage0_duration = model.NewIntVar(0, horizon, f'trans_b{batch}_s0_duration')
        model.Add(stage0_duration == stage0_sink_end - stage0_lift_start)
        
        stage0_interval = model.NewIntervalVar(stage0_lift_start, stage0_duration, stage0_sink_end, f'trans_interval_b{batch}_s0')
        transporter_intervals[transporter].append(stage0_interval)
        
        # Tallenna muuttujat
        transporter_task_vars[(batch, 0, transporter)] = {
            'lift_station': 301,
            'sink_station': first_station,
            'lift_start': stage0_lift_start,
            'sink_end': stage0_sink_end
        }
        
        # STAGE 1-N: Käsittelyvaiheet
        for i in range(len(stages)):
            curr_stage = int(stages[i])
            curr_task = task_vars[(batch, curr_stage)]
            
            # Haetaan asematiedot
            station_id = int(matrix_df[(matrix_df['Batch']==batch) & (matrix_df['Stage']==curr_stage)]['Station'].values[0])
            
            # Hae lift ja sink ajat TÄSTÄ asemasta
            lift_time_curr = lift_times.get((station_id, transporter), 0)
            sink_time_curr = sink_times.get((station_id, transporter), 0)
            
            # NOSTIMEN TEHTÄVÄ:
            # Alkaa: lift ALKAA tältä asemalta = curr_task['end'] - lift_time
            # Päättyy: sink VALMIS seuraavalla asemalla = next_task['start'] + sink_time
            
            trans_start = model.NewIntVar(0, horizon, f'trans_b{batch}_s{curr_stage}_lift_start')
            model.Add(trans_start == curr_task['end'] - lift_time_curr)
            
            if i < len(stages) - 1:
                # On seuraava vaihe
                next_stage = int(stages[i+1])
                next_task = task_vars[(batch, next_stage)]
                next_station_id = int(matrix_df[(matrix_df['Batch']==batch) & (matrix_df['Stage']==next_stage)]['Station'].values[0])
                sink_time_next = sink_times.get((next_station_id, transporter), 0)
                
                # TÄRKEÄ: Nostintehtävä päättyy kun sink valmis SEURAAVALLA asemalla
                # MUTTA nostimen interval pitää kattaa myös TYHJÄ SIIRTYMÄ seuraavan tehtävän alkuasemalle
                # 
                # Tämän erän tehtävä: station_id → next_station_id (sink valmis next_task['start'] + sink_time_next)
                # Seuraavan erän tehtävä alkaa: jostain asemasta (ei välttämättä next_station_id)
                # 
                # ONGELMA: Tässä vaiheessa ei tiedetä SEURAAVAN ERÄN tehtävää (voi olla eri erä)!
                # RATKAISU: Interval kattaa vain TÄMÄN tehtävän, tyhjä siirtymä lisätään ERIKSEEN
                
                trans_end = model.NewIntVar(0, horizon, f'trans_b{batch}_s{curr_stage}_sink_end')
                model.Add(trans_end == next_task['start'] + sink_time_next)
            else:
                # Viimeinen vaihe: Sink_stat = Lift_stat (sama asema)
                trans_end = model.NewIntVar(0, horizon, f'trans_b{batch}_s{curr_stage}_sink_end')
                model.Add(trans_end == curr_task['end'])
            
            trans_duration = model.NewIntVar(0, horizon, f'trans_b{batch}_s{curr_stage}_duration')
            model.Add(trans_duration == trans_end - trans_start)
            
            trans_interval = model.NewIntervalVar(trans_start, trans_duration, trans_end, f'trans_interval_b{batch}_s{curr_stage}')
            transporter_intervals[transporter].append(trans_interval)
            
            # Tallenna muuttujat
            if i < len(stages) - 1:
                next_station = int(matrix_df[(matrix_df['Batch']==batch) & (matrix_df['Stage']==int(stages[i+1]))]['Station'].values[0])
                sink_station = next_station
            else:
                sink_station = station_id
            
            transporter_task_vars[(batch, curr_stage, transporter)] = {
                'lift_station': station_id,
                'sink_station': sink_station,
                'lift_start': trans_start,
                'sink_end': trans_end
            }
    
    for transporter, intervals in transporter_intervals.items():
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)
    
    # RAJOITE 3b: Nostimen tyhjä siirtymä tehtävien välillä
    # Kun nostintehtävä A päättyy asemalla X ja tehtävä B alkaa asemalta Y,
    # nostimen täytyy siirtyä tyhjänä X → Y
    print(f"  Lisätään nostimen tyhjän siirtymän rajoitteet...")
    
    # Luo lista kaikista nostintehtävistä per transporter
    tasks_by_transporter = {}
    for key, task_info in transporter_task_vars.items():
        batch, stage, transporter = key
        if transporter not in tasks_by_transporter:
            tasks_by_transporter[transporter] = []
        tasks_by_transporter[transporter].append((key, task_info))
    
    # Lisää disjunktiiviset rajoitteet pareittain
    empty_transfer_count = 0
    for transporter, tasks in tasks_by_transporter.items():
        for i, (key_a, task_a) in enumerate(tasks):
            for j, (key_b, task_b) in enumerate(tasks):
                if i >= j:
                    continue
                
                # Hae siirtymäajat
                transfer_a_to_b = transfer_times.get((task_a['sink_station'], task_b['lift_station'], transporter), 0)
                transfer_b_to_a = transfer_times.get((task_b['sink_station'], task_a['lift_station'], transporter), 0)
                
                # Jos A ennen B: A_sink_end + transfer_a_to_b <= B_lift_start
                # Jos B ennen A: B_sink_end + transfer_b_to_a <= A_lift_start
                
                # Luo boolean: a_before_b
                a_before_b = model.NewBoolVar(f'empty_trans_{key_a[0]}_{key_a[1]}_before_{key_b[0]}_{key_b[1]}')
                
                # Jos a_before_b = True: A ennen B
                model.Add(task_a['sink_end'] + transfer_a_to_b <= task_b['lift_start']).OnlyEnforceIf(a_before_b)
                
                # Jos a_before_b = False: B ennen A
                model.Add(task_b['sink_end'] + transfer_b_to_a <= task_a['lift_start']).OnlyEnforceIf(a_before_b.Not())
                
                empty_transfer_count += 1
    
    if empty_transfer_count > 0:
        print(f"    Lisätty {empty_transfer_count} nostimen tyhjän siirtymän rajoitetta")
    
    # RAJOITE 4: Aseman vapautuminen ennen seuraavaa erää
    # FYYSINEN RAJOITE: Nostin ei voi laskea uutta erää altaaseen ennen kuin edellinen on nostettu pois!
    # 
    # Aikajana per erä asemalla:
    #   [EntryTime] --Sink--> [Sink valmis] --CalcTime--> [Lift alkaa] --Lift--> [Lift valmis]
    # 
    # Rajoite: Erä A:n Lift täytyy VALMISTUA ennen kuin Erä B:n Sink voi ALKAA
    #   → B.EntryTime >= A.EntryTime + sink_time + calc_time + lift_time
    #   → B.EntryTime >= A.end (koska A.end = A.start + sink + calc + lift)
    # 
    # TAI päinvastoin: A.EntryTime >= B.end
    print(f"  Lisätään disjunktiiviset rajoitteet asemille...")
    
    # Kerää kaikki tehtävät asemakohtaisesti
    station_tasks = {}  # {station_id: [(batch, stage, task)]}
    
    for batch in batches:
        batch_tasks = matrix_df[matrix_df['Batch'] == batch].sort_values('Stage')
        
        for _, task_row in batch_tasks.iterrows():
            batch_id = int(task_row['Batch'])
            stage = int(task_row['Stage'])
            station_id = int(task_row['Station'])
            
            if station_id not in station_tasks:
                station_tasks[station_id] = []
            
            task = task_vars[(batch_id, stage)]
            
            station_tasks[station_id].append({
                'batch': batch_id,
                'stage': stage,
                'start': task['start'],  # EntryTime (Sink alkaa)
                'end': task['end'],      # Lift valmis (nostinoperaatio kokonaan valmis)
            })
    
    # Lisää rajoitteet: jokaisella asemalla erien välillä disjunktio
    # RAJOITE: A.end <= B.start TAI B.end <= A.start
    # (A:n Lift valmis ennen B:n Sink alkaa TAI päinvastoin)
    constraints_added = 0
    for station_id, tasks in station_tasks.items():
        # Jokainen pari tehtäviä samalla asemalla
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                task_a = tasks[i]
                task_b = tasks[j]
                
                # Jos eri erät, lisää disjunktio:
                # JOKO A:n Lift valmis ennen B:n Sink alkaa TAI päinvastoin
                if task_a['batch'] != task_b['batch']:
                    # Luo boolean: onko A ennen B:tä?
                    var_name = f'a{task_a["batch"]}_s{task_a["stage"]}_before_b{task_b["batch"]}_s{task_b["stage"]}_stat{station_id}'
                    a_before_b = model.NewBoolVar(var_name)
                    
                    # Jos A ennen B:tä → A:n Lift valmis ennen B:n Sink alkaa
                    # A.end <= B.start
                    model.Add(task_a['end'] <= task_b['start']).OnlyEnforceIf(a_before_b)
                    
                    # Jos B ennen A:ta → B:n Lift valmis ennen A:n Sink alkaa
                    # B.end <= A.start
                    model.Add(task_b['end'] <= task_a['start']).OnlyEnforceIf(a_before_b.Not())
                    
                    constraints_added += 1
    
    if constraints_added > 0:
        print(f"    Lisätty {constraints_added} disjunktiivista rajoitetta")
    
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
        
        # Pura ratkaisu (TÄRKEÄ: Tallenna optimoidut calc_time-arvot!)
        solution = {}
        for (batch, stage), task in task_vars.items():
            solution[(batch, stage)] = {
                'start': solver.Value(task['start']),
                'end': solver.Value(task['end']),
                'station': solver.Value(task['station_assignment']),
                'calc_time': solver.Value(task['calc_time']),  # OPTIMOITU ARVO!
                'min_time': task['min_time'],
                'max_time': task['max_time'],
                'transporter': task['transporter']
            }
        
        return status, solution, makespan
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ratkaisua ei löytynyt!")
        return status, None, None


def cpsat_solution_to_dataframe(solution, matrix_df, stations_df, transporters_df, transfer_times, lift_times, sink_times):
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
        
        phase_1 = transfer_times.get((int(start_station), int(first_station), int(transporter_id)), 0)
        phase_2 = lift_times.get((int(first_station), int(transporter_id)), 0)
        phase_3 = 0  # Ei siirtoa
        phase_4 = sink_times.get((int(first_station), int(transporter_id)), 0)
        
        # Laske Lift_time taaksepäin Start_time:sta
        # HUOM: Varmista että lift_time >= 0 (nostin ei voi toimia ennen aikaa 0)
        ideal_lift_time = first_start - int(phase_1) - int(phase_2) - int(phase_4)
        lift_time = max(0, ideal_lift_time)
        
        # Jos lift_time pakotettiin 0:aan, sink_time pitää säätää
        if lift_time == 0:
            # Nostintehtävä: lift (phase_2) + siirto (phase_1) + sink (phase_4)
            sink_time = lift_time + int(phase_2) + int(phase_1) + int(phase_4)
        else:
            sink_time = first_start
        
        # Stage 0 -rivi
        task_row_0 = {
            'Transporter_id': transporter_id,
            'Batch': batch,
            'Treatment_program': treatment_program,
            'Stage': 0,
            'Lift_stat': start_station,
            'Lift_time': lift_time,
            'Sink_stat': first_station,
            'Sink_time': sink_time,
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
            
            phase_1 = transfer_times.get((int(current_station), int(next_station), int(transporter_id)), 0)
            phase_2 = lift_times.get((int(current_station), int(transporter_id)), 0)
            phase_3 = transfer_times.get((int(current_station), int(current_station), int(transporter_id)), 0)
            phase_4 = sink_times.get((int(current_station), int(transporter_id)), 0)
            
            # KORJATTU: Oikea tulkinta interval-muuttujista
            # task['start'] = Aika kun SINK ALKAA (erä tulee asemalle)
            # task['end'] = Aika kun LIFT VALMIS (erä lähtee asemalta)
            # 
            # Aikajana: [start] --sink--> [entry] --calc--> [exit] --lift--> [end]
            #
            # Nostintehtävä = NOSTO tältä asemalta ja LASKU seuraavalle
            
            # Lift alkaa: end - lift_time
            lift_time = task['end'] - int(phase_2)
            
            # Sink valmis seuraavalla asemalla: next_task['start'] + sink_time
            if i < len(batch_stages) - 1:
                next_task = solution[(batch, next_stage)]
                sink_time = next_task['start'] + int(phase_4)
            else:
                # Viimeinen vaihe: Sink_stat = Lift_stat (sama asema)
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


def validate_empty_transporter_movements(df, transfer_times):
    """
    Validoi että nostimen tehtävien välissä on riittävästi aikaa tyhjälle siirtymälle.
    
    Args:
        df: transporter_tasks DataFrame (sisältää Lift_stat, Sink_stat, Lift_time, Sink_time)
        transfer_times: esilasketut siirtoajat {(from_station, to_station, transporter): time}
    
    Returns:
        list: Lista varoituksista jos tyhjä siirtymä ei ole riittävä
    """
    warnings = []
    
    # Järjestä tehtävät aikajärjestykseen
    df_sorted = df.sort_values('Lift_time').reset_index(drop=True)
    
    for i in range(len(df_sorted) - 1):
        curr = df_sorted.iloc[i]
        next_task = df_sorted.iloc[i + 1]
        
        # Tarkista onko sama nostin
        if curr['Transporter_id'] != next_task['Transporter_id']:
            continue
        
        # Edellinen tehtävä päättyy: Sink valmis asemalla curr['Sink_stat']
        prev_end_station = int(curr['Sink_stat'])
        prev_end_time = int(curr['Sink_time'])
        
        # Seuraava tehtävä alkaa: Lift alkaa asemalta next_task['Lift_stat']
        next_start_station = int(next_task['Lift_stat'])
        next_start_time = int(next_task['Lift_time'])
        
        # Aikavä tehtävien välillä
        time_gap = next_start_time - prev_end_time
        
        # Tarvittava tyhjä siirtymäaika
        transporter_id = int(curr['Transporter_id'])
        transfer_key = (prev_end_station, next_start_station, transporter_id)
        required_transfer = transfer_times.get(transfer_key, 0)
        
        # Tarkista riittääkö aika
        if time_gap < required_transfer:
            warnings.append({
                'prev_task': f"Erä {int(curr['Batch'])} Stage {int(curr['Stage'])}",
                'next_task': f"Erä {int(next_task['Batch'])} Stage {int(next_task['Stage'])}",
                'prev_end_station': prev_end_station,
                'next_start_station': next_start_station,
                'prev_end_time': prev_end_time,
                'next_start_time': next_start_time,
                'time_gap': time_gap,
                'required_transfer': required_transfer,
                'deficit': required_transfer - time_gap
            })
    
    return warnings


def create_line_matrix_from_solution(solution, matrix_df, treatment_programs_df, output_dir):
    """
    Luo line_matrix_stretched.csv muodon CP-SAT:n ratkaisusta.
    
    Muoto: Batch, Program, Treatment_program, Stage, Station, MinTime, MaxTime, CalcTime, EntryTime, ExitTime, Phase_1-4
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Luodaan line_matrix CP-SAT:n ratkaisusta...")
    
    rows = []
    
    # Käy läpi kaikki tehtävät
    for (batch, stage), sol in sorted(solution.items()):
        # Hae tehtävän tiedot matrix_df:stä
        task_row = matrix_df[(matrix_df['Batch'] == batch) & (matrix_df['Stage'] == stage)]
        if len(task_row) == 0:
            continue
        
        task_row = task_row.iloc[0]
        station = sol['station']
        program_id = int(task_row['Treatment_program'])
        
        # Hae CalcTime, MinTime, MaxTime treatment_programs_df:stä
        if program_id in treatment_programs_df:
            prog_df = treatment_programs_df[program_id]
            stage_row = prog_df[prog_df['Stage'] == stage]
            
            if len(stage_row) > 0:
                stage_row = stage_row.iloc[0]
                min_time = pd.to_timedelta(stage_row['MinTime']).total_seconds()
                max_time = pd.to_timedelta(stage_row['MaxTime']).total_seconds()
            else:
                min_time = sol['calc_time']
                max_time = sol['calc_time']
        else:
            min_time = sol['calc_time']
            max_time = sol['calc_time']
        
        # Entry/Exit time = start/end (CP-SAT ratkaisu)
        entry_time = sol['start']
        exit_time = sol['end']
        calc_time = sol['calc_time']
        
        rows.append({
            'Batch': batch,
            'Program': program_id,
            'Treatment_program': program_id,
            'Stage': stage,
            'Station': station,
            'MinTime': int(min_time),
            'MaxTime': int(max_time),
            'CalcTime': int(calc_time),
            'EntryTime': int(entry_time),
            'ExitTime': int(exit_time),
            'Phase_1': 0,  # Ei tarvita line_matrix muodossa
            'Phase_2': 0,
            'Phase_3': 0,
            'Phase_4': 0
        })
    
    df = pd.DataFrame(rows)
    print(f"  Luotu {len(df)} riviä line_matrix muotoon")
    
    return df


def save_optimized_calctimes(optimized_df, matrix_df, output_dir):
    """
    Tallentaa optimoidut CalcTime-arvot treatment_program-tiedostoihin.
    
    Logiikka:
    - Käy läpi optimoitu aikataulu eräkohtaisesti
    - Jokaiselle asemakäynnille: CalcTime = Lift_time (tältä asemalta) - Sink_time (tälle asemalle)
    - Sink_time = edellisen stage:n Sink_time (tai stage 0:n alkuaika)
    - Tallenna CalcTime käsittelyohjelmaan
    
    Args:
        optimized_df: Optimoitu transporter_tasks DataFrame
        matrix_df: line_matrix_original.csv DataFrame
        output_dir: Output-kansio
    """
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tallennetaan optimoidut CalcTime-arvot...")
    
    # Kerää optimoidut CalcTime-arvot eräkohtaisesti
    batch_calctimes = {}  # {(batch, program_id): {stage: calc_time}}
    
    # Käy läpi erät
    batches = sorted(optimized_df['Batch'].unique())
    
    for batch in batches:
        batch_rows = optimized_df[optimized_df['Batch'] == batch].sort_values('Stage')
        
        # Hae treatment_program
        program_id = int(batch_rows.iloc[0]['Treatment_program'])
        
        if (batch, program_id) not in batch_calctimes:
            batch_calctimes[(batch, program_id)] = {}
        
        prev_sink_time = None
        
        for idx, row in batch_rows.iterrows():
            stage = int(row['Stage'])
            
            # Stage 0: Skipata (ei ole käsittelyohjelmassa)
            if stage == 0:
                prev_sink_time = row['Sink_time']
                continue
            
            # CalcTime = Lift_time (tältä asemalta) - Sink_time (tälle asemalle)
            # Sink_time tälle asemalle = edellisen stage:n Sink_time
            lift_time = row['Lift_time']
            sink_time = prev_sink_time if prev_sink_time is not None else row['Sink_time']
            
            calc_time_sec = int(lift_time - sink_time)
            
            # Tallenna
            batch_calctimes[(batch, program_id)][stage] = calc_time_sec
            
            # Päivitä edellinen sink_time seuraavaa kierrosta varten
            prev_sink_time = row['Sink_time']
    
    # Kerää muutostiedot raportointiin
    changes_report = []
    
    # Päivitä treatment_program-tiedostot eräkohtaisesti
    for (batch, program_id), stage_times in batch_calctimes.items():
        # Lue alkuperäinen tiedosto
        program_file = os.path.join(output_dir, "initialization", f"treatment_program_{program_id:03d}.csv")
        
        if not os.path.exists(program_file):
            print(f"  ⚠️ Ei löydy: {program_file}")
            continue
        
        df = pd.read_csv(program_file)
        
        # Varmista että CalcTime-sarake on olemassa (luodaan jos puuttuu)
        if 'CalcTime' not in df.columns:
            # Alusta CalcTime = MinTime jos saraketta ei ole
            df['CalcTime'] = df['MinTime']
        
        # Päivitä CalcTime-arvot
        for stage, calc_time_sec in stage_times.items():
            mask = df['Stage'] == stage
            if mask.any():
                # Hae alkuperäinen CalcTime
                original_calctime_str = df.loc[mask, 'CalcTime'].values[0]
                original_sec = pd.to_timedelta(original_calctime_str).total_seconds()
                
                # Hae min/max rajat
                min_time_str = df.loc[mask, 'MinTime'].values[0]
                max_time_str = df.loc[mask, 'MaxTime'].values[0]
                min_sec = pd.to_timedelta(min_time_str).total_seconds()
                max_sec = pd.to_timedelta(max_time_str).total_seconds()
                
                # Muunna sekunnit HH:MM:SS-muotoon
                hours = int(calc_time_sec // 3600)
                minutes = int((calc_time_sec % 3600) // 60)
                seconds = int(calc_time_sec % 60)
                calc_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                
                df.loc[mask, 'CalcTime'] = calc_time_str
                
                # Tallenna muutostieto
                if abs(calc_time_sec - original_sec) > 1:  # Yli 1 sekunnin muutos
                    changes_report.append({
                        'Batch': batch,
                        'Program': program_id,
                        'Stage': stage,
                        'Original_CalcTime': original_calctime_str,
                        'Optimized_CalcTime': calc_time_str,
                        'Change_sec': calc_time_sec - original_sec,
                        'MinTime': min_time_str,
                        'MaxTime': max_time_str
                    })
        
        # Tallenna eräkohtainen tiedosto
        optimized_dir = os.path.join(output_dir, "optimized_programs")
        os.makedirs(optimized_dir, exist_ok=True)
        
        output_file = os.path.join(optimized_dir, f"Batch_{batch:03d}_Treatment_program_{program_id:03d}.csv")
        df.to_csv(output_file, index=False)
        print(f"  ✅ Tallennettu: Batch_{batch:03d}_Treatment_program_{program_id:03d}.csv")
    
    # Tallenna muutosraportti
    if changes_report:
        changes_df = pd.DataFrame(changes_report)
        report_file = os.path.join(output_dir, "optimized_programs", "calctime_changes_report.csv")
        changes_df.to_csv(report_file, index=False)
        print(f"\n  📊 CalcTime-muutokset ({len(changes_report)} vaiheessa):")
        print(f"     Tallennettu: calctime_changes_report.csv")
        
        # Näytä yhteenveto
        total_change = changes_df['Change_sec'].sum()
        print(f"     Kokonaismuutos: {total_change:+.0f} s ({total_change/60:+.1f} min)")
    else:
        print(f"\n  ℹ️  Ei merkittäviä CalcTime-muutoksia (alle 1s)")


def save_optimized_production(optimized_df, output_dir):
    """
    Tallentaa optimoidut alkuajat ja järjestyksen production.csv-tiedostoon.
    Päivittää initialization/production.csv Start_optimized-saraketta.
    
    Args:
        optimized_df: Optimoitu transporter_tasks DataFrame
        output_dir: Output-kansio
    """
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tallennetaan optimoitu production.csv...")
    
    # Kerää erien alkuajat (Stage 0 Lift_time = hetki kun erä lähtee aloitusasemalta)
    batch_starts = {}  # {batch: lift_time_sec}
    
    for _, row in optimized_df.iterrows():
        if int(row['Stage']) == 0:
            batch = int(row['Batch'])
            batch_starts[batch] = int(row['Lift_time'])
    
    # Lue alkuperäinen production.csv
    production_file = os.path.join(output_dir, "initialization", "production.csv")
    
    if not os.path.exists(production_file):
        print(f"  ⚠️ Ei löydy: {production_file}")
        return
    
    prod_df = pd.read_csv(production_file)
    
    # Tallenna alkuperäinen järjestys
    original_order = prod_df['Batch'].tolist()
    
    # Päivitä Start_optimized-sarake
    for batch, start_sec in batch_starts.items():
        mask = prod_df['Batch'] == batch
        if mask.any():
            # Muunna sekunnit HH:MM:SS-muotoon
            hours = int(start_sec // 3600)
            minutes = int((start_sec % 3600) // 60)
            seconds = int(start_sec % 60)
            start_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            prod_df.loc[mask, 'Start_optimized'] = start_str
    
    # TALLENNA PÄIVITETTY production.csv (säilyttää järjestyksen)
    prod_df.to_csv(production_file, index=False)
    print(f"  ✅ Päivitetty: initialization/production.csv (lisätty Start_optimized)")
    
    # TALLENNA MYÖS järjestetty versio optimized_programs-kansioon (raportointia varten)
    prod_df_sorted = prod_df.copy()
    prod_df_sorted['_sort_key'] = prod_df_sorted['Batch'].map(batch_starts)
    prod_df_sorted = prod_df_sorted.sort_values('_sort_key')
    prod_df_sorted = prod_df_sorted.drop(columns=['_sort_key'])
    optimized_order = prod_df_sorted['Batch'].tolist()
    
    optimized_file = os.path.join(output_dir, "optimized_programs", "production_optimized.csv")
    os.makedirs(os.path.dirname(optimized_file), exist_ok=True)
    prod_df_sorted.to_csv(optimized_file, index=False)
    print(f"  ✅ Tallennettu: optimized_programs/production_optimized.csv (järjestetty)")
    
    # Raportti järjestyksen muutoksista
    if original_order != optimized_order:
        print(f"\n  📊 Erien järjestys muuttui:")
        print(f"     Alkuperäinen: {original_order}")
        print(f"     Optimoitu:     {optimized_order}")
    else:
        print(f"\n  ℹ️  Erien järjestys ei muuttunut")




def optimize_transporter_schedule(matrix_df, stations_df, transporters_df, output_dir, time_limit=60):
    """
    Pääfunktio: Optimoi nostimien aikataulun CP-SAT:lla.
    Optimoi: erien järjestys, alkuajat, CalcTime-arvot (MinTime-MaxTime)
    
    Args:
        matrix_df: line_matrix_original.csv DataFrame
        stations_df: stations.csv DataFrame
        transporters_df: transporters.csv DataFrame
        output_dir: Output-kansio, josta luetaan treatment_program-tiedostot
        time_limit: Maksimiaika optimointiin (sekunteja)
        
    Returns:
        pd.DataFrame: Optimoitu aikataulu
    """
    print(f"\n{'='*60}")
    print(f"CP-SAT OPTIMOINTI ALKAA")
    print(f"{'='*60}\n")
    
    # Vaihe 0: Lue treatment_program-tiedosto
    treatment_programs_df = {}
    treatment_program_files = sorted(os.listdir(os.path.join(output_dir, "initialization")))
    for file in treatment_program_files:
        if file.endswith(".csv") and "treatment_program" in file:
            program_id = int(file.split("_")[-1].split(".")[0])
            df = pd.read_csv(os.path.join(output_dir, "initialization", file))
            treatment_programs_df[program_id] = df
    
    # Vaihe 1: Esilaskenta siirto-, lift- ja sink-ajoista
    transfer_times, lift_times, sink_times, stage0_times = precalculate_transfer_times(matrix_df, stations_df, transporters_df)
    
    # Vaihe 2: CP-SAT-mallin rakentaminen
    model, task_vars = build_cpsat_model(matrix_df, transfer_times, lift_times, sink_times, stage0_times, transporters_df, stations_df, treatment_programs_df)
    
    # Vaihe 3: Mallin ratkaisu
    status, solution, makespan = solve_cpsat_model(model, task_vars, time_limit_seconds=time_limit)
    
    # Vaihe 4: Muuntaminen DataFrame-muotoon (transporter_tasks)
    optimized_df = cpsat_solution_to_dataframe(solution, matrix_df, stations_df, transporters_df, transfer_times, lift_times, sink_times)
    
    # Vaihe 5: Tallennus treatment_program-tiedostoihin
    save_optimized_calctimes(optimized_df, matrix_df, output_dir)
    
    # Vaihe 6: Tallennus production.csv
    save_optimized_production(optimized_df, output_dir)
    
    print(f"\n{'='*60}")
    print(f"OPTIMOINTI VALMIS")
    print(f"{'='*60}\n")
    
    return optimized_df
