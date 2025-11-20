"""
Generates a detailed transporter movement log based on a cyclic pattern.

This script takes a high-level task pattern (from pattern_mining.py) and
deconstructs each task into fine-grained physical movements (Idle, Move, Lift, etc.),
simulating a continuous process over multiple cycles.
"""
import os
import pandas as pd
from typing import Dict, Any

def load_physics(init_dir: str) -> Dict[str, Any]:
    """Lataa fysiikkaparametrit ensimmäiseltä nostimelta."""
    transporters_path = os.path.join(init_dir, "transporters.json")
    if not os.path.exists(transporters_path):
        raise FileNotFoundError(f"Transporters file not found: {transporters_path}")
    
    import json
    with open(transporters_path, 'r') as f:
        transporters_data = json.load(f)
    
    # Käytetään ensimmäisen nostimen (id: 1) fysiikkaa
    physics_data = transporters_data['transporters'][0]['physics']
    
    # Muunnetaan arvot oikeisiin yksiköihin (mm/s -> m/s)
    # ja lasketaan nosto/laskuajat
    z_total_dist_m = physics_data['z_total_distance_mm'] / 1000.0
    z_fast_speed_m_s = physics_data['z_fast_speed_mm_s'] / 1000.0
    
    # Yksinkertaistettu nosto/laskuaika
    lift_sink_time = z_total_dist_m / z_fast_speed_m_s

    return {
        "speed_loaded": physics_data['x_max_speed_mm_s'] / 1000.0,
        "speed_unloaded": physics_data['x_max_speed_mm_s'] / 1000.0 * 1.5, # Oletus: tyhjänä 1.5x nopeampi
        "lift_time": lift_sink_time,
        "sink_time": lift_sink_time,
    }

def load_stations(init_dir: str) -> Dict[int, Dict[str, Any]]:
    """Lataa asemien koordinaatit."""
    stations_path = os.path.join(init_dir, "stations.json")
    if not os.path.exists(stations_path):
        raise FileNotFoundError(f"Stations file not found: {stations_path}")
    
    import json
    with open(stations_path, 'r') as f:
        stations_data = json.load(f)

    # JSON-rakenne on { "stations": [ { "number": ... } ] }
    stations_dict = {}
    for station in stations_data['stations']:
        stations_dict[station['number']] = {
            'x': station['x_position'], 
            'y': station['y_position'], 
            'z': station['z_position']
        }
    return stations_dict

def load_pattern(reports_dir: str) -> pd.DataFrame:
    """Lataa pattern-miningin löytämä sykli."""
    pattern_path = os.path.join(reports_dir, "pattern_0_tasks.csv")
    if not os.path.exists(pattern_path):
        raise FileNotFoundError(f"Pattern file not found: {pattern_path}")
    
    return pd.read_csv(pattern_path)

def calculate_distance(stations: Dict, from_station_id: int, to_station_id: int) -> float:
    """Laskee etäisyyden kahden aseman välillä (XY-tasossa) ja palauttaa sen metreinä."""
    pos1 = stations[from_station_id]
    pos2 = stations[to_station_id]
    distance_mm = ((pos1['x'] - pos2['x'])**2 + (pos1['y'] - pos2['y'])**2)**0.5
    return distance_mm / 1000.0 # Muunnetaan metreiksi

def generate_movement_log(output_dir: str, num_cycles: int = 3):
    """
    Luo yksityiskohtaisen liikelokin kolmen syklin ajalta.
    """
    init_dir = os.path.join(output_dir, "initialization")
    reports_dir = os.path.join(output_dir, "reports")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # 1. Lataa datat
    try:
        stations = load_stations(init_dir)
        pattern_tasks = load_pattern(reports_dir)
        physics = load_physics(init_dir)
        print("✓ Asema-, pattern- ja fysiikkadata ladattu.")
    except FileNotFoundError as e:
        print(f"❌ Virhe: {e}")
        return

    # Järjestä pattern-tehtävät nostimen ja ajan mukaan
    pattern_tasks = pattern_tasks.sort_values(["Transporter", "TaskStart"]).reset_index(drop=True)

    # Etsi syklin absoluuttinen alkuaika (aikaisin TaskStart kaikista nostimista)
    global_start_time = float(pattern_tasks['TaskStart'].min())
    
    # Laske syklin kokonaiskesto (viimeinen TaskEnd - aikaisin TaskStart)
    global_end_time = float(pattern_tasks['TaskEnd'].max())
    cycle_duration = global_end_time - global_start_time
    
    # Normalisoi kaikki tehtävät suhteessa globaaliin alkuaikaan
    pattern_tasks_normalized = pattern_tasks.copy()
    pattern_tasks_normalized['TaskStart'] = pattern_tasks_normalized['TaskStart'] - global_start_time
    pattern_tasks_normalized['TaskEnd'] = pattern_tasks_normalized['TaskEnd'] - global_start_time
    
    # Tallenna jokaisen nostimen aloitusaika normalisoidussa syklissä
    transporter_start_offset = {}
    for trans_id in pattern_tasks_normalized['Transporter'].unique():
        trans_tasks = pattern_tasks_normalized[pattern_tasks_normalized['Transporter'] == trans_id].sort_values("TaskStart")
        transporter_start_offset[int(trans_id)] = float(trans_tasks.iloc[0]['TaskStart'])

    # Alusta muuttujat
    movements = []
    movement_id = 1
    task_seq = 0
    
    # Alusta nostimien sijainnit
    transporter_locations = {}
    last_task_end_time = {}
    
    for trans_id in pattern_tasks_normalized['Transporter'].unique():
        trans_tasks = pattern_tasks_normalized[pattern_tasks_normalized['Transporter'] == trans_id].sort_values("TaskStart")
        first_task = trans_tasks.iloc[0]
        transporter_locations[int(trans_id)] = int(first_task['From_Station'])
        # Aloita ajasta 0 (idle-viiva lisätään myöhemmin)
        last_task_end_time[int(trans_id)] = 0.0

    print(f"Simuloidaan {num_cycles} sykliä...")
    print(f"Syklin kokonaiskesto: {cycle_duration:.1f}s")
    print(f"Nostimen 1 aloitusaika syklissä: {transporter_start_offset[1]:.1f}s")
    print(f"Nostimen 2 aloitusaika syklissä: {transporter_start_offset[2]:.1f}s")
    
    # Lisää alkuperäinen idle-viiva 0 --> ensimmäinen tehtävä
    for trans_id in pattern_tasks_normalized['Transporter'].unique():
        start_offset = transporter_start_offset[int(trans_id)]
        if start_offset > 0:
            # Idle ajasta 0 aloitusaikaan
            movements.append([int(trans_id), 0, 0, 0.0, start_offset, transporter_locations[int(trans_id)], transporter_locations[int(trans_id)], 'Idle', 0, movement_id])
            movement_id += 1
            last_task_end_time[int(trans_id)] = start_offset

    for cycle in range(num_cycles):
        # Lajittele tehtävät nostimittain ja alkuajan mukaan
        cycle_tasks = pattern_tasks_normalized.sort_values(["Transporter", "TaskStart"]).reset_index(drop=True)
        
        task_seq_in_cycle = 0
        for _, task in cycle_tasks.iterrows():
            task_seq_in_cycle += 1
            task_seq = cycle * len(cycle_tasks) + task_seq_in_cycle

            transporter_id = int(task['Transporter'])
            batch_id = int(task['Batch'])
            from_station = int(task['From_Station'])
            to_station = int(task['To_Station'])
            
            # Laske tehtävän alkuaika tässä syklissä
            task_start_in_pattern = float(task['TaskStart'])
            task_end_in_pattern = float(task['TaskEnd'])
            
            # Syklin offset = cycle * syklin kokonaiskesto
            cycle_offset = cycle * cycle_duration
            expected_start = cycle_offset + task_start_in_pattern
            
            # Jos edellinen tehtävä päättyi myöhemmin, lisää idle-aika
            current_time = last_task_end_time[transporter_id]
            if current_time < expected_start:
                # Idle kunnes odotettu alkuaika
                idle_duration = expected_start - current_time
                movements.append([transporter_id, batch_id, 0, current_time, expected_start, transporter_locations[transporter_id], transporter_locations[transporter_id], 'Idle', task_seq, movement_id])
                movement_id += 1
                current_time = expected_start

            # --- Vaihe 1: Move to lifting station ---
            start_time = current_time
            distance = calculate_distance(stations, transporter_locations[transporter_id], from_station)
            move_duration = distance / physics['speed_unloaded']
            current_time += move_duration
            movements.append([transporter_id, batch_id, 1, start_time, current_time, transporter_locations[transporter_id], from_station, 'Move to lifting station', task_seq, movement_id])
            movement_id += 1
            transporter_locations[transporter_id] = from_station

            # --- Vaihe 2: Lifting ---
            start_time = current_time
            current_time += physics['lift_time']
            movements.append([transporter_id, batch_id, 2, start_time, current_time, from_station, from_station, 'Lifting', task_seq, movement_id])
            movement_id += 1

            # --- Vaihe 3: Move to sinking station ---
            start_time = current_time
            distance = calculate_distance(stations, from_station, to_station)
            move_duration = distance / physics['speed_loaded']
            current_time += move_duration
            movements.append([transporter_id, batch_id, 3, start_time, current_time, from_station, to_station, 'Move to sinking station', task_seq, movement_id])
            movement_id += 1
            transporter_locations[transporter_id] = to_station

            # --- Vaihe 4: Sinking ---
            start_time = current_time
            current_time += physics['sink_time']
            movements.append([transporter_id, batch_id, 4, start_time, current_time, to_station, to_station, 'Sinking', task_seq, movement_id])
            movement_id += 1
            
            # Päivitä tämän nostimen viimeisin päättymisaika
            last_task_end_time[transporter_id] = current_time

    # 3. Tallenna tulokset
    columns = ['Transporter', 'Batch', 'Phase', 'Start_Time', 'End_Time', 'From_Station', 'To_Station', 'Description', 'Task_Seq', 'Movement_ID']
    log_df = pd.DataFrame(movements, columns=columns)
    
    # Pyöristä ajat
    log_df['Start_Time'] = log_df['Start_Time'].round().astype(int)
    log_df['End_Time'] = log_df['End_Time'].round().astype(int)

    output_path = os.path.join(logs_dir, "sequence_transporters_movement.csv")
    log_df.to_csv(output_path, index=False)
    print(f"\n✓ Yksityiskohtainen liikeloki tallennettu: {output_path}")
    print(f"  - Sisältää {len(log_df)} liikettä {num_cycles} syklin ajalta.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python generate_sequence_movement_log.py <output_directory>")
        sys.exit(1)
    
    output_dir_arg = sys.argv[1]
    generate_movement_log(output_dir_arg)
