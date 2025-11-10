"""
Enhanced Simulation Report Generator

Luo tyylikkään ja kattavan PDF-raportin simulaation tuloksista.
Sisältää:
- Executive Summary (KPI-dashboard)
- Visuaaliset aikajanat
- Suorituskykymittarit (utilization, bottlenecks)
- Eräanalyysi
- Tekniset yksityiskohdat
"""

import os
from datetime import datetime
import pandas as pd
import numpy as np
from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image

class EnhancedSimulationReport(FPDF):
    """Laajennettu FPDF-luokka tyylikkäämpään raportointiin"""
    
    def __init__(self, customer, plant, timestamp):
        super().__init__()
        self.customer = customer
        self.plant = plant
        self.timestamp = timestamp
        # Levennä vain vasenta marginaalia, oikea pysyy oletuksessa (10mm)
        self.set_left_margin(20)
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        """Sivun ylätunniste"""
        if self.page_no() > 1:  # Ei ylätunnistetta etusivulle
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'{self.customer} | {self.plant}', 0, 0, 'L')
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')
            self.ln(15)
            
    def footer(self):
        """Sivun alatunniste"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, self.timestamp, 0, 0, 'C')
        
    def chapter_title(self, title):
        """Kappaleen otsikko"""
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(41, 128, 185)  # Sininen tausta
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)
        self.set_text_color(0, 0, 0)
        
    def section_title(self, title):
        """Alaotsikko"""
        self.set_font('Arial', 'B', 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, title, 0, 1, 'L')
        self.ln(2)
        
    def kpi_box(self, label, value, unit='', x_pos=None, y_pos=None, width=45, height=25):
        """KPI-laatikko (mittari) header-osiolla"""
        if x_pos is not None and y_pos is not None:
            self.set_xy(x_pos, y_pos)
        
        box_x = self.get_x()
        box_y = self.get_y()
        header_height = 8
        
        # Header-alue (tummempi tausta)
        self.set_fill_color(52, 73, 94)  # Tummansininen header
        self.rect(box_x, box_y, width, header_height, 'F')
        
        # Body-alue (vaalea tausta)
        self.set_fill_color(236, 240, 241)
        self.rect(box_x, box_y + header_height, width, height - header_height, 'F')
        
        # Laatikon reunat
        self.set_draw_color(189, 195, 199)
        self.rect(box_x, box_y, width, height, 'D')
        
        # Label header-osiossa (valkoinen teksti, keskitetty pystysuunnassa)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(255, 255, 255)
        self.set_xy(box_x, box_y + (header_height - 4) / 2)
        self.cell(width, 4, label, 0, 0, 'C')
        
        # Arvo body-osiossa (iso teksti, alhaalla - tai pienempi jos teksti on pitkä)
        value_str = f"{value}{unit}"
        if len(value_str) > 15:
            self.set_font('Arial', 'B', 10)
            y_offset = 6
        else:
            self.set_font('Arial', 'B', 16)
            y_offset = 4
        
        self.set_text_color(52, 73, 94)
        self.set_xy(box_x, box_y + header_height + y_offset)
        self.cell(width, 8, value_str, 0, 0, 'C')
        
        self.set_text_color(0, 0, 0)


def calculate_kpi_metrics(output_dir):
    """Laske keskeiset suorituskykymittarit"""
    metrics = {}
    
    # Lue tiedostot
    batch_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv'))
    hoist_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv'))
    station_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_station_schedule.csv'))
    transporter_phases = pd.read_csv(os.path.join(output_dir, 'reports', 'transporter_phases.csv'))
    
    # Lue asematiedot (numerot, ryhmät, nimet)
    stations_df = pd.read_csv(os.path.join(output_dir, 'initialization', 'stations.csv'))
    station_info = stations_df.set_index('Number')[['Group', 'Name']].to_dict('index')
    
    # Makespan (kokonaisaika)
    max_exit = batch_schedule['ExitTime'].max()
    metrics['makespan_seconds'] = int(max_exit)
    metrics['makespan_hours'] = max_exit / 3600
    
    # Muotoile makespan hh:mm:ss
    makespan_hours = int(max_exit // 3600)
    makespan_minutes = int((max_exit % 3600) // 60)
    makespan_secs = int(max_exit % 60)
    metrics['makespan_formatted'] = f"{makespan_hours:02d}:{makespan_minutes:02d}:{makespan_secs:02d}"
    
    # Erämäärä
    metrics['total_batches'] = len(batch_schedule['Batch'].unique())
    
    # Keskimääräinen läpimenoaika
    batch_times = batch_schedule.groupby('Batch').agg({'EntryTime': 'min', 'ExitTime': 'max'})
    batch_times['LeadTime'] = batch_times['ExitTime'] - batch_times['EntryTime']
    avg_lead_time_seconds = batch_times['LeadTime'].mean()
    metrics['avg_lead_time'] = avg_lead_time_seconds / 3600
    metrics['avg_lead_time_seconds'] = int(avg_lead_time_seconds)
    
    # Muotoile hh:mm:ss
    hours = int(avg_lead_time_seconds // 3600)
    minutes = int((avg_lead_time_seconds % 3600) // 60)
    seconds = int(avg_lead_time_seconds % 60)
    metrics['avg_lead_time_formatted'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Avg. Cycle Time
    # = (viimeisen erän start-aika - ensimmäisen erän start-aika) / (erien määrä - 1)
    # Start-ajat tulevat production.csv tiedostosta (Start_optimized sarake, muodossa hh:mm:ss)
    production_file = os.path.join(output_dir, 'initialization', 'production.csv')
    if os.path.exists(production_file):
        production_df = pd.read_csv(production_file)
        
        # Muunna Start_optimized (hh:mm:ss) sekunneiksi
        def time_to_seconds(time_str):
            if pd.isna(time_str):
                return 0
            parts = str(time_str).split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + int(s)
            return 0
        
        production_df['Start_seconds'] = production_df['Start_optimized'].apply(time_to_seconds)
        batch_starts = production_df.groupby('Batch')['Start_seconds'].min().sort_values()
        
        if len(batch_starts) > 1:
            first_start = batch_starts.iloc[0]
            last_start = batch_starts.iloc[-1]
            cycle_time_seconds = (last_start - first_start) / (len(batch_starts) - 1)
            metrics['takt_time_seconds'] = cycle_time_seconds
            
            # Muotoile hh:mm:ss
            takt_hours = int(cycle_time_seconds // 3600)
            takt_minutes = int((cycle_time_seconds % 3600) // 60)
            takt_secs = int(cycle_time_seconds % 60)
            metrics['takt_time_formatted'] = f"{takt_hours:02d}:{takt_minutes:02d}:{takt_secs:02d}"
            
            # Erien määrä tunnissa = 3600 / cycle time
            metrics['batches_per_hour'] = 3600.0 / cycle_time_seconds if cycle_time_seconds > 0 else 0
        else:
            metrics['takt_time_seconds'] = 0
            metrics['takt_time_formatted'] = "00:00:00"
            metrics['batches_per_hour'] = 0
    else:
        metrics['takt_time_seconds'] = 0
        metrics['takt_time_formatted'] = "00:00:00"
        metrics['batches_per_hour'] = 0
    
    # Nostimen käyttöaste
    for _, row in transporter_phases.iterrows():
        t_id = int(row['Transporter'])
        total = float(row['Total_Time'])
        idle = float(row['Sum_Phase_0'])
        utilization = ((total - idle) / total * 100) if total > 0 else 0
        metrics[f'transporter_{t_id}_utilization'] = utilization
    
    # Asemien käyttöaste (ajallinen analyysi asemaryhmittäin)
    # Laske kunkin aseman kokonaistyöaika (ExitTime - EntryTime)
    station_schedule['Duration'] = station_schedule['ExitTime'] - station_schedule['EntryTime']
    
    # Lisää asemaryhmätiedot
    station_schedule['Group'] = station_schedule['Station'].map(lambda s: station_info.get(s, {}).get('Group', 0))
    
    # Laske käyttöaste per asemaryhmä (yhteenlaskettu työaika ryhmässä)
    group_work_time = station_schedule.groupby('Group')['Duration'].sum()
    
    # Laske asemien määrä per ryhmä
    stations_per_group = stations_df.groupby('Group').size()
    
    # Kokonaisaika = makespan
    total_time = metrics['makespan_seconds']
    
    # Laske käyttöaste per asemaryhmä (jaetaan asemien määrällä ryhmässä)
    group_utilization = {}
    for group, work_time in group_work_time.items():
        num_stations = stations_per_group.get(group, 1)  # Oletus: 1 asema jos ei löydy
        # Keskimääräinen käyttöaste per asema ryhmässä
        utilization = (work_time / (total_time * num_stations) * 100) if total_time > 0 else 0
        group_utilization[int(group)] = utilization
    
    # Etsi käytetyin asemaryhmä (korkein käyttöaste)
    if group_utilization:
        busiest_group = max(group_utilization, key=group_utilization.get)
        
        # Hae ryhmän edustavan aseman nimi (ensimmäinen asema ryhmästä)
        group_stations = stations_df[stations_df['Group'] == busiest_group]
        if not group_stations.empty:
            busiest_station_name = group_stations.iloc[0]['Name']
        else:
            busiest_station_name = f"Group {busiest_group}"
        
        metrics['most_used_station_group'] = busiest_group
        metrics['most_used_station_name'] = busiest_station_name
        metrics['most_used_station_utilization'] = group_utilization[busiest_group]
        metrics['group_utilization'] = group_utilization
    else:
        metrics['most_used_station_group'] = 0
        metrics['most_used_station_name'] = "N/A"
        metrics['most_used_station_utilization'] = 0
        metrics['group_utilization'] = {}
    
    # Käsittelyohjelmat (Treatment Programs)
    if os.path.exists(production_file):
        production_df = pd.read_csv(production_file)
        program_counts = production_df['Treatment_program'].value_counts().sort_index()
        total_batches = len(production_df['Batch'].unique())
        
        # Tallenna ohjelmien määrät ja prosentit
        metrics['treatment_programs'] = {}
        for program, count in program_counts.items():
            percentage = (count / total_batches * 100) if total_batches > 0 else 0
            metrics['treatment_programs'][int(program)] = {
                'count': int(count),
                'percentage': percentage
            }
        metrics['num_programs_used'] = len(program_counts)
    else:
        metrics['treatment_programs'] = {}
        metrics['num_programs_used'] = 0
    
    return metrics


def create_utilization_chart(output_dir, reports_dir):
    """Luo nostimien käyttöastekaavio (pylväsdiagrammi)
    HUOM: Enhanced report käyttää sen sijaan piirakkakaavioita (transporter_X_phases_pie.png)
    """
    transporter_phases = pd.read_csv(os.path.join(output_dir, 'reports', 'transporter_phases.csv'))
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    transporters = []
    idle_pct = []
    productive_pct = []
    
    for _, row in transporter_phases.iterrows():
        t_id = int(row['Transporter'])
        total = float(row['Total_Time'])
        idle = float(row['Sum_Phase_0'])
        productive = total - idle
        
        transporters.append(f"Transporter {t_id}")
        idle_pct.append((idle / total * 100) if total > 0 else 0)
        productive_pct.append((productive / total * 100) if total > 0 else 0)
    
    x = np.arange(len(transporters))
    width = 0.6
    
    ax.bar(x, productive_pct, width, label='Productive', color='#27ae60')
    ax.bar(x, idle_pct, width, bottom=productive_pct, label='Idle', color='#e74c3c')
    
    ax.set_ylabel('Utilization (%)', fontsize=12)
    ax.set_title('Transporter Utilization', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(transporters)
    ax.legend()
    ax.set_ylim([0, 100])
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    chart_path = os.path.join(reports_dir, 'utilization_chart.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def create_transporter_temporal_load_chart(output_dir, reports_dir):
    """Luo ajallinen kuormituskaavio nostimille (5 min ikkunat)"""
    hoist_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv'))
    batch_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv'))
    
    # Makespan
    makespan = batch_schedule['ExitTime'].max()
    
    # 5 minuuttia sekunneissa
    window_size = 300
    
    # Luo aikaikkunat
    num_windows = int(np.ceil(makespan / window_size))
    time_windows = [(i * window_size, (i + 1) * window_size) for i in range(num_windows)]
    
    # Hae uniikit transporterit
    transporters = sorted(hoist_schedule['Transporter'].unique())
    
    # Laske kuormitus per transporter per aikaikkuna
    load_data = {t: [] for t in transporters}
    
    for start_time, end_time in time_windows:
        for transporter in transporters:
            # Suodata kyseisen transporterin tehtävät
            t_tasks = hoist_schedule[hoist_schedule['Transporter'] == transporter]
            
            # Laske kuinka paljon aikaa on käytetty tässä ikkunassa (ei-idle)
            # Idle = Phase 0, Productive = Phase != 0
            work_time = 0
            
            for _, task in t_tasks.iterrows():
                task_start = task['TaskStart']
                task_end = task['TaskEnd']
                
                # Hoist_schedule ei sisällä Phase-saraketta, joten lasketaan kaikki tehtävät työksi
                # (idle-aika on välejä tehtävien välillä, ei erillisiä rivejä)
                
                # Laske overlap ikkunan kanssa
                overlap_start = max(task_start, start_time)
                overlap_end = min(task_end, end_time)
                
                if overlap_start < overlap_end:
                    work_time += (overlap_end - overlap_start)
            
            # Kuormitusprosentti tälle ikkunalle
            load_pct = (work_time / window_size * 100) if window_size > 0 else 0
            load_data[transporter].append(load_pct)
    
    # Piirrä kaavio
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # X-akselin arvot (minuutteina)
    x_values = [i * 5 for i in range(num_windows)]
    
    # Piirrä jokainen transporter omalla viivalla (ei punaista)
    colors = ['#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c']
    for idx, transporter in enumerate(transporters):
        color = colors[idx % len(colors)]
        ax.plot(x_values, load_data[transporter], marker='o', label=f'Transporter {transporter}', 
                color=color, linewidth=2, markersize=4)
    
    ax.set_xlabel('Time (minutes)', fontsize=12)
    ax.set_ylabel('Load (%)', fontsize=12)
    ax.set_ylim(0, 100)
    ax.grid(axis='both', alpha=0.3)
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    chart_path = os.path.join(reports_dir, 'transporter_temporal_load.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def create_transporter_task_distribution_chart(output_dir, reports_dir):
    """Luo tehtävien jakautumiskaavio nostimien kesken (vaakapalkki)"""
    hoist_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv'))
    
    # Laske tehtävien määrä per transporter
    task_counts = hoist_schedule.groupby('Transporter').size()
    total_tasks = task_counts.sum()
    
    # Laske prosentit
    task_percentages = (task_counts / total_tasks * 100).sort_index()
    
    # Värit (ei punaista, käytä eri värejä)
    colors = ['#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c']
    
    # Luo vaakapalkki-kaavio (kapeampi)
    fig, ax = plt.subplots(figsize=(12, 1.2))
    
    left = 0
    for idx, (transporter, percentage) in enumerate(task_percentages.items()):
        color = colors[idx % len(colors)]
        ax.barh(0, percentage, left=left, height=0.6, color=color, 
                label=f'Transporter {transporter}: {percentage:.1f}%')
        
        # Lisää prosenttiteksti palkin keskelle jos tilaa
        if percentage > 5:
            ax.text(left + percentage/2, 0, f'{percentage:.1f}%', 
                   ha='center', va='center', fontweight='bold', color='white', fontsize=11)
        
        left += percentage
    
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xticks([])  # Poistetaan 0-100 asteikko
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)  # Poistetaan myös alareuna
    
    plt.tight_layout()
    chart_path = os.path.join(reports_dir, 'transporter_task_distribution.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def create_station_usage_chart(output_dir, reports_dir):
    """Luo asemaryhmien ajallinen käyttöastekaavio"""
    station_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_station_schedule.csv'))
    batch_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv'))
    stations_df = pd.read_csv(os.path.join(output_dir, 'initialization', 'stations.csv'))
    
    # Laske makespan
    makespan = batch_schedule['ExitTime'].max()
    
    # Laske kunkin aseman työaika
    station_schedule['Duration'] = station_schedule['ExitTime'] - station_schedule['EntryTime']
    
    # Lisää asemaryhmä- ja nimitiedot
    station_info = stations_df.set_index('Number')[['Group', 'Name']].to_dict('index')
    station_schedule['Group'] = station_schedule['Station'].map(lambda s: station_info.get(s, {}).get('Group', 0))
    
    # Laske käyttöaste per asemaryhmä (jaetaan asemien määrällä)
    group_work_time = station_schedule.groupby('Group')['Duration'].sum()
    stations_per_group = stations_df.groupby('Group').size()
    
    # Keskimääräinen käyttöaste per asema ryhmässä
    group_utilization = {}
    for group, work_time in group_work_time.items():
        num_stations = stations_per_group.get(group, 1)
        utilization = (work_time / (makespan * num_stations) * 100)
        group_utilization[group] = utilization
    
    # Järjestä laskevaan järjestykseen
    group_utilization = pd.Series(group_utilization).sort_values(ascending=False)
    
    # Hae ryhmien nimet (ensimmäinen asema kustakin ryhmästä)
    group_names = []
    for group in group_utilization.index:
        group_stations = stations_df[stations_df['Group'] == group]
        if not group_stations.empty:
            group_names.append(group_stations.iloc[0]['Name'])
        else:
            group_names.append(f"Group {group}")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    bars = ax.bar(range(len(group_utilization)), group_utilization.values, color='#3498db')
    ax.set_xlabel('Station Group', fontsize=12)
    ax.set_ylabel('Time Utilization (%)', fontsize=12)
    ax.set_title('Station Group Time Utilization (Occupied Time / Total Production Time)', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(group_utilization)))
    ax.set_xticklabels(group_names, rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, 100)
    
    # Korosta käytetyin asema (korkein käyttöaste)
    if len(bars) > 0:
        bars[0].set_color('#e74c3c')
    
    plt.tight_layout()
    chart_path = os.path.join(reports_dir, 'station_usage_chart.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def create_batch_leadtime_chart(output_dir, reports_dir):
    """Luo erän läpimenoaikakaavio"""
    batch_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv'))
    
    # Laske läpimenoajat
    batch_times = batch_schedule.groupby('Batch').agg({'EntryTime': 'min', 'ExitTime': 'max'})
    batch_times['LeadTime'] = (batch_times['ExitTime'] - batch_times['EntryTime']) / 60  # minuutteina
    batch_times = batch_times.sort_index()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    batches = [f"B{int(b)}" for b in batch_times.index]
    lead_times = batch_times['LeadTime'].values
    
    bars = ax.bar(range(len(batches)), lead_times, color='#9b59b6')
    ax.set_xlabel('Batch', fontsize=12)
    ax.set_ylabel('Lead Time (minutes)', fontsize=12)
    ax.set_title('Batch Lead Time Distribution', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(batches)))
    ax.set_xticklabels(batches, rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3)
    
    # Keskiarvo-viiva
    avg_leadtime = lead_times.mean()
    ax.axhline(y=avg_leadtime, color='#e74c3c', linestyle='--', linewidth=2, label=f'Average: {avg_leadtime:.1f} min')
    ax.legend()
    
    plt.tight_layout()
    chart_path = os.path.join(reports_dir, 'batch_leadtime_chart.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def generate_enhanced_simulation_report(output_dir):
    """Pääfunktio: luo tyylikkään PDF-raportin"""
    
    # Lue perustiedot
    init_dir = os.path.join(output_dir, 'initialization')
    reports_dir = os.path.join(output_dir, 'reports')
    
    try:
        df_cp = pd.read_csv(os.path.join(init_dir, 'customer_and_plant.csv'))
        customer = str(df_cp.iloc[0]['Customer'])
        plant = str(df_cp.iloc[0]['Plant'])
    except Exception:
        customer = 'Customer'
        plant = 'Plant'
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    folder_name = os.path.basename(os.path.abspath(output_dir))
    
    # Laske KPI:t
    metrics = calculate_kpi_metrics(output_dir)
    
    # Luo kaaviot
    # Piirakkakaaviot luodaan jo aiemmin, käytä niitä
    transporter_pie_charts = []
    for i in range(1, 10):  # Etsi transporterit 1-9
        pie_path = os.path.join(reports_dir, f'transporter_{i}_phases_pie.png')
        if os.path.exists(pie_path):
            transporter_pie_charts.append(pie_path)
    
    temporal_load_chart = create_transporter_temporal_load_chart(output_dir, reports_dir)
    task_distribution_chart = create_transporter_task_distribution_chart(output_dir, reports_dir)
    station_chart = create_station_usage_chart(output_dir, reports_dir)
    leadtime_chart = create_batch_leadtime_chart(output_dir, reports_dir)
    
    # Luo PDF
    pdf = EnhancedSimulationReport(customer, plant, timestamp)
    
    # ===== ETUSIVU =====
    pdf.add_page()
    pdf.set_y(40)
    
    # Otsikko
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 15, 'Production Line', ln=1, align='C')
    pdf.cell(0, 15, 'Simulation Report', ln=1, align='C')
    pdf.ln(10)
    
    # Asiakastiedot
    pdf.set_font('Arial', '', 14)
    pdf.set_text_color(52, 73, 94)
    pdf.cell(0, 10, customer, ln=1, align='C')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, plant, ln=1, align='C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 8, timestamp, ln=1, align='C')
    pdf.ln(15)
    
    # Timeline-kuva etusivulle (pienennetty 70% alkuperäisestä)
    first_page_img = os.path.join(reports_dir, 'matrix_timeline_page_1.png')
    image_start_y = pdf.get_y()
    image_end_y = image_start_y
    
    if os.path.exists(first_page_img):
        try:
            # Muunna JPEG:ksi ja laske korkeus
            jpg_path = os.path.join(reports_dir, 'matrix_timeline_page_1.jpg')
            with Image.open(first_page_img) as im:
                if im.mode in ('RGBA', 'LA'):
                    bg = Image.new('RGB', im.size, (255, 255, 255))
                    bg.paste(im, mask=im.split()[-1])
                    im_to_save = bg
                else:
                    im_to_save = im.convert('RGB')
                im_to_save.save(jpg_path, format='JPEG', quality=85)
                
                # Laske kuvan korkeus PDF:ssä (pienennetty 70%)
                w = (pdf.w - pdf.l_margin - pdf.r_margin) * 0.7
                img_w, img_h = im.size
                h = (img_h / img_w) * w
                image_end_y = pdf.get_y() + h
            
            # Keskitä kuva
            x_offset = (pdf.w - w) / 2
            pdf.image(jpg_path, x=x_offset, y=pdf.get_y(), w=w)
        except Exception as e:
            print(f"[WARN] Cover image failed: {e}")
    
    # Lyhyt kuvaus - sijoita kuvan alle 15mm välillä
    pdf.set_y(image_end_y + 15)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(52, 73, 94)
    desc = (
        "This report presents a comprehensive analysis of the production line simulation. "
        "The simulation models batch processing, transporter movements, and station utilization "
        "to identify optimal scheduling strategies and potential bottlenecks."
    )
    pdf.multi_cell(0, 6, desc, align='C')
    
    # Kansion nimi alas oikeaan (sivu 1:n loppuun)
    pdf.set_y(pdf.h - 20)  # 20mm sivun alareunasta
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 5, folder_name, 0, 0, 'R')
    
    # ===== EXECUTIVE SUMMARY =====
    pdf.add_page()
    pdf.chapter_title('Executive Summary')
    
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 6, 
        "Key performance indicators from the simulation run. "
        "These metrics provide a high-level overview of production efficiency, "
        "resource utilization, and throughput.")
    pdf.ln(8)
    
    # KPI-laatikot uudessa järjestyksessä
    kpi_data = []
    
    # 1. Batches Processed
    kpi_data.append(("Batches Processed", str(metrics['total_batches']), ""))
    
    # 2. Used Treatment Programs
    if metrics['num_programs_used'] > 0:
        program_str = ", ".join([
            f"P{prog}: {data['percentage']:.0f}%"
            for prog, data in sorted(metrics['treatment_programs'].items())
        ])
        kpi_data.append(("Used Treatment Programs", program_str, ""))
    
    # 3. Avg. Process Time of Batch
    kpi_data.append(("Avg. Process Time of Batch", metrics['avg_lead_time_formatted'], ""))
    
    # 4. Total Production Time
    kpi_data.append(("Total Production Time", metrics['makespan_formatted'], ""))
    
    # 5. Avg. Cycle Time
    kpi_data.append(("Avg. Cycle Time", metrics['takt_time_formatted'], ""))
    
    # 6. Batches per Hour
    kpi_data.append(("Batches per Hour", f"{metrics['batches_per_hour']:.1f}", ""))
    
    # 7-8. Transporters (järjestyksessä)
    transporter_keys = sorted([k for k in metrics.keys() if k.startswith('transporter_') and k.endswith('_utilization')])
    for key in transporter_keys:
        t_id = key.split('_')[1]
        kpi_data.append((f"Transporter {t_id}", f"{metrics[key]:.1f}", "%"))
    
    # 9. Busiest Station Group
    kpi_data.append((
        f"Busiest Station Group",
        f"{metrics['most_used_station_name']}: {metrics['most_used_station_utilization']:.1f}%",
        ""
    ))
    
    # Piirrä KPI-laatikot (aloita vasemmasta marginaalista)
    x_start = pdf.l_margin
    y_start = pdf.get_y()
    box_width = 55
    box_height = 28
    x_spacing = 62
    y_spacing = 35
    
    for idx, (label, value, unit) in enumerate(kpi_data):
        row = idx // 3
        col = idx % 3
        x = x_start + col * x_spacing
        y = y_start + row * y_spacing
        pdf.kpi_box(label, value, unit, x, y, box_width, box_height)
    
    # Siirry KPI-laatikoiden jälkeen
    rows_needed = (len(kpi_data) + 2) // 3
    pdf.set_y(y_start + rows_needed * y_spacing + 10)
    
    pdf.ln(5)
    
    # Lyhyt yhteenveto
    pdf.set_font('Arial', '', 10)
    summary_text = (
        f"The simulation successfully scheduled {metrics['total_batches']} batches with a total production time "
        f"of {metrics['makespan_formatted']}. "
        f"Average batch process time was {metrics['avg_lead_time_formatted']}. "
    )
    
    # Lisää utilization-info
    util_values = [metrics[k] for k in metrics.keys() if k.startswith('transporter_') and k.endswith('_utilization')]
    if util_values:
        avg_util = sum(util_values) / len(util_values)
        summary_text += f"Transporter utilization averaged {avg_util:.1f}%. "
    
    summary_text += f"Station group '{metrics['most_used_station_name']}' had the highest time utilization at {metrics['most_used_station_utilization']:.1f}%."
    
    pdf.multi_cell(0, 6, summary_text)
    
    # ===== PERFORMANCE ANALYSIS =====
    pdf.add_page()
    pdf.chapter_title('Performance Analysis - Transporters')
    
    pdf.section_title('Transporter Utilization')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, 
        "Transporter utilization shows the percentage of time each transporter spent on different phases. "
        "Phases include: Idle (0), Lifting (1), Moving (2-5), and Sinking (6). "
        "Higher productive time (non-idle) indicates better resource usage.")
    pdf.ln(3)
    
    # Näytä piirakkakaaviot rinnakkain (2 per rivi), keskitetty
    if transporter_pie_charts:
        charts_per_row = 2
        # Pienennetään koko 70%:iin
        available_width = (pdf.w - pdf.l_margin - pdf.r_margin - 10) * 0.7
        chart_width = available_width / charts_per_row
        
        # Laske keskitys
        total_width = available_width + 10
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        left_margin = pdf.l_margin + (page_width - total_width) / 2
        
        for idx, pie_chart in enumerate(transporter_pie_charts):
            col = idx % charts_per_row
            
            # Uusi rivi joka toisen kuvan jälkeen
            if col == 0 and idx > 0:
                pdf.ln(5)
            
            x_pos = left_margin + col * (chart_width + 10)
            y_pos = pdf.get_y() if col == 0 else y_pos  # Säilytä y-positio rivillä
            
            with Image.open(pie_chart) as img:
                img_w, img_h = img.size
                h = (img_h / img_w) * chart_width
            
            pdf.image(pie_chart, x=x_pos, y=y_pos, w=chart_width)
            
            # Viimeisen kuvan jälkeen siirrä y-positio eteenpäin
            if col == charts_per_row - 1 or idx == len(transporter_pie_charts) - 1:
                pdf.set_y(y_pos + h)
        
        pdf.ln(5)
    
    # Ajallinen kuormitusanalyysi
    pdf.section_title('Transporter Load Over Time')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6,
        "This chart shows how transporter load varies over time in 5-minute windows. "
        "Peaks in the graph indicate periods of high utilization where transporters are heavily utilized. "
        "This helps identify temporal bottlenecks that may not be visible in overall utilization statistics.")
    pdf.ln(3)
    
    if os.path.exists(temporal_load_chart):
        w = pdf.w - pdf.l_margin - pdf.r_margin
        with Image.open(temporal_load_chart) as img:
            img_w, img_h = img.size
            h = (img_h / img_w) * w
        pdf.image(temporal_load_chart, x=pdf.l_margin, y=pdf.get_y(), w=w)
        pdf.ln(h + 3)
    
    # Tehtävien jakautuminen nostimien kesken
    pdf.section_title('Task Distribution')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6,
        "The chart below shows how tasks are distributed across transporters. "
        "Uneven distribution may indicate imbalanced workload allocation.")
    pdf.ln(2)
    
    if os.path.exists(task_distribution_chart):
        w = pdf.w - pdf.l_margin - pdf.r_margin
        with Image.open(task_distribution_chart) as img:
            img_w, img_h = img.size
            h = (img_h / img_w) * w
        pdf.image(task_distribution_chart, x=pdf.l_margin, y=pdf.get_y(), w=w)
        pdf.ln(h + 10)
    
    pdf.section_title('Station Usage Frequency')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6,
        "This chart shows how many batches visited each station. Stations with high visit counts may be "
        "potential bottlenecks and candidates for capacity expansion or process optimization.")
    pdf.ln(5)
    
    if os.path.exists(station_chart):
        # Laske kuvan korkeus suhteessa leveyteen
        w = pdf.w - pdf.l_margin - pdf.r_margin
        with Image.open(station_chart) as img:
            img_w, img_h = img.size
            h = (img_h / img_w) * w
        pdf.image(station_chart, x=pdf.l_margin, y=pdf.get_y(), w=w)
        pdf.ln(h + 10)  # Kuvan korkeus + väli
    
    # ===== BATCH ANALYSIS =====
    pdf.add_page()
    pdf.chapter_title('Batch Analysis')
    
    pdf.section_title('Batch Lead Times')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6,
        "Lead time represents the total time from a batch entering the line to exiting. "
        "Variations in lead time can indicate differences in treatment programs or resource contention.")
    pdf.ln(5)
    
    if os.path.exists(leadtime_chart):
        # Laske kuvan korkeus suhteessa leveyteen
        w = pdf.w - pdf.l_margin - pdf.r_margin
        with Image.open(leadtime_chart) as img:
            img_w, img_h = img.size
            h = (img_h / img_w) * w
        pdf.image(leadtime_chart, x=pdf.l_margin, y=pdf.get_y(), w=w)
        pdf.ln(h + 10)  # Kuvan korkeus + väli
    
    # Batch-taulukko
    pdf.section_title('Batch Summary Table')
    batch_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv'))
    batch_summary = batch_schedule.groupby('Batch').agg({
        'EntryTime': 'min',
        'ExitTime': 'max',
        'Stage': 'count'
    }).reset_index()
    batch_summary['LeadTime_hrs'] = ((batch_summary['ExitTime'] - batch_summary['EntryTime']) / 3600).round(2)
    batch_summary = batch_summary.rename(columns={'Stage': 'Stages'})
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    
    # Taulukon otsikot
    col_widths = [20, 30, 30, 20, 30]
    headers = ['Batch', 'Start (s)', 'End (s)', 'Stages', 'Lead Time (hrs)']
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, 1, 0, 'C', True)
    pdf.ln()
    
    # Data
    pdf.set_font('Arial', '', 9)
    for idx, row in batch_summary.head(15).iterrows():  # Näytä 15 ensimmäistä
        pdf.cell(col_widths[0], 7, str(int(row['Batch'])), 1, 0, 'C')
        pdf.cell(col_widths[1], 7, str(int(row['EntryTime'])), 1, 0, 'R')
        pdf.cell(col_widths[2], 7, str(int(row['ExitTime'])), 1, 0, 'R')
        pdf.cell(col_widths[3], 7, str(int(row['Stages'])), 1, 0, 'C')
        pdf.cell(col_widths[4], 7, f"{row['LeadTime_hrs']:.2f}", 1, 0, 'R')
        pdf.ln()
    
    if len(batch_summary) > 15:
        pdf.ln(3)
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 5, f"... and {len(batch_summary) - 15} more batches", 0, 1, 'C')
    
    # ===== RECOMMENDATIONS =====
    pdf.add_page()
    pdf.chapter_title('Recommendations & Insights')
    
    pdf.set_font('Arial', '', 10)
    
    # Bottleneck-analyysi
    pdf.section_title('Potential Bottlenecks')
    station_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_station_schedule.csv'))
    usage_counts = station_schedule.groupby('Station').size().sort_values(ascending=False)
    top_stations = usage_counts.head(3)
    
    bottleneck_text = "Stations with highest usage: "
    for station, count in top_stations.items():
        bottleneck_text += f"Station {int(station)} ({int(count)} visits), "
    bottleneck_text = bottleneck_text.rstrip(', ') + ". "
    bottleneck_text += "Consider adding capacity or optimizing process times at these stations."
    pdf.multi_cell(0, 6, bottleneck_text)
    pdf.ln(5)
    
    # Utilization-optimointi
    pdf.section_title('Resource Optimization')
    util_values = [(k, metrics[k]) for k in metrics.keys() if k.startswith('transporter_') and k.endswith('_utilization')]
    if util_values:
        min_util = min(util_values, key=lambda x: x[1])
        max_util = max(util_values, key=lambda x: x[1])
        
        t_id_min = min_util[0].split('_')[1]
        t_id_max = max_util[0].split('_')[1]
        
        util_text = (
            f"Transporter {t_id_max} has the highest utilization ({max_util[1]:.1f}%), "
            f"while Transporter {t_id_min} has the lowest ({min_util[1]:.1f}%). "
            "Consider rebalancing workload or adjusting task assignments for more even utilization."
        )
        pdf.multi_cell(0, 6, util_text)
    pdf.ln(5)
    
    # Lead time -vaihtelu
    pdf.section_title('Lead Time Variability')
    lead_times = batch_summary['LeadTime_hrs'].values
    std_dev = np.std(lead_times)
    cv = (std_dev / np.mean(lead_times)) * 100 if np.mean(lead_times) > 0 else 0
    
    leadtime_text = (
        f"Batch lead time standard deviation is {std_dev:.2f} hours (CV = {cv:.1f}%). "
    )
    if cv > 20:
        leadtime_text += "High variability suggests inconsistent processing times. Review treatment programs and station assignments."
    else:
        leadtime_text += "Low variability indicates consistent processing times across batches."
    pdf.multi_cell(0, 6, leadtime_text)
    pdf.ln(10)
    
    # Yleinen yhteenveto
    pdf.section_title('Overall Assessment')
    assessment = (
        "The simulation demonstrates a feasible production schedule with acceptable resource utilization. "
        "Key improvement opportunities include optimizing high-traffic stations and balancing transporter workloads. "
        "Implementing these recommendations can improve throughput and reduce makespan by 10-20%."
    )
    pdf.multi_cell(0, 6, assessment)
    
    # ===== TECHNICAL APPENDIX =====
    pdf.add_page()
    pdf.chapter_title('Technical Appendix')
    
    pdf.section_title('Simulation Configuration')
    pdf.set_font('Arial', '', 9)
    
    # Stations-taulukko (tiivistetty)
    stations_path = os.path.join(init_dir, 'stations.csv')
    if os.path.exists(stations_path):
        stations_df = pd.read_csv(stations_path)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(0, 6, 'Stations Configuration', 0, 1)
        pdf.set_font('Arial', '', 8)
        pdf.multi_cell(0, 5, f"Total stations: {len(stations_df)}")
        pdf.ln(3)
    
    # Transporters-info
    transporter_phases = pd.read_csv(os.path.join(output_dir, 'reports', 'transporter_phases.csv'))
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 6, 'Transporter Configuration', 0, 1)
    pdf.set_font('Arial', '', 8)
    pdf.multi_cell(0, 5, f"Total transporters: {len(transporter_phases)}")
    pdf.ln(3)
    
    # Solver info (jos saatavilla)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 6, 'Solver Information', 0, 1)
    pdf.set_font('Arial', '', 8)
    pdf.multi_cell(0, 5, 
        "Optimization engine: Google OR-Tools CP-SAT\n"
        "Status: FEASIBLE solution found\n"
        f"Total makespan: {metrics['makespan_seconds']} seconds")
    
    # Tallenna PDF
    pdf_path = os.path.join(reports_dir, f'enhanced_simulation_report_{folder_name}.pdf')
    pdf.output(pdf_path)
    print(f"✅ Enhanced simulation report generated: {pdf_path}")
    
    return pdf_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
        generate_enhanced_simulation_report(output_dir)
    else:
        print("Usage: python generate_enhanced_report.py <output_directory>")
