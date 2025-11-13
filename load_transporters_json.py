"""
Unified JSON loader for transporter configuration.
Replaces separate CSV files: transporters_physics.csv, transporters_task_areas.csv, transporters_start_positions.csv

Key fields:
- physics.avoid_distance_mm: Minimum X-direction distance (mm) between transporters for collision avoidance
- physics.x_*: Horizontal movement along production line
- physics.y_*: Horizontal movement perpendicular to line (0 for 2D transporters)
- physics.z_*: Vertical lift/sink movement
"""

import json
import os
import pandas as pd


def load_transporters_from_json(init_dir):
    """
    Load transporter configuration from JSON file and return three DataFrames
    matching the legacy CSV format for backward compatibility.
    
    Args:
        init_dir: Path to initialization directory containing transporters.json
        
    Returns:
        tuple: (physics_df, task_areas_df, start_positions_df)
            - physics_df: DataFrame with columns matching transporters _physics.csv
            - task_areas_df: DataFrame with columns matching transporters _task_areas.csv
            - start_positions_df: DataFrame with columns matching transporters_start_positions.csv
    """
    json_path = os.path.join(init_dir, "transporters.json")
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Transporters JSON not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    transporters = data.get('transporters', [])
    
    # Build physics DataFrame
    physics_rows = []
    for t in transporters:
        p = t.get('physics', {})
        physics_rows.append({
            'Transporter_id': t['id'],
            'X_acceleration_time (s)': p.get('x_acceleration_time_s', 0.0),
            'X_deceleration_time (s)': p.get('x_deceleration_time_s', 0.0),
            'X_max_speed (mm/s)': p.get('x_max_speed_mm_s', 0),
            'Y_acceleration_time (s)': p.get('y_acceleration_time_s', 0.0),
            'Y_deceleration_time (s)': p.get('y_deceleration_time_s', 0.0),
            'Y_max_speed (mm/s)': p.get('y_max_speed_mm_s', 0),
            'Z_total_distance (mm)': p.get('z_total_distance_mm', 0),
            'Z_slow_distance_dry (mm)': p.get('z_slow_distance_dry_mm', 0),
            'Z_slow_distance_wet (mm)': p.get('z_slow_distance_wet_mm', 0),
            'Z_slow_end_distance (mm)': p.get('z_slow_end_distance_mm', 0),
            'Z_slow_speed (mm/s)': p.get('z_slow_speed_mm_s', 0),
            'Z_fast_speed (mm/s)': p.get('z_fast_speed_mm_s', 0),
            'Avoid_distance (mm)': p.get('avoid_distance_mm', 0)
        })
    physics_df = pd.DataFrame(physics_rows)
    
    # Ensure correct types for physics
    physics_df['Transporter_id'] = physics_df['Transporter_id'].astype(int)
    for col in ['X_acceleration_time (s)', 'X_deceleration_time (s)', 
                'Y_acceleration_time (s)', 'Y_deceleration_time (s)']:
        physics_df[col] = physics_df[col].astype(float)
    for col in ['X_max_speed (mm/s)', 'Y_max_speed (mm/s)',
                'Z_total_distance (mm)', 'Z_slow_distance_dry (mm)',
                'Z_slow_distance_wet (mm)', 'Z_slow_end_distance (mm)', 
                'Z_slow_speed (mm/s)', 'Z_fast_speed (mm/s)', 'Avoid_distance (mm)']:
        physics_df[col] = physics_df[col].astype(int)
    
    # Build task_areas DataFrame
    task_rows = []
    for t in transporters:
        task_areas = t.get('task_areas', {})
        row = {
            'Transporter_id': t['id'],
            'Model': t.get('model', '2D')
        }
        
        # Line 100
        line_100 = task_areas.get('line_100', {})
        row['Min_Lift_Station_100'] = line_100.get('min_lift_station', 0)
        row['Max_Lift_Station_100'] = line_100.get('max_lift_station', 0)
        row['Min_Sink_Station_100'] = line_100.get('min_sink_station', 0)
        row['Max_Sink_Station_100'] = line_100.get('max_sink_station', 0)
        
        # Line 200
        line_200 = task_areas.get('line_200', {})
        row['Min_Lift_Station_200'] = line_200.get('min_lift_station', 0)
        row['Max_Lift_Station_200'] = line_200.get('max_lift_station', 0)
        row['Min_Sink_Station_200'] = line_200.get('min_sink_station', 0)
        row['Max_Sink_Station_200'] = line_200.get('max_sink_station', 0)
        
        # Line 300
        line_300 = task_areas.get('line_300', {})
        row['Min_Lift_Station_300'] = line_300.get('min_lift_station', 0)
        row['Max_Lift_Station_300'] = line_300.get('max_lift_station', 0)
        row['Min_Sink_Station_300'] = line_300.get('min_sink_station', 0)
        row['Max_Sink_Station_300'] = line_300.get('max_sink_station', 0)
        
        # Line 400
        line_400 = task_areas.get('line_400', {})
        row['Min_Lift_Station_400'] = line_400.get('min_lift_station', 0)
        row['Max_Lift_Station_400'] = line_400.get('max_lift_station', 0)
        row['Min_Sink_Station_400'] = line_400.get('min_sink_station', 0)
        row['Max_Sink_Station_400'] = line_400.get('max_sink_station', 0)
        
        task_rows.append(row)
    
    task_areas_df = pd.DataFrame(task_rows)
    
    # Ensure correct types for task_areas
    task_areas_df['Transporter_id'] = task_areas_df['Transporter_id'].astype(int)
    for col in ['Min_Lift_Station_100', 'Max_Lift_Station_100', 
                'Min_Sink_Station_100', 'Max_Sink_Station_100',
                'Min_Lift_Station_200', 'Max_Lift_Station_200',
                'Min_Sink_Station_200', 'Max_Sink_Station_200',
                'Min_Lift_Station_300', 'Max_Lift_Station_300',
                'Min_Sink_Station_300', 'Max_Sink_Station_300',
                'Min_Lift_Station_400', 'Max_Lift_Station_400',
                'Min_Sink_Station_400', 'Max_Sink_Station_400']:
        task_areas_df[col] = task_areas_df[col].astype(int)
    
    # Build start_positions DataFrame
    start_rows = []
    for t in transporters:
        start_rows.append({
            'Transporter': t['id'],
            'Start_station': t.get('start_station', 0)
        })
    
    start_positions_df = pd.DataFrame(start_rows)
    start_positions_df['Transporter'] = start_positions_df['Transporter'].astype(int)
    start_positions_df['Start_station'] = start_positions_df['Start_station'].astype(int)
    
    return physics_df, task_areas_df, start_positions_df


def load_transporter_physics_from_json(init_dir):
    """Convenience function to load only physics data."""
    physics_df, _, _ = load_transporters_from_json(init_dir)
    return physics_df


def load_transporter_task_areas_from_json(init_dir):
    """Convenience function to load only task areas data."""
    _, task_areas_df, _ = load_transporters_from_json(init_dir)
    return task_areas_df


def load_transporter_start_positions_from_json(init_dir):
    """Convenience function to load only start positions data."""
    _, _, start_positions_df = load_transporters_from_json(init_dir)
    return start_positions_df
