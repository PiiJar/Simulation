#!/usr/bin/env python3
"""
Transporter Movement Visualization

This script simulates and visualizes the horizontal movement of a transporter
from one position to another, taking into account acceleration, deceleration,
and maximum speed constraints.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

def calculate_transporter_movement(start_pos, end_pos, acceleration_time, deceleration_time, max_speed):
    """
    Calculate the time profile for transporter movement.
    
    Args:
        start_pos (float): Starting position in mm
        end_pos (float): Ending position in mm
        acceleration_time (float): Time to accelerate from 0 to max_speed in seconds
        deceleration_time (float): Time to decelerate from max_speed to 0 in seconds
        max_speed (float): Maximum speed in mm/s
    
    Returns:
        tuple: (time_points, position_points, speed_points, phase_info)
    """
    
    distance = abs(end_pos - start_pos)
    direction = 1 if end_pos > start_pos else -1
    
    # Calculate acceleration and deceleration values from times
    acceleration = max_speed / acceleration_time  # mm/s²
    deceleration = max_speed / deceleration_time  # mm/s²
    
    # Use the original acceleration_time and deceleration_time directly
    t_accel = acceleration_time
    t_decel = deceleration_time
    
    # Distance covered during acceleration and deceleration
    d_accel = 0.5 * acceleration * t_accel**2
    d_decel = 0.5 * deceleration * t_decel**2
    
    # Check if we can reach max speed
    if d_accel + d_decel >= distance:
        # Triangular profile - we don't reach max speed        # Solve for the meeting point
        # d_accel + d_decel = distance
        # 0.5 * a * t_a^2 + 0.5 * d * t_d^2 = distance
        # Where a = max_speed/acceleration_time and d = max_speed/deceleration_time
        # Also: v_max = a * t_a = d * t_d
        # So: t_d = (a/d) * t_a = (deceleration_time/acceleration_time) * t_a
        
        # Substituting: 0.5 * a * t_a^2 + 0.5 * d * (deceleration_time/acceleration_time * t_a)^2 = distance
        combined_factor = 0.5 * acceleration * (1 + (acceleration_time/deceleration_time))
        t_accel_actual = np.sqrt(distance / combined_factor)
        t_decel_actual = (acceleration_time / deceleration_time) * t_accel_actual
        
        peak_speed = acceleration * t_accel_actual
        d_accel_actual = 0.5 * acceleration * t_accel_actual**2
        d_decel_actual = distance - d_accel_actual
        
        t_constant = 0
        d_constant = 0
        
    else:
        # Trapezoidal profile - we reach max speed
        t_accel_actual = t_accel
        t_decel_actual = t_decel
        peak_speed = max_speed
        d_accel_actual = d_accel
        d_decel_actual = d_decel
        d_constant = distance - d_accel_actual - d_decel_actual
        t_constant = d_constant / max_speed
      # Create time and position arrays
    dt = 0.1  # 0.1 second intervals
    total_time = t_accel_actual + t_constant + t_decel_actual
    
    # Create unified time array
    time_points = np.arange(0, total_time + dt, dt)
    position_points = np.zeros_like(time_points)
    speed_points = np.zeros_like(time_points)
    
    for i, t in enumerate(time_points):
        if t <= t_accel_actual:
            # Phase 1: Acceleration
            position_points[i] = start_pos + direction * 0.5 * acceleration * t**2
            speed_points[i] = acceleration * t
        elif t <= t_accel_actual + t_constant:
            # Phase 2: Constant speed
            t_rel = t - t_accel_actual
            position_points[i] = start_pos + direction * (d_accel_actual + peak_speed * t_rel)
            speed_points[i] = peak_speed
        else:
            # Phase 3: Deceleration
            t_rel = t - t_accel_actual - t_constant
            position_points[i] = start_pos + direction * (d_accel_actual + d_constant + peak_speed * t_rel - 0.5 * deceleration * t_rel**2)
            speed_points[i] = peak_speed - deceleration * t_rel
    
    # Phase information
    phase_info = {
        'total_time': t_accel_actual + t_constant + t_decel_actual,
        'accel_time': t_accel_actual,
        'constant_time': t_constant,
        'decel_time': t_decel_actual,
        'peak_speed': peak_speed,
        'accel_distance': d_accel_actual,
        'constant_distance': d_constant,
        'decel_distance': d_decel_actual,
        'total_distance': distance
    }
    
    return time_points, position_points, speed_points, phase_info

def visualize_transporter_movement(start_pos, end_pos, transporter_params, output_dir=None):
    """
    Create visualization of transporter movement.
    
    Args:
        start_pos (float): Starting position in mm
        end_pos (float): Ending position in mm
        transporter_params (dict): Transporter parameters
        output_dir (str): Output directory for saving plots
    """
    
    if output_dir is None:
        output_dir = "output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate movement
    time_points, position_points, speed_points, phase_info = calculate_transporter_movement(
        start_pos, end_pos,
        transporter_params['acceleration_time'],
        transporter_params['deceleration_time'],
        transporter_params['max_speed']
    )
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Position vs Time
    ax1.plot(time_points, position_points, 'b-', linewidth=2, label='Position')
    ax1.axhline(y=start_pos, color='g', linestyle='--', alpha=0.7, label=f'Start: {start_pos} mm')
    ax1.axhline(y=end_pos, color='r', linestyle='--', alpha=0.7, label=f'End: {end_pos} mm')
    
    # Mark phase transitions
    if phase_info['constant_time'] > 0:
        ax1.axvline(x=phase_info['accel_time'], color='orange', linestyle=':', alpha=0.7, label='Accel→Constant')
        ax1.axvline(x=phase_info['accel_time'] + phase_info['constant_time'], color='purple', linestyle=':', alpha=0.7, label='Constant→Decel')
    else:
        ax1.axvline(x=phase_info['accel_time'], color='orange', linestyle=':', alpha=0.7, label='Accel→Decel')
    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Position (mm)')
    ax1.set_title(f'Transporter Movement: {start_pos} mm → {end_pos} mm')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Speed vs Time
    ax2.plot(time_points, speed_points, 'r-', linewidth=2, label='Speed')
    ax2.axhline(y=transporter_params['max_speed'], color='orange', linestyle='--', alpha=0.7, label=f'Max Speed: {transporter_params["max_speed"]} mm/s')
    
    # Mark phase transitions
    if phase_info['constant_time'] > 0:
        ax2.axvline(x=phase_info['accel_time'], color='orange', linestyle=':', alpha=0.7)
        ax2.axvline(x=phase_info['accel_time'] + phase_info['constant_time'], color='purple', linestyle=':', alpha=0.7)
    else:
        ax2.axvline(x=phase_info['accel_time'], color='orange', linestyle=':', alpha=0.7)
    
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Speed (mm/s)')
    ax2.set_title('Transporter Speed Profile')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    
    # Save plot
    plot_filename = os.path.join(output_dir, f'transporter_movement_{start_pos}_to_{end_pos}.png')
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"✓ Movement visualization saved: {plot_filename}")
    
    # Print summary
    print(f"\n📊 Movement Summary:")
    print(f"   Distance: {phase_info['total_distance']:.1f} mm")
    print(f"   Total time: {phase_info['total_time']:.2f} s")
    print(f"   Peak speed: {phase_info['peak_speed']:.1f} mm/s")
    print(f"   Acceleration phase: {phase_info['accel_time']:.2f} s ({phase_info['accel_distance']:.1f} mm)")
    if phase_info['constant_time'] > 0:
        print(f"   Constant speed phase: {phase_info['constant_time']:.2f} s ({phase_info['constant_distance']:.1f} mm)")
    print(f"   Deceleration phase: {phase_info['decel_time']:.2f} s ({phase_info['decel_distance']:.1f} mm)")
    
    plt.show()
    
    return phase_info

def main():
    """Main function to run transporter movement visualization."""
    
    # Read transporter parameters
    transporters_file = os.path.join("Initialization", "Transporters.csv")
    if not os.path.exists(transporters_file):
        print(f"❌ Error: {transporters_file} not found!")
        return
    
    df_transporters = pd.read_csv(transporters_file)
      # Use first transporter    if len(df_transporters) == 0:
        print("❌ Error: No transporters found in CSV file!")
        return
    
    transporter = df_transporters.iloc[0]
    transporter_params = {
        'id': transporter['Transporter_id'],
        'acceleration_time': transporter['Acceleration_time (s)'],
        'deceleration_time': transporter['Deceleration_time (s)'],
        'max_speed': transporter['Max_speed (mm/s)']
    }
    
    print(f"🏗️  Simulating Transporter Movement")
    print(f"    Transporter ID: {transporter_params['id']}")
    print(f"    Acceleration time: {transporter_params['acceleration_time']} s")
    print(f"    Deceleration time: {transporter_params['deceleration_time']} s")
    print(f"    Max Speed: {transporter_params['max_speed']} mm/s")
    print(f"    Movement: 500 mm → 700 mm (Very short distance test)")
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_dir = os.path.join("output", f"transporter_very_short_simulation_{timestamp}")
    
    # Simulate movement from 500 to 700 (very short distance)
    phase_info = visualize_transporter_movement(
        start_pos=500,
        end_pos=700,
        transporter_params=transporter_params,
        output_dir=output_dir
    )    # Save movement data to CSV
    time_points, position_points, speed_points, _ = calculate_transporter_movement(
        500, 700,
        transporter_params['acceleration_time'],
        transporter_params['deceleration_time'],
        transporter_params['max_speed']
    )
    
    movement_df = pd.DataFrame({
        'Time (s)': time_points,
        'Position (mm)': position_points,
        'Speed (mm/s)': speed_points
    })
    
    csv_filename = os.path.join(output_dir, 'movement_data.csv')
    movement_df.to_csv(csv_filename, index=False)
    print(f"✓ Movement data saved: {csv_filename}")

if __name__ == "__main__":
    main()
