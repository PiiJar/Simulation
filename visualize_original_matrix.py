#!/usr/bin/env python3
"""
visualize_original_matrix.py

Creates a timeline visualization showing batch movements through stations over time.
X-axis: Time (seconds from start)
Y-axis: All stations in the production line
Shows: 
- Batch position at each station over time
- Processing time: EntryTime → ExitTime (käsittely alkaa heti kun erä saapuu)
- No waiting times (ei odotusaikoja)
- Realistic hoist movement visualization with physics-based timing

Author: Simulation Pipeline
Version: 1.0
Date: 2025-06-21
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
from simulation_logger import get_logger


def visualize_original_matrix(output_dir):
    """
    Visualizes original matrix as timeline showing batch movement through stations.
    
    Args:
        output_dir: Path to the simulation output directory
        
    Returns:
        str: Path to saved visualization file
    """
    
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    logger.log_data("Original matrix visualization started")
    # Load required files
    matrix_file = os.path.join(output_dir, "Logs", "line_matrix_original.csv")
    stations_file = os.path.join(output_dir, "Initialization", "Stations.csv")
    
    for file_path in [matrix_file, stations_file]:
        if not os.path.exists(file_path):
            logger.log_error(f"Required file not found: {file_path}")
            print(f"ERROR: Required file not found: {file_path}")
            raise FileNotFoundError(f"Required file not found: {file_path}")
    
    df = pd.read_csv(matrix_file)
    stations_df = pd.read_csv(stations_file)
    logger.log_data(f"Loaded original matrix: {len(df)} stages, {len(stations_df)} stations")
    
    # X-AKSELI ALKAA AINA NOLLASTA, ei pienimmästä EntryTime:sta
    min_time = 0  # KIINTEÄ NOLLA-ALKUPISTE
    max_time = df["ExitTime"].max() if "ExitTime" in df.columns else 0
    
    # Paging setup - TIIVISTETTY: 5400 sekuntia per sivu
    PAGE_SECONDS = 5400
    n_pages = int(max_time // PAGE_SECONDS) + 1 if max_time > 0 else 1
    all_stations = sorted(stations_df['Number'].tolist())
    output_files = []
    
    for page in range(n_pages):
        # Sivut alkavat aina nollasta: 0-5400, 5400-10800, jne.
        page_start = page * PAGE_SECONDS  # 0, 5400, 10800, ...
        page_end = page_start + PAGE_SECONDS  # 5400, 10800, 16200, ...
        
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # Filter data for this page
        df_page = df[(df["EntryTime"] < page_end) & (df["ExitTime"] > page_start)]
        # Process each batch
        batches = sorted(df_page['Batch'].unique())
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        station_names = {row['Number']: row['Name'] for _, row in stations_df.iterrows()}
        for batch_idx, batch in enumerate(batches):
            batch_data = df_page[df_page['Batch'] == batch].sort_values('Stage')
            color = colors[batch_idx % len(colors)]
            if not batch_data.empty:
                start_station = batch_data.iloc[0]['Station']
            else:
                start_station = None
            for i, row in batch_data.iterrows():
                station = row['Station']
                entry_time = row['EntryTime']
                exit_time = row['ExitTime']
                calc_time = row['CalcTime']
                # Only plot if in this page
                if calc_time > 0:
                    # EI ODOTUSAIKOJA: Käsittely alkaa heti kun erä saapuu (EntryTime)
                    processing_start = entry_time  # Käsittely alkaa heti
                    processing_end = exit_time      # Käsittely päättyy ExitTime:ssa
                    ax.plot([processing_start, processing_end], [station, station],
                            color=color, linestyle='-', linewidth=6, alpha=0.9,
                            label=f'Batch {batch}' if row["Stage"] == 1 else "")
                    ax.plot(entry_time, station, 'o', color=color, markersize=4, alpha=0.8)
                    ax.plot(exit_time, station, 's', color=color, markersize=4, alpha=0.8)
                else:
                    ax.plot(entry_time, station, 'o', color=color, markersize=6, alpha=0.8)
        # Set up axes
        ax.set_yticks(all_stations)
        ax.set_yticklabels([f"{num}: {station_names.get(num, 'Unknown')}" for num in all_stations])
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Stations', fontsize=12)
        ax.set_title(f'Original Matrix: Batch Timeline (Page {page+1}/{n_pages})', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='both')
        
        # Lisää 5 minuutin (300s) välein pystysuorat apuviivat - KIINTEÄ 5400s SKAALAUS
        ax.set_xticks(range(int(page_start), int(page_start + PAGE_SECONDS) + 1, 300))
        ax.tick_params(axis='x', which='major', length=8)
        
        # KIINTEÄ 5400 sekunnin x-akseli kaikille sivuille
        ax.set_xlim(page_start, page_start + PAGE_SECONDS)
        station_margin = (max(all_stations) - min(all_stations)) * 0.05
        ax.set_ylim(min(all_stations) - station_margin, max(all_stations) + station_margin)
        
        # Legend poistettu käyttäjän pyynnöstä
        
        # Save chart for this page
        output_file = os.path.join(output_dir, "Logs", f"original_matrix_timeline_page_{page+1}.png")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.log_viz(f"Original matrix timeline page {page+1} saved: {output_file}")
        output_files.append(output_file)
    logger.log_data("Original matrix visualization completed (paged)")
    return output_files
