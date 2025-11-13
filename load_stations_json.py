"""
Helper function to load stations from JSON file.
Replaces _read_csv_lenient() for stations.csv.
"""

import json
import pandas as pd
from pathlib import Path


def load_stations_from_json(init_dir: str) -> pd.DataFrame:
    """
    Load stations from stations.json file.
    
    Args:
        init_dir: Path to initialization directory
        
    Returns:
        DataFrame with columns matching CSV format for backward compatibility:
        Number, Tank, Group, Name, X Position, Y Position, Z Position,
        Dropping_Time, Station_type, Device_delay
    """
    json_path = Path(init_dir) / "stations.json"
    
    if not json_path.exists():
        raise FileNotFoundError(f"stations.json not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract stations array
    stations = data.get("stations", [])
    
    if not stations:
        raise ValueError("No stations found in stations.json")
    
    # Convert to DataFrame
    df = pd.DataFrame(stations)
    
    # Rename columns to match CSV format (CSV uses spaces, JSON uses snake_case)
    df = df.rename(columns={
        'number': 'Number',
        'tank': 'Tank',
        'group': 'Group',
        'name': 'Name',
        'x_position': 'X Position',
        'y_position': 'Y Position',
        'z_position': 'Z Position',
        'dropping_time': 'Dropping_Time',
        'station_type': 'Station_type',
        'device_delay': 'Device_delay'
    })
    
    # Ensure correct data types
    df['Number'] = df['Number'].astype(int)
    df['Tank'] = df['Tank'].astype(int)
    df['Group'] = df['Group'].astype(int)
    df['X Position'] = df['X Position'].astype(int)
    df['Y Position'] = df['Y Position'].astype(int)
    df['Z Position'] = df['Z Position'].astype(int)
    df['Dropping_Time'] = df['Dropping_Time'].astype(int)
    df['Station_type'] = df['Station_type'].astype(int)
    df['Device_delay'] = df['Device_delay'].astype(float)
    
    return df
