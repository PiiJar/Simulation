#!/usr/bin/env python3
"""
Station Type Movement Simulation

This script simulates transporter movement for different station types:
- Station type 0: Dry stations (faster vertical movement)
- Station type 1: Wet stations (slower, more careful vertical movement)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

def get_vertical_parameters_for_station(transporter_params, station_type):
    """
    Get vertical movement parameters based on station type.
    
    Args:
        transporter_params (dict): Transporter parameters
        station_type (int): 0 for dry station, 1 for wet station
    
    Returns:
        dict: Vertical movement parameters for the station type
    """
    
    if station_type == 0:  # Dry station - faster movement
        return {
            'z_slow_distance': transporter_params['z_slow_distance_dry'],
            'z_slow_end_distance': transporter_params['z_slow_end_distance'],  # Same for all
            'z_slow_speed': transporter_params['z_slow_speed'],
            'z_fast_speed': transporter_params['z_fast_speed']
        }
    else:  # Wet station - more careful movement
        return {
            'z_slow_distance': transporter_params['z_slow_distance_wet'],
            'z_slow_end_distance': transporter_params['z_slow_end_distance'],  # Same for all
            'z_slow_speed': transporter_params['z_slow_speed'],
            'z_fast_speed': transporter_params['z_fast_speed']
        }

def calculate_vertical_movement_by_station(total_distance, station_params, direction="up"):
    """
    Calculate vertical movement based on station type parameters.
    
    Args:
        total_distance (float): Total vertical distance in mm
        station_params (dict): Station-specific vertical parameters
        direction (str): "up" for lifting, "down" for lowering
    
    Returns:
        tuple: (time_points, position_points, speed_points, phase_info)
    """
    
    slow_distance = station_params['z_slow_distance']
    slow_end_distance = station_params['z_slow_end_distance']
    slow_speed = station_params['z_slow_speed']
    fast_speed = station_params['z_fast_speed']
    
    if direction == "up":
        # LIFTING: slow start + fast middle + slow end
        slow_start_distance = slow_distance
        slow_end_distance_actual = slow_end_distance
        fast_distance = total_distance - slow_start_distance - slow_end_distance_actual
        
        if fast_distance < 0:
            slow_start_distance = total_distance / 2
            slow_end_distance_actual = total_distance / 2
            fast_distance = 0
        
        t_slow_start = slow_start_distance / slow_speed
        t_fast = fast_distance / fast_speed if fast_distance > 0 else 0
        t_slow_end = slow_end_distance_actual / slow_speed
        
    else:  # direction == "down"
        # LOWERING: fast start + slow end
        fast_distance = total_distance - slow_distance
        slow_end_distance_actual = slow_distance
        
        if fast_distance < 0:
            fast_distance = total_distance / 2
            slow_end_distance_actual = total_distance / 2
        
        t_slow_start = 0
        t_fast = fast_distance / fast_speed if fast_distance > 0 else 0
        t_slow_end = slow_end_distance_actual / slow_speed
    
    # Create time arrays
    dt = 0.1
    
    # Generate movement profiles
    if direction == "up":
        # Phase 1: Slow start
        t1_points = np.arange(0, t_slow_start + dt, dt) if t_slow_start > 0 else np.array([0])
        pos1_points = slow_speed * t1_points
        speed1_points = np.full_like(t1_points, slow_speed)
        
        # Phase 2: Fast middle
        if t_fast > 0:
            t2_points = np.arange(t_slow_start + dt, t_slow_start + t_fast + dt, dt)
            pos2_start = slow_start_distance
            pos2_points = pos2_start + fast_speed * (t2_points - t_slow_start)
            speed2_points = np.full_like(t2_points, fast_speed)
        else:
            t2_points = np.array([])
            pos2_points = np.array([])
            speed2_points = np.array([])
        
        # Phase 3: Slow end
        t3_start = t_slow_start + t_fast
        t3_points = np.arange(t3_start + dt, t3_start + t_slow_end + dt, dt) if t_slow_end > 0 else np.array([])
        if len(t3_points) > 0:
            pos3_start = slow_start_distance + fast_distance
            pos3_points = pos3_start + slow_speed * (t3_points - t3_start)
            speed3_points = np.full_like(t3_points, slow_speed)
        else:
            t3_points = np.array([])
            pos3_points = np.array([])
            speed3_points = np.array([])
        
        time_points = np.concatenate([t1_points, t2_points, t3_points])
        position_points = np.concatenate([pos1_points, pos2_points, pos3_points])
        speed_points = np.concatenate([speed1_points, speed2_points, speed3_points])
        
    else:  # down
        # Phase 1: Fast start
        t1_points = np.arange(0, t_fast + dt, dt) if t_fast > 0 else np.array([0])
        pos1_points = total_distance - fast_speed * t1_points
        speed1_points = np.full_like(t1_points, -fast_speed)
        
        # Phase 2: Slow end
        t2_start = t_fast
        t2_points = np.arange(t2_start + dt, t2_start + t_slow_end + dt, dt) if t_slow_end > 0 else np.array([])
        if len(t2_points) > 0:
            pos2_start = total_distance - fast_distance
            pos2_points = pos2_start - slow_speed * (t2_points - t2_start)
            speed2_points = np.full_like(t2_points, -slow_speed)
        else:
            t2_points = np.array([])
            pos2_points = np.array([])
            speed2_points = np.array([])
        
        time_points = np.concatenate([t1_points, t2_points])
        position_points = np.concatenate([pos1_points, pos2_points])
        speed_points = np.concatenate([speed1_points, speed2_points])
    
    # Phase info
    if direction == "up":
        phase_info = {
            'total_time': t_slow_start + t_fast + t_slow_end,
            'slow_start_time': t_slow_start,
            'fast_time': t_fast,
            'slow_end_time': t_slow_end,
            'slow_start_distance': slow_start_distance,
            'fast_distance': fast_distance,
            'slow_end_distance': slow_end_distance_actual,
            'direction': direction
        }
    else:
        phase_info = {
            'total_time': t_fast + t_slow_end,
            'slow_start_time': 0,
            'fast_time': t_fast,
            'slow_end_time': t_slow_end,
            'slow_start_distance': 0,
            'fast_distance': fast_distance,
            'slow_end_distance': slow_end_distance_actual,
            'direction': direction
        }
    
    return time_points, position_points, speed_points, phase_info

def compare_station_types(transporter_params, stations_df, output_dir=None):
    """
    Compare vertical movement for different station types.
    """
    
    if output_dir is None:
        output_dir = "output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get examples of each station type
    dry_stations = stations_df[stations_df['Station_type'] == 0]
    wet_stations = stations_df[stations_df['Station_type'] == 1]
    
    if len(dry_stations) == 0 or len(wet_stations) == 0:
        print("⚠️  Warning: Need both dry and wet stations for comparison")
        return
    
    # Use first station of each type for comparison
    dry_station = dry_stations.iloc[0]
    wet_station = wet_stations.iloc[0]
    
    print(f"🏗️  Comparing Station Types:")
    print(f"    Dry station: {dry_station['Name']} (type {dry_station['Station_type']})")
    print(f"    Wet station: {wet_station['Name']} (type {wet_station['Station_type']})")
    
    # Get parameters for each station type
    dry_params = get_vertical_parameters_for_station(transporter_params, 0)
    wet_params = get_vertical_parameters_for_station(transporter_params, 1)
    
    # Calculate movements for both station types (lifting only for comparison)
    total_distance = transporter_params['z_total_distance']
    
    # Dry station movement
    time_dry, pos_dry, speed_dry, info_dry = calculate_vertical_movement_by_station(
        total_distance, dry_params, "up"
    )
    
    # Wet station movement
    time_wet, pos_wet, speed_wet, info_wet = calculate_vertical_movement_by_station(
        total_distance, wet_params, "up"
    )
    
    # Create comparison visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Position comparison
    ax1.plot(time_dry, pos_dry, 'b-', linewidth=2, label=f'Dry Station ({dry_station["Name"]})')
    ax1.plot(time_wet, pos_wet, 'r-', linewidth=2, label=f'Wet Station ({wet_station["Name"]})')
    
    ax1.axhline(y=0, color='g', linestyle='--', alpha=0.7, label='Start: 0 mm')
    ax1.axhline(y=total_distance, color='purple', linestyle='--', alpha=0.7, 
               label=f'End: {total_distance} mm')
    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Z Position (mm)')
    ax1.set_title('Station Type Comparison: Vertical Position vs Time (LIFTING)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Speed comparison
    ax2.plot(time_dry, speed_dry, 'b-', linewidth=2, label=f'Dry Station ({dry_station["Name"]})')
    ax2.plot(time_wet, speed_wet, 'r-', linewidth=2, label=f'Wet Station ({wet_station["Name"]})')
    
    ax2.axhline(y=transporter_params['z_slow_speed'], color='orange', linestyle='--', alpha=0.7,
               label=f'Slow Speed: {transporter_params["z_slow_speed"]} mm/s')
    ax2.axhline(y=transporter_params['z_fast_speed'], color='purple', linestyle='--', alpha=0.7,
               label=f'Fast Speed: {transporter_params["z_fast_speed"]} mm/s')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Z Speed (mm/s)')
    ax2.set_title('Station Type Comparison: Vertical Speed vs Time (LIFTING)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    
    # Save comparison plot
    plot_filename = os.path.join(output_dir, 'station_type_comparison.png')
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"✓ Station type comparison saved: {plot_filename}")
    
    # Print detailed comparison
    print(f"\n📊 Movement Comparison Results:")
    print(f"   DRY STATION ({dry_station['Name']}):")
    print(f"     Total time: {info_dry['total_time']:.2f} s")
    print(f"     Slow start: {info_dry['slow_start_time']:.2f} s ({info_dry['slow_start_distance']:.0f} mm)")
    print(f"     Fast middle: {info_dry['fast_time']:.2f} s ({info_dry['fast_distance']:.0f} mm)")
    print(f"     Slow end: {info_dry['slow_end_time']:.2f} s ({info_dry['slow_end_distance']:.0f} mm)")
    
    print(f"\n   WET STATION ({wet_station['Name']}):")
    print(f"     Total time: {info_wet['total_time']:.2f} s")
    print(f"     Slow start: {info_wet['slow_start_time']:.2f} s ({info_wet['slow_start_distance']:.0f} mm)")
    print(f"     Fast middle: {info_wet['fast_time']:.2f} s ({info_wet['fast_distance']:.0f} mm)")
    print(f"     Slow end: {info_wet['slow_end_time']:.2f} s ({info_wet['slow_end_distance']:.0f} mm)")
    
    time_diff = info_wet['total_time'] - info_dry['total_time']
    print(f"\n   ⏱️  TIME DIFFERENCE: +{time_diff:.2f} s slower for wet station")
    
    plt.show()
    
    return info_dry, info_wet

def main():
    """Main function to run station type movement comparison."""
    
    # Read configuration files
    transporters_file = os.path.join("Initialization", "Transporters.csv")
    stations_file = os.path.join("Initialization", "Stations.csv")
    
    if not os.path.exists(transporters_file):
        print(f"❌ Error: {transporters_file} not found!")
        return
        
    if not os.path.exists(stations_file):
        print(f"❌ Error: {stations_file} not found!")
        return
    
    # Load data
    df_transporters = pd.read_csv(transporters_file)
    df_stations = pd.read_csv(stations_file)
    
    if len(df_transporters) == 0:
        print("❌ Error: No transporters found!")
        return
          # Get transporter parameters
    transporter = df_transporters.iloc[0]
    transporter_params = {
        'id': transporter['Transporter_id'],
        'z_total_distance': transporter['Z_total_distance (mm)'],
        'z_slow_distance_dry': transporter['Z_slow_distance_dry (mm)'],
        'z_slow_distance_wet': transporter['Z_slow_distance_wet (mm)'],
        'z_slow_end_distance': transporter['Z_slow_end_distance (mm)'],  # Same for all stations
        'z_slow_speed': transporter['Z_slow_speed (mm/s)'],
        'z_fast_speed': transporter['Z_fast_speed (mm/s)']
    }
    
    print(f"🏗️  Station Type Movement Analysis")
    print(f"    Transporter ID: {transporter_params['id']}")
    print(f"    Total Z distance: {transporter_params['z_total_distance']} mm")
    print(f"    Dry station slow distance: {transporter_params['z_slow_distance_dry']} mm (start)")
    print(f"    Wet station slow distance: {transporter_params['z_slow_distance_wet']} mm (start)")
    print(f"    Common slow end distance: {transporter_params['z_slow_end_distance']} mm (all stations)")
    print(f"    Speeds: {transporter_params['z_slow_speed']} mm/s slow, {transporter_params['z_fast_speed']} mm/s fast")
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_dir = os.path.join("output", f"station_type_analysis_{timestamp}")
    
    # Run comparison
    dry_info, wet_info = compare_station_types(transporter_params, df_stations, output_dir)
    
    # Create summary CSV
    summary_data = []
    
    # Add station type information
    for _, station in df_stations.iterrows():
        station_params = get_vertical_parameters_for_station(transporter_params, station['Station_type'])
        
        # Calculate lifting time for this station
        _, _, _, lift_info = calculate_vertical_movement_by_station(
            transporter_params['z_total_distance'], station_params, "up"
        )
        
        # Calculate lowering time for this station
        _, _, _, lower_info = calculate_vertical_movement_by_station(
            transporter_params['z_total_distance'], station_params, "down"
        )
        
        summary_data.append({
            'Station_Number': station['Number'],
            'Station_Name': station['Name'],
            'Station_Type': 'Dry' if station['Station_type'] == 0 else 'Wet',
            'X_Position': station['X Position'],
            'Dropping_Time': station['Dropping_Time'],
            'Lift_Time': lift_info['total_time'],
            'Lower_Time': lower_info['total_time'],
            'Total_Vertical_Time': lift_info['total_time'] + lower_info['total_time']
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_file = os.path.join(output_dir, 'station_movement_times.csv')
    summary_df.to_csv(summary_file, index=False)
    print(f"✓ Station movement summary saved: {summary_file}")
    
    print(f"\n📋 Station Movement Times Summary:")
    print(summary_df.to_string(index=False))

if __name__ == "__main__":
    main()
