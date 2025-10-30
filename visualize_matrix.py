import os
import pandas as pd
import matplotlib.pyplot as plt

def visualize_matrix(output_dir):
    logs_dir = os.path.join(output_dir, "logs")
    matrix_file = os.path.join(logs_dir, "line_matrix.csv")
    stations_file = os.path.join(output_dir, "initialization", "stations.csv")
    for file_path in [matrix_file, stations_file]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Required file not found: {file_path}")
    df = pd.read_csv(matrix_file)
    for col in ["Batch", "Treatment_program", "Stage", "Station"]:
        if col in df.columns:
            df[col] = df[col].astype(int)
    if "EntryTime" in df.columns:
        min_time = df["EntryTime"].min()
        for time_col in ["EntryTime", "ExitTime"]:
            if time_col in df.columns:
                df[time_col] = df[time_col] - min_time
    stations_df = pd.read_csv(stations_file)
    if 'Number' in stations_df.columns:
        stations_df['Number'] = stations_df['Number'].astype(int)
    max_time = df["ExitTime"].max() if "ExitTime" in df.columns else 0
    min_time = 0
    PAGE_SECONDS = 5400
    n_pages = int(max_time // PAGE_SECONDS) + 1 if max_time > 0 else 1
    all_stations = sorted(stations_df['Number'].tolist())
    station_names = {int(row['Number']): row['Name'] for _, row in stations_df.iterrows()}
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    all_batches = sorted(df['Batch'].unique())
    batch_color_map = {batch: colors[i % len(colors)] for i, batch in enumerate(all_batches)}
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
        # Draw hoist movements
        movement_file = os.path.join(logs_dir, "transporters_movement.csv")
        if os.path.exists(movement_file):
            move_df = pd.read_csv(movement_file)
            for col in ["Transporter", "Batch", "Phase", "Start_Time", "End_Time", "From_Station", "To_Station"]:
                if col in move_df.columns:
                    move_df[col] = move_df[col].astype(int)
            move_df_page = move_df[(move_df['Start_Time'] < page_end) & (move_df['End_Time'] > page_start)]
            for _, move in move_df_page.iterrows():
                start_time = int(move['Start_Time'])
                end_time = int(move['End_Time'])
                from_station = int(move['From_Station'])
                to_station = int(move['To_Station'])
                phase = int(move['Phase'])
                transporter_id = int(move['Transporter'])
                transporter_color = transporter_colors.get(transporter_id, '#888888')
                ax.plot([start_time, end_time], [from_station, to_station], color=transporter_color, linestyle=':', linewidth=1, alpha=0.5, zorder=5)
                if phase == 2 and start_time < end_time:
                    mid_time = (start_time + end_time) / 2
                    ax.scatter(mid_time, from_station + 0.08, marker='^', color=transporter_color, s=32, zorder=8)
                elif phase == 4:
                    ax.scatter(start_time, from_station - 0.08, marker='v', color=transporter_color, s=32, zorder=8)
        df_page = df[(df["EntryTime"] < page_end) & (df["ExitTime"] > page_start)]
        batches = sorted(df_page['Batch'].unique())
        for batch in batches:
            batch_data = df_page[df_page['Batch'] == batch].sort_values('Stage')
            color = batch_color_map.get(batch, '#1f77b4')
            if not batch_data.empty:
                start_station = int(batch_data.iloc[0]['Station'])
            else:
                start_station = None
            prev_station = start_station
            prev_exit_time = 0
            for i, row in batch_data.iterrows():
                station = int(row['Station'])
                entry_time = int(round(row['EntryTime']))
                exit_time = int(round(row['ExitTime']))
                calc_time = int(round(row['CalcTime'])) if 'CalcTime' in row else 0
                batch_int = int(row['Batch']) if 'Batch' in row else int(batch)
                treatment_program = int(row['Treatment_program']) if 'Treatment_program' in row else 0
                stage_int = int(row['Stage']) if 'Stage' in row else 0
                y = station
                if calc_time == 0 and stage_int == 0:
                    ax.plot(entry_time, y, 'o', color=color, markersize=6, alpha=0.8)
                    continue
                if calc_time > 0:
                    total_time_at_station = exit_time - entry_time
                    ax.plot([entry_time, exit_time], [y, y], color=color, linestyle='-', linewidth=3, alpha=0.3)
                    processing_start = exit_time - calc_time
                    processing_end = exit_time
                    ax.plot([processing_start, processing_end], [y, y], color=color, linestyle='-', linewidth=3, alpha=0.9)
                else:
                    ax.plot(entry_time, y, 'o', color=color, markersize=6, alpha=0.8)
                if calc_time > 0:
                    ax.plot(entry_time, y, 'o', color=color, markersize=3, alpha=0.6)
                    ax.plot(exit_time, y, 's', color=color, markersize=3, alpha=0.6)
                prev_station = station
                prev_exit_time = exit_time
        ax.set_yticks(all_stations)
        ax.set_yticklabels([f"{num}: {station_names.get(num, 'Unknown')}" for num in all_stations], fontsize=8)
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Stations', fontsize=12)
        ax.set_title(f'Stretched Matrix: Batch Timeline (Page {page+1}/{n_pages})', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='both')
        ax.set_xticks(range(int(page_start), int(page_start + PAGE_SECONDS) + 1, 300))
        ax.tick_params(axis='x', which='major', length=8)
        ax.set_xlim(page_start, page_start + PAGE_SECONDS)
        if all_stations:
            station_margin = (max(all_stations) - min(all_stations)) * 0.05
            ax.set_ylim(min(all_stations) - station_margin, max(all_stations) + station_margin)
        output_file = os.path.join(logs_dir, f"matrix_timeline_page_{page+1}.png")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        output_files.append(output_file)
    print(f"Visualized matrix from {matrix_file}, saved {len(output_files)} image(s) to {logs_dir}")
