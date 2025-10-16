#!/usr/bin/env python3
"""
Very Short Distance Transporter Movement Test

Tests transporter movement for a very short distance (500→700mm = 200mm)
to demonstrate triangular speed profile when max speed is not reached.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

def calculate_transporter_movement(start_pos, end_pos, acceleration_time, deceleration_time, max_speed):
    """
    Calculate the time profile for transporter movement.
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
        # Triangular profile - we don't reach max speed
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
        'total_distance': distance,
        'profile_type': 'Triangular' if t_constant == 0 else 'Trapezoidal'
    }
    
    return time_points, position_points, speed_points, phase_info

def main():
    """Main function."""
    
    # Read transporter parameters
    transporters_file = os.path.join("Initialization", "Transporters.csv")
    if not os.path.exists(transporters_file):
        print(f"❌ Error: {transporters_file} not found!")
        return
    
    df_transporters = pd.read_csv(transporters_file)
    
    if len(df_transporters) == 0:
        print("❌ Error: No transporters found in CSV file!")
        return
    
    transporter = df_transporters.iloc[0]
    
    print(f"🏗️  Very Short Distance Movement Test")
    print(f"    Transporter ID: {transporter['Transporter_id']}")
    print(f"    Acceleration time: {transporter['Acceleration_time (s)']} s")
    print(f"    Deceleration time: {transporter['Deceleration_time (s)']} s")
    print(f"    Max Speed: {transporter['Max_speed (mm/s)']} mm/s")
    print(f"    Movement: 500 mm → 700 mm (200 mm distance)")
    
    # Calculate movement
    time_points, position_points, speed_points, phase_info = calculate_transporter_movement(
        500, 700,
        transporter['Acceleration_time (s)'],
        transporter['Deceleration_time (s)'],
        transporter['Max_speed (mm/s)']
    )
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_dir = os.path.join("output", f"very_short_distance_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Position vs Time
    ax1.plot(time_points, position_points, 'b-', linewidth=2, label='Position')
    ax1.axhline(y=500, color='g', linestyle='--', alpha=0.7, label='Start: 500 mm')
    ax1.axhline(y=700, color='r', linestyle='--', alpha=0.7, label='End: 700 mm')
    
    if phase_info['constant_time'] > 0:
        ax1.axvline(x=phase_info['accel_time'], color='orange', linestyle=':', alpha=0.7, label='Accel→Constant')
        ax1.axvline(x=phase_info['accel_time'] + phase_info['constant_time'], color='purple', linestyle=':', alpha=0.7, label='Constant→Decel')
    else:
        ax1.axvline(x=phase_info['accel_time'], color='orange', linestyle=':', alpha=0.7, label='Accel→Decel')
    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Position (mm)')
    ax1.set_title(f'Very Short Distance Movement: 500 mm → 700 mm ({phase_info["profile_type"]} Profile)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Speed vs Time
    ax2.plot(time_points, speed_points, 'r-', linewidth=2, label='Speed')
    ax2.axhline(y=transporter['Max_speed (mm/s)'], color='orange', linestyle='--', alpha=0.7, 
               label=f'Max Speed: {transporter["Max_speed (mm/s)"]} mm/s')
    ax2.axhline(y=phase_info['peak_speed'], color='purple', linestyle=':', alpha=0.7, 
               label=f'Peak Speed Reached: {phase_info["peak_speed"]:.1f} mm/s')
    
    if phase_info['constant_time'] > 0:
        ax2.axvline(x=phase_info['accel_time'], color='orange', linestyle=':', alpha=0.7)
        ax2.axvline(x=phase_info['accel_time'] + phase_info['constant_time'], color='purple', linestyle=':', alpha=0.7)
    else:
        ax2.axvline(x=phase_info['accel_time'], color='orange', linestyle=':', alpha=0.7)
    
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Speed (mm/s)')
    ax2.set_title(f'Speed Profile: {phase_info["profile_type"]}')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    
    # Save plot
    plot_filename = os.path.join(output_dir, 'very_short_movement.png')
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"✓ Visualization saved: {plot_filename}")
    
    # Print detailed summary
    print(f"\n📊 Movement Analysis:")
    print(f"   Distance: {phase_info['total_distance']:.1f} mm")
    print(f"   Total time: {phase_info['total_time']:.2f} s")
    print(f"   Profile type: {phase_info['profile_type']}")
    print(f"   Peak speed reached: {phase_info['peak_speed']:.1f} mm/s (max: {transporter['Max_speed (mm/s)']} mm/s)")
    print(f"   Speed utilization: {(phase_info['peak_speed']/transporter['Max_speed (mm/s)'])*100:.1f}%")
    print(f"   Acceleration phase: {phase_info['accel_time']:.2f} s ({phase_info['accel_distance']:.1f} mm)")
    if phase_info['constant_time'] > 0:
        print(f"   Constant speed phase: {phase_info['constant_time']:.2f} s ({phase_info['constant_distance']:.1f} mm)")
    else:
        print(f"   No constant speed phase (triangular profile)")
    print(f"   Deceleration phase: {phase_info['decel_time']:.2f} s ({phase_info['decel_distance']:.1f} mm)")
    
    # Save data
    movement_df = pd.DataFrame({
        'Time (s)': time_points,
        'Position (mm)': position_points,
        'Speed (mm/s)': speed_points
    })
    
    csv_filename = os.path.join(output_dir, 'movement_data.csv')
    movement_df.to_csv(csv_filename, index=False)
    print(f"✓ Movement data saved: {csv_filename}")
    
    plt.show()

if __name__ == "__main__":
    main()
