#!/usr/bin/env python3
"""
Transporter Assumed First Task for Batch Simulation

Simuloi nostin ensimmäisen tehtävän erätlle:
- Lähtöpaikka: Linjan keskeltä (4250mm)
- Lift Station: Station 101 (Loading)
- Sink Station: Station 102 (Decreasing) - käsittelyohjelman 001 ensimmäinen asema

Tämä on tyypillinen "batch aloitus" -skenaario.
Tuottaa raporttisivun pääsimulaatioon.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime
from simulation_logger import SimulationLogger

def load_transporters_config():
    """Load transporter configuration from CSV"""
    try:
        config_path = os.path.join("Initialization", "Transporters.csv")
        df = pd.read_csv(config_path)
        return df.iloc[0].to_dict()
    except Exception as e:
        print(f"Error loading transporter config: {e}")
        return None

def load_stations_config():
    """Load stations configuration from CSV"""
    try:
        stations_path = os.path.join("Initialization", "Stations.csv")
        df = pd.read_csv(stations_path)
        return df.set_index('Number').to_dict('index')
    except Exception as e:
        print(f"Error loading stations config: {e}")
        return None

def calculate_horizontal_movement(distance, config):
    """Calculate horizontal movement profile"""
    max_speed = config['Max_speed (mm/s)']
    accel_time = config['Acceleration_time (s)']
    decel_time = config['Deceleration_time (s)']
    
    # Distance during acceleration and deceleration
    accel_dist = 0.5 * max_speed * accel_time
    decel_dist = 0.5 * max_speed * decel_time
    
    total_accel_decel_dist = accel_dist + decel_dist
    
    if distance <= total_accel_decel_dist:
        # Triangular profile
        peak_speed = distance / (0.5 * (accel_time + decel_time))
        actual_accel_time = peak_speed / (max_speed / accel_time)
        actual_decel_time = peak_speed / (max_speed / decel_time)
        total_time = actual_accel_time + actual_decel_time
        profile_type = "Triangular"
        peak_speed_used = peak_speed
    else:
        # Trapezoidal profile
        const_speed_dist = distance - total_accel_decel_dist
        const_speed_time = const_speed_dist / max_speed
        total_time = accel_time + const_speed_time + decel_time
        profile_type = "Trapezoidal"
        peak_speed_used = max_speed
    
    return total_time, profile_type, peak_speed_used

def calculate_vertical_movement(station_type, direction, config):
    """Calculate vertical movement time"""
    z_total = config['Z_total_distance (mm)']
    z_slow_speed = config['Z_slow_speed (mm/s)']
    z_fast_speed = config['Z_fast_speed (mm/s)']
    z_slow_end = config['Z_slow_end_distance (mm)']
    
    if station_type == 0:  # Dry station
        z_slow_start = config['Z_slow_distance_dry (mm)']
    else:  # Wet station
        z_slow_start = config['Z_slow_distance_wet (mm)']
    
    if direction == "up":
        # Up: slow start + fast middle + slow end
        slow_start_time = z_slow_start / z_slow_speed
        fast_distance = z_total - z_slow_start - z_slow_end
        fast_time = fast_distance / z_fast_speed
        slow_end_time = z_slow_end / z_slow_speed
        total_time = slow_start_time + fast_time + slow_end_time
        phases = f"{slow_start_time:.1f}s slow + {fast_time:.1f}s fast + {slow_end_time:.1f}s slow"
    else:  # down
        # Down: fast start + slow end
        fast_distance = z_total - z_slow_start
        fast_time = fast_distance / z_fast_speed
        slow_time = z_slow_start / z_slow_speed
        total_time = fast_time + slow_time
        phases = f"{fast_time:.1f}s fast + {slow_time:.1f}s slow"
    
    return total_time, phases

def simulate_first_batch_task(output_dir=None, logger=None):
    """Simulate the first task for a batch"""
    
    # Load configurations
    config = load_transporters_config()
    stations = load_stations_config()
    
    if not config or not stations:
        if logger:
            logger.log("ERROR", "Failed to load configuration files for first batch task")
        print("❌ Error loading configuration files")
        return None
    
    # Initialize logger if not provided
    if logger is None:
        logger = SimulationLogger(output_dir or "output")    
    logger.log("INFO", "Starting first batch task simulation")
    
    # Define task parameters
    line_center = 4250  # Linjan keskikohta (noin keskelle 500-8000mm)
    lift_station = 101  # Loading
    sink_station = 102  # Decreasing (käsittelyohjelman 001 ensimmäinen)
    
    lift_pos = stations[lift_station]['X Position']
    sink_pos = stations[sink_station]['X Position']
    lift_type = stations[lift_station]['Station_type']
    sink_type = stations[sink_station]['Station_type']
    lift_name = stations[lift_station]['Name']
    sink_name = stations[sink_station]['Name']
    dropping_time = stations[sink_station]['Dropping_Time']
    
    logger.log("INFO", f"Task definition: Center({line_center}mm) → Station {lift_station}({lift_name}) → Station {sink_station}({sink_name})")
    
    print("🏭 First Batch Task Simulation")
    print(f"    Start: Line center at {line_center}mm")
    print(f"    Lift Station: Station {lift_station} ({lift_name}) at {lift_pos}mm (type {lift_type})")
    print(f"    Sink Station: Station {sink_station} ({sink_name}) at {sink_pos}mm (type {sink_type})")
    print("")
      # Phase 1: Move to lift station
    distance1 = abs(lift_pos - line_center)
    time1, profile1, peak1 = calculate_horizontal_movement(distance1, config)
    logger.log("SIMULATION", f"Phase 1 - Move to lift station: {distance1}mm in {time1:.2f}s ({profile1})")
    print(f"🔄 Phase 1: Moving to lift station (Center → {lift_station})")
    print(f"   Distance: {distance1} mm")
    print(f"   Time: {time1:.2f} s")
    print(f"   Profile: {profile1} (peak: {peak1:.1f} mm/s)")
    
    # Phase 2: Lifting at lift station
    time2, phases2 = calculate_vertical_movement(lift_type, "up", config)
    station_type_name = "Dry" if lift_type == 0 else "Wet"
    logger.log("SIMULATION", f"Phase 2 - Lifting at {station_type_name} station: {time2:.2f}s")
    print(f"🔼 Phase 2: Lifting at lift station (Station {lift_station})")
    print(f"   Station type: {station_type_name}")
    print(f"   Time: {time2:.2f} s")
    print(f"   Phases: {phases2}")
    
    # Phase 3: Move to sink station
    distance3 = abs(sink_pos - lift_pos)
    time3, profile3, peak3 = calculate_horizontal_movement(distance3, config)
    logger.log("SIMULATION", f"Phase 3 - Move to sink station: {distance3}mm in {time3:.2f}s ({profile3})")
    print(f"🔄 Phase 3: Moving to sink station ({lift_station} → {sink_station})")
    print(f"   Distance: {distance3} mm")
    print(f"   Time: {time3:.2f} s")
    print(f"   Profile: {profile3} (peak: {peak3:.1f} mm/s)")
    
    # Phase 4: Lowering at sink station
    time4, phases4 = calculate_vertical_movement(sink_type, "down", config)
    station_type_name = "Dry" if sink_type == 0 else "Wet"
    logger.log("SIMULATION", f"Phase 4 - Lowering at {station_type_name} station: {time4:.2f}s")
    print(f"🔽 Phase 4: Lowering at sink station (Station {sink_station})")
    print(f"   Station type: {station_type_name}")
    print(f"   Time: {time4:.2f} s")
    print(f"   Phases: {phases4}")
    
    # Phase 5: Dropping time
    time5 = dropping_time
    logger.log("SIMULATION", f"Phase 5 - Dropping time: {time5}s")
    print(f"⏱️  Phase 5: Dropping time at destination")
    print(f"   Time: {time5} s")
    
    # Calculate totals
    total_time = time1 + time2 + time3 + time4 + time5
    total_horizontal = distance1 + distance3
    total_vertical = config['Z_total_distance (mm)']
    
    print(f"📊 Task Summary:")
    print(f"   Total time: {total_time:.2f} s ({total_time/60:.1f} min)")
    print(f"   Horizontal distance: {total_horizontal} mm")
    print(f"   Vertical distance: {total_vertical} mm")
      # Phase breakdown
    phases_data = [
        ("Move to lift station", time1, time1/total_time*100),
        ("Lifting", time2, time2/total_time*100),
        ("Move to sink station", time3, time3/total_time*100),        ("Lowering", time4, time4/total_time*100),
        ("Dropping", time5, time5/total_time*100)
    ]
    
    print(f"   Phase breakdown:")
    for phase, time, percent in phases_data:
        print(f"     {phase}: {time:.2f} s ({percent:.1f}%)")
    
    # Create output directory if not provided
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        output_dir = os.path.join("output", f"first_batch_task_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Save task summary
    summary_df = pd.DataFrame(phases_data, columns=['Phase', 'Time (s)', 'Percentage'])
    summary_df.loc[len(summary_df)] = ['TOTAL', total_time, 100.0]
    summary_path = os.path.join(output_dir, "first_batch_task_summary.csv")
    summary_df.to_csv(summary_path, index=False)
    
    # Create visualization for report
    create_first_batch_report_page(phases_data, total_time, output_dir, 
                                 line_center, lift_station, sink_station, 
                                 lift_pos, sink_pos, config, 
                                 distance1, time1, profile1, peak1)
    
    logger.log("INFO", f"First batch task report saved to {output_dir}")
    print(f"✓ Two-page report generated:")
    print(f"  Page 1: transporter_analysis_page1.png")
    print(f"  Page 2: task_analysis_page2.png")
    print(f"✓ Task summary saved: {summary_path}")
    
    # Return results for integration
    return {
        'total_time': total_time,
        'phases': phases_data,
        'config': config,
        'distances': [distance1, distance3],
        'output_dir': output_dir
    }

def create_first_batch_report_page(phases_data, total_time, output_dir, 
                                 start_pos, lift_station, sink_station,
                                 lift_pos, sink_pos, config, 
                                 distance1, time1, profile1, peak1):
    """Create comprehensive two-page report for first batch task"""
    
    # Create Page 1: Transporter Analysis
    create_transporter_analysis_page(output_dir, config)
    print(f"✓ Page 1 created: transporter_analysis_page1.png")
    
    # Create Page 2: Task Analysis (current version)
    create_task_analysis_page(phases_data, total_time, output_dir, 
                             start_pos, lift_station, sink_station,
                             lift_pos, sink_pos, config, 
                             distance1, time1, profile1, peak1)
    print(f"✓ Page 2 created: task_analysis_page2.png")

def create_transporter_analysis_page(output_dir, config):
    """Create Page 1: Transporter parameters and movement profiles (landscape)"""
    
    # Use landscape orientation for better space utilization
    fig = plt.figure(figsize=(20, 12))
    fig.suptitle('Transporter Analysis - Movement Profiles & Parameters', 
                 fontsize=24, fontweight='bold', y=0.95)
    
    # Create horizontal layout: table on top, graphs below
    gs = fig.add_gridspec(3, 4, height_ratios=[1.2, 1, 1], width_ratios=[1, 1, 1, 1], 
                         hspace=0.25, wspace=0.2)
    
    # Top section: Transporter Parameters Table (spanning full width, top row)
    ax_table = fig.add_subplot(gs[0, :])
    create_parameter_table_horizontal(ax_table, config)
    
    # Bottom section: 4 movement profile graphs (2x2 grid in remaining space)
    ax1 = fig.add_subplot(gs[1, 0])  # Second row, first column: Long movement
    ax2 = fig.add_subplot(gs[1, 1])  # Second row, second column: Short movement  
    ax3 = fig.add_subplot(gs[1, 2])  # Second row, third column: Dry vertical
    ax4 = fig.add_subplot(gs[1, 3])  # Second row, fourth column: Wet vertical
    
    # Generate movement profiles
    create_long_movement_profile(ax1, config)
    create_short_movement_profile(ax2, config)
    create_dry_vertical_profile(ax3, config)
    create_wet_vertical_profile(ax4, config)
    
    # Add explanatory text box spanning bottom row
    ax_text = fig.add_subplot(gs[2, :])
    ax_text.axis('off')
    
    explanation_text = """
MOVEMENT ANALYSIS SUMMARY

The four graphs above demonstrate key movement scenarios: 🔵 LONG HORIZONTAL: Trapezoidal profile reaching max speed with constant velocity phase  |  🟢 SHORT HORIZONTAL: Triangular profile without reaching max speed  |  🔴 DRY STATION VERTICAL: Precise movements with shorter slow approach distances  |  🟦 WET STATION VERTICAL: Extended slow approach distances for safety and contamination prevention

These movement profiles are optimized for both operational efficiency and safety requirements across different station types and distance scenarios.
    """
    
    ax_text.text(0.5, 0.5, explanation_text, transform=ax_text.transAxes, 
                fontsize=12, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.6", facecolor="#f8f9fa", alpha=0.9,
                         edgecolor="#dee2e6", linewidth=1.5))
    
    plt.tight_layout()
    
    # Save Page 1
    page1_path = os.path.join(output_dir, "transporter_analysis_page1.png")
    plt.savefig(page1_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

def create_task_analysis_page(phases_data, total_time, output_dir, 
                            start_pos, lift_station, sink_station,
                            lift_pos, sink_pos, config, 
                            distance1, time1, profile1, peak1):
    """Create Page 2: Task Analysis (original content)"""
    
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('First Batch Task Analysis - Detailed Timeline & Performance', 
                 fontsize=22, fontweight='bold', y=0.96)
    
    # Create subplot layout
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 1], width_ratios=[1.2, 1, 1],
                         hspace=0.3, wspace=0.25)
    
    # 1. Transporter Parameters Table (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.axis('tight')
    ax1.axis('off')
    ax1.set_title('Key Parameters', fontweight='bold', fontsize=14, pad=15)
    
    params_data = [
        ['Parameter', 'Value', 'Unit'],
        ['Max Speed', f"{config['Max_speed (mm/s)']:,.0f}", 'mm/s'],
        ['Acceleration Time', f"{config['Acceleration_time (s)']:.1f}", 's'],
        ['Deceleration Time', f"{config['Deceleration_time (s)']:.1f}", 's'],
        ['Z Total Distance', f"{config['Z_total_distance (mm)']:,.0f}", 'mm'],
        ['Z Slow Speed', f"{config['Z_slow_speed (mm/s)']:,.0f}", 'mm/s'],
        ['Z Fast Speed', f"{config['Z_fast_speed (mm/s)']:,.0f}", 'mm/s'],
        ['Slow Distance (Dry)', f"{config['Z_slow_distance_dry (mm)']:,.0f}", 'mm'],
        ['Slow Distance (Wet)', f"{config['Z_slow_distance_wet (mm)']:,.0f}", 'mm']
    ]
    
    table1 = ax1.table(cellText=params_data[1:], colLabels=params_data[0],
                      cellLoc='center', loc='center')
    table1.auto_set_font_size(False)
    table1.set_fontsize(10)
    table1.scale(1.1, 1.8)
    
    # Style the table
    for i in range(len(params_data[0])):
        table1[(0, i)].set_facecolor('#2c3e50')
        table1[(0, i)].set_text_props(weight='bold', color='white')
    
    # Right-align value column
    for row in range(1, len(params_data)):
        table1[(row, 1)].set_text_props(ha='right')
    
    # 2. Speed & Position Profile for Long Movement (top middle)
    ax2 = fig.add_subplot(gs[0, 1])
    create_speed_profile_plot(ax2, distance1, config, time1, profile1, peak1)
    ax2.set_title('Speed Profile - Move to Lift Station', fontweight='bold', fontsize=12)
    
    # 3. Position Timeline (top right)
    ax3 = fig.add_subplot(gs[0, 2])
    create_position_timeline(ax3, phases_data, total_time, start_pos, lift_pos, sink_pos, 
                           lift_station, sink_station)
    ax3.set_title('Position Over Time', fontweight='bold', fontsize=12)
    
    # 4. Phase Timeline (middle, spanning all columns)
    ax4 = fig.add_subplot(gs[1, :])
    create_phase_timeline(ax4, phases_data, total_time)
    ax4.set_title('Task Timeline by Phase', fontweight='bold', fontsize=14)
    
    # 5. Task Summary Table (bottom left)
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.axis('tight')
    ax5.axis('off')
    ax5.set_title('Phase Summary', fontweight='bold', fontsize=14, pad=15)
    
    summary_data = [
        ['Phase', 'Time (s)', 'Percentage'],
        *[(phase, f'{time:.2f}', f'{perc:.1f}%') for phase, time, perc in phases_data],
        ['TOTAL', f'{total_time:.2f}', '100.0%']
    ]
    
    table2 = ax5.table(cellText=summary_data[1:], colLabels=summary_data[0],
                      cellLoc='center', loc='center')
    table2.auto_set_font_size(False)
    table2.set_fontsize(10)
    table2.scale(1.1, 1.8)
    
    # Style the table
    for i in range(len(summary_data[0])):
        table2[(0, i)].set_facecolor('#2c3e50')
        table2[(0, i)].set_text_props(weight='bold', color='white')
    
    # Color the total row
    for i in range(len(summary_data[0])):
        table2[(len(summary_data)-1, i)].set_facecolor('#ecf0f1')
        table2[(len(summary_data)-1, i)].set_text_props(weight='bold')
    
    # Right-align numeric columns
    for row in range(1, len(summary_data)):
        table2[(row, 1)].set_text_props(ha='right')
        table2[(row, 2)].set_text_props(ha='right')
    
    # 6. Station Information (bottom middle)
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.axis('tight')
    ax6.axis('off')
    ax6.set_title('Station Information', fontweight='bold', fontsize=14, pad=15)
    
    # Get station types from config
    stations = load_stations_config()
    lift_type_name = "Dry" if stations[lift_station]['Station_type'] == 0 else "Wet"
    sink_type_name = "Dry" if stations[sink_station]['Station_type'] == 0 else "Wet"
    
    station_data = [
        ['Location', 'Position', 'Type'],
        ['Start (Center)', f'{start_pos:,} mm', 'N/A'],
        [f'Lift (St.{lift_station})', f'{lift_pos:,} mm', lift_type_name],
        [f'Sink (St.{sink_station})', f'{sink_pos:,} mm', sink_type_name]
    ]
    
    table3 = ax6.table(cellText=station_data[1:], colLabels=station_data[0],
                      cellLoc='center', loc='center')
    table3.auto_set_font_size(False)
    table3.set_fontsize(10)
    table3.scale(1.1, 1.8)
    
    # Style the table
    for i in range(len(station_data[0])):
        table3[(0, i)].set_facecolor('#2c3e50')
        table3[(0, i)].set_text_props(weight='bold', color='white')
    
    # Right-align position column
    for row in range(1, len(station_data)):
        table3[(row, 1)].set_text_props(ha='right')
    
    # 7. Key Metrics (bottom right)
    ax7 = fig.add_subplot(gs[2, 2])
    ax7.axis('off')
    ax7.set_title('Performance Metrics', fontweight='bold', fontsize=14, pad=15)
    
    total_horizontal = distance1 + abs(sink_pos - lift_pos)
    
    # Find longest and shortest phases
    phase_times = [(phase, time, perc) for phase, time, perc in phases_data]
    longest_phase = max(phase_times, key=lambda x: x[1])
    shortest_phase = min(phase_times, key=lambda x: x[1])
    
    metrics_text = f"""Total Task Time: {total_time:.1f} s ({total_time/60:.1f} min)

Movement Summary:
• Horizontal: {total_horizontal:,} mm
• Vertical: {config['Z_total_distance (mm)']:,.0f} mm

Phase Analysis:
• Longest: {longest_phase[0]} 
  ({longest_phase[2]:.1f}%)
• Shortest: {shortest_phase[0]}
  ({shortest_phase[2]:.1f}%)

Movement Profile: {profile1}
Peak Speed: {peak1:.0f} mm/s

Efficiency Rating: ⭐⭐⭐⭐
"""
    
    ax7.text(0.05, 0.95, metrics_text, transform=ax7.transAxes, fontsize=11,
            verticalalignment='top', 
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#e8f4fd", alpha=0.9,
                     edgecolor="#3498db", linewidth=1.5))
    
    plt.tight_layout()
    
    # Save Page 2
    page2_path = os.path.join(output_dir, "task_analysis_page2.png")
    plt.savefig(page2_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

def create_speed_profile_plot(ax, distance, config, total_time, profile_type, peak_speed):
    """Create speed and position profile plot for horizontal movement"""
    max_speed = config['Max_speed (mm/s)']
    accel_time = config['Acceleration_time (s)']
    decel_time = config['Deceleration_time (s)']
    
    # Create time array
    time_points = np.linspace(0, total_time, 1000)
    speed_points = []
    position_points = []
    current_pos = 0
    
    for i, t in enumerate(time_points):
        if t <= accel_time:
            # Acceleration phase
            speed = (peak_speed / accel_time) * t
            # Position during acceleration: 0.5 * a * t^2
            current_pos = 0.5 * (peak_speed / accel_time) * t**2
        elif t >= total_time - decel_time:
            # Deceleration phase
            speed = peak_speed * (total_time - t) / decel_time
            # Position during deceleration
            t_const = total_time - decel_time - accel_time
            pos_after_accel = 0.5 * peak_speed * accel_time
            pos_after_const = pos_after_accel + peak_speed * t_const
            t_decel = t - (total_time - decel_time)
            current_pos = pos_after_const + peak_speed * t_decel - 0.5 * (peak_speed / decel_time) * t_decel**2
        else:
            # Constant speed phase
            speed = peak_speed
            # Position during constant speed
            pos_after_accel = 0.5 * peak_speed * accel_time
            t_const = t - accel_time
            current_pos = pos_after_accel + peak_speed * t_const
        
        speed_points.append(speed)
        position_points.append(current_pos)
    
    # Create dual-axis plot
    ax2 = ax.twinx()
    
    # Plot speed profile
    line1 = ax.plot(time_points, speed_points, 'b-', linewidth=2, label=f'Speed ({profile_type})')
    ax.fill_between(time_points, speed_points, alpha=0.2, color='blue')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Speed (mm/s)', color='blue')
    ax.tick_params(axis='y', labelcolor='blue')
    ax.grid(True, alpha=0.3)
    
    # Plot position profile
    line2 = ax2.plot(time_points, position_points, 'r-', linewidth=2, label='Position')
    ax2.set_ylabel('Position (mm)', color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    
    # Add annotations
    ax.annotate(f'Peak Speed: {peak_speed:.0f} mm/s', 
                xy=(total_time/2, peak_speed), xytext=(total_time*0.7, peak_speed*1.2),
                arrowprops=dict(arrowstyle='->', color='blue'),
                ha='center', fontweight='bold', color='blue')
    
    ax2.annotate(f'Total Distance: {distance:.0f} mm', 
                xy=(total_time, distance), xytext=(total_time*0.7, distance*0.8),
                arrowprops=dict(arrowstyle='->', color='red'),
                ha='center', fontweight='bold', color='red')
    
    # Combined legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='upper left')

def create_position_timeline(ax, phases_data, total_time, start_pos, lift_pos, sink_pos,
                           lift_station, sink_station):
    """Create position over time plot"""
    # Calculate cumulative times
    phase_times = [phase[1] for phase in phases_data]
    cumulative_times = np.cumsum([0] + phase_times)
    
    # Position changes at each phase transition
    positions = [start_pos, lift_pos, lift_pos, sink_pos, sink_pos, sink_pos]
    times = list(cumulative_times)
    
    # Ensure arrays have same length
    min_len = min(len(times), len(positions))
    times = times[:min_len]
    positions = positions[:min_len]
    
    ax.plot(times, positions, 'o-', linewidth=3, markersize=8, color='green')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('X Position (mm)')
    ax.grid(True, alpha=0.3)
    
    # Add station annotations
    if len(cumulative_times) > 0:
        ax.annotate(f'Start\n({start_pos}mm)', 
                    xy=(0, start_pos), xytext=(total_time*0.1, start_pos+400),
                    arrowprops=dict(arrowstyle='->', color='blue'))
    if len(cumulative_times) > 1:
        ax.annotate(f'Station {lift_station}\n({lift_pos}mm)', 
                    xy=(cumulative_times[1], lift_pos), xytext=(cumulative_times[1], lift_pos+400),
                    arrowprops=dict(arrowstyle='->', color='green'))
    if len(cumulative_times) > 3:
        ax.annotate(f'Station {sink_station}\n({sink_pos}mm)', 
                    xy=(cumulative_times[-1], sink_pos), xytext=(cumulative_times[-1], sink_pos+400),
                    arrowprops=dict(arrowstyle='->', color='red'))

def create_phase_timeline(ax, phases_data, total_time):
    """Create colored phase timeline"""
    colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC']
    
    phases, times, percentages = zip(*phases_data)
    cumulative_times = np.cumsum([0] + list(times))
    
    for i, (phase, time, perc) in enumerate(phases_data):
        ax.barh(0, time, left=cumulative_times[i], 
                color=colors[i], label=f'{phase}: {time:.1f}s ({perc:.1f}%)',
                height=0.5, alpha=0.8)
        
        # Add text in the middle of each bar if it's wide enough
        if time > total_time * 0.08:  # Only add text if bar is wide enough
            ax.text(cumulative_times[i] + time/2, 0, f'{time:.1f}s', 
                   ha='center', va='center', fontweight='bold', fontsize=10)
    
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('')
    ax.set_yticks([])
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_xlim(0, total_time*1.05)

def create_parameter_table(ax, config):
    """Create formatted parameter table with left-aligned text and right-aligned numbers"""
    ax.axis('tight')
    ax.axis('off')
    ax.set_title('Transporter Parameters', fontweight='bold', fontsize=16, pad=25)
    
    # Prepare table data with proper formatting and spacing
    params_data = [
        ['Parameter', 'Value', 'Unit'],
        # Horizontal movement parameters
        ['HORIZONTAL MOVEMENT', '', ''],
        ['  Max Speed', f"{config['Max_speed (mm/s)']:>8,.0f}", 'mm/s'],
        ['  Acceleration Time', f"{config['Acceleration_time (s)']:>8.1f}", 's'],
        ['  Deceleration Time', f"{config['Deceleration_time (s)']:>8.1f}", 's'],
        ['  Min Position', f"{config['Min_x_position']:>8,.0f}", 'mm'],
        ['  Max Position', f"{config['Max_x_Position']:>8,.0f}", 'mm'],
        ['', '', ''],
        # Vertical movement parameters
        ['VERTICAL MOVEMENT', '', ''],
        ['  Total Distance', f"{config['Z_total_distance (mm)']:>8,.0f}", 'mm'],
        ['  Slow Speed', f"{config['Z_slow_speed (mm/s)']:>8,.0f}", 'mm/s'],
        ['  Fast Speed', f"{config['Z_fast_speed (mm/s)']:>8,.0f}", 'mm/s'],
        ['  Slow End Distance', f"{config['Z_slow_end_distance (mm)']:>8,.0f}", 'mm'],
        ['', '', ''],
        # Station-specific parameters
        ['STATION PARAMETERS', '', ''],
        ['  Slow Distance (Dry)', f"{config['Z_slow_distance_dry (mm)']:>8,.0f}", 'mm'],
        ['  Slow Distance (Wet)', f"{config['Z_slow_distance_wet (mm)']:>8,.0f}", 'mm'],
    ]
    
    # Create table
    table = ax.table(cellText=params_data[1:], colLabels=params_data[0],
                    cellLoc='left', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.4, 2.2)
    
    # Style the header
    for i in range(len(params_data[0])):
        table[(0, i)].set_facecolor('#2c3e50')
        table[(0, i)].set_text_props(weight='bold', color='white', fontsize=12)
    
    # Style section headers
    section_rows = [1, 8, 14]  # HORIZONTAL, VERTICAL, STATION rows
    for row in section_rows:
        for col in range(len(params_data[0])):
            table[(row, col)].set_facecolor('#3498db')
            table[(row, col)].set_text_props(weight='bold', color='white', fontsize=11)
    
    # Style empty spacer rows
    spacer_rows = [7, 13]
    for row in spacer_rows:
        for col in range(len(params_data[0])):
            table[(row, col)].set_facecolor('#ecf0f1')
            table[(row, col)].set_height(0.8)
    
    # Right-align value column (parameter values)
    for row in range(1, len(params_data)):
        if row not in section_rows and row not in spacer_rows:
            table[(row, 1)].set_text_props(ha='right', fontfamily='monospace', fontsize=11)
            # Left-align parameter names for better readability
            table[(row, 0)].set_text_props(ha='left', fontsize=11)
            # Center-align units
            table[(row, 2)].set_text_props(ha='center', fontsize=11)
    
    # Add alternating row colors for better readability
    for row in range(1, len(params_data)):
        if row not in section_rows and row not in spacer_rows:
            if (row - 1) % 2 == 0:
                for col in range(len(params_data[0])):
                    table[(row, col)].set_facecolor('#f8f9fa')
            else:
                for col in range(len(params_data[0])):
                    table[(row, col)].set_facecolor('white')

def create_long_movement_profile(ax, config):
    """Create long movement profile (10-15s at max speed)"""
    # Calculate distance for 12s at max speed
    max_speed = config['Max_speed (mm/s)']
    accel_time = config['Acceleration_time (s)']
    decel_time = config['Deceleration_time (s)']
    const_speed_time = 10.0  # Target constant speed time
    
    # Distance calculation
    accel_dist = 0.5 * max_speed * accel_time
    decel_dist = 0.5 * max_speed * decel_time
    const_dist = max_speed * const_speed_time
    total_distance = accel_dist + const_dist + decel_dist
    total_time = accel_time + const_speed_time + decel_time
    
    # Create time and speed arrays
    time_points = np.linspace(0, total_time, 1000)
    speed_points = []
    
    for t in time_points:
        if t <= accel_time:
            speed = (max_speed / accel_time) * t
        elif t <= accel_time + const_speed_time:
            speed = max_speed
        else:
            speed = max_speed * (total_time - t) / decel_time
        speed_points.append(max(0, speed))
    
    # Plot with improved styling
    ax.plot(time_points, speed_points, 'b-', linewidth=2.5, label='Speed Profile')
    ax.fill_between(time_points, speed_points, alpha=0.3, color='#3498db')
    ax.set_title('🔵 Long Movement (Trapezoidal)', fontweight='bold', fontsize=12, pad=10)
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Speed (mm/s)', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add phase labels
    ax.axvline(x=accel_time, color='red', linestyle='--', alpha=0.7, linewidth=1)
    ax.axvline(x=accel_time + const_speed_time, color='red', linestyle='--', alpha=0.7, linewidth=1)
    
    ax.text(accel_time/2, max_speed*0.3, 'Accel', ha='center', fontsize=9, 
            bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.7))
    ax.text(accel_time + const_speed_time/2, max_speed*1.05, 'Constant', ha='center', fontsize=9,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="lightgreen", alpha=0.7))
    ax.text(accel_time + const_speed_time + decel_time/2, max_speed*0.3, 'Decel', ha='center', fontsize=9,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="orange", alpha=0.7))
    
    # Improved stats box
    stats_text = f'Distance: {total_distance:,.0f} mm\nTime: {total_time:.1f} s\nMax Speed: {max_speed:,.0f} mm/s'
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, ha='right', va='top', 
            fontsize=10, bbox=dict(boxstyle="round,pad=0.4", facecolor="#e8f4fd", alpha=0.9,
                                 edgecolor="#3498db", linewidth=1))

def create_short_movement_profile(ax, config):
    """Create short movement profile (triangular, no max speed reached)"""
    max_speed = config['Max_speed (mm/s)']
    accel_time = config['Acceleration_time (s)']
    decel_time = config['Deceleration_time (s)']
    
    # Short distance that creates triangular profile
    short_distance = 800  # mm
    
    # Calculate peak speed for triangular profile
    peak_speed = short_distance / (0.5 * (accel_time + decel_time))
    actual_accel_time = peak_speed / (max_speed / accel_time)
    actual_decel_time = peak_speed / (max_speed / decel_time)
    total_time = actual_accel_time + actual_decel_time
    
    # Create time and speed arrays
    time_points = np.linspace(0, total_time, 1000)
    speed_points = []
    
    for t in time_points:
        if t <= actual_accel_time:
            speed = (peak_speed / actual_accel_time) * t
        else:
            speed = peak_speed * (total_time - t) / actual_decel_time
        speed_points.append(max(0, speed))
    
    # Plot with improved styling
    ax.plot(time_points, speed_points, 'g-', linewidth=2.5, label='Speed Profile')
    ax.fill_between(time_points, speed_points, alpha=0.3, color='#27ae60')
    ax.set_title('🟢 Short Movement (Triangular)', fontweight='bold', fontsize=12, pad=10)
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Speed (mm/s)', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add phase separator
    ax.axvline(x=actual_accel_time, color='red', linestyle='--', alpha=0.7, linewidth=1)
    
    # Add phase labels
    ax.text(actual_accel_time/2, peak_speed*0.3, 'Accel', ha='center', fontsize=9,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.7))
    ax.text(actual_accel_time + actual_decel_time/2, peak_speed*0.3, 'Decel', ha='center', fontsize=9,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="orange", alpha=0.7))
    
    # Show that max speed is not reached
    ax.axhline(y=max_speed, color='red', linestyle=':', alpha=0.5, linewidth=1)
    ax.text(0.02, 0.85, f'Max Speed: {max_speed:,.0f} mm/s', transform=ax.transAxes, 
            fontsize=8, color='red', style='italic')
    
    # Improved stats box
    efficiency = (peak_speed / max_speed) * 100
    stats_text = f'Distance: {short_distance} mm\nTime: {total_time:.1f} s\nPeak Speed: {peak_speed:.0f} mm/s\nEfficiency: {efficiency:.0f}%'
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, ha='right', va='top',
            fontsize=10, bbox=dict(boxstyle="round,pad=0.4", facecolor="#e8f6f0", alpha=0.9,
                                 edgecolor="#27ae60", linewidth=1))

def create_dry_vertical_profile(ax, config):
    """Create dry station vertical movement profile"""
    z_total = config['Z_total_distance (mm)']
    z_slow_speed = config['Z_slow_speed (mm/s)']
    z_fast_speed = config['Z_fast_speed (mm/s)']
    z_slow_start = config['Z_slow_distance_dry (mm)']
    z_slow_end = config['Z_slow_end_distance (mm)']
    
    # Calculate times and distances for UP movement
    slow_start_time = z_slow_start / z_slow_speed
    fast_distance = z_total - z_slow_start - z_slow_end
    fast_time = fast_distance / z_fast_speed
    slow_end_time = z_slow_end / z_slow_speed
    up_total_time = slow_start_time + fast_time + slow_end_time
    
    # Create time and speed arrays for UP movement
    time_points = np.linspace(0, up_total_time, 1000)
    speed_points = []
    
    for t in time_points:
        if t <= slow_start_time:
            speed = z_slow_speed
        elif t <= slow_start_time + fast_time:
            speed = z_fast_speed
        else:
            speed = z_slow_speed
        speed_points.append(speed)
    
    # Plot UP movement
    ax.plot(time_points, speed_points, '#e74c3c', linewidth=2.5, label='Up (Lift)')
    ax.fill_between(time_points, speed_points, alpha=0.3, color='#e74c3c')
    
    # DOWN movement (fast then slow)
    down_fast_distance = z_total - z_slow_start
    down_fast_time = down_fast_distance / z_fast_speed
    down_slow_time = z_slow_start / z_slow_speed
    down_total_time = down_fast_time + down_slow_time
    
    down_time_points = np.linspace(0, down_total_time, 1000)
    down_speed_points = []
    
    for t in down_time_points:
        if t <= down_fast_time:
            speed = -z_fast_speed  # Negative for down
        else:
            speed = -z_slow_speed
        down_speed_points.append(speed)
    
    # Plot DOWN movement
    ax.plot(down_time_points, down_speed_points, '#f39c12', linewidth=2.5, label='Down (Lower)')
    ax.fill_between(down_time_points, down_speed_points, alpha=0.3, color='#f39c12')
    
    ax.set_title('🔴 Dry Station Vertical Movement', fontweight='bold', fontsize=12, pad=10)
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Z Speed (mm/s)', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
    
    # Add phase separators for UP movement
    ax.axvline(x=slow_start_time, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(x=slow_start_time + fast_time, color='red', linestyle='--', alpha=0.5, linewidth=1)
    
    # Phase labels for UP movement
    ax.text(slow_start_time/2, z_fast_speed*0.7, 'Slow\nStart', ha='center', fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.7))
    ax.text(slow_start_time + fast_time/2, z_fast_speed*0.85, 'Fast', ha='center', fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="lightgreen", alpha=0.7))
    ax.text(slow_start_time + fast_time + slow_end_time/2, z_fast_speed*0.7, 'Slow\nEnd', ha='center', fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="orange", alpha=0.7))
    
    # Improved stats box
    stats_text = f'Up: {up_total_time:.1f} s\nDown: {down_total_time:.1f} s\nSlow Start: {z_slow_start} mm\nTotal Height: {z_total:,.0f} mm'
    ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, ha='right', va='bottom',
            fontsize=10, bbox=dict(boxstyle="round,pad=0.4", facecolor="#fdeaea", alpha=0.9,
                                 edgecolor="#e74c3c", linewidth=1))

def create_wet_vertical_profile(ax, config):
    """Create wet station vertical movement profile"""
    z_total = config['Z_total_distance (mm)']
    z_slow_speed = config['Z_slow_speed (mm/s)']
    z_fast_speed = config['Z_fast_speed (mm/s)']
    z_slow_start = config['Z_slow_distance_wet (mm)']  # Different for wet station
    z_slow_end = config['Z_slow_end_distance (mm)']
    
    # Calculate times and distances for UP movement
    slow_start_time = z_slow_start / z_slow_speed
    fast_distance = z_total - z_slow_start - z_slow_end
    fast_time = fast_distance / z_fast_speed
    slow_end_time = z_slow_end / z_slow_speed
    up_total_time = slow_start_time + fast_time + slow_end_time
    
    # Create time and speed arrays for UP movement
    time_points = np.linspace(0, up_total_time, 1000)
    speed_points = []
    
    for t in time_points:
        if t <= slow_start_time:
            speed = z_slow_speed
        elif t <= slow_start_time + fast_time:
            speed = z_fast_speed
        else:
            speed = z_slow_speed
        speed_points.append(speed)
    
    # Plot UP movement
    ax.plot(time_points, speed_points, '#3498db', linewidth=2.5, label='Up (Lift)')
    ax.fill_between(time_points, speed_points, alpha=0.3, color='#3498db')
    
    # DOWN movement (fast then slow)
    down_fast_distance = z_total - z_slow_start
    down_fast_time = down_fast_distance / z_fast_speed
    down_slow_time = z_slow_start / z_slow_speed
    down_total_time = down_fast_time + down_slow_time
    
    down_time_points = np.linspace(0, down_total_time, 1000)
    down_speed_points = []
    
    for t in down_time_points:
        if t <= down_fast_time:
            speed = -z_fast_speed  # Negative for down
        else:
            speed = -z_slow_speed
        down_speed_points.append(speed)
    
    # Plot DOWN movement
    ax.plot(down_time_points, down_speed_points, '#9b59b6', linewidth=2.5, label='Down (Lower)')
    ax.fill_between(down_time_points, down_speed_points, alpha=0.3, color='#9b59b6')
    
    ax.set_title('🟦 Wet Station Vertical Movement', fontweight='bold', fontsize=12, pad=10)
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Z Speed (mm/s)', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=9)
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
    
    # Add phase separators for UP movement
    ax.axvline(x=slow_start_time, color='blue', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(x=slow_start_time + fast_time, color='blue', linestyle='--', alpha=0.5, linewidth=1)
    
    # Phase labels for UP movement
    ax.text(slow_start_time/2, z_fast_speed*0.7, 'Slow\nStart', ha='center', fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.7))
    ax.text(slow_start_time + fast_time/2, z_fast_speed*0.85, 'Fast', ha='center', fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="lightgreen", alpha=0.7))
    ax.text(slow_start_time + fast_time + slow_end_time/2, z_fast_speed*0.7, 'Slow\nEnd', ha='center', fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="orange", alpha=0.7))
    
    # Highlight difference from dry station
    dry_slow_start = config['Z_slow_distance_dry (mm)']
    difference = z_slow_start - dry_slow_start
    
    # Improved stats box with comparison
    stats_text = f'Up: {up_total_time:.1f} s\nDown: {down_total_time:.1f} s\nSlow Start: {z_slow_start} mm\n(+{difference} mm vs Dry)\nTotal Height: {z_total:,.0f} mm'
    ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, ha='right', va='bottom',
            fontsize=10, bbox=dict(boxstyle="round,pad=0.4", facecolor="#eaf4fd", alpha=0.9,
                                 edgecolor="#3498db", linewidth=1))
    
def create_parameter_table_horizontal(ax, config):
    """Create horizontal parameter table optimized for landscape layout"""
    ax.axis('tight')
    ax.axis('off')
    ax.set_title('Transporter Parameters', fontweight='bold', fontsize=18, pad=20)
    
    # Organize parameters in rows for horizontal display
    # Row 1: Horizontal movement parameters
    horizontal_params = [
        ['HORIZONTAL MOVEMENT', '', '', '', '', '', ''],
        ['Max Speed', 'Accel Time', 'Decel Time', 'Min Position', 'Max Position', '', ''],
        [f"{config['Max_speed (mm/s)']:,.0f} mm/s", 
         f"{config['Acceleration_time (s)']:.1f} s", 
         f"{config['Deceleration_time (s)']:.1f} s",
         f"{config['Min_x_position']:,.0f} mm",
         f"{config['Max_x_Position']:,.0f} mm", '', '']
    ]
    
    # Row 2: Vertical movement parameters
    vertical_params = [
        ['VERTICAL MOVEMENT', '', '', '', '', '', ''],
        ['Total Distance', 'Slow Speed', 'Fast Speed', 'Slow End Dist', 'Slow Dry Dist', 'Slow Wet Dist', ''],
        [f"{config['Z_total_distance (mm)']:,.0f} mm",
         f"{config['Z_slow_speed (mm/s)']:,.0f} mm/s",
         f"{config['Z_fast_speed (mm/s)']:,.0f} mm/s", 
         f"{config['Z_slow_end_distance (mm)']:,.0f} mm",
         f"{config['Z_slow_distance_dry (mm)']:,.0f} mm",
         f"{config['Z_slow_distance_wet (mm)']:,.0f} mm", '']
    ]
    
    # Combine all parameters
    all_params = horizontal_params + [['', '', '', '', '', '', '']] + vertical_params
    
    # Create table
    table = ax.table(cellText=all_params, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 2.5)
    
    # Style section headers (rows 0, 3, 4, 7)
    section_header_rows = [0, 4]
    for row in section_header_rows:
        for col in range(7):
            table[(row, col)].set_facecolor('#2c3e50')
            table[(row, col)].set_text_props(weight='bold', color='white', fontsize=12)
    
    # Style parameter name rows (rows 1, 5)
    param_name_rows = [1, 5]
    for row in param_name_rows:
        for col in range(7):
            table[(row, col)].set_facecolor('#3498db')
            table[(row, col)].set_text_props(weight='bold', color='white', fontsize=10)
    
    # Style value rows (rows 2, 6)
    value_rows = [2, 6]
    for row in value_rows:
        for col in range(7):
            table[(row, col)].set_facecolor('#ecf0f1')
            table[(row, col)].set_text_props(fontfamily='monospace', fontsize=10)
    
    # Style spacer row
    for col in range(7):
        table[(3, col)].set_facecolor('#f8f9fa')
        table[(3, col)].set_height(0.5)
      # Hide unused columns for cleaner look
    for row in range(len(all_params)):
        if all_params[row][5] == '' and all_params[row][6] == '':
            table[(row, 5)].set_facecolor('white')
            table[(row, 6)].set_facecolor('white')
            table[(row, 5)].set_alpha(0)
            table[(row, 6)].set_alpha(0)

if __name__ == "__main__":
    simulate_first_batch_task()
