#!/usr/bin/env python3
"""
visualize_hoist_movement.py

Creates a detailed visualization showing hoist and batch movements over time.
Shows both batch processing at stations and hoist transport movements.

X-axis: Time (seconds from start)  
Y-axis: Station numbers (all line stations)
Shows: 
- Batch processing periods (colored bars)
- Hoist movement paths (arrows)
- Current position markers

Author: Simulation Pipeline  
Version: 1.0
Date: 2025-06-21
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime


def log_event(log_file, event_type, description):
    """Add event to simulation log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, 'a', encoding='utf-8', newline='') as f:
        f.write(f"{timestamp},{event_type},{description}\n")


def visualize_hoist_movement(output_dir):
    """
    Creates detailed hoist and batch movement visualization.
    
    Args:
        output_dir: Path to the simulation output directory
        
    Returns:
        str: Path to saved visualization file
    """
    
    # Set up logging
    log_file = os.path.join(output_dir, "Logs", "simulation_log.csv")
    
    print(f"Creating hoist movement visualization...")
    log_event(log_file, "VISUAL", "Started creating hoist movement visualization")
    
    # Load required files
    matrix_file = os.path.join(output_dir, "Logs", "line_matrix_original.csv")
    stations_file = os.path.join(output_dir, "Initialization", "Stations.csv")
    
    for file_path in [matrix_file, stations_file]:
        if not os.path.exists(file_path):
            error_msg = f"Required file not found: {file_path}"
            print(f"ERROR: {error_msg}")
            log_event(log_file, "VISUAL", f"ERROR: {error_msg}")
            raise FileNotFoundError(error_msg)
    
    # Read data
    df = pd.read_csv(matrix_file)
    stations_df = pd.read_csv(stations_file)
    
    print(f"Loaded matrix with {len(df)} stages")
    print(f"Loaded {len(stations_df)} stations")
    log_event(log_file, "VISUAL", f"Loaded matrix: {len(df)} stages, {len(stations_df)} stations")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(18, 12))
    
    # Main timeline plot
    ax1 = plt.subplot(2, 1, 1)
    
    # Get station info
    all_stations = sorted(stations_df['Number'].tolist())
    station_names = {row['Number']: row['Name'] for _, row in stations_df.iterrows()}
    
    print(f"Stations: {all_stations}")
    
    # Process each batch
    batches = sorted(df['Batch'].unique())
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    max_time = 0
    
    for batch_idx, batch in enumerate(batches):
        batch_data = df[df['Batch'] == batch].sort_values('Stage')
        color = colors[batch_idx % len(colors)]
        
        print(f"\nProcessing Batch {batch}:")
        
        # Create timeline for this batch showing station occupation and transfers
        prev_station = None
        prev_exit_time = None
        
        for _, row in batch_data.iterrows():
            station = row['Station']
            entry_time = row['EntryTime']
            exit_time = row['ExitTime']
            calc_time = row['CalcTime']
            stage = row['Stage']
            
            # 1. Draw transfer movement (dashed line) from previous station if exists
            if prev_station is not None and prev_station != station:
                transport_start = prev_exit_time
                transport_end = entry_time
                
                if transport_end > transport_start:  # Valid transport
                    # Draw dashed line for transfer movement
                    ax1.plot([transport_start, transport_end], [prev_station, station], 
                            color=color, linestyle='--', linewidth=3, alpha=0.8,
                            label=f'Batch {batch} Transfer' if prev_station == batch_data.iloc[0]['Station'] else "")
                    
                    # Add transport time label
                    mid_time = (transport_start + transport_end) / 2
                    mid_station = (prev_station + station) / 2
                    transport_time = transport_end - transport_start
                    ax1.text(mid_time, mid_station, f'{transport_time:.1f}s', 
                            ha='center', va='center', fontsize=7, 
                            bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.7))
                    
                    print(f"  Transfer: St{prev_station}→St{station}, {transport_start:.0f}s-{transport_end:.0f}s ({transport_time:.1f}s)")
            
            # 2. Draw processing period (solid line) at station
            if calc_time > 0:  # Only show actual processing time
                # Solid line for processing at station
                ax1.plot([entry_time, exit_time], [station, station], 
                        color=color, linestyle='-', linewidth=6, alpha=0.9,
                        label=f'Batch {batch} Processing' if stage == 1 else "")
                
                # Add stage label
                mid_time = entry_time + calc_time/2
                ax1.text(mid_time, station + 1, f'S{stage}', ha='center', va='bottom', 
                        fontsize=8, fontweight='bold', color=color,
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
                
                print(f"  Processing: Stage {stage} at Station {station}, {entry_time:.0f}s-{exit_time:.0f}s ({calc_time:.0f}s)")
                max_time = max(max_time, exit_time)
            
            # 3. Mark entry/exit points with dots
            if calc_time > 0:
                ax1.plot(entry_time, station, 'o', color=color, markersize=8, alpha=0.9)
                ax1.plot(exit_time, station, 's', color=color, markersize=8, alpha=0.9)
            
            prev_station = station
            prev_exit_time = exit_time
    
    # Set up main plot
    ax1.set_yticks(all_stations)
    ax1.set_yticklabels([f"{num}: {station_names.get(num, 'Unknown')}" for num in all_stations])
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Stations')
    ax1.set_title('Hoist and Batch Movement Timeline', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    if max_time > 0:
        ax1.set_xlim(0, max_time * 1.05)
      # Add legend for batches
    if len(batches) > 1:
        legend_elements = []
        for i, batch in enumerate(batches):
            color = colors[i % len(colors)]
            legend_elements.append(plt.Line2D([0], [0], color=color, linewidth=6, alpha=0.9, label=f'Batch {batch} Processing'))
            legend_elements.append(plt.Line2D([0], [0], color=color, linestyle='--', linewidth=3, alpha=0.8, label=f'Batch {batch} Transfer'))
        ax1.legend(handles=legend_elements, loc='upper right', fontsize=8)
    else:
        # Single batch - show processing/transfer legend
        if len(batches) == 1:
            color = colors[0]
            legend_elements = [
                plt.Line2D([0], [0], color=color, linewidth=6, alpha=0.9, label='Processing at Station'),
                plt.Line2D([0], [0], color=color, linestyle='--', linewidth=3, alpha=0.8, label='Transfer Between Stations')
            ]
            ax1.legend(handles=legend_elements, loc='upper right', fontsize=9)
    
    # Station utilization plot
    ax2 = plt.subplot(2, 1, 2)
    
    # Calculate station utilization
    station_utilization = {}
    total_time = max_time if max_time > 0 else 1
    
    for station in all_stations:
        station_data = df[df['Station'] == station]
        total_processing = station_data['CalcTime'].sum()
        utilization = (total_processing / total_time) * 100 if total_time > 0 else 0
        station_utilization[station] = utilization
    
    # Plot utilization bars
    stations_list = list(station_utilization.keys())
    utilization_list = list(station_utilization.values())
    
    bars = ax2.bar(stations_list, utilization_list, color='skyblue', alpha=0.7, edgecolor='black')
    
    # Add value labels on bars
    for bar, util in zip(bars, utilization_list):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{util:.1f}%', ha='center', va='bottom', fontsize=8)
    
    ax2.set_xlabel('Station Number')
    ax2.set_ylabel('Utilization (%)')
    ax2.set_title('Station Utilization', fontsize=12, fontweight='bold')
    ax2.set_xticks(stations_list)
    ax2.set_xticklabels([f"{num}\n{station_names.get(num, 'Unknown')}" for num in stations_list], fontsize=8)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_ylim(0, max(utilization_list) * 1.1 if utilization_list else 100)
    
    # Save chart
    output_file = os.path.join(output_dir, "Logs", "hoist_movement_visualization.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\nHoist movement visualization saved to: {output_file}")
    log_event(log_file, "VISUAL", f"Hoist movement visualization saved to {os.path.basename(output_file)}")
    
    # Print summary statistics
    print(f"\nSUMMARY STATISTICS:")
    print(f"  Total simulation time: {max_time:.0f}s ({max_time/60:.1f}min)")
    print(f"  Number of batches: {len(batches)}")
    print(f"  Number of stations: {len(all_stations)}")
    print(f"  Station utilization:")
    for station in stations_list:
        print(f"    Station {station} ({station_names.get(station, 'Unknown')}): {station_utilization[station]:.1f}%")
    
    log_event(log_file, "VISUAL", f"Simulation time: {max_time:.0f}s, batches: {len(batches)}, stations: {len(all_stations)}")
    
    return output_file


def main():
    """Main execution function."""
    import sys
    
    print("="*70)
    print("HOIST AND BATCH MOVEMENT VISUALIZATION")
    print("="*70)
    
    # Determine output directory
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        # Find latest simulation folder
        output_base = "output"
        if os.path.exists(output_base):
            subdirs = [d for d in os.listdir(output_base) 
                      if os.path.isdir(os.path.join(output_base, d))]
            if subdirs:
                latest_dir = max(subdirs)
                output_dir = os.path.join(output_base, latest_dir)
            else:
                print("ERROR: No simulation folders found in output/")
                sys.exit(1)
        else:
            print("ERROR: Output directory does not exist")
            sys.exit(1)
    
    # Verify workspace structure
    required_files = [
        os.path.join(output_dir, "Logs", "line_matrix_original.csv"),
        os.path.join(output_dir, "Initialization", "Stations.csv")
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"ERROR: Required file missing: {file_path}")
            sys.exit(1)
    
    try:
        # Create hoist movement visualization
        chart_file = visualize_hoist_movement(output_dir)
        
        print(f"\nHoist movement visualization completed successfully!")
        print(f"Visualization saved to: {chart_file}")
        print(f"Simulation workspace: {output_dir}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
