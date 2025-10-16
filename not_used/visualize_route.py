#!/usr/bin/env python3
"""
visualize_route.py

Creates a route visualization showing how a batch moves between stations over time.
X-axis: Time (seconds from start)
Y-axis: Station numbers (all available stations)
Shows: Batch position and movements between stations

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


def visualize_batch_route(output_dir):
    """
    Visualizes batch route through stations over time.
    
    Args:
        output_dir: Path to the simulation output directory
        
    Returns:
        str: Path to saved visualization file
    """
    
    # Set up logging
    log_file = os.path.join(output_dir, "Logs", "simulation_log.csv")
    
    print(f"Creating route visualization...")
    log_event(log_file, "VISUAL", "Started creating batch route visualization")
    
    # Load matrix file
    matrix_file = os.path.join(output_dir, "Logs", "line_matrix_original.csv")
    if not os.path.exists(matrix_file):
        error_msg = f"Matrix file not found: {matrix_file}"
        print(f"ERROR: {error_msg}")
        log_event(log_file, "VISUAL", f"ERROR: {error_msg}")
        raise FileNotFoundError(error_msg)
    
    # Load stations file
    stations_file = os.path.join(output_dir, "Initialization", "Stations.csv")
    if not os.path.exists(stations_file):
        error_msg = f"Stations file not found: {stations_file}"
        print(f"ERROR: {error_msg}")
        log_event(log_file, "VISUAL", f"ERROR: {error_msg}")
        raise FileNotFoundError(error_msg)
    
    # Read data
    df = pd.read_csv(matrix_file)
    stations_df = pd.read_csv(stations_file)
    
    print(f"Loaded matrix with {len(df)} stages")
    print(f"Loaded {len(stations_df)} stations")
    log_event(log_file, "VISUAL", f"Loaded matrix with {len(df)} stages and {len(stations_df)} stations")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Get all station numbers and sort them
    all_stations = sorted(stations_df['Number'].tolist())
    station_names = {row['Number']: row['Name'] for _, row in stations_df.iterrows()}
    
    print(f"Stations: {all_stations}")
    
    # Process each batch
    batches = sorted(df['Batch'].unique())
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for batch_idx, batch in enumerate(batches):
        batch_data = df[df['Batch'] == batch].sort_values('Stage')
        color = colors[batch_idx % len(colors)]
        
        print(f"\nProcessing Batch {batch}:")
        
        # Collect route points
        times = []
        stations = []
        events = []
        
        for _, row in batch_data.iterrows():
            station = row['Station']
            entry_time = row['EntryTime']
            exit_time = row['ExitTime']
            calc_time = row['CalcTime']
            
            print(f"  Stage {row['Stage']}: Station {station}, {entry_time}s -> {exit_time}s ({calc_time}s)")
            
            # Add entry point
            times.append(entry_time)
            stations.append(station)
            events.append(f"Enter St{station}")
            
            # Add exit point (only if processing time > 0)
            if calc_time > 0:
                times.append(exit_time)
                stations.append(station)
                events.append(f"Exit St{station}")
        
        # Plot the route
        if len(times) > 1:
            # Create line plot showing batch movement
            ax.plot(times, stations, 'o-', color=color, linewidth=2, markersize=6, 
                   label=f'Batch {batch}', alpha=0.8)
            
            # Add arrows to show direction
            for i in range(len(times)-1):
                dx = times[i+1] - times[i]
                dy = stations[i+1] - stations[i]
                if dx > 0:  # Only add arrow if time progresses
                    ax.annotate('', xy=(times[i+1], stations[i+1]), xytext=(times[i], stations[i]),
                               arrowprops=dict(arrowstyle='->', color=color, alpha=0.6, lw=1.5))
            
            # Add time annotations for key points
            for i, (time, station, event) in enumerate(zip(times, stations, events)):
                if i % 2 == 0:  # Only annotate entry points to avoid clutter
                    ax.annotate(f'{time:.0f}s', (time, station), 
                               xytext=(5, 5), textcoords='offset points',
                               fontsize=8, alpha=0.7, color=color)
    
    # Set up axes
    ax.set_yticks(all_stations)
    ax.set_yticklabels([f"{num}: {station_names.get(num, 'Unknown')}" for num in all_stations])
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Stations')
    ax.set_title('Batch Route Through Production Line', fontsize=14, fontweight='bold')
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Add legend
    if len(batches) > 1:
        ax.legend(loc='upper right')
    
    # Set reasonable axis limits
    if len(times) > 0:
        time_margin = (max(times) - min(times)) * 0.05
        ax.set_xlim(min(times) - time_margin, max(times) + time_margin)
    
    station_margin = (max(all_stations) - min(all_stations)) * 0.05
    ax.set_ylim(min(all_stations) - station_margin, max(all_stations) + station_margin)
    
    # Save chart
    output_file = os.path.join(output_dir, "Logs", "batch_route_visualization.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\nRoute visualization saved to: {output_file}")
    log_event(log_file, "VISUAL", f"Route visualization saved to {os.path.basename(output_file)}")
    
    return output_file


def main():
    """Main execution function."""
    import sys
    
    print("="*60)
    print("BATCH ROUTE VISUALIZATION")
    print("="*60)
    
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
        os.path.join(output_dir, "Logs", "simulation_log.csv"),
        os.path.join(output_dir, "Logs", "line_matrix_original.csv"),
        os.path.join(output_dir, "Initialization", "Stations.csv")
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"ERROR: Required file missing: {file_path}")
            sys.exit(1)
    
    try:
        # Create route visualization
        chart_file = visualize_batch_route(output_dir)
        
        print(f"\nRoute visualization completed successfully!")
        print(f"Visualization saved to: {chart_file}")
        print(f"Simulation workspace: {output_dir}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
