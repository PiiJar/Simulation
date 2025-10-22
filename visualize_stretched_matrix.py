import os
import pandas as pd
import matplotlib.pyplot as plt
from simulation_logger import get_logger

def visualize_stretched_matrix(output_dir):
    logger = get_logger()
    if logger is None:
        raise RuntimeError("Logger is not initialized. Please initialize logger in main pipeline before calling this function.")
    logger.log_data("Stretched matrix visualization started")
    logs_dir = os.path.join(output_dir, "logs")
    log_file = os.path.join(logs_dir, "simulation_log.csv")
    matrix_file = os.path.join(logs_dir, "line_matrix_stretched.csv")
    stations_file = os.path.join(output_dir, "initialization", "stations.csv")

    for file_path in [matrix_file, stations_file]:
        if not os.path.exists(file_path):
            logger.log_error(f"Required file not found: {file_path}")
            raise FileNotFoundError(f"Required file not found: {file_path}")

    # Read data
    df = pd.read_csv(matrix_file)
    # Pakota kokonaisluvut ohjelma-, vaihe- ja asemakenttiin
    for col in ["Batch", "Treatment_program", "Stage", "Station"]:
        if col in df.columns:
            df[col] = df[col].astype(int)
    # Siirrä x-akselin nollakohta origoon (vähennä pienin EntryTime kaikista ajoista)
    if "EntryTime" in df.columns:
        min_time = df["EntryTime"].min()
        for time_col in ["EntryTime", "ExitTime"]:
            if time_col in df.columns:
                df[time_col] = df[time_col] - min_time
    stations_df = pd.read_csv(stations_file)
    if 'Number' in stations_df.columns:
        stations_df['Number'] = stations_df['Number'].astype(int)
    logger.log_data(f"Loaded stretched matrix: {len(df)} stages, {len(stations_df)} stations")
    
    # X-AKSELI ALKAA AINA NOLLASTA, ei pienimmästä EntryTime:sta
    max_time = df["ExitTime"].max() if "ExitTime" in df.columns else 0
    min_time = 0  # KIINTEÄ NOLLA-ALKUPISTE
    
    # Paging setup - TIIVISTETTY: 5400 sekuntia per sivu
    PAGE_SECONDS = 5400
    n_pages = int(max_time // PAGE_SECONDS) + 1 if max_time > 0 else 1
    all_stations = sorted(stations_df['Number'].tolist())
    station_names = {int(row['Number']): row['Name'] for _, row in stations_df.iterrows()}
    # --- Värit kaikille erille pysyvästi ---
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    all_batches = sorted(df['Batch'].unique())
    batch_color_map = {batch: colors[i % len(colors)] for i, batch in enumerate(all_batches)}
    
    # --- Värit nostimille ---
    transporter_colors = {
        1: '#FF6B6B',  # Punainen
        2: '#4ECDC4',  # Turkoosi  
        3: '#FFB347',  # Oranssi (muutettu paremmin erottuvaksi)
        4: '#96CEB4'   # Vihreä
    }
    output_files = []
    
    for page in range(n_pages):
        # Sivut alkavat aina nollasta: 0-5400, 5400-10800, jne.
        page_start = page * PAGE_SECONDS  # 0, 5400, 10800, ...
        page_end = page_start + PAGE_SECONDS  # 5400, 10800, 16200, ...
        
        fig, ax = plt.subplots(figsize=(16, 10))
        # --- PIIRRETÄÄN NOSTIMEN LIIKKEET TÄMÄN SIVUN AIKAVÄLILLÄ ---
        movement_file = os.path.join(logs_dir, "transporters_movement.csv")
        if os.path.exists(movement_file):
            move_df = pd.read_csv(movement_file)
            # Pakota kokonaisluvut
            for col in ["Transporter", "Batch", "Phase", "Start_Time", "End_Time", "From_Station", "To_Station"]:
                if col in move_df.columns:
                    move_df[col] = move_df[col].astype(int)
            # Filter moves for this page
            move_df_page = move_df[(move_df['Start_Time'] < page_end) & (move_df['End_Time'] > page_start)]
            for _, move in move_df_page.iterrows():
                start_time = int(move['Start_Time'])
                end_time = int(move['End_Time'])
                from_station = int(move['From_Station'])
                to_station = int(move['To_Station'])
                phase = int(move['Phase'])
                transporter_id = int(move['Transporter'])
                
                # Valitse nostinkohtainen väri
                transporter_color = transporter_colors.get(transporter_id, '#888888')
                
                # Kaikki vaiheet piirretään nostinkohtaisella värillä (katkoviiva) - OHENNETTU
                ax.plot([start_time, end_time], [from_station, to_station], 
                       color=transporter_color, linestyle=':', linewidth=1, alpha=0.5, zorder=5)
                
                # Lisää merkit nostamiselle ja laskemiselle  
                if phase == 2 and start_time < end_time:  # Nostaminen
                    mid_time = (start_time + end_time) / 2
                    ax.scatter(mid_time, from_station + 0.08, marker='^', 
                             color=transporter_color, s=32, zorder=8)
                elif phase == 4:  # Laskeminen
                    ax.scatter(start_time, from_station - 0.08, marker='v', 
                             color=transporter_color, s=32, zorder=8)
                

        # Process each batch for this page
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
                # Lasketaan tarvittavat arvot ensin
                station = int(row['Station'])
                entry_time = int(round(row['EntryTime']))
                exit_time = int(round(row['ExitTime']))
                calc_time = int(round(row['CalcTime']))
                batch_int = int(row['Batch']) if 'Batch' in row else int(batch)
                treatment_program = int(row['Treatment_program']) if 'Treatment_program' in row else 0
                stage_int = int(row['Stage']) if 'Stage' in row else 0
                y = station
                # Jos CalcTime == 0 ja Stage == 0 (ensimmäinen vaihe), piirrä vain yksi pallo kuten muiden erien alussa
                if calc_time == 0 and stage_int == 0:
                    ax.plot(entry_time, y, 'o', color=color, markersize=6, alpha=0.8)
                    continue
                station = int(row['Station'])
                entry_time = int(round(row['EntryTime']))
                exit_time = int(round(row['ExitTime']))
                calc_time = int(round(row['CalcTime']))
                batch_int = int(row['Batch']) if 'Batch' in row else int(batch)
                treatment_program = int(row['Treatment_program']) if 'Treatment_program' in row else 0
                stage_int = int(row['Stage']) if 'Stage' in row else 0
                y = station
                if calc_time > 0:
                    total_time_at_station = exit_time - entry_time
                    # Odotusaika (kokonaisaika) - OHENNETTU
                    ax.plot([entry_time, exit_time], [y, y],
                            color=color, linestyle='-', linewidth=3, alpha=0.3)
                    processing_start = exit_time - calc_time
                    processing_end = exit_time
                    # Käsittelyaika - OHENNETTU
                    ax.plot([processing_start, processing_end], [y, y],
                            color=color, linestyle='-', linewidth=3, alpha=0.9)
                    # Käytä samaa logiikkaa kuin generate_matrix_stretched: optimized_programs jos saatavilla
                    optimized_file = os.path.join(output_dir, "optimized_programs", f"Batch_{batch_int:03d}_Treatment_program_{treatment_program:03d}.csv")
                    stretched_file = os.path.join(output_dir, "stretched_programs", f"Batch_{batch_int:03d}_Treatment_program_{treatment_program:03d}.csv")
                    
                    # Valitse optimized jos saatavilla, muuten stretched
                    if os.path.exists(optimized_file):
                        program_file = optimized_file
                    else:
                        program_file = stretched_file
                    min_time_prog = None
                    max_time_prog = None
                    calc_time_prog = None
                    try:
                        prog_df = pd.read_csv(program_file)
                        if 'Stage' in prog_df.columns:
                            prog_df['Stage'] = prog_df['Stage'].astype(int)
                        stage_row = prog_df[prog_df['Stage'] == stage_int]
                        if not stage_row.empty:
                            min_time_prog = int(round(pd.to_timedelta(stage_row.iloc[0]['MinTime']).total_seconds()))
                            max_time_prog = int(round(pd.to_timedelta(stage_row.iloc[0]['MaxTime']).total_seconds()))
                            calc_time_prog = int(round(pd.to_timedelta(stage_row.iloc[0]['CalcTime']).total_seconds()))
                    except Exception as e:
                        min_time_prog = None
                        max_time_prog = None
                        calc_time_prog = None
                    is_last_stage = False
                    try:
                        if not stage_row.empty:
                            idx = stage_row.index[0]
                            is_last_stage = idx == prog_df.index[-1]
                    except Exception:
                        is_last_stage = False
                    if min_time_prog is not None and calc_time_prog is not None and calc_time_prog > min_time_prog:
                        added = int(calc_time_prog - min_time_prog)
                        color_txt = 'green' if calc_time_prog <= max_time_prog else 'red'
                        mid_processing_time = (processing_start + processing_end) / 2
                        # Venytysarvon näyttö poistettu - käytetään vain min/calc/max näyttöä
                    
                    # === UUSI: MinTime - CalcTime - MaxTime tiedot ===
                    if min_time_prog is not None and calc_time_prog is not None and max_time_prog is not None:
                        # Määrittele väri: harmaa jos CalcTime = MinTime, vihreä jos rajojen sisällä, punainen jos ei
                        if calc_time_prog == min_time_prog:
                            time_color = 'gray'
                        elif min_time_prog <= calc_time_prog <= max_time_prog:
                            time_color = 'green'
                        else:
                            time_color = 'red'
                        
                        mid_processing_time = (processing_start + processing_end) / 2
                        
                        # ÄLYKKÄÄMPI TEKSTIN SIJOITTELU: Laske näkyvän osan keskikohta sivun rajojen sisällä
                        visible_start = max(processing_start, page_start)
                        visible_end = min(processing_end, page_start + PAGE_SECONDS)
                        
                        # Jos käsittely näkyy tällä sivulla, sijoita teksti näkyvän osan keskelle
                        if visible_start < visible_end:
                            text_x_position = (visible_start + visible_end) / 2
                            # Näytä min/cal/max kompaktissa muodossa pienemmällä fontilla ja hieman alempana
                            time_text = f"{min_time_prog}/{calc_time_prog}/{max_time_prog}"
                            ax.text(text_x_position, y + 0.15, time_text, 
                                   color=time_color, fontsize=5, ha='center', va='bottom', 
                                   fontweight='normal', alpha=0.8)
                else:
                    ax.plot(entry_time, y, 'o', color=color, markersize=6, alpha=0.8)
                if calc_time > 0:
                    ax.plot(entry_time, y, 'o', color=color, markersize=3, alpha=0.6)
                    ax.plot(exit_time, y, 's', color=color, markersize=3, alpha=0.6)
                prev_station = station
                prev_exit_time = exit_time
        # Set up axes - PIENENNETTY Y-AKSELIN FONTTI
        ax.set_yticks(all_stations)
        ax.set_yticklabels([f"{num}: {station_names.get(num, 'Unknown')}" for num in all_stations], fontsize=8)
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Stations', fontsize=12)
        ax.set_title(f'Stretched Matrix: Batch Timeline (Page {page+1}/{n_pages})', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='both')
        
        # Lisää 5 minuutin (300s) välein pystysuorat apuviivat - KIINTEÄ 5400s SKAALAUS
        ax.set_xticks(range(int(page_start), int(page_start + PAGE_SECONDS) + 1, 300))
        ax.tick_params(axis='x', which='major', length=8)
        
        # KIINTEÄ 5400 sekunnin x-akseli kaikille sivuille
        ax.set_xlim(page_start, page_start + PAGE_SECONDS)
        if all_stations:
            station_margin = (max(all_stations) - min(all_stations)) * 0.05
            ax.set_ylim(min(all_stations) - station_margin, max(all_stations) + station_margin)
        
        # Legend poistettu käyttäjän pyynnöstä
        
        # Save chart for this page
        output_file = os.path.join(logs_dir, f"stretched_matrix_timeline_page_{page+1}.png")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        logger.log_viz(f"Stretched matrix timeline page {page+1} saved: {output_file}")
        output_files.append(output_file)
    logger.log_data("Stretched matrix visualization completed (paged)")
    return output_files
