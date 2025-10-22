import pandas as pd
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
import numpy as np
from datetime import timedelta

def generate_simulation_report(output_dir):
    """Luo kattavan PDF-raportin simulaatiosta"""
    print("Luodaan simulaatioraportti...")
    
    # Lue tarvittavat tiedostot
    try:
        production_df = pd.read_csv(os.path.join(output_dir, "Initialization", "Production.csv"))
        stations_df = pd.read_csv("Initialization/Stations.csv")
        program_df = pd.read_csv(os.path.join(output_dir, "initialization", "treatment_program_001.csv"))
        
        original_matrix = pd.read_csv(os.path.join(output_dir, "line_matrix_original.csv"))
        updated_matrix = pd.read_csv(os.path.join(output_dir, "line_matrix_updated.csv"))
        
        tasks_stretched = pd.read_csv(os.path.join(output_dir, "Logs", "transporter_tasks_stretched.csv"))
        adjustments = pd.read_csv(os.path.join(output_dir, "logs", "calc_time_adjustments.csv"))
        
        # Yritä lukea päivitettyä Production-tiedostoa
        updated_production_file = os.path.join(output_dir, "Production_updated.csv")
        if os.path.exists(updated_production_file):
            production_updated_df = pd.read_csv(updated_production_file)
        else:
            production_updated_df = production_df
            
    except Exception as e:
        print(f"Virhe tiedostojen lukemisessa: {e}")
        return
    
    # Luo PDF-raportti
    report_file = os.path.join(output_dir, "simulation_report.pdf")
    
    with PdfPages(report_file) as pdf:
        # Sivu 1: Lähtötiedot
        create_input_data_page(pdf, production_df, production_updated_df, stations_df, program_df)
        
        # Sivu 2: Simulaation vertailukuva
        create_comparison_page(pdf, output_dir, original_matrix, updated_matrix)
        
        # Sivu 3: Analyysi ja tilastot
        create_analysis_page(pdf, tasks_stretched, adjustments, original_matrix, updated_matrix, stations_df)
    
    print(f"Raportti luotu: {report_file}")
    return report_file

def create_input_data_page(pdf, production_df, production_updated_df, stations_df, program_df):
    """Page 1: Input Data with proper tables"""
    fig = plt.figure(figsize=(11.7, 8.3))
    fig.suptitle('Simulation Input Data', fontsize=16, fontweight='bold')
    
    # Create 2x2 layout
    gs = fig.add_gridspec(2, 2, hspace=0.4, wspace=0.3)
    
    # 1. Stations table
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.axis('off')
    ax1.set_title('Stations', fontweight='bold', fontsize=12, pad=20)
    
    # Create stations table data
    stations_data = []
    for _, row in stations_df.iterrows():
        stations_data.append([row['Number'], row['Name']])
    
    # Create table
    table1 = ax1.table(cellText=stations_data,
                      colLabels=['Station ID', 'Station Name'],
                      cellLoc='left',
                      loc='upper center',
                      bbox=[0, 0, 1, 1])
    table1.auto_set_font_size(False)
    table1.set_fontsize(9)
    table1.scale(1, 1.5)
    
    # Style the table
    for i in range(len(stations_data) + 1):
        for j in range(2):
            cell = table1[(i, j)]
            if i == 0:  # Header
                cell.set_facecolor('#4CAF50')
                cell.set_text_props(weight='bold', color='white')
            else:
                cell.set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
    
    # 2. Treatment Program table
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis('off')
    ax2.set_title('Treatment Program (001)', fontweight='bold', fontsize=12, pad=20)
    
    # Create station name mapping
    station_names = {row['Number']: row['Name'] for _, row in stations_df.iterrows()}
    
    # Prepare program data with station names
    program_data = []
    for _, row in program_df.head(8).iterrows():  # Show first 8 stages
        min_time = str(timedelta(seconds=pd.to_timedelta(row['MinTime']).total_seconds() if isinstance(row['MinTime'], str) else row['MinTime'])).split('.')[0]
        max_time = str(timedelta(seconds=pd.to_timedelta(row['MaxTime']).total_seconds() if isinstance(row['MaxTime'], str) else row['MaxTime'])).split('.')[0]
        station_name = station_names.get(row['MinStat'], f"Station {row['MinStat']}")
        program_data.append([row['Stage'], station_name, min_time, max_time])
    
    # Create table
    table2 = ax2.table(cellText=program_data,
                      colLabels=['Stage', 'Station', 'Min Time', 'Max Time'],
                      cellLoc='center',
                      loc='upper center',
                      bbox=[0, 0, 1, 1])
    table2.auto_set_font_size(False)
    table2.set_fontsize(8)
    table2.scale(1, 1.5)
    
    # Style the table
    for i in range(len(program_data) + 1):
        for j in range(4):
            cell = table2[(i, j)]
            if i == 0:  # Header
                cell.set_facecolor('#2196F3')
                cell.set_text_props(weight='bold', color='white')
            else:
                cell.set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
    
    if len(program_df) > 8:
        ax2.text(0.5, -0.1, f"... (+{len(program_df)-8} more stages)", 
                ha='center', transform=ax2.transAxes, fontsize=9, style='italic')
    
    # 3. Original Production Schedule
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.axis('off')
    ax3.set_title('Original Production Schedule', fontweight='bold', fontsize=12, pad=20)
    
    prod_data = []
    for _, row in production_df.iterrows():
        prod_data.append([row['Batch'], row['Treatment_program'], row['Start_time']])
    
    table3 = ax3.table(cellText=prod_data,
                      colLabels=['Batch', 'Program', 'Start Time'],
                      cellLoc='center',
                      loc='upper center',
                      bbox=[0, 0, 1, 1])
    table3.auto_set_font_size(False)
    table3.set_fontsize(9)
    table3.scale(1, 1.5)
    
    # Style the table
    for i in range(len(prod_data) + 1):
        for j in range(3):
            cell = table3[(i, j)]
            if i == 0:  # Header
                cell.set_facecolor('#FF9800')
                cell.set_text_props(weight='bold', color='white')
            else:
                cell.set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
    
    # 4. Optimized Production Schedule
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')
    ax4.set_title('Optimized Production Schedule', fontweight='bold', fontsize=12, pad=20)
    
    # Check for changes and prepare data
    opt_data = []
    changes_found = False
    for orig_row, upd_row in zip(production_df.itertuples(), production_updated_df.itertuples()):
        change_text = ""
        if orig_row.Start_time != upd_row.Start_time:
            orig_sec = pd.to_timedelta(orig_row.Start_time).total_seconds()
            upd_sec = pd.to_timedelta(upd_row.Start_time).total_seconds()
            diff = upd_sec - orig_sec
            change_text = f"(+{int(diff)}s)"
            changes_found = True
        
        opt_data.append([upd_row.Batch, upd_row.Treatment_program, upd_row.Start_time, change_text])
    
    table4 = ax4.table(cellText=opt_data,
                      colLabels=['Batch', 'Program', 'Start Time', 'Change'],
                      cellLoc='center',
                      loc='upper center',
                      bbox=[0, 0, 1, 1])
    table4.auto_set_font_size(False)
    table4.set_fontsize(8)
    table4.scale(1, 1.5)
    
    # Style the table
    for i in range(len(opt_data) + 1):
        for j in range(4):
            cell = table4[(i, j)]
            if i == 0:  # Header
                cell.set_facecolor('#9C27B0')
                cell.set_text_props(weight='bold', color='white')
            else:
                # Highlight rows with changes
                if i > 0 and opt_data[i-1][3]:  # Has change
                    cell.set_facecolor('#ffeb3b' if j < 3 else '#ff5722')
                    if j == 3:  # Change column
                        cell.set_text_props(weight='bold', color='white')
                else:
                    cell.set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
    
    if not changes_found:
        ax4.text(0.5, -0.1, "No changes required", 
                ha='center', transform=ax4.transAxes, fontsize=10, 
                style='italic', color='green', weight='bold')
    
    plt.tight_layout()
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

def create_comparison_page(pdf, output_dir, original_matrix, updated_matrix):
    """Page 2: Simulation Comparison Visualization"""
    
    # Load existing comparison image if available
    comparison_image = os.path.join(output_dir, "routes_comparison_clean.png")
    
    if os.path.exists(comparison_image):
        fig, ax = plt.subplots(figsize=(11.7, 8.3))
        
        # Load and display image
        import matplotlib.image as mpimg
        img = mpimg.imread(comparison_image)
        ax.imshow(img)
        ax.axis('off')
        ax.set_title('Production Line Simulation: Original vs Optimized', 
                    fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    else:
        # If no image available, create simple placeholder
        fig, ax = plt.subplots(figsize=(11.7, 8.3))
        ax.text(0.5, 0.5, 'Comparison visualization not available\n\nRun visualize_comparison.py\nto generate comparison chart', 
                ha='center', va='center', fontsize=16, transform=ax.transAxes)
        ax.set_title('Production Line Comparison', fontsize=14, fontweight='bold')
        ax.axis('off')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

def create_analysis_page(pdf, tasks_df, adjustments_df, original_matrix, updated_matrix, stations_df):
    """Page 3: Analysis and Statistics"""
    fig = plt.figure(figsize=(11.7, 8.3))
    
    # Create 2x2 grid
    gs = fig.add_gridspec(2, 2, hspace=0.4, wspace=0.3)
    
    # 1. Production Summary
    ax1 = fig.add_subplot(gs[0, :])  # Span across top
    create_production_summary(ax1, tasks_df, original_matrix, updated_matrix)
    
    # 2. Transporter Load
    ax2 = fig.add_subplot(gs[1, 0])
    create_transporter_load_chart(ax2, tasks_df)
    
    # 3. Station Utilization
    ax3 = fig.add_subplot(gs[1, 1])
    create_station_utilization_chart(ax3, updated_matrix, stations_df, tasks_df)
    
    fig.suptitle('Simulation Analysis and Statistics', fontsize=16, fontweight='bold')
    
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

def create_production_summary(ax, tasks_df, original_matrix, updated_matrix):
    """Production summary with key metrics"""
    ax.set_title('Production Summary', fontweight='bold', fontsize=14)
    ax.axis('off')
    
    # Calculate key metrics
    total_batches = original_matrix['Batch'].nunique()
    
    # Calculate time span between first and last batch
    if len(tasks_df) > 0:
        # Convert time columns to numeric if they're strings
        start_times = pd.to_numeric(tasks_df['StartTime'])
        end_times = pd.to_numeric(tasks_df['EndTime'])
        
        first_batch_start = start_times.min()
        last_batch_end = end_times.max()
        total_sim_time = last_batch_end - first_batch_start
        
        # Calculate takt time (average interval between batches)
        loading_tasks = tasks_df[tasks_df['FromStation'] == 101]
        if len(loading_tasks) > 0:
            batch_starts = pd.to_numeric(loading_tasks['StartTime']).sort_values()
            if len(batch_starts) > 1:
                intervals = batch_starts.diff().dropna()
                avg_takt_time = intervals.mean()
            else:
                avg_takt_time = 0
        else:
            avg_takt_time = 0
        
        # Calculate single batch processing time (from first to last stage)
        batch_process_times = []
        for batch in original_matrix['Batch'].unique():
            batch_stages = updated_matrix[updated_matrix['Batch'] == batch]
            if len(batch_stages) > 0:
                # Convert StartTime and EndTime if they exist
                if 'StartTime' in batch_stages.columns and 'EndTime' in batch_stages.columns:
                    start_time = pd.to_numeric(batch_stages['StartTime']).min()
                    end_time = pd.to_numeric(batch_stages['EndTime']).max()
                    process_time = end_time - start_time
                    batch_process_times.append(process_time)
        
        avg_batch_time = np.mean(batch_process_times) if batch_process_times else 0
        
    else:
        total_sim_time = 0
        avg_takt_time = 0
        avg_batch_time = 0
        first_batch_start = 0
        last_batch_end = 0
    
    # Create summary text in two columns
    col1_metrics = [
        f"Total Batches: {total_batches}",
        f"Simulation Duration: {str(timedelta(seconds=int(total_sim_time))).split('.')[0]}",
        f"Average Takt Time: {str(timedelta(seconds=int(avg_takt_time))).split('.')[0]}"
    ]
    
    col2_metrics = [
        f"Avg. Batch Processing Time: {str(timedelta(seconds=int(avg_batch_time))).split('.')[0]}",
        f"First Batch In: {str(timedelta(seconds=int(first_batch_start))).split('.')[0]}" if len(tasks_df) > 0 else "N/A",
        f"Last Batch Out: {str(timedelta(seconds=int(last_batch_end))).split('.')[0]}" if len(tasks_df) > 0 else "N/A"
    ]
    
    # Display metrics in table format
    summary_data = []
    for i in range(max(len(col1_metrics), len(col2_metrics))):
        row = []
        row.append(col1_metrics[i] if i < len(col1_metrics) else "")
        row.append(col2_metrics[i] if i < len(col2_metrics) else "")
        summary_data.append(row)
    
    table = ax.table(cellText=summary_data,
                    colLabels=['Production Metrics', 'Timing Information'],
                    cellLoc='left',
                    loc='center',
                    bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    
    # Style the table
    for i in range(len(summary_data) + 1):
        for j in range(2):
            cell = table[(i, j)]
            if i == 0:  # Header
                cell.set_facecolor('#607D8B')
                cell.set_text_props(weight='bold', color='white')
            else:
                cell.set_facecolor('#f5f5f5' if i % 2 == 0 else 'white')

def create_transporter_load_chart(ax, tasks_df):
    """Transporter load analysis (percentage only)"""
    ax.set_title('Transporter Utilization', fontweight='bold')
    
    if len(tasks_df) == 0:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
        return
    
    # Calculate transporter activity
    start_times = pd.to_numeric(tasks_df['StartTime'])
    end_times = pd.to_numeric(tasks_df['EndTime'])
    
    total_time = end_times.max() - start_times.min()
    transport_time = (end_times - start_times).sum()
    idle_time = total_time - transport_time
    
    # Calculate percentages
    transport_pct = (transport_time / total_time) * 100
    idle_pct = (idle_time / total_time) * 100
    
    # Pie chart with percentages only
    sizes = [transport_pct, idle_pct]
    labels = ['Active', 'Idle']
    colors = ['#4CAF50', '#FF5722']
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, 
                                     autopct='%1.1f%%', startangle=90)
    
    # Style the text
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

def create_station_utilization_chart(ax, matrix_df, stations_df, tasks_df):
    """Station utilization as percentages"""
    ax.set_title('Station Utilization (%)', fontweight='bold')
    
    if len(matrix_df) == 0 or len(tasks_df) == 0:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
        return
    
    # Calculate total simulation time (first batch in to last batch out)
    start_times = pd.to_numeric(tasks_df['StartTime'])
    end_times = pd.to_numeric(tasks_df['EndTime'])
    total_sim_time = end_times.max() - start_times.min()
    
    # Calculate station usage times
    station_usage = matrix_df.groupby('Station')['CalcTime'].sum()
    
    # Take only processing stations (exclude Loading 101)
    processing_stations = station_usage[station_usage.index != 101].head(8)
    
    if len(processing_stations) == 0:
        ax.text(0.5, 0.5, 'No processing stations', ha='center', va='center', transform=ax.transAxes)
        return
    
    # Get station names
    station_names = {row['Number']: row['Name'] for _, row in stations_df.iterrows()}
    
    # Calculate utilization percentages
    stations = [f"{station}\n{station_names.get(station, f'Station {station}')}" 
               for station in processing_stations.index]
    utilization_pct = [(usage / total_sim_time) * 100 for usage in processing_stations.values]
    
    # Create bar chart
    bars = ax.bar(range(len(stations)), utilization_pct, color='lightblue', edgecolor='navy')
    ax.set_xticks(range(len(stations)))
    ax.set_xticklabels(stations, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Utilization (%)')
    ax.set_ylim(0, max(utilization_pct) * 1.1 if utilization_pct else 100)
    ax.grid(axis='y', alpha=0.3)
    
    # Add percentage values on top of bars
    for bar, value in zip(bars, utilization_pct):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{value:.1f}%', ha='center', va='bottom', fontsize=8, fontweight='bold')

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    generate_simulation_report(output_dir)
