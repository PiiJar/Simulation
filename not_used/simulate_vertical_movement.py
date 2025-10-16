#!/usr/bin/env python3
"""
Transporter Vertical Movement Simulation

This script simulates and visualizes the vertical (lifting/lowering) movement 
of a transporter, taking into account slow and fast speed phases.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

def calculate_vertical_movement(total_distance, slow_distance, slow_end_distance, slow_speed, fast_speed, direction="up"):
    """
    Calculate the time profile for vertical transporter movement.
    
    Args:
        total_distance (float): Total vertical distance in mm
        slow_distance (float): Distance to move at slow speed at beginning in mm
        slow_end_distance (float): Distance to move at slow speed at end (for UP movement) in mm
        slow_speed (float): Slow speed in mm/s
        fast_speed (float): Fast speed in mm/s
        direction (str): "up" for lifting, "down" for lowering
    
    Returns:
        tuple: (time_points, position_points, speed_points, phase_info)
    """
    
    if direction == "up":
        # LIFTING: slow start + fast middle + slow end
        slow_start_distance = slow_distance
        slow_end_distance_actual = slow_end_distance
        fast_distance = total_distance - slow_start_distance - slow_end_distance_actual
        
        # Ensure we don't have negative fast distance
        if fast_distance < 0:
            slow_start_distance = total_distance / 2
            slow_end_distance_actual = total_distance / 2
            fast_distance = 0
            print(f"⚠️  Warning: Total distance ({total_distance}mm) is too short for slow phases")
        
        # Calculate times
        t_slow_start = slow_start_distance / slow_speed
        t_fast = fast_distance / fast_speed if fast_distance > 0 else 0
        t_slow_end = slow_end_distance_actual / slow_speed
        
    else:  # direction == "down"
        # LOWERING: fast start + slow end (same distance as up slow start)
        fast_distance = total_distance - slow_distance  # slow end distance same as up slow start
        slow_end_distance_actual = slow_distance
        
        # Ensure we don't have negative fast distance
        if fast_distance < 0:
            fast_distance = total_distance / 2
            slow_end_distance_actual = total_distance / 2
            print(f"⚠️  Warning: Total distance ({total_distance}mm) is too short for phases")
        
        # Calculate times
        t_slow_start = 0  # No slow start for down movement
        t_fast = fast_distance / fast_speed if fast_distance > 0 else 0
        t_slow_end = slow_end_distance_actual / slow_speed
      # Create time arrays for each phase
    dt = 0.1  # 0.1 second intervals
    
    # Phase 1: Start phase
    if direction == "up":
        # Slow start for lifting
        t1_points = np.arange(0, t_slow_start + dt, dt) if t_slow_start > 0 else np.array([0])
        pos1_points = slow_speed * t1_points
        speed1_points = np.full_like(t1_points, slow_speed)
    else:
        # Fast start for lowering
        t1_points = np.arange(0, t_fast + dt, dt) if t_fast > 0 else np.array([0])
        pos1_points = total_distance - fast_speed * t1_points
        speed1_points = np.full_like(t1_points, -fast_speed)
    
    # Phase 2: Middle/End phase
    if direction == "up":
        # Fast middle + slow end for lifting
        if t_fast > 0:
            t2_points = np.arange(t_slow_start + dt, t_slow_start + t_fast + dt, dt)
            pos2_start = slow_start_distance
            pos2_points = pos2_start + fast_speed * (t2_points - t_slow_start)
            speed2_points = np.full_like(t2_points, fast_speed)
        else:
            t2_points = np.array([])
            pos2_points = np.array([])
            speed2_points = np.array([])
        
        # Slow end phase
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
            
    else:  # direction == "down"
        # Only slow end for lowering (fast start already handled in phase 1)
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
        
        # No third phase for down movement
        t3_points = np.array([])
        pos3_points = np.array([])
        speed3_points = np.array([])
    
    # Combine all phases
    if direction == "up":
        time_points = np.concatenate([t1_points, t2_points, t3_points])
        position_points = np.concatenate([pos1_points, pos2_points, pos3_points])
        speed_points = np.concatenate([speed1_points, speed2_points, speed3_points])
    else:
        time_points = np.concatenate([t1_points, t2_points])
        position_points = np.concatenate([pos1_points, pos2_points])
        speed_points = np.concatenate([speed1_points, speed2_points])
      # Phase information
    if direction == "up":
        phase_info = {
            'total_time': t_slow_start + t_fast + t_slow_end,
            'slow_start_time': t_slow_start,
            'fast_time': t_fast,
            'slow_end_time': t_slow_end,
            'slow_start_distance': slow_start_distance,
            'fast_distance': fast_distance,
            'slow_end_distance': slow_end_distance_actual,
            'total_distance': total_distance,
            'direction': direction
        }
    else:  # down
        phase_info = {
            'total_time': t_fast + t_slow_end,
            'slow_start_time': 0,  # No slow start for down
            'fast_time': t_fast,
            'slow_end_time': t_slow_end,
            'slow_start_distance': 0,  # No slow start for down
            'fast_distance': fast_distance,
            'slow_end_distance': slow_end_distance_actual,
            'total_distance': total_distance,
            'direction': direction
        }
    
    return time_points, position_points, speed_points, phase_info

def visualize_vertical_movement(transporter_params, direction="up", output_dir=None):
    """
    Create visualization of vertical transporter movement.
    
    Args:
        transporter_params (dict): Transporter parameters
        direction (str): "up" for lifting, "down" for lowering
        output_dir (str): Output directory for saving plots
    """
    
    if output_dir is None:
        output_dir = "output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate movement
    time_points, position_points, speed_points, phase_info = calculate_vertical_movement(
        transporter_params['z_total_distance'],
        transporter_params['z_slow_distance'],
        transporter_params['z_slow_end_distance'],
        transporter_params['z_slow_speed'],
        transporter_params['z_fast_speed'],
        direction
    )
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Position vs Time
    ax1.plot(time_points, position_points, 'b-', linewidth=2, label=f'Z Position ({direction})')
    
    if direction == "up":
        ax1.axhline(y=0, color='g', linestyle='--', alpha=0.7, label='Start: 0 mm')
        ax1.axhline(y=transporter_params['z_total_distance'], color='r', linestyle='--', alpha=0.7, 
                   label=f'End: {transporter_params["z_total_distance"]} mm')
    else:
        ax1.axhline(y=transporter_params['z_total_distance'], color='g', linestyle='--', alpha=0.7, 
                   label=f'Start: {transporter_params["z_total_distance"]} mm')
        ax1.axhline(y=0, color='r', linestyle='--', alpha=0.7, label='End: 0 mm')
      # Mark phase transitions
    if direction == "up":
        if phase_info['fast_time'] > 0:
            ax1.axvline(x=phase_info['slow_start_time'], color='orange', linestyle=':', alpha=0.7, label='Slow→Fast')
            ax1.axvline(x=phase_info['slow_start_time'] + phase_info['fast_time'], color='purple', linestyle=':', alpha=0.7, label='Fast→Slow')
    else:  # down
        if phase_info['fast_time'] > 0:
            ax1.axvline(x=phase_info['fast_time'], color='purple', linestyle=':', alpha=0.7, label='Fast→Slow')
    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Z Position (mm)')
    ax1.set_title(f'Transporter Vertical Movement: {direction.upper()}')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Speed vs Time
    ax2.plot(time_points, speed_points, 'r-', linewidth=2, label='Z Speed')
    ax2.axhline(y=transporter_params['z_slow_speed'] * (1 if direction == "up" else -1), 
               color='orange', linestyle='--', alpha=0.7, 
               label=f'Slow Speed: {transporter_params["z_slow_speed"]} mm/s')
    ax2.axhline(y=transporter_params['z_fast_speed'] * (1 if direction == "up" else -1), 
               color='purple', linestyle='--', alpha=0.7, 
               label=f'Fast Speed: {transporter_params["z_fast_speed"]} mm/s')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
      # Mark phase transitions
    if direction == "up":
        if phase_info['fast_time'] > 0:
            ax2.axvline(x=phase_info['slow_start_time'], color='orange', linestyle=':', alpha=0.7)
            ax2.axvline(x=phase_info['slow_start_time'] + phase_info['fast_time'], color='purple', linestyle=':', alpha=0.7)
    else:  # down
        if phase_info['fast_time'] > 0:
            ax2.axvline(x=phase_info['fast_time'], color='purple', linestyle=':', alpha=0.7)
    
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Z Speed (mm/s)')
    ax2.set_title(f'Transporter Vertical Speed Profile: {direction.upper()}')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    
    # Save plot
    plot_filename = os.path.join(output_dir, f'transporter_vertical_{direction}.png')
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"✓ Vertical movement visualization saved: {plot_filename}")
      # Print summary
    print(f"\n📊 Vertical Movement Summary ({direction.upper()}):")
    print(f"   Total distance: {phase_info['total_distance']:.1f} mm")
    print(f"   Total time: {phase_info['total_time']:.2f} s")
    
    if direction == "up":
        print(f"   Slow start phase: {phase_info['slow_start_time']:.2f} s ({phase_info['slow_start_distance']:.1f} mm at {transporter_params['z_slow_speed']} mm/s)")
        if phase_info['fast_time'] > 0:
            print(f"   Fast middle phase: {phase_info['fast_time']:.2f} s ({phase_info['fast_distance']:.1f} mm at {transporter_params['z_fast_speed']} mm/s)")
        print(f"   Slow end phase: {phase_info['slow_end_time']:.2f} s ({phase_info['slow_end_distance']:.1f} mm at {transporter_params['z_slow_speed']} mm/s)")
    else:  # down
        if phase_info['fast_time'] > 0:
            print(f"   Fast start phase: {phase_info['fast_time']:.2f} s ({phase_info['fast_distance']:.1f} mm at {transporter_params['z_fast_speed']} mm/s)")
        print(f"   Slow end phase: {phase_info['slow_end_time']:.2f} s ({phase_info['slow_end_distance']:.1f} mm at {transporter_params['z_slow_speed']} mm/s)")
    
    plt.show()
    
    return phase_info

def main():
    """Main function to run vertical transporter movement visualization."""
    
    # Read transporter parameters
    transporters_file = os.path.join("Initialization", "Transporters.csv")
    if not os.path.exists(transporters_file):
        print(f"❌ Error: {transporters_file} not found!")
        return
    
    df_transporters = pd.read_csv(transporters_file)
      # Use first transporter
    if len(df_transporters) == 0:
        print("❌ Error: No transporters found in CSV file!")
        return
    
    transporter = df_transporters.iloc[0]
    transporter_params = {
        'id': transporter['Transporter_id'],
        'z_total_distance': transporter['Z_total_distance (mm)'],
        'z_slow_distance': transporter['Z_slow_distance (mm)'],
        'z_slow_end_distance': transporter['Z_slow_end_distance (mm)'],
        'z_slow_speed': transporter['Z_slow_speed (mm/s)'],
        'z_fast_speed': transporter['Z_fast_speed (mm/s)']
    }
    
    print(f"🏗️  Simulating Transporter Vertical Movement")
    print(f"    Transporter ID: {transporter_params['id']}")
    print(f"    Total Z distance: {transporter_params['z_total_distance']} mm")
    print(f"    Slow start distance (UP): {transporter_params['z_slow_distance']} mm")
    print(f"    Slow end distance (UP): {transporter_params['z_slow_end_distance']} mm")
    print(f"    Slow speed: {transporter_params['z_slow_speed']} mm/s")
    print(f"    Fast speed: {transporter_params['z_fast_speed']} mm/s")
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_dir = os.path.join("output", f"vertical_simulation_{timestamp}")
    
    # Simulate lifting movement
    print(f"\n🔼 Simulating LIFTING movement...")
    lift_info = visualize_vertical_movement(
        transporter_params=transporter_params,
        direction="up",
        output_dir=output_dir
    )
    
    # Simulate lowering movement
    print(f"\n🔽 Simulating LOWERING movement...")
    lower_info = visualize_vertical_movement(
        transporter_params=transporter_params,
        direction="down",
        output_dir=output_dir
    )
    
    # Save movement data to CSV
    print(f"\n💾 Saving movement data...")
      # Calculate lifting data
    time_points_up, position_points_up, speed_points_up, _ = calculate_vertical_movement(
        transporter_params['z_total_distance'],
        transporter_params['z_slow_distance'],
        transporter_params['z_slow_end_distance'],
        transporter_params['z_slow_speed'],
        transporter_params['z_fast_speed'],
        "up"
    )
    
    # Calculate lowering data  
    time_points_down, position_points_down, speed_points_down, _ = calculate_vertical_movement(
        transporter_params['z_total_distance'],
        transporter_params['z_slow_distance'],
        transporter_params['z_slow_end_distance'],
        transporter_params['z_slow_speed'],
        transporter_params['z_fast_speed'],
        "down"
    )
    
    # Save lifting data
    lift_df = pd.DataFrame({
        'Time (s)': time_points_up,
        'Z_Position (mm)': position_points_up,
        'Z_Speed (mm/s)': speed_points_up
    })
    lift_csv = os.path.join(output_dir, 'vertical_movement_lift.csv')
    lift_df.to_csv(lift_csv, index=False)
    print(f"✓ Lifting data saved: {lift_csv}")
    
    # Save lowering data
    lower_df = pd.DataFrame({
        'Time (s)': time_points_down,
        'Z_Position (mm)': position_points_down,
        'Z_Speed (mm/s)': speed_points_down
    })
    lower_csv = os.path.join(output_dir, 'vertical_movement_lower.csv')
    lower_df.to_csv(lower_csv, index=False)
    print(f"✓ Lowering data saved: {lower_csv}")
    
    print(f"\n🎯 Summary:")
    print(f"   Lifting time: {lift_info['total_time']:.2f} s")
    print(f"   Lowering time: {lower_info['total_time']:.2f} s")

if __name__ == "__main__":
    main()
