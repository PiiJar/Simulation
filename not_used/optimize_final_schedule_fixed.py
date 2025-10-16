#!/usr/bin/env python3
"""
Lopullisen aikataulun optimointi - korjaa asema- ja nostinkonfliktit.

TÄRKEÄ PERIAATE:
- Muuttaa VAIN Production.csv lähtöaikoja
- Käsittelyohjelmat (CalcTime) pysyvät ennallaan
- Käsittelyajat ovat kemiallis-fysikaalisia prosesseja
"""

import pandas as pd
import os
import shutil

def detect_station_conflicts(df):
    """Tunnistaa asemakonfliktit - useita eriä samalla asemalla samaan aikaan"""
    conflicts = []
    
    # Gruppaa tehtävät asemittain
    for station in range(df['Lift_stat'].min(), df['Sink_stat'].max() + 1):
        station_tasks = []
        
        # Kerää kaikki tehtävät jotka koskettavat tätä asemaa
        for idx, row in df.iterrows():
            # Lift-vaihe
            if row['Lift_stat'] == station:
                station_tasks.append({
                    'task_id': idx,
                    'batch': row['Batch'],
                    'start_time': row['Lift_time'],
                    'end_time': row['Lift_time'],  # Nostaminen on hetkellinen
                    'type': 'lift',
                    'station': station
                })
            
            # Käsittely-vaihe (erä on asemalla Lift_time:sta Sink_time:een)
            if row['Lift_stat'] == station and row['Sink_stat'] == station:
                # Sama asema lift ja sink - erä käsitellään täällä
                station_tasks.append({
                    'task_id': idx,
                    'batch': row['Batch'],
                    'start_time': row['Lift_time'],
                    'end_time': row['Sink_time'],
                    'type': 'treatment',
                    'station': station
                })
            
            # Sink-vaihe
            if row['Sink_stat'] == station:
                station_tasks.append({
                    'task_id': idx,
                    'batch': row['Batch'],
                    'start_time': row['Sink_time'],
                    'end_time': row['Sink_time'],  # Laskeminen on hetkellinen
                    'type': 'sink',
                    'station': station
                })
        
        # Tarkista päällekkäisyydet
        station_tasks = sorted(station_tasks, key=lambda x: x['start_time'])
        for i in range(len(station_tasks)):
            for j in range(i+1, len(station_tasks)):
                task_a = station_tasks[i]
                task_b = station_tasks[j]
                
                # Eri erät samalla asemalla samaan aikaan = konflikti
                if (task_a['batch'] != task_b['batch'] and 
                    task_a['end_time'] > task_b['start_time']):
                    conflicts.append({
                        'type': 'station_conflict',
                        'station': station,
                        'task_a': task_a,
                        'task_b': task_b,
                        'overlap_time': task_a['end_time'] - task_b['start_time']
                    })
    
    return conflicts

def detect_transporter_conflicts(df):
    """Tunnistaa nostinkonfliktit - sama nostin tekemässä useita tehtäviä samaan aikaan"""
    conflicts = []
    
    for transporter_id in df['Transporter_id'].unique():
        transporter_tasks = df[df['Transporter_id'] == transporter_id].copy()
        transporter_tasks = transporter_tasks.sort_values('Lift_time').reset_index(drop=True)
        
        for i in range(len(transporter_tasks) - 1):
            current_task = transporter_tasks.iloc[i]
            next_task = transporter_tasks.iloc[i + 1]
            
            # Tarkista että edellinen tehtävä on valmis ennen seuraavan alkua
            actual_gap = next_task['Lift_time'] - current_task['Sink_time']
            
            if actual_gap < 0:
                conflicts.append({
                    'type': 'transporter_overlap',
                    'transporter_id': transporter_id,
                    'current_task': current_task.to_dict(),
                    'next_task': next_task.to_dict(),
                    'overlap_time': -actual_gap
                })
    
    return conflicts

def resolve_station_conflicts(df, conflicts, stations_df, logger):
    """Ratkaisee asemakonfliktit siirtämällä tehtäviä"""
    df_optimized = df.copy()
    total_shifts = 0
    
    for conflict in conflicts:
        if conflict['type'] != 'station_conflict':
            continue
            
        # Yksinkertainen ratkaisu: siirrä myöhäisempää tehtävää
        task_a = conflict['task_a']
        task_b = conflict['task_b']
        overlap = conflict['overlap_time']
        
        # Siirrä task_b:tä niin että konflikti ratkeaa
        shift_amount = overlap + 1  # +1s marginaali
        
        # Etsi kaikki task_b:n erän tehtävät ja siirrä niitä
        batch_mask = df_optimized['Batch'] == task_b['batch']
        df_optimized.loc[batch_mask, 'Lift_time'] += shift_amount
        df_optimized.loc[batch_mask, 'Sink_time'] += shift_amount
        
        total_shifts += shift_amount
        logger.log_optimization(f"Resolved station {conflict['station']} conflict: shifted batch {task_b['batch']} by +{shift_amount:.1f}s")
    
    return df_optimized

def resolve_transporter_conflicts(df, conflicts, logger):
    """Ratkaisee nostinkonfliktit siirtämällä myöhempiä tehtäviä"""
    df_optimized = df.copy()
    
    for conflict in conflicts:
        if conflict['type'] != 'transporter_overlap':
            continue
            
        transporter_id = conflict['transporter_id']
        current_task = conflict['current_task']
        next_task = conflict['next_task']
        overlap = conflict['overlap_time']
        
        # Laske tarvittava siirto
        required_move_time = 5.0  # Nostimen siirtoaika
        total_shift = overlap + required_move_time + 1.0  # +1s marginaali
        
        # Etsi kaikki myöhemmät tehtävät samalla nostimella
        shift_time_threshold = next_task['Lift_time']
        later_tasks_mask = (df_optimized['Transporter_id'] == transporter_id) & \
                          (df_optimized['Lift_time'] >= shift_time_threshold)
        
        if later_tasks_mask.any():
            shift_count = later_tasks_mask.sum()
            df_optimized.loc[later_tasks_mask, 'Lift_time'] += int(round(total_shift))
            df_optimized.loc[later_tasks_mask, 'Sink_time'] += int(round(total_shift))
            
            logger.log_optimization(f"Resolved transporter {transporter_id} conflict: shifted {shift_count} tasks "
                                  f"from time {shift_time_threshold}+ by +{total_shift:.1f}s")
            logger.log_optimization(f"  Details: overlap={overlap:.1f}s, move_time={required_move_time:.1f}s, margin=1s")
    
    return df_optimized

def update_production_and_programs(df_original, df_optimized, output_dir, logger):
    """Päivittää VAIN Production.csv:n lähtöaikoja - käsittelyohjelmat pysyvät ennallaan"""
    
    # Kopioi stretched_programs -> optimized_programs SELLAISENAAN
    # (käsittelyajat eivät muutu optimoinnissa - vain lähtöaikataulu muuttuu)
    stretched_dir = os.path.join(output_dir, "stretched_programs")
    optimized_dir = os.path.join(output_dir, "optimized_programs")
    os.makedirs(optimized_dir, exist_ok=True)
    
    if os.path.exists(stretched_dir):
        for fname in os.listdir(stretched_dir):
            src = os.path.join(stretched_dir, fname)
            dst = os.path.join(optimized_dir, fname)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                logger.log_optimization(f"Copied unchanged program: {fname}")
    
    # Laske lähtöaikojen muutokset vain Stage 0:lle (erien lähtö linjaan)
    start_time_changes = {}
    for idx in df_original.index:
        if idx < len(df_optimized):
            orig_lift = df_original.at[idx, 'Lift_time']
            opt_lift = df_optimized.at[idx, 'Lift_time']
            shift = opt_lift - orig_lift
            
            if abs(shift) > 0.1:  # Merkittävä muutos
                batch = df_optimized.at[idx, 'Batch']
                stage = df_optimized.at[idx, 'Stage']
                
                # Tallenna vain Stage 0 (lähtöaika) muutokset
                if stage == 0:
                    if batch not in start_time_changes:
                        start_time_changes[batch] = shift
                    # Jos samalle erälle useita Stage 0 tehtäviä, ota ensimmäinen
    
    # Päivitä Production.csv (vain lähtöaikoja)
    production_file = os.path.join(output_dir, "initialization", "Production.csv")
    if os.path.exists(production_file):
        prod_df = pd.read_csv(production_file)
        
        for batch, shift in start_time_changes.items():
            mask = prod_df["Batch"] == batch
            if mask.any():
                old_time = pd.to_timedelta(prod_df.loc[mask, "Start_time"]).dt.total_seconds().values[0]
                new_time = old_time + shift
                prod_df.loc[mask, "Start_time"] = pd.to_datetime(new_time, unit='s').strftime('%H:%M:%S')
                if "Start_time_seconds" in prod_df.columns:
                    prod_df.loc[mask, "Start_time_seconds"] = new_time
                
                logger.log_optimization(f"Updated Production.csv: Batch {batch} Start_time by {shift:+.1f}s "
                                      f"({pd.to_datetime(old_time, unit='s').strftime('%H:%M:%S')} -> "
                                      f"{pd.to_datetime(new_time, unit='s').strftime('%H:%M:%S')})")
        
        prod_df.to_csv(production_file, index=False)
        logger.log_optimization(f"Updated {len(start_time_changes)} batch start times in Production.csv")
    
    # KÄSITTELYOHJELMAT PYSYVÄT MUUTTUMATTOMINA!
    # Optimointi vaikuttaa vain aikatauluun, ei kemiallis-fysikalisiin prosesseihin
    logger.log_optimization("Treatment programs kept unchanged - optimization affects only scheduling, not process times")

def optimize_final_schedule(output_dir="output", max_iterations=10):
    """
    Optimoi lopullisen aikataulun ratkaisemalla asema- ja nostinkonfliktit.
    
    TÄRKEÄÄ: Muuttaa vain Production.csv lähtöaikoja, ei käsittelyohjelmia!
    Käsittelyajat (CalcTime) ovat kemiallis-fysikaalisia ja pysyvät ennallaan.
    
    Sijoittuu pipeline:ssä stretch_tasks() ja generate_matrix_stretched() väliin.
    """
    from simulation_logger import get_logger
    
    logger = get_logger()
    if not logger:
        print("❌ Logger ei ole käytettävissä - optimointi ohitetaan")
        return
    
    logger.log_optimization("=" * 60)
    logger.log_optimization("STARTING FINAL SCHEDULE OPTIMIZATION")
    logger.log_optimization("=" * 60)
    logger.log_optimization("PRINCIPLE: Only Production.csv start times are modified")
    logger.log_optimization("Treatment programs (CalcTime) remain unchanged - they are chemical processes")
    
    # Lue venytetyt nostintehtävät
    transporter_file = os.path.join(output_dir, "logs", "transporter_tasks_stretched.csv")
    if not os.path.exists(transporter_file):
        logger.log_optimization("❌ No stretched transporter tasks found - skipping optimization")
        return
    
    df_original = pd.read_csv(transporter_file)
    logger.log_optimization(f"📊 Loaded {len(df_original)} transporter tasks for optimization")
    
    # Iteratiivinen optimointi
    df_current = df_original.copy()
    
    for iteration in range(1, max_iterations + 1):
        logger.log_optimization(f"\n🔄 ITERATION {iteration}/{max_iterations}")
        
        # Tunnista konfliktit
        station_conflicts = detect_station_conflicts(df_current)
        transporter_conflicts = detect_transporter_conflicts(df_current)
        
        total_conflicts = len(station_conflicts) + len(transporter_conflicts)
        logger.log_optimization(f"Found {len(station_conflicts)} station conflicts, {len(transporter_conflicts)} transporter conflicts")
        
        if total_conflicts == 0:
            logger.log_optimization("✅ No conflicts found - optimization complete!")
            break
        
        # Ratkaise konfliktit
        if station_conflicts:
            df_current = resolve_station_conflicts(df_current, station_conflicts, None, logger)
        
        if transporter_conflicts:
            df_current = resolve_transporter_conflicts(df_current, transporter_conflicts, logger)
        
        if iteration == max_iterations:
            logger.log_optimization(f"⚠️  Reached maximum iterations ({max_iterations})")
            remaining_conflicts = len(detect_station_conflicts(df_current)) + len(detect_transporter_conflicts(df_current))
            if remaining_conflicts > 0:
                logger.log_optimization(f"⚠️  {remaining_conflicts} conflicts remain unresolved")
    
    # Tallenna optimoidut nostintehtävät
    optimized_tasks_file = os.path.join(output_dir, "logs", "transporter_tasks_optimized.csv")
    df_current.to_csv(optimized_tasks_file, index=False)
    logger.log_optimization(f"💾 Saved optimized transporter tasks: {optimized_tasks_file}")
    
    # Päivitä Production.csv (vain lähtöaikoja!)
    update_production_and_programs(df_original, df_current, output_dir, logger)
    
    logger.log_optimization("=" * 60)
    logger.log_optimization("FINAL SCHEDULE OPTIMIZATION COMPLETE")
    logger.log_optimization("=" * 60)

if __name__ == "__main__":
    # Testikäyttö
    optimize_final_schedule("output/latest")
