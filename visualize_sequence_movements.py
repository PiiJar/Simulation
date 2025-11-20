import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from simulation_logger import get_logger
from load_stations_json import load_stations_from_json

def visualize_sequence_movements(output_dir):
    """
    Visualizes transporter movements from 'sequence_transporters_movement.csv'.
    This function is a modified version of visualize_matrix, focused only on
    transporter movements without batch data.
    """
    logger = get_logger()
    if logger is None:
        print("Logger not initialized, using print statements.")
        log_func = print
    else:
        log_func = logger.log_data

    log_func("Sequence movement visualization started")

    logs_dir = os.path.join(output_dir, "logs")
    reports_dir = os.path.join(output_dir, "reports")
    images_dir = os.path.join(reports_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    init_dir = os.path.join(output_dir, "initialization")

    movement_file = os.path.join(logs_dir, "sequence_transporters_movement.csv")
    if not os.path.exists(movement_file):
        message = f"Required file not found: {movement_file}"
        if logger:
            logger.log_error(message)
        else:
            print(f"ERROR: {message}")
        raise FileNotFoundError(message)

    # Read movement data
    move_df = pd.read_csv(movement_file)
    log_func(f"Loaded sequence movements: {len(move_df)} records")

    # Load stations from JSON
    stations_df = load_stations_from_json(init_dir)
    if 'Number' in stations_df.columns:
        stations_df['Number'] = stations_df['Number'].astype(int)
    log_func(f"Loaded {len(stations_df)} stations")

    # X-axis starts at zero
    max_time = move_df["End_Time"].max() if not move_df.empty else 0

    PAGE_SECONDS = 1800
    n_pages = int(max_time // PAGE_SECONDS) + 1 if max_time > 0 else 1
    
    # Create station Y-axis mapping
    station_numbers = sorted(set(stations_df['Number'].dropna().astype(int).tolist()))
    station_to_y = {num: i + 1 for i, num in enumerate(station_numbers)}
    all_stations_y = [station_to_y[num] for num in station_numbers]
    station_names = {int(row['Number']): row.get('Name', '') for _, row in stations_df.iterrows()}

    transporter_colors = {
        1: '#FF6B6B',
        2: '#4ECDC4',
        3: '#FFB347',
        4: '#96CEB4'
    }
    
    output_files = []
    for page in range(n_pages):
        page_start = page * PAGE_SECONDS
        page_end = page_start + PAGE_SECONDS
        fig, ax = plt.subplots(figsize=(16, 10))

        # Filter movements for the current page
        move_df_page = move_df[(move_df['Start_Time'] < page_end) & (move_df['End_Time'] > page_start)].copy()

        for _, move in move_df_page.iterrows():
            start_time = move['Start_Time']
            end_time = move['End_Time']
            from_num = int(move['From_Station'])
            to_num = int(move['To_Station'])
            description = str(move.get('Description', '')).lower()
            transporter_id = int(move['Transporter'])
            
            if from_num not in station_to_y or to_num not in station_to_y:
                continue

            from_y = station_to_y[from_num]
            to_y = station_to_y[to_num]
            color = transporter_colors.get(transporter_id, '#888888')

            if from_num == to_num:  # Stationary actions (Idle, Lifting, Sinking)
                ls, lw, a, z = ':', 1.0, 0.35, 4
                ax.plot([start_time, end_time], [from_y, from_y], color=color, linestyle=ls, linewidth=lw, alpha=a, zorder=z)
                
                # Add arrow markers for lifting and sinking
                if 'lifting' in description and start_time < end_time:
                    mid_time = (start_time + end_time) / 2
                    ax.scatter(mid_time, from_y + 0.08, marker='^', color=color, s=32, zorder=8)
                elif 'sinking' in description and start_time < end_time:
                    mid_time = (start_time + end_time) / 2
                    ax.scatter(mid_time, from_y - 0.08, marker='v', color=color, s=32, zorder=8)
            else:  # Movement
                ls, lw, a, z = ':', 1.2, 0.6, 6
                ax.plot([start_time, end_time], [from_y, to_y], color=color, linestyle=ls, linewidth=lw, alpha=a, zorder=z)

        # Set up axes
        ax.set_yticks(all_stations_y)
        labels = [f"{num}: {station_names.get(num, 'Unknown')}" for num in station_numbers]
        ax.set_yticklabels(labels, fontsize=8)
        
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Stations', fontsize=12)
        ax.set_title(f'Transporter Sequence Movements (Page {page+1}/{n_pages})', fontsize=14)
        ax.grid(True, alpha=0.3, axis='both')

        ax.set_xticks(range(int(page_start), int(page_start + PAGE_SECONDS) + 1, 300))
        ax.tick_params(axis='x', which='major', length=8)
        ax.set_xlim(page_start, page_start + PAGE_SECONDS)
        
        if all_stations_y:
            ax.set_ylim(min(all_stations_y) - 1, max(all_stations_y) + 1)

        # Save chart
        output_file = os.path.join(images_dir, f"sequence_movements_page_{page+1}.png")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        log_func(f"Sequence movement visualization page {page+1} saved: {output_file}")
        output_files.append(output_file)

    log_func("Sequence movement visualization completed.")
    return output_files

if __name__ == '__main__':
    if len(sys.argv) > 1:
        output_dir_arg = sys.argv[1]
        # Initialize a basic logger if the script is run standalone
        from simulation_logger import initialize_logger
        logger = initialize_logger(output_dir_arg)
        visualize_sequence_movements(output_dir_arg)
    else:
        print("Usage: python visualize_sequence_movements.py <output_dir>")
        sys.exit(1)
