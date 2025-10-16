#!/usr/bin/env python3
"""
Complete Transporter Task Simulation

Simulates a complete transporter task sequence:
1. Horizontal movement: Station 110 → Station 101
2. Vertical lift at Station 101 (dry station)
3. Horizontal movement: Station 101 → Station 102  
4. Vertical lower at Station 102 (wet station)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

def calculate_horizontal_movement(start_pos, end_pos, acceleration_time, deceleration_time, max_speed):
    """Calculate horizontal movement profile."""
    
    distance = abs(end_pos - start_pos)
    direction = 1 if end_pos > start_pos else -1
    
    acceleration = max_speed / acceleration_time
    deceleration = max_speed / deceleration_time
    
    t_accel = acceleration_time
    t_decel = deceleration_time
    
    d_accel = 0.5 * acceleration * t_accel**2
    d_decel = 0.5 * deceleration * t_decel**2
    
    if d_accel + d_decel >= distance:
        # Triangular profile
        combined_factor = 0.5 * acceleration * (1 + (acceleration_time/deceleration_time))
        t_accel_actual = np.sqrt(distance / combined_factor)
        t_decel_actual = (acceleration_time / deceleration_time) * t_accel_actual
        peak_speed = acceleration * t_accel_actual
        d_accel_actual = 0.5 * acceleration * t_accel_actual**2
        d_decel_actual = distance - d_accel_actual
        t_constant = 0
        d_constant = 0
    else:
        # Trapezoidal profile
        t_accel_actual = t_accel
        t_decel_actual = t_decel
        peak_speed = max_speed
        d_accel_actual = d_accel
        d_decel_actual = d_decel
        d_constant = distance - d_accel_actual - d_decel_actual
        t_constant = d_constant / max_speed
    
    total_time = t_accel_actual + t_constant + t_decel_actual
    
    return {
        'total_time': total_time,
        'peak_speed': peak_speed,
        'profile_type': 'Triangular' if t_constant == 0 else 'Trapezoidal',
        'distance': distance,
        'direction': direction
    }

def calculate_vertical_movement(total_distance, slow_distance, slow_end_distance, slow_speed, fast_speed, direction="up"):
    """Calculate vertical movement profile."""
    
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
    
    total_time = t_slow_start + t_fast + t_slow_end
    
    return {
        'total_time': total_time,
        'slow_start_time': t_slow_start,
        'fast_time': t_fast,
        'slow_end_time': t_slow_end,
        'direction': direction
    }

def get_station_info(stations_df, station_number):
    """Get station information by number."""
    station = stations_df[stations_df['Number'] == station_number]
    if len(station) == 0:
        return None
    return station.iloc[0]

def get_vertical_parameters(transporter_params, station_type):
    """Get vertical parameters based on station type."""
    if station_type == 0:  # Dry station
        return {
            'z_slow_distance': transporter_params['z_slow_distance_dry'],
            'z_slow_end_distance': transporter_params['z_slow_end_distance'],
            'z_slow_speed': transporter_params['z_slow_speed'],
            'z_fast_speed': transporter_params['z_fast_speed']
        }
    else:  # Wet station
        return {
            'z_slow_distance': transporter_params['z_slow_distance_wet'],
            'z_slow_end_distance': transporter_params['z_slow_end_distance'],
            'z_slow_speed': transporter_params['z_slow_speed'],
            'z_fast_speed': transporter_params['z_fast_speed']
        }

def simulate_complete_task(stations_df, transporter_params, start_station, lift_station, sink_station):
    """Simulate complete transporter task."""
    
    # Get station information
    start_info = get_station_info(stations_df, start_station)
    pickup_info = get_station_info(stations_df, pickup_station)
    dropoff_info = get_station_info(stations_df, dropoff_station)
    
    if start_info is None or pickup_info is None or dropoff_info is None:
        print("❌ Error: Could not find all required stations!")
        return None
    
    print(f"🏗️  Complete Transporter Task Simulation")
    print(f"    Start: Station {start_station} ({start_info['Name']}) at {start_info['X Position']}mm")
    print(f"    Pickup: Station {pickup_station} ({pickup_info['Name']}) at {pickup_info['X Position']}mm (type {pickup_info['Station_type']})")
    print(f"    Dropoff: Station {dropoff_station} ({dropoff_info['Name']}) at {dropoff_info['X Position']}mm (type {dropoff_info['Station_type']})")
    
    # Phase 1: Move to pickup station
    print(f"\n🔄 Phase 1: Moving to pickup station ({start_station} → {pickup_station})")
    move1 = calculate_horizontal_movement(
        start_info['X Position'], pickup_info['X Position'],
        transporter_params['acceleration_time'], transporter_params['deceleration_time'],
        transporter_params['max_speed']
    )
    print(f"   Distance: {abs(pickup_info['X Position'] - start_info['X Position'])} mm")
    print(f"   Time: {move1['total_time']:.2f} s")
    print(f"   Profile: {move1['profile_type']} (peak: {move1['peak_speed']:.1f} mm/s)")
    
    # Phase 2: Lift at pickup station
    print(f"\n🔼 Phase 2: Lifting at pickup station (Station {pickup_station})")
    pickup_params = get_vertical_parameters(transporter_params, pickup_info['Station_type'])
    lift = calculate_vertical_movement(
        transporter_params['z_total_distance'],
        pickup_params['z_slow_distance'],
        pickup_params['z_slow_end_distance'],
        pickup_params['z_slow_speed'],
        pickup_params['z_fast_speed'],
        "up"
    )
    station_type_name = "Dry" if pickup_info['Station_type'] == 0 else "Wet"
    print(f"   Station type: {station_type_name}")
    print(f"   Time: {lift['total_time']:.2f} s")
    print(f"   Phases: {lift['slow_start_time']:.1f}s slow + {lift['fast_time']:.1f}s fast + {lift['slow_end_time']:.1f}s slow")
    
    # Phase 3: Move to dropoff station
    print(f"\n🔄 Phase 3: Moving to dropoff station ({pickup_station} → {dropoff_station})")
    move2 = calculate_horizontal_movement(
        pickup_info['X Position'], dropoff_info['X Position'],
        transporter_params['acceleration_time'], transporter_params['deceleration_time'],
        transporter_params['max_speed']
    )
    print(f"   Distance: {abs(dropoff_info['X Position'] - pickup_info['X Position'])} mm")
    print(f"   Time: {move2['total_time']:.2f} s")
    print(f"   Profile: {move2['profile_type']} (peak: {move2['peak_speed']:.1f} mm/s)")
    
    # Phase 4: Lower at dropoff station
    print(f"\n🔽 Phase 4: Lowering at dropoff station (Station {dropoff_station})")
    dropoff_params = get_vertical_parameters(transporter_params, dropoff_info['Station_type'])
    lower = calculate_vertical_movement(
        transporter_params['z_total_distance'],
        dropoff_params['z_slow_distance'],
        dropoff_params['z_slow_end_distance'],
        dropoff_params['z_slow_speed'],
        dropoff_params['z_fast_speed'],
        "down"
    )
    station_type_name = "Dry" if dropoff_info['Station_type'] == 0 else "Wet"
    print(f"   Station type: {station_type_name}")
    print(f"   Time: {lower['total_time']:.2f} s")
    print(f"   Phases: {lower['fast_time']:.1f}s fast + {lower['slow_end_time']:.1f}s slow")
    
    # Phase 5: Dropping time at destination
    dropping_time = dropoff_info['Dropping_Time']
    print(f"\n⏱️  Phase 5: Dropping time at destination")
    print(f"   Time: {dropping_time} s")
    
    # Calculate totals
    total_time = move1['total_time'] + lift['total_time'] + move2['total_time'] + lower['total_time'] + dropping_time
    total_horizontal_distance = move1['distance'] + move2['distance']
    total_vertical_distance = transporter_params['z_total_distance'] * 2  # up + down
    
    print(f"\n📊 Task Summary:")
    print(f"   Total time: {total_time:.2f} s ({total_time/60:.1f} min)")
    print(f"   Horizontal distance: {total_horizontal_distance} mm")
    print(f"   Vertical distance: {total_vertical_distance} mm")
    print(f"   Phase breakdown:")
    print(f"     Move to pickup: {move1['total_time']:.2f} s ({(move1['total_time']/total_time)*100:.1f}%)")
    print(f"     Lifting: {lift['total_time']:.2f} s ({(lift['total_time']/total_time)*100:.1f}%)")
    print(f"     Move to dropoff: {move2['total_time']:.2f} s ({(move2['total_time']/total_time)*100:.1f}%)")
    print(f"     Lowering: {lower['total_time']:.2f} s ({(lower['total_time']/total_time)*100:.1f}%)")
    print(f"     Dropping: {dropping_time} s ({(dropping_time/total_time)*100:.1f}%)")
    
    return {
        'total_time': total_time,
        'move1': move1,
        'lift': lift,
        'move2': move2,
        'lower': lower,
        'dropping_time': dropping_time,
        'stations': {
            'start': start_info,
            'pickup': pickup_info,
            'dropoff': dropoff_info
        }
    }

def create_task_visualization(task_result, output_dir):
    """Create visualization of the complete task."""
    
    if task_result is None:
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Create timeline visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Timeline data
    phases = ['Move to\nPickup', 'Lifting', 'Move to\nDropoff', 'Lowering', 'Dropping']
    times = [
        task_result['move1']['total_time'],
        task_result['lift']['total_time'],
        task_result['move2']['total_time'],
        task_result['lower']['total_time'],
        task_result['dropping_time']
    ]
    colors = ['blue', 'green', 'blue', 'red', 'orange']
    
    # Cumulative timeline
    cumulative_times = [0]
    for t in times:
        cumulative_times.append(cumulative_times[-1] + t)
    
    # Plot 1: Phase timeline
    for i, (phase, time, color) in enumerate(zip(phases, times, colors)):
        ax1.barh(0, time, left=cumulative_times[i], color=color, alpha=0.7, 
                label=f'{phase}: {time:.1f}s')
        # Add text in the middle of each bar
        mid_point = cumulative_times[i] + time/2
        ax1.text(mid_point, 0, f'{time:.1f}s', ha='center', va='center', fontweight='bold')
    
    ax1.set_xlim(0, task_result['total_time'])
    ax1.set_ylim(-0.5, 0.5)
    ax1.set_xlabel('Time (s)')
    ax1.set_title(f'Complete Task Timeline: {task_result["total_time"]:.1f} seconds total')
    ax1.set_yticks([])
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Station positions and movements
    stations = task_result['stations']
    station_positions = [
        stations['start']['X Position'],
        stations['pickup']['X Position'],
        stations['dropoff']['X Position']
    ]
    station_names = [
        f"Start\n{stations['start']['Name']}\n({stations['start']['Number']})",
        f"Pickup\n{stations['pickup']['Name']}\n({stations['pickup']['Number']})",
        f"Dropoff\n{stations['dropoff']['Name']}\n({stations['dropoff']['Number']})"
    ]
    
    # Plot stations
    ax2.scatter(station_positions, [0, 0, 0], s=200, c=['gray', 'green', 'red'], 
               alpha=0.7, zorder=3)
    
    # Add station labels
    for pos, name in zip(station_positions, station_names):
        ax2.annotate(name, (pos, 0), xytext=(0, 30), textcoords='offset points',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Draw movement arrows
    ax2.annotate('', xy=(stations['pickup']['X Position'], -0.1), 
                xytext=(stations['start']['X Position'], -0.1),
                arrowprops=dict(arrowstyle='->', lw=2, color='blue'))
    ax2.text((stations['start']['X Position'] + stations['pickup']['X Position'])/2, -0.15,
            f"Move 1\n{task_result['move1']['total_time']:.1f}s", ha='center', va='top', color='blue')
    
    ax2.annotate('', xy=(stations['dropoff']['X Position'], -0.25), 
                xytext=(stations['pickup']['X Position'], -0.25),
                arrowprops=dict(arrowstyle='->', lw=2, color='blue'))
    ax2.text((stations['pickup']['X Position'] + stations['dropoff']['X Position'])/2, -0.3,
            f"Move 2\n{task_result['move2']['total_time']:.1f}s", ha='center', va='top', color='blue')
    
    ax2.set_xlabel('X Position (mm)')
    ax2.set_title('Station Layout and Movement Path')
    ax2.set_ylim(-0.4, 0.1)
    ax2.grid(True, alpha=0.3)
    ax2.set_yticks([])
    
    plt.tight_layout()
    
    # Save plot
    plot_filename = os.path.join(output_dir, 'complete_task_analysis.png')
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"✓ Task visualization saved: {plot_filename}")
    
    plt.show()

def main():
    """Main function."""
    
    # Read configuration files
    transporters_file = os.path.join("Initialization", "Transporters.csv")
    stations_file = os.path.join("Initialization", "Stations.csv")
    
    if not os.path.exists(transporters_file) or not os.path.exists(stations_file):
        print("❌ Error: Configuration files not found!")
        return
    
    df_transporters = pd.read_csv(transporters_file)
    df_stations = pd.read_csv(stations_file)
    
    if len(df_transporters) == 0:
        print("❌ Error: No transporters found!")
        return
    
    # Get transporter parameters
    transporter = df_transporters.iloc[0]
    transporter_params = {
        'acceleration_time': transporter['Acceleration_time (s)'],
        'deceleration_time': transporter['Deceleration_time (s)'],
        'max_speed': transporter['Max_speed (mm/s)'],
        'z_total_distance': transporter['Z_total_distance (mm)'],
        'z_slow_distance_dry': transporter['Z_slow_distance_dry (mm)'],
        'z_slow_distance_wet': transporter['Z_slow_distance_wet (mm)'],
        'z_slow_end_distance': transporter['Z_slow_end_distance (mm)'],
        'z_slow_speed': transporter['Z_slow_speed (mm/s)'],
        'z_fast_speed': transporter['Z_fast_speed (mm/s)']
    }
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_dir = os.path.join("output", f"complete_task_{timestamp}")
    
    # Simulate the complete task: 110 → 101 → 102
    task_result = simulate_complete_task(
        df_stations, transporter_params,
        start_station=110,      # Drier
        pickup_station=101,     # Loading
        dropoff_station=102     # Decreasing
    )
    
    # Create visualization
    if task_result:
        create_task_visualization(task_result, output_dir)
        
        # Save task summary to CSV
        summary_data = {
            'Phase': ['Move to Pickup', 'Lifting', 'Move to Dropoff', 'Lowering', 'Dropping', 'TOTAL'],
            'Time (s)': [
                task_result['move1']['total_time'],
                task_result['lift']['total_time'],
                task_result['move2']['total_time'],
                task_result['lower']['total_time'],
                task_result['dropping_time'],
                task_result['total_time']
            ],
            'Percentage': [
                (task_result['move1']['total_time']/task_result['total_time'])*100,
                (task_result['lift']['total_time']/task_result['total_time'])*100,
                (task_result['move2']['total_time']/task_result['total_time'])*100,
                (task_result['lower']['total_time']/task_result['total_time'])*100,
                (task_result['dropping_time']/task_result['total_time'])*100,
                100.0
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_file = os.path.join(output_dir, 'task_summary.csv')
        summary_df.to_csv(summary_file, index=False)
        print(f"✓ Task summary saved: {summary_file}")

if __name__ == "__main__":
    main()
