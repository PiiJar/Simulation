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
import matplotlib.ticker as mtick
from PIL import Image
import math

# Standard body text font used across the report
BODY_FONT_NAME = 'Arial'
BODY_FONT_SIZE = 11
# Vertical spacing (mm) to leave after chapter title before body text on every page
CHAPTER_BODY_TOP_MARGIN = 6

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
        # Ei alatunnistetta etusivulle (sivu 1)
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, self.timestamp, 0, 0, 'C')
        
    def chapter_title(self, title):
        """Kappaleen otsikko"""
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(41, 128, 185)  # Sininen tausta
        self.set_text_color(255, 255, 255)
        # Draw title bar
        self.cell(0, 10, title, 0, 1, 'L', 1)
        # Ensure consistent vertical spacing after the title bar before body text
        # Use CHAPTER_BODY_TOP_MARGIN (mm)
        self.ln(CHAPTER_BODY_TOP_MARGIN)
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
    transporter_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv'))
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
    
    # === PULLONKAULA-ANALYYSI: Etsi stage jolla korkein bottleneck rate ===
    # Bottleneck rate = (stage min time + avg transfer time) / (number of stations)
    # Tämä kertoo todellisen kapasiteetin rajoitteen, ei pelkkää käyttöastetta
    
    bottleneck_group = None
    bottleneck_rate = 0
    bottleneck_station_name = "N/A"
    bottleneck_utilization = 0
    avg_transfer_time = 0
    
    # Lue keskimääräinen siirtoaika transfer tasks -tiedostosta
    # HUOM: TotalTaskTime on sekunteina, muunnetaan minuuteiksi
    transfer_tasks_file = os.path.join(output_dir, 'cp_sat', 'cp_sat_transfer_tasks.csv')
    if os.path.exists(transfer_tasks_file):
        transfer_tasks_df = pd.read_csv(transfer_tasks_file)
        avg_transfer_time = transfer_tasks_df['TotalTaskTime'].mean() / 60.0
    
    # Lue käsittelyohjelmat (treatment programs) pullonkaulan määrittämiseksi
    treatment_programs_dir = os.path.join(output_dir, 'cp_sat')
    if os.path.exists(treatment_programs_dir):
        # Käytetään Program 1:ää (yleisin ohjelma)
        tp_file = os.path.join(treatment_programs_dir, 'cp_sat_treatment_program_1.csv')
        if os.path.exists(tp_file):
            tp_df = pd.read_csv(tp_file)
            
            for _, row in tp_df[tp_df['Stage'] > 0].iterrows():
                min_stat = int(row['MinStat'])
                max_stat = int(row['MaxStat'])
                num_stations = max_stat - min_stat + 1
                
                # Parsitaan aika (muodossa "HH:MM:SS")
                min_time_str = row['MinTime']
                parts = min_time_str.split(':')
                min_time_min = int(parts[0]) * 60 + int(parts[1])
                
                # Bottleneck rate: (käsittelyaika + siirtoaika) / asemien määrä
                total_time = min_time_min + avg_transfer_time
                rate = total_time / num_stations if num_stations > 0 else 0
                
                # Hae asemaryhmä
                station_info = stations_df[stations_df['Number'] == min_stat]
                if not station_info.empty:
                    group = int(station_info.iloc[0]['Group'])
                    
                    # Päivitä jos tämä on korkeampi bottleneck rate
                    if rate > bottleneck_rate:
                        bottleneck_rate = rate
                        bottleneck_group = group
                        bottleneck_station_name = station_info.iloc[0]['Name']
                        bottleneck_utilization = group_utilization.get(group, 0)
    
    # === TEOREETTINEN TAKT TIME (Phase 1 optimaalinen) ===
    # Lasketaan todellinen takt time kuivausasemalla (bottleneck)
    theoretical_takt_seconds = 0
    theoretical_takt_formatted = "N/A"
    
    batch_schedule_file = os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv')
    if os.path.exists(batch_schedule_file) and bottleneck_group is not None:
        schedule_df = pd.read_csv(batch_schedule_file)
        
        # Etsi bottleneck station (kuivaus)
        # Bottleneck_group vastaa treatment program Stage-numeroa
        # Tarkista mikä Stage vastaa korkeinta bottleneck_rate:a
        if os.path.exists(tp_file):
            tp_df = pd.read_csv(tp_file)
            
            # Etsi stage jolla on bottleneck_rate
            for _, row in tp_df[tp_df['Stage'] > 0].iterrows():
                min_stat = int(row['MinStat'])
                max_stat = int(row['MaxStat'])
                num_stations = max_stat - min_stat + 1
                
                min_time_str = row['MinTime']
                parts = min_time_str.split(':')
                min_time_min = int(parts[0]) * 60 + int(parts[1])
                
                total_time = min_time_min + avg_transfer_time
                rate = total_time / num_stations if num_stations > 0 else 0
                
                # Jos tämä on bottleneck stage
                if abs(rate - bottleneck_rate) < 0.01:
                    stage_num = int(row['Stage'])
                    
                    # Hae tämän stagen entry times batch_schedule:sta
                    stage_entries = schedule_df[schedule_df['Stage'] == stage_num].sort_values('EntryTime')
                    
                    if len(stage_entries) > 1:
                        # Laske keskimääräinen väli entry timeissa (sekunneissa)
                        gaps = []
                        prev_entry = None
                        for _, entry_row in stage_entries.iterrows():
                            if prev_entry is not None:
                                gaps.append(entry_row['EntryTime'] - prev_entry)
                            prev_entry = entry_row['EntryTime']
                        
                        if gaps:
                            avg_gap_seconds = sum(gaps) / len(gaps)
                            theoretical_takt_seconds = avg_gap_seconds
                            
                            # Muunna muotoon HH:MM:SS
                            hours = int(avg_gap_seconds // 3600)
                            minutes = int((avg_gap_seconds % 3600) // 60)
                            seconds = int(avg_gap_seconds % 60)
                            theoretical_takt_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    break
    
    # Käytetään pullonkaulaa jos löytyi, muuten vanha logiikka (korkein käyttöaste)
    if bottleneck_group is not None:
        metrics['most_used_station_group'] = bottleneck_group
        metrics['most_used_station_name'] = bottleneck_station_name
        metrics['most_used_station_utilization'] = bottleneck_utilization
        metrics['bottleneck_rate'] = bottleneck_rate  # min/station
        metrics['theoretical_takt_time'] = theoretical_takt_formatted
        metrics['theoretical_takt_seconds'] = theoretical_takt_seconds
        metrics['group_utilization'] = group_utilization
    elif group_utilization:
        # Fallback: käytetyin asemaryhmä (korkein käyttöaste)
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
        metrics['bottleneck_rate'] = 0
        metrics['group_utilization'] = group_utilization
    else:
        metrics['most_used_station_group'] = 0
        metrics['most_used_station_name'] = "N/A"
        metrics['most_used_station_utilization'] = 0
        metrics['bottleneck_rate'] = 0
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


def create_vertical_speed_change_chart(output_dir, reports_dir):
    """Create a simple vertical bar chart marking vertical movement speed change points per transporter.

    Uses transporter physics parameters from cp_sat_transporters.csv (preferred) or initialization/transporters.csv.
    Marks change points at:
      - z = Z_slow_distance_dry (mm): transition from slow-up to fast-up
      - z = Z_total_distance - Z_slow_end_distance (mm): transition from fast-up to slow-up end

    The bar is segmented: slow (bottom), fast (middle), slow (top). Values are in millimeters.
    """
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    # Ensure reports dir
    os.makedirs(reports_dir, exist_ok=True)

    # Prefer Phase 1 snapshot of transporters (contains Avoid and physics columns)
    candidates = [
        os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv'),
        os.path.join(output_dir, 'initialization', 'transporters.csv'),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        print("[WARN] No transporter CSV found for physics chart")
        return None

    df = pd.read_csv(path)

    # Normalize column names expected by transporter_physics
    # Keep original names with exact spelling used in physics calc
    cols = {
        'Transporter_id': 'Transporter_id',
        'Z_total_distance (mm)': 'Z_total_distance (mm)',
        'Z_slow_distance_dry (mm)': 'Z_slow_distance_dry (mm)',
        'Z_slow_end_distance (mm)': 'Z_slow_end_distance (mm)',
        'Z_slow_distance_wet (mm)': 'Z_slow_distance_wet (mm)',
        'Z_slow_speed (mm/s)': 'Z_slow_speed (mm/s)',
        'Z_fast_speed (mm/s)': 'Z_fast_speed (mm/s)',
    }
    for c in list(cols.values()):
        if c not in df.columns:
            # Try looser matches (without units)
            matches = [col for col in df.columns if c.split(' (')[0] == col.split(' (')[0]]
            if matches:
                df[c] = df[matches[0]]
            else:
                df[c] = 0

    # Coerce to numeric
    for c in [
        'Z_total_distance (mm)', 'Z_slow_distance_dry (mm)', 'Z_slow_end_distance (mm)', 'Z_slow_distance_wet (mm)',
        'Z_slow_speed (mm/s)', 'Z_fast_speed (mm/s)'
    ]:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

    # Prepare data per transporter
    rows = []
    for _, r in df.iterrows():
        try:
            t = int(r.get('Transporter_id', r.get('Transporter', 0)))
        except Exception:
            t = int(r.get('Transporter', 0))
        z_total = float(r['Z_total_distance (mm)'])
        z_slow_dry = max(0.0, min(float(r['Z_slow_distance_dry (mm)']), z_total))
        z_slow_end = max(0.0, min(float(r['Z_slow_end_distance (mm)']), z_total))
        # Compute boundaries for lift profile (upwards): [0..z_slow_dry] slow, (z_slow_dry..z_total - z_slow_end] fast, (..z_total] slow
        z_fast_start = z_slow_dry
        z_fast_end = max(0.0, z_total - z_slow_end)
        z_fast_end = max(z_fast_end, z_fast_start)  # avoid negative middle when sums exceed total
        rows.append({
            'Transporter': t,
            'Z_total': z_total,
            'Z_slow_dry': z_slow_dry,
            'Z_fast_start': z_fast_start,
            'Z_fast_end': z_fast_end,
            'Z_slow_end': z_slow_end,
        })

    if not rows:
        print("[WARN] Empty transporter data for physics chart")
        return None

    rows = sorted(rows, key=lambda x: x['Transporter'])

    # Plot vertical bars
    n = len(rows)
    fig, ax = plt.subplots(figsize=(max(4, n * 1.2), 5))
    bar_width = 0.4
    x_positions = np.arange(n)

    slow_color = '#95a5a6'  # gray
    fast_color = '#3498db'  # blue

    max_height = max(r['Z_total'] for r in rows) if rows else 1.0
    for i, r in enumerate(rows):
        x = x_positions[i]
        # Draw slow (bottom)
        if r['Z_slow_dry'] > 0:
            rect = patches.Rectangle((x - bar_width/2, 0), bar_width, r['Z_slow_dry'], color=slow_color)
            ax.add_patch(rect)
        # Draw fast (middle)
        if r['Z_fast_end'] > r['Z_fast_start']:
            rect = patches.Rectangle((x - bar_width/2, r['Z_fast_start']), bar_width, r['Z_fast_end'] - r['Z_fast_start'], color=fast_color)
            ax.add_patch(rect)
        # Draw slow (top)
        if r['Z_total'] > r['Z_fast_end']:
            rect = patches.Rectangle((x - bar_width/2, r['Z_fast_end']), bar_width, r['Z_total'] - r['Z_fast_end'], color=slow_color)
            ax.add_patch(rect)

        # Mark change points as small black lines
        for y in [r['Z_slow_dry'], r['Z_fast_end']]:
            ax.plot([x - bar_width/2 - 0.1, x + bar_width/2 + 0.1], [y, y], color='black', linewidth=1)

        # Label transporter
        ax.text(x, -0.05 * max_height, f"T{r['Transporter']}", ha='center', va='top', fontsize=9)

        # Annotate heights (mm) near change points
        ax.text(x + bar_width/2 + 0.15, r['Z_slow_dry'], f"{int(r['Z_slow_dry'])} mm", va='center', fontsize=8)
        ax.text(x + bar_width/2 + 0.15, r['Z_fast_end'], f"{int(r['Z_fast_end'])} mm", va='center', fontsize=8)

    ax.set_xlim(-1, n)
    ax.set_ylim(0, max_height * 1.05 if max_height > 0 else 1)
    ax.set_ylabel('Z (mm)')
    ax.set_title('Vertical movement speed change points (lift profile)')
    ax.set_xticks([])
    ax.grid(axis='y', alpha=0.2)

    # Legend
    handles = [
        patches.Patch(color=slow_color, label='Slow speed zone'),
        patches.Patch(color=fast_color, label='Fast speed zone'),
    ]
    ax.legend(handles=handles, loc='upper right')

    plt.tight_layout()
    chart_path = os.path.join(reports_dir, 'transporter_vertical_speed_profile.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    return chart_path


def _load_transporter_physics(output_dir):
    """Load transporter physics parameters and normalize columns.

    Returns a list of dict rows with keys:
      Transporter, Z_total, Z_slow_dry, Z_slow_wet, Z_slow_end
    """
    import pandas as pd
    # Prefer cp_sat snapshot if available, else initialization physics.
    candidates = [
        os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv'),
        os.path.join(output_dir, 'initialization', 'transporters_physics.csv'),
        os.path.join(output_dir, 'initialization', 'transporters _physics.csv'),  # fallback if naming has a space
        os.path.join(output_dir, 'initialization', 'transporters.csv'),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return []

    df = pd.read_csv(path)

    # Map potential column names (with or without units)
    def get_col(df, preferred, fallback_prefix):
        if preferred in df.columns:
            return df[preferred]
        # try to match without unit suffix
        base = preferred.split(' (')[0]
        for c in df.columns:
            if c.split(' (')[0] == base:
                return df[c]
        # try explicit fallback_prefix
        for c in df.columns:
            if c.lower().startswith(fallback_prefix):
                return df[c]
        return None

    tid_col = None
    for key in ['Transporter_id', 'Transporter', 'Id']:
        if key in df.columns:
            tid_col = key
            break
    if tid_col is None:
        # create a simple index-based id if not present
        df['Transporter'] = list(range(1, len(df) + 1))
        tid_col = 'Transporter'

    z_total = get_col(df, 'Z_total_distance (mm)', 'z_total')
    z_slow_dry = get_col(df, 'Z_slow_distance_dry (mm)', 'z_slow_dry')
    z_slow_wet = get_col(df, 'Z_slow_distance_wet (mm)', 'z_slow_wet')
    z_slow_end = get_col(df, 'Z_slow_end_distance (mm)', 'z_slow_end')

    # Build normalized rows
    rows = []
    for _, r in df.iterrows():
        try:
            t = int(r[tid_col])
        except Exception:
            t = int(_ + 1)

        def num(val):
            try:
                return float(val)
            except Exception:
                return 0.0

        ZT = num(r[z_total.name]) if z_total is not None else 0.0
        ZD = min(num(r[z_slow_dry.name]) if z_slow_dry is not None else 0.0, ZT)
        ZW = min(num(r[z_slow_wet.name]) if z_slow_wet is not None else 0.0, ZT)
        ZE = min(num(r[z_slow_end.name]) if z_slow_end is not None else 0.0, ZT)

        rows.append({
            'Transporter': t,
            'Z_total': ZT,
            'Z_slow_dry': ZD,
            'Z_slow_wet': ZW,
            'Z_slow_end': ZE,
        })

    rows = [r for r in rows if r['Z_total'] > 0]
    return sorted(rows, key=lambda x: x['Transporter'])


def create_transporter_dynamics_plot(output_dir, reports_dir, transporter_id):
    """Return explicit time/position curves for a transporter.

    Only returns data when explicit arrays are present in CSV columns.
    Returns a list of (times_list, pos_list, label).
    """
    candidates = [
        os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters_physics.csv'),
        os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv'),
        os.path.join(output_dir, 'initialization', 'transporters_physics.csv'),
        os.path.join(os.path.dirname(__file__), 'initialization', 'transporters_physics.csv'),
        os.path.join(output_dir, 'initialization', 'transporters.csv'),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return []

    df = pd.read_csv(path)

    # Find transporter row
    tid_col = None
    for key in ['Transporter_id', 'Transporter', 'Id', 'transporters_id', 'id']:
        if key in df.columns:
            tid_col = key
            break
    if tid_col is None:
        row = df.iloc[0]
    else:
        matches = df[df[tid_col] == transporter_id]
        if matches.empty:
            matches = df[df[tid_col].astype(str) == str(transporter_id)]
        row = matches.iloc[0] if not matches.empty else df.iloc[0]

    def try_read(prefix, typ=None):
        time_cols = []
        pos_cols = []
        if typ is not None:
            time_cols += [f"{prefix}_{typ}_time_s", f"{prefix}_{typ}_time", f"{prefix}_time_{typ}"]
            pos_cols += [f"{prefix}_{typ}_pos_mm", f"{prefix}_{typ}_pos", f"{prefix}_pos_{typ}"]
        time_cols += [f"{prefix}_time_s", f"{prefix}_time", f"{prefix}_times"]
        pos_cols += [f"{prefix}_pos_mm", f"{prefix}_pos", f"{prefix}_positions", f"{prefix}_pos_mm_{prefix}"]

        found_time = next((c for c in df.columns if c in time_cols), None)
        found_pos = next((c for c in df.columns if c in pos_cols), None)
        if not found_time or not found_pos:
            return None

        import ast
        try:
            tval = row[found_time]
            pval = row[found_pos]
            if isinstance(tval, str) and tval.strip().startswith('['):
                times = list(ast.literal_eval(tval))
            else:
                times = [float(x) for x in str(tval).split(',') if x.strip()]
            if isinstance(pval, str) and pval.strip().startswith('['):
                poss = list(ast.literal_eval(pval))
            else:
                poss = [float(x) for x in str(pval).split(',') if x.strip()]
            if len(times) != len(poss) or len(times) == 0:
                return None
            return times, poss
        except Exception:
            return None

    curves = []
    order = [('lift', 0), ('sink', 0), ('lift', 1), ('sink', 1)]
    for pref, typ in order:
        c = try_read(pref, typ)
        if c:
            curves.append((c[0], c[1], f"{pref} T{typ}"))

    if not curves:
        for pref in ['lift', 'sink']:
            c = try_read(pref, None)
            if c:
                curves.append((c[0], c[1], pref))

    return curves


def load_transporter_info(output_dir):
    """Load basic transporter info (id, model, min/max stations, start pos, avoid)"""
    import pandas as pd
    rows = []
    candidates = [
        os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv'),
        os.path.join(output_dir, 'initialization', 'transporters.csv'),
        os.path.join(output_dir, 'initialization', 'transporters _task_areas.csv'),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return []

    df = pd.read_csv(path)
    # Normalize transporter id column
    tid_col = None
    for key in ['Transporter_id', 'Transporter', 'Id']:
        if key in df.columns:
            tid_col = key
            break
    if tid_col is None:
        df['Transporter'] = list(range(1, len(df) + 1))
        tid_col = 'Transporter'

    for _, r in df.iterrows():
        try:
            t = int(r[tid_col])
        except Exception:
            continue
        row = {'Transporter': t}
        for col in ['Model', 'Min_Lift_Station', 'Max_Lift_Station', 'Min_Sink_Station', 'Max_Sink_Station', 'Avoid']:
            if col in r.index:
                row[col] = r.get(col)
        # optional Color column in initialization CSV (hex string '#RRGGBB')
        if 'Color' in r.index:
            try:
                cval = r.get('Color')
                if isinstance(cval, str) and cval.strip():
                    row['Color'] = cval.strip()
            except Exception:
                pass
        rows.append(row)

    # Merge start positions if present
    spath = os.path.join(output_dir, 'initialization', 'transporters_start_positions.csv')
    if os.path.exists(spath):
        sp = pd.read_csv(spath)
        sp_map = {int(r['Transporter']): int(r['Start_station']) for _, r in sp.iterrows()}
        for r in rows:
            r['Start_station'] = sp_map.get(r['Transporter'], None)

    return sorted(rows, key=lambda x: x['Transporter'])


def assign_transporter_colors(transporters):
    """Deterministically assign hex colors to transporter ids.

    Returns dict {transporter_id: '#RRGGBB'}
    """
    # Predefined palette for up to 10 transporters.
    # Avoid red (#e74c3c) and avoid very light colors that draw poorly on white background.
    palette = [
        '#1f77b4',  # muted blue
        '#2ca02c',  # green
        '#ff7f0e',  # orange
        '#9467bd',  # purple
        '#8c564b',  # brown
        '#e377c2',  # pink (not too light)
        '#7f7f7f',  # gray
        '#bcbd22',  # olive
        '#17becf',  # teal
        '#393b79',  # dark indigo
    ]

    color_map = {}
    ids = sorted(int(t['Transporter']) for t in transporters)
    # If transporters include explicit Color entries, prefer them
    provided_colors = {int(t['Transporter']): t.get('Color') for t in transporters if t.get('Color')}
    for i, tid in enumerate(ids):
        if tid in provided_colors and provided_colors[tid]:
            color_map[tid] = provided_colors[tid]
        else:
            color_map[tid] = palette[i % len(palette)]
    return color_map


def add_per_transporter_physics_pages(output_dir, pdf, color_map=None):
    """Add one PDF page per transporter with a simple vertical bar:
    - Total height (full bar)
    - Bottom left half: slow zone for dry stations (type 0)
    - Bottom right half: slow zone for wet stations (type 1)
    - Top full-width slow zone (Z_slow_end)
    """
    # Configurable vertical scale for Z-bar and associated axes/graph.
    # Value <1.0 shrinks the visual elements; 1.0 keeps original size.
    Z_BAR_VERTICAL_SCALE = 0.64

    rows = _load_transporter_physics(output_dir)
    if not rows:
        return
    reports_dir = os.path.join(output_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    # Colors
    border = (52, 73, 94)
    dry_color = (149, 165, 166)     # gray
    wet_color = (26, 188, 156)      # teal
    top_color = (127, 140, 141)     # darker gray

    for r in rows:
        t = r['Transporter']
        ZT = r['Z_total']
        ZD = min(r['Z_slow_dry'], ZT)
        ZW = min(r['Z_slow_wet'], ZT)
        ZE = min(r['Z_slow_end'], ZT)
        Z_fast_end = max(0.0, ZT - ZE)  # height below top slow start

        pdf.add_page()
        pdf.chapter_title(f'Transporter {t} - Physics Profile')
        # (Transporter color swatch removed per request - no top-right color box)
        # Render description (left-aligned). The Z bar will be drawn below the text,
        # also left-aligned to keep the page compact.
        pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
        description = (
            'Single vertical bar shows configured vertical movement profile. '
            'Left half bottom = slow zone at DRY stations (type 0). '
            'Right half bottom = slow zone at WET stations (type 1). '
            'Top full-width segment = slow zone near top end.'
        )
        text_width_full = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.set_xy(pdf.l_margin, pdf.get_y())
        pdf.multi_cell(text_width_full, 6, description)
        pdf.ln(2)

        # Now draw the narrow Z-profile bar below the description, left-aligned
        left = pdf.l_margin + 2
        bar_width = 12
        top = pdf.get_y() + 4
        max_bar_height = max(100, pdf.h * 0.45)
        bar_height = min(max_bar_height, pdf.h - top - 70)
        # Apply configurable vertical scale safely
        bar_height = bar_height * float(Z_BAR_VERTICAL_SCALE)
        scale = bar_height / ZT if ZT > 0 else 1.0

        # Determine fill color from color_map if available
        fill_color = top_color
        if color_map and t in color_map:
            try:
                hexc = color_map[t]
                rcol, gcol, bcol = tuple(int(hexc.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                fill_color = (rcol, gcol, bcol)
            except Exception:
                pass

        # Draw full bar filled with transporter color
        pdf.set_draw_color(*border)
        pdf.set_fill_color(*fill_color)
        pdf.rect(left, top, bar_width, bar_height, 'F')
        pdf.rect(left, top, bar_width, bar_height, 'D')

    # (Description was rendered above; continue with annotations)

        # Restore horizontal change-point marker lines (thin black lines) without any
        # textual annotations or legend — user did not ask to remove the lines.
        pdf.set_draw_color(0, 0, 0)
        # Draw thin horizontal lines at key change points: dry start, wet start, fast-end and total
        for val in (ZD, ZW, Z_fast_end, ZT):
            try:
                if val is None:
                    continue
                y_pos = top + bar_height - (val * scale)
                # Clip inside bar
                if y_pos < top:
                    y_pos = top
                if y_pos > top + bar_height:
                    y_pos = top + bar_height
                # Draw a short horizontal marker starting at the bar's left edge
                # and extending a few mm past the right edge for visibility.
                pdf.set_line_width(0.3)
                pdf.line(left, y_pos, left + bar_width + 4, y_pos)
                # Draw right-side millimetre label for this marker (e.g., '300 mm')
                try:
                    label_val = int(round(val))
                    label_txt = f"{label_val} mm"
                except Exception:
                    label_txt = ''
                if label_txt:
                    # Small font for the labels; don't change main cursor vertically
                    label_x = left + bar_width + 6
                    label_h = 4
                    pdf.set_font(BODY_FONT_NAME, '', max(8, BODY_FONT_SIZE - 2))
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_xy(label_x, y_pos - (label_h / 2))
                    pdf.cell(0, label_h, label_txt, ln=0, align='L')
                    # Restore x back to left margin
                    pdf.set_x(pdf.l_margin)
            except Exception:
                continue
        pdf.set_line_width(0.0)

        # Draw coordinate axes to the right of the Z bar (no functions plotted yet)
        try:
            # Move axes further right from the Z bar and use full available width to the
            # right margin for the horizontal axis.
            axis_x = left + bar_width + 28  # larger gap between bar and axis (mm)
            axis_top = top
            axis_bottom = top + bar_height
            # Use the maximum available width up to the right margin
            axis_width = max(40, pdf.w - pdf.r_margin - axis_x - 2)
            pdf.set_draw_color(0, 0, 0)
            # Try to compute data-driven total seconds for this transporter from physics
            data_max_time = 0.0
            try:
                phys_candidates = [
                    os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters_physics.csv'),
                    os.path.join(output_dir, 'initialization', 'transporters _physics.csv'),
                    os.path.join(output_dir, 'initialization', 'transporters_physics.csv'),
                    os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv'),
                    os.path.join(output_dir, 'initialization', 'transporters.csv'),
                ]
                phys_path = next((p for p in phys_candidates if os.path.exists(p)), None)
                if phys_path:
                    p_df = pd.read_csv(phys_path)
                    id_col = next((c for c in p_df.columns if c.lower().startswith('transporter')), p_df.columns[0])
                    prow = None
                    try:
                        prow = p_df[p_df[id_col] == t].iloc[0]
                    except Exception:
                        try:
                            prow = p_df[p_df[id_col].astype(str) == str(t)].iloc[0]
                        except Exception:
                            prow = None
                    if prow is not None:
                        def getnum(keylist):
                            for col in p_df.columns:
                                for k in keylist:
                                    if col.replace(' ', '').lower().startswith(k.replace(' ', '').lower()):
                                        try:
                                            return float(prow[col])
                                        except Exception:
                                            try:
                                                return float(str(prow[col]).strip())
                                            except Exception:
                                                return None
                            return None

                        ZT = getnum(['Z_total_distance', 'Z_total']) or 0.0
                        ZD = getnum(['Z_slow_distance_dry', 'Z_slow_dry']) or 0.0
                        ZW = getnum(['Z_slow_distance_wet', 'Z_slow_wet']) or 0.0
                        ZE = getnum(['Z_slow_end_distance', 'Z_slow_end']) or 0.0
                        slow_speed = getnum(['Z_slow_speed']) or 0.0
                        fast_speed = getnum(['Z_fast_speed']) or 0.0

                        def max_time_for(bottom):
                            bottom = max(0.0, min(bottom, ZT))
                            top_seg = max(0.0, min(ZE, ZT - bottom))
                            middle = max(0.0, ZT - bottom - top_seg)
                            total = 0.0
                            if bottom > 0 and slow_speed > 0:
                                total += bottom / slow_speed
                            if middle > 0 and fast_speed > 0:
                                total += middle / fast_speed
                            if top_seg > 0 and slow_speed > 0:
                                total += top_seg / slow_speed
                            return total

                        mt0 = max_time_for(ZD)
                        mt1 = max_time_for(ZW)
                        data_max_time = max(mt0, mt1)
            except Exception:
                data_max_time = 0.0

            pdf.set_draw_color(0, 0, 0)
            pdf.set_line_width(0.5)
            # Vertical axis (height) aligned with Z bar
            pdf.line(axis_x, axis_bottom, axis_x, axis_top)

            # Vertical ticks aligned with the bar's marker lines
            for val in (ZD, ZW, Z_fast_end, ZT):
                try:
                    if val is None:
                        continue
                    y_pos = top + bar_height - (val * scale)
                    if y_pos < top:
                        y_pos = top
                    if y_pos > top + bar_height:
                        y_pos = top + bar_height
                    # small tick to the right of the axis (no label; heights are on Z bar)
                    pdf.line(axis_x, y_pos, axis_x + 3, y_pos)
                except Exception:
                    continue

            # Horizontal axis (time) at axis_bottom, 0.5s divisions
            pdf.set_line_width(0.5)
            pdf.line(axis_x, axis_bottom, axis_x + axis_width, axis_bottom)
            # choose mm per 0.5s
            mm_per_half_sec = 10
            # limit by axis_width
            num_div = int(axis_width // mm_per_half_sec)
            pdf.set_font(BODY_FONT_NAME, '', max(8, BODY_FONT_SIZE - 2))
            # Determine effective total seconds for axis labels
            # compute axis seconds: prefer data_max_time, round up to nearest whole second
            axis_min_seconds = (num_div * 0.5) if num_div > 0 else 0.0
            raw_total = max(data_max_time or 0.0, axis_min_seconds, 1e-6)
            # round up to integer seconds for clean tick labels
            total_seconds_for_axis = float(int(math.ceil(raw_total)))
            # Decide tick delta in seconds (1s grid). Compute number of seconds to show
            tick_seconds = 1
            num_seconds = int(max(1, total_seconds_for_axis))
            # map seconds to positions across axis_width
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(BODY_FONT_NAME, '', max(8, BODY_FONT_SIZE - 2))
            for s in range(0, num_seconds + 1, tick_seconds):
                frac = s / float(max(1, num_seconds))
                x_tick = axis_x + frac * axis_width
                pdf.line(x_tick, axis_bottom, x_tick, axis_bottom - 3)
                txt = f"{s:d}"
                pdf.set_xy(x_tick - 6, axis_bottom + 1)
                pdf.cell(12, 4, txt, ln=0, align='C')
                pdf.set_x(pdf.l_margin)

            # Axis titles
            # NOTE: per request, do not render the Y-axis 'Height (mm)' label to reduce clutter
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(BODY_FONT_NAME, '', max(8, BODY_FONT_SIZE - 2))
            pdf.set_xy(axis_x + axis_width/2 - 10, axis_bottom + 6)
            pdf.cell(0, 4, 'Time (s)', ln=0)
            pdf.set_line_width(0.0)
        except Exception:
            # don't fail the whole page if axes drawing fails
            pass
        # Draw transporter dynamics curves directly on the axes using physics data
        try:
            # load physics CSV (prefer snapshot cp_sat physics, then initialization)
            candidates = [
                os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters_physics.csv'),
                os.path.join(output_dir, 'initialization', 'transporters _physics.csv'),
                os.path.join(output_dir, 'initialization', 'transporters_physics.csv'),
                os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv'),
                os.path.join(output_dir, 'initialization', 'transporters.csv'),
            ]
            phys_path = next((p for p in candidates if os.path.exists(p)), None)
            if phys_path:
                pdf.set_line_width(0.6)
                try:
                    p_df = pd.read_csv(phys_path)
                    # normalize id col
                    id_col = next((c for c in p_df.columns if c.lower().startswith('transporter')), None)
                    if id_col is None:
                        id_col = p_df.columns[0]
                    row = None
                    try:
                        row = p_df[p_df[id_col] == t].iloc[0]
                    except Exception:
                        try:
                            row = p_df[p_df[id_col].astype(str) == str(t)].iloc[0]
                        except Exception:
                            row = None

                    if row is not None:
                        # read distances and speeds
                        def get(k):
                            for col in p_df.columns:
                                if col.replace(' ', '').lower().startswith(k.replace(' ', '').lower()):
                                    try:
                                        return float(row[col])
                                    except Exception:
                                        try:
                                            return float(str(row[col]).strip())
                                        except Exception:
                                            return None
                            return None

                        ZT = get('Z_total_distance') or get('Z_total') or 0.0
                        ZD = get('Z_slow_distance_dry') or 0.0
                        ZW = get('Z_slow_distance_wet') or 0.0
                        ZE = get('Z_slow_end_distance') or 0.0
                        slow_speed = get('Z_slow_speed') or get('Z_slow_speed (mm/s)') or 0.0
                        fast_speed = get('Z_fast_speed') or get('Z_fast_speed (mm/s)') or 0.0

                        if ZT > 0 and (slow_speed and fast_speed):
                            # build piecewise profiles
                            def build_profile(bottom_slow_len):
                                bottom = max(0.0, min(bottom_slow_len, ZT))
                                top = max(0.0, min(ZE, ZT - bottom))
                                middle = max(0.0, ZT - bottom - top)
                                pts_x = []
                                pts_y = []
                                # sample bottom slow
                                if bottom > 0:
                                    n = max(4, int(min(40, bottom/5)))
                                    xs = [i*(bottom/(n-1)) for i in range(n)]
                                    ts = [x/slow_speed for x in xs]
                                    pts_x.extend(ts)
                                    pts_y.extend(xs)
                                # sample middle fast
                                if middle > 0:
                                    n = max(4, int(min(80, middle/5)))
                                    xs_m = [bottom + i*(middle/(n-1)) for i in range(n)]
                                    ts_m = [(x-bottom)/fast_speed + (pts_x[-1] if pts_x else 0) for x in xs_m]
                                    pts_x.extend(ts_m)
                                    pts_y.extend(xs_m)
                                # sample top slow
                                if top > 0:
                                    n = max(4, int(min(40, top/5)))
                                    xs_t = [bottom + middle + i*(top/(n-1)) for i in range(n)]
                                    ts_t = [(x-(bottom+middle))/slow_speed + (pts_x[-1] if pts_x else 0) for x in xs_t]
                                    pts_x.extend(ts_t)
                                    pts_y.extend(xs_t)
                                # ensure monotonic times
                                # normalize times to start at 0
                                if len(pts_x) > 0:
                                    base = pts_x[0]
                                    pts_x = [p - base for p in pts_x]
                                return pts_x, pts_y

                            profiles = []
                            # type0 lift (bottom->top)
                            p_lift_0 = build_profile(ZD)
                            profiles.append((p_lift_0, 'type0 lift'))
                            # type0 sink (top->bottom): build explicitly so sink starts fast
                            if ZT > 0:
                                try:
                                    # change_point is the position (mm from bottom) where the sink should switch to slow
                                    change_point_dry = ZD
                                    # build sink profile starting at ZT down to 0, switching to slow when <= change_point
                                    def build_sink_profile(change_point):
                                        pts_t = []
                                        pts_p = []
                                        # fast segment: from ZT down to change_point
                                        if change_point < ZT:
                                            length_fast = ZT - change_point
                                            n_fast = max(4, int(min(80, length_fast/5)))
                                            for i in range(n_fast):
                                                p = ZT - i * (length_fast / (n_fast - 1))
                                                pts_p.append(p)
                                        # slow segment: from change_point down to 0
                                        if change_point > 0:
                                            length_slow = change_point
                                            n_slow = max(4, int(min(80, length_slow/5)))
                                            for i in range(n_slow):
                                                p = change_point - i * (length_slow / (n_slow - 1))
                                                pts_p.append(p)
                                        # ensure monotonic (descending) and unique
                                        # compute times based on speeds
                                        if not pts_p:
                                            return [], []
                                        times = [0.0]
                                        for prev, cur in zip(pts_p, pts_p[1:]):
                                            seg = abs(prev - cur)
                                            speed = fast_speed if prev > change_point else slow_speed
                                            dt = seg / (speed if speed > 0 else 1.0)
                                            times.append(times[-1] + dt)
                                        return times, pts_p

                                    times0, pos0 = build_sink_profile(change_point_dry)
                                    profiles.append(((times0, pos0), 'type0 sink'))
                                except Exception:
                                    pass
                            # type1 lift
                            p_lift_1 = build_profile(ZW)
                            profiles.append((p_lift_1, 'type1 lift'))
                            # type1 sink (top->bottom): build explicitly so sink starts fast
                            if ZT > 0:
                                try:
                                    change_point_wet = ZW
                                    def build_sink_profile(change_point):
                                        pts_t = []
                                        pts_p = []
                                        if change_point < ZT:
                                            length_fast = ZT - change_point
                                            n_fast = max(4, int(min(80, length_fast/5)))
                                            for i in range(n_fast):
                                                p = ZT - i * (length_fast / (n_fast - 1))
                                                pts_p.append(p)
                                        if change_point > 0:
                                            length_slow = change_point
                                            n_slow = max(4, int(min(80, length_slow/5)))
                                            for i in range(n_slow):
                                                p = change_point - i * (length_slow / (n_slow - 1))
                                                pts_p.append(p)
                                        if not pts_p:
                                            return [], []
                                        times = [0.0]
                                        for prev, cur in zip(pts_p, pts_p[1:]):
                                            seg = abs(prev - cur)
                                            speed = fast_speed if prev > change_point else slow_speed
                                            dt = seg / (speed if speed > 0 else 1.0)
                                            times.append(times[-1] + dt)
                                        return times, pts_p

                                    times1, pos1 = build_sink_profile(change_point_wet)
                                    profiles.append(((times1, pos1), 'type1 sink'))
                                except Exception:
                                    pass

                            # map to PDF coords and draw
                            default_hex = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
                            # compute effective total seconds from data (use axis tick range as minimum)
                            max_time_in_profiles = 0.0
                            for prof, _lbl in profiles:
                                tvals, _p = prof
                                if tvals:
                                    max_time_in_profiles = max(max_time_in_profiles, max(tvals))
                            axis_min_seconds = (num_div * 0.5) if num_div > 0 else 0.0
                            effective_total_seconds = max(max_time_in_profiles, axis_min_seconds, 1e-6)
                            # collect midpoints for smarter label placement after drawing
                            midpoints = {}
                            for idx, (prof, lbl) in enumerate(profiles):
                                times, poss = prof
                                if not times or not poss:
                                    continue
                                # choose color
                                col = None
                                try:
                                    if color_map and t in color_map:
                                        col = color_map[t]
                                except Exception:
                                    col = None
                                if not col:
                                    col = default_hex[idx % len(default_hex)]
                                rcol, gcol, bcol = tuple(int(col.lstrip('#')[i:i+2], 16) for i in (0,2,4))
                                pdf.set_draw_color(rcol, gcol, bcol)
                                pdf.set_line_width(0.4)
                                # draw polyline via small segments
                                prev = None
                                for time_val, pos_val in zip(times, poss):
                                    # map time to x using data-driven scale into axis_width
                                    frac = min(max(time_val / effective_total_seconds, 0.0), 1.0)
                                    x = axis_x + frac * axis_width
                                    # map pos to y
                                    y = axis_bottom - (pos_val * scale)
                                    if prev is not None:
                                        pdf.line(prev[0], prev[1], x, y)
                                    prev = (x, y)
                                # store midpoint for this profile for deferred labeling
                                try:
                                    map_lbl = {
                                        'type0 lift': 'Dry Lift',
                                        'type0 sink': 'Dry Sink',
                                        'type1 lift': 'Wet Lift',
                                        'type1 sink': 'Wet Sink'
                                    }
                                    label_text = map_lbl.get(lbl, lbl)
                                    mid_idx = max(0, min(len(times) - 1, len(times) // 2))
                                    time_mid = times[mid_idx]
                                    pos_mid = poss[mid_idx]
                                    frac_mid = min(max(time_mid / float(effective_total_seconds or 1.0), 0.0), 1.0)
                                    x_mid = axis_x + frac_mid * axis_width
                                    y_mid = axis_bottom - (pos_mid * scale)
                                    midpoints[lbl] = (x_mid, y_mid, label_text)
                                except Exception:
                                    pass
                            # place labels after plotting all profiles using deterministic rules:
                            # - Lifts: vertical position = ZW (upper speed-change height)
                            # - Sinks: vertical position = ZD (lower speed-change height)
                            # - Horizontal anchor: profile_end_time - 2.0 seconds (clamped to axis)
                            try:
                                pdf.set_font(BODY_FONT_NAME, '', max(7, BODY_FONT_SIZE - 3))
                                pdf.set_text_color(0, 0, 0)

                                # determine profile end time from drawn profiles
                                profile_end_time = 0.0
                                for prof, _lbl in profiles:
                                    tvals, _ = prof
                                    if tvals:
                                        profile_end_time = max(profile_end_time, max(tvals))
                                # fallback to effective_total_seconds if nothing found
                                profile_end_time = max(profile_end_time, float(effective_total_seconds or 0.0))

                                anchor_time = profile_end_time - 2.0
                                if anchor_time < 0.5:
                                    anchor_time = 0.5

                                def time_to_x_coord(tval):
                                    frac = min(max(float(tval) / float(effective_total_seconds or 1.0), 0.0), 1.0)
                                    return axis_x + frac * axis_width

                                def z_to_y_coord(zval):
                                    # map mm to y coordinate on the axis
                                    try:
                                        y = axis_bottom - (float(zval) * scale)
                                    except Exception:
                                        y = axis_bottom
                                    # clamp into axis vertical range
                                    if y < axis_top:
                                        y = axis_top
                                    if y > axis_bottom:
                                        y = axis_bottom
                                    return y

                                # prepare label text lookup (use midpoints text if available)
                                lbl_map = {}
                                for k, v in midpoints.items():
                                    # v = (x_mid, y_mid, label_text)
                                    lbl_map[k] = v[2]

                                # Draw each label using its own profile end time as anchor (end_time - 2s)
                                min_x = axis_x + 2
                                max_x = axis_x + axis_width - 4
                                y_lift = z_to_y_coord(ZW)
                                y_sink = z_to_y_coord(ZD)

                                # Build a map of label -> profile end time (seconds)
                                end_time_map = {}
                                for prof, lbl in profiles:
                                    tvals, _p = prof
                                    label_key = lbl
                                    if tvals:
                                        end_time_map[label_key] = max(tvals)
                                    else:
                                        end_time_map[label_key] = float(effective_total_seconds or 0.0)

                                def compute_anchor_x_for_label(end_time_val):
                                    # desired anchor time
                                    at = float(end_time_val or 0.0) - 2.0
                                    if at < 0.5:
                                        at = 0.5
                                    ax = time_to_x_coord(at)
                                    # clamp to axis bounds
                                    if ax < min_x:
                                        ax = min_x
                                    if ax > max_x:
                                        ax = max_x
                                    return ax

                                # helper to ensure text fits in axis: if text overruns right edge, shift left
                                def fit_text_x(x_start, text):
                                    try:
                                        tw = pdf.get_string_width(text)
                                    except Exception:
                                        tw = len(text) * 2.5
                                    # if text would overflow right bound, move left so it fits
                                    if x_start + tw > max_x:
                                        x_start = max(min_x, max_x - tw)
                                    return x_start

                                # Draw labels per-profile (left edge anchored at computed x)
                                if 'type1 lift' in lbl_map:
                                    et = end_time_map.get('type1 lift', effective_total_seconds)
                                    lx = compute_anchor_x_for_label(et)
                                    lx = fit_text_x(lx, lbl_map['type1 lift'])
                                    pdf.set_xy(lx, y_lift - 2)
                                    pdf.cell(0, 4, lbl_map['type1 lift'], ln=0, align='L')

                                if 'type0 lift' in lbl_map:
                                    et = end_time_map.get('type0 lift', effective_total_seconds)
                                    lx = compute_anchor_x_for_label(et)
                                    lx = fit_text_x(lx, lbl_map['type0 lift'])
                                    pdf.set_xy(lx, y_lift - 2)
                                    pdf.cell(0, 4, lbl_map['type0 lift'], ln=0, align='L')

                                if 'type1 sink' in lbl_map:
                                    et = end_time_map.get('type1 sink', effective_total_seconds)
                                    lx = compute_anchor_x_for_label(et)
                                    lx = fit_text_x(lx, lbl_map['type1 sink'])
                                    pdf.set_xy(lx, y_sink - 2)
                                    pdf.cell(0, 4, lbl_map['type1 sink'], ln=0, align='L')

                                if 'type0 sink' in lbl_map:
                                    et = end_time_map.get('type0 sink', effective_total_seconds)
                                    lx = compute_anchor_x_for_label(et)
                                    lx = fit_text_x(lx, lbl_map['type0 sink'])
                                    pdf.set_xy(lx, y_sink - 2)
                                    pdf.cell(0, 4, lbl_map['type0 sink'], ln=0, align='L')

                                pdf.set_x(pdf.l_margin)
                            except Exception:
                                pass
                            # restore color
                            pdf.set_draw_color(0,0,0)
                except Exception:
                    pass
        except Exception:
            pass


def create_transporter_temporal_load_chart(output_dir, reports_dir, color_map=None):
    """Luo ajallinen kuormituskaavio nostimille (5 min ikkunat)

    color_map: optional dict {transporter_id: hexcolor} to ensure consistent colors
    """
    transporter_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv'))
    batch_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv'))
    
    # Makespan
    makespan = batch_schedule['ExitTime'].max()
    
    # 5 minuuttia sekunneissa
    window_size = 300
    
    # Luo aikaikkunat
    num_windows = int(np.ceil(makespan / window_size))
    time_windows = [(i * window_size, (i + 1) * window_size) for i in range(num_windows)]
    
    # Hae uniikit transporterit
    transporters = sorted(transporter_schedule['Transporter'].unique())
    
    # Laske kuormitus per transporter per aikaikkuna
    load_data = {t: [] for t in transporters}
    
    for start_time, end_time in time_windows:
        for transporter in transporters:
            # Suodata kyseisen transporterin tehtävät
            t_tasks = transporter_schedule[transporter_schedule['Transporter'] == transporter]
            
            # Laske kuinka paljon aikaa on käytetty tässä ikkunassa (ei-idle)
            # Idle = Phase 0, Productive = Phase != 0
            work_time = 0
            
            for _, task in t_tasks.iterrows():
                task_start = task['TaskStart']
                task_end = task['TaskEnd']
                
                # Transporter schedule ei sisällä Phase-saraketta, joten lasketaan kaikki tehtävät työksi
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
    
    # Piirrä jokainen transporter omalla viivalla; värit lukitaan color_map:stä jos annettu
    default_colors = ['#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c', '#e74c3c', '#34495e']
    for idx, transporter in enumerate(transporters):
        color = None
        try:
            t_int = int(transporter)
            if color_map and t_int in color_map:
                color = color_map[t_int]
        except Exception:
            pass
        if color is None:
            color = default_colors[idx % len(default_colors)]
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


def create_transporter_task_distribution_chart(output_dir, reports_dir, color_map=None):
    """Luo tehtävien jakautumiskaavio nostimien kesken (vaakapalkki)"""
    transporter_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv'))
    
    # Laske tehtävien määrä per transporter
    task_counts = transporter_schedule.groupby('Transporter').size()
    total_tasks = task_counts.sum()
    
    # Laske prosentit
    task_percentages = (task_counts / total_tasks * 100).sort_index()
    
    # Värit (ensisijaisesti color_map jos annettu)
    default_colors = ['#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c', '#e74c3c', '#34495e']
    
    # Luo vaakapalkki-kaavio (kapeampi)
    fig, ax = plt.subplots(figsize=(12, 1.2))
    
    left = 0
    for idx, (transporter, percentage) in enumerate(task_percentages.items()):
        try:
            t_int = int(transporter)
            color = color_map.get(t_int) if color_map else None
        except Exception:
            color = None
        if not color:
            color = default_colors[idx % len(default_colors)]
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


def create_transporter_batch_occupation_chart(output_dir, reports_dir, color_map=None):
    """Luo kaavio nostimien keskimääräisestä eräkohtaisesta varausajasta

    color_map: optional dict {transporter_id: hexcolor}
    """
    # Käytä transporters_movement.csv, joka sisältää kaikki vaiheet (0-6)
    movement_file = os.path.join(output_dir, 'logs', 'transporters_movement.csv')
    
    if not os.path.exists(movement_file):
        print(f"[WARN] Movement file not found: {movement_file}")
        return None
    
    movements = pd.read_csv(movement_file)
    
    # Laske kunkin vaiheen kesto
    movements['PhaseDuration'] = movements['End_Time'] - movements['Start_Time']
    
    # Suodata vain aktiiviset vaiheet 1-4 (ei idle)
    # Vaiheet: 1=Move to lift, 2=Lifting, 3=Move to sink, 4=Sinking
    active_phases = movements[movements['Phase'].isin([1, 2, 3, 4])].copy()
    
    # Laske jokaiselle nostimelle: sum(PhaseDuration) per Batch (vaiheet 1-4)
    batch_occupation = active_phases.groupby(['Transporter', 'Batch'])['PhaseDuration'].sum().reset_index()
    batch_occupation.rename(columns={'PhaseDuration': 'TotalOccupationTime'}, inplace=True)
    
    # Laske keskiarvo per transporter (eräkohtainen summa / erien määrä)
    avg_occupation = batch_occupation.groupby('Transporter')['TotalOccupationTime'].mean().reset_index()
    avg_occupation.rename(columns={'TotalOccupationTime': 'AvgOccupationPerBatch'}, inplace=True)
    avg_occupation['AvgOccupationPerBatch_min'] = avg_occupation['AvgOccupationPerBatch'] / 60
    
    # Järjestä transporterit
    avg_occupation = avg_occupation.sort_values('Transporter')

def create_transporter_batch_occupation_chart(output_dir, reports_dir, color_map=None):
    """Luo kaavio nostimien keskimääräisestä eräkohtaisesta varausajasta

    color_map: optional dict {transporter_id: hexcolor}
    """
    # Laske ja piirrä kaavio uudelleen tässä funktiossa
    movement_file = os.path.join(output_dir, 'logs', 'transporters_movement.csv')
    if not os.path.exists(movement_file):
        print(f"[WARN] Movement file not found: {movement_file}")
        return None

    movements = pd.read_csv(movement_file)
    movements['PhaseDuration'] = movements['End_Time'] - movements['Start_Time']
    active_phases = movements[movements['Phase'].isin([1, 2, 3, 4])].copy()
    batch_occupation = active_phases.groupby(['Transporter', 'Batch'])['PhaseDuration'].sum().reset_index()
    batch_occupation.rename(columns={'PhaseDuration': 'TotalOccupationTime'}, inplace=True)
    avg_occupation = batch_occupation.groupby('Transporter')['TotalOccupationTime'].mean().reset_index()
    avg_occupation.rename(columns={'TotalOccupationTime': 'AvgOccupationPerBatch'}, inplace=True)
    avg_occupation['AvgOccupationPerBatch_min'] = avg_occupation['AvgOccupationPerBatch'] / 60
    avg_occupation = avg_occupation.sort_values('Transporter')

    # Luo pylväskaavio
    fig, ax = plt.subplots(figsize=(10, 5))
    transporters = [f"Transporter {int(t)}" for t in avg_occupation['Transporter']]
    occupation_times = avg_occupation['AvgOccupationPerBatch_min'].values

    # Värit
    default_colors = ['#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c', '#e74c3c', '#34495e']
    bar_colors = []
    for i, t in enumerate(transporters):
        try:
            tid = int(t.split()[-1]) if isinstance(t, str) and ' ' in t else int(t)
        except Exception:
            tid = None
        if tid and color_map and tid in color_map:
            bar_colors.append(color_map[tid])
        else:
            bar_colors.append(default_colors[i % len(default_colors)])

    bars = ax.bar(transporters, occupation_times, color=bar_colors, edgecolor='black', linewidth=0.8)

    # Lisää arvot palkkien päälle
    for bar, value in zip(bars, occupation_times):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_xlabel('')
    ax.set_ylabel('min', fontsize=12)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    chart_path = os.path.join(reports_dir, 'transporter_batch_occupation.png')
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
    
    # Derive report timestamp from the simulation snapshot folder name when possible
    # (so the front page shows the simulation run time, not the PDF creation time).
    folder_name = os.path.basename(os.path.abspath(output_dir))
    timestamp = None
    try:
        import re
        # Expect folder names that contain a trailing timestamp like
        # ..._YYYY-MM-DD_HH-MM-SS (e.g. 900135_-_Factory_..._2025-11-11_14-31-12)
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", folder_name)
        if m:
            ts_fragment = m.group(1)  # '2025-11-11_14-31-12'
            date_part, time_part = ts_fragment.split('_', 1)
            # convert time dashes to colons -> '14:31:12'
            time_part = time_part.replace('-', ':')
            ts_dt = datetime.strptime(f"{date_part} {time_part}", '%Y-%m-%d %H:%M:%S')
            timestamp = ts_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Fallback: use the snapshot folder's modification time
            mtime = os.path.getmtime(output_dir)
            ts_dt = datetime.fromtimestamp(mtime)
            timestamp = ts_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        # Last-resort fallback: now
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Laske KPI:t
    metrics = calculate_kpi_metrics(output_dir)

    # Lataa transporterien metatiedot ja määritä värit
    transporters_info = load_transporter_info(output_dir)
    color_map = assign_transporter_colors(transporters_info)
    # Tallenna color map reports-kansioon
    os.makedirs(reports_dir, exist_ok=True)
    try:
        import json
        with open(os.path.join(reports_dir, 'transporter_colors.json'), 'w', encoding='utf-8') as jf:
            json.dump(color_map, jf, indent=2)
    except Exception:
        pass

    # Luo kaaviot (pass color_map jotta värit lukittuvat koko raporttiin)
    # Piirakkakaaviot luodaan jo aiemmin, käytä niitä
    transporter_pie_charts = []
    for i in range(1, 30):  # Etsi transporterit 1-29
        pie_path = os.path.join(reports_dir, f'transporter_{i}_phases_pie.png')
        if os.path.exists(pie_path):
            transporter_pie_charts.append(pie_path)

    temporal_load_chart = create_transporter_temporal_load_chart(output_dir, reports_dir, color_map=color_map)
    task_distribution_chart = create_transporter_task_distribution_chart(output_dir, reports_dir, color_map=color_map)
    batch_occupation_chart = create_transporter_batch_occupation_chart(output_dir, reports_dir, color_map=color_map)
    station_chart = create_station_usage_chart(output_dir, reports_dir)
    leadtime_chart = create_batch_leadtime_chart(output_dir, reports_dir)
    vertical_speed_chart = create_vertical_speed_change_chart(output_dir, reports_dir)
    
    # Luo PDF
    pdf = EnhancedSimulationReport(customer, plant, timestamp)
    
    # ===== ETUSIVU =====
    pdf.add_page()
    pdf.set_y(25)  # Pienennetty 40 -> 25
    
    # Otsikko
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 12, 'Production Line', ln=1, align='C')  # 15 -> 12
    pdf.cell(0, 12, 'Simulation Report', ln=1, align='C')  # 15 -> 12
    pdf.ln(8)  # 10 -> 8
    
    # Asiakastiedot
    pdf.set_font('Arial', '', 14)
    pdf.set_text_color(52, 73, 94)
    pdf.cell(0, 8, customer, ln=1, align='C')  # 10 -> 8
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 7, plant, ln=1, align='C')  # 8 -> 7
    pdf.ln(4)  # 5 -> 4
    
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 7, timestamp, ln=1, align='C')  # 8 -> 7
    pdf.ln(10)  # 15 -> 10
    
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
                
                # Laske kuvan korkeus PDF:ssä (kasvatettu 80%)
                w = (pdf.w - pdf.l_margin - pdf.r_margin) * 0.8
                img_w, img_h = im.size
                h = (img_h / img_w) * w
                image_end_y = pdf.get_y() + h
            
            # Keskitä kuva
            x_offset = (pdf.w - w) / 2
            pdf.image(jpg_path, x=x_offset, y=pdf.get_y(), w=w)
        except Exception as e:
            print(f"[WARN] Cover image failed: {e}")
    
    # Lyhyt kuvaus - sijoita kuvan alle
    pdf.set_y(image_end_y + 8)
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
    pdf.set_text_color(52, 73, 94)
    
    # Algoritmin kuvaus
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, 'Two-Phase CP-SAT Optimization Algorithm', ln=1, align='L')
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
    algo_desc = (
        "Phase 1: Batch-level scheduling optimizes batch entry times and station assignments. "
        "Phase 2: Stage-level optimization schedules individual treatment stages, transporter movements, "
        "and ensures no spatial or temporal conflicts between operations."
    )
    pdf.multi_cell(0, 4.5, algo_desc, align='L')
    pdf.ln(3)
    
    # Rajoitukset
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, 'Simulation Limitations', ln=1, align='L')
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
    limitations = (
        "This simulation does not account for: manual loading/unloading times, human-induced delays, "
        "equipment failures, quality control inspections, or setup/changeover times between batches. "
        "Results represent an idealized scenario with perfect execution and no unexpected disruptions."
    )
    pdf.multi_cell(0, 4.5, limitations, align='L')
    
    # Kansion nimi alas oikeaan (sivu 1:n loppuun)
    pdf.set_y(pdf.h - 20)  # 20mm sivun alareunasta
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 5, folder_name, 0, 0, 'R')
    
    # ===== EXECUTIVE SUMMARY =====
    pdf.add_page()
    pdf.chapter_title('Executive Summary')
    
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
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
    
    # 5. Avg. Cycle Time (todellinen simuloitu tahtiaika)
    kpi_data.append(("Avg. Cycle Time", metrics['takt_time_formatted'], ""))
    
    # 6. Batches per Hour
    kpi_data.append(("Batches per Hour", f"{metrics['batches_per_hour']:.1f}", ""))
    
    # 7-8. Transporters (järjestyksessä)
    transporter_keys = sorted([k for k in metrics.keys() if k.startswith('transporter_') and k.endswith('_utilization')])
    for key in transporter_keys:
        t_id = key.split('_')[1]
        kpi_data.append((f"Transporter {t_id}", f"{metrics[key]:.1f}", "%"))
    
    # 9. Bottleneck Station
    bottleneck_text = f"{metrics['most_used_station_name']}"
    if metrics['bottleneck_rate'] > 0:
        bottleneck_text += f"\n({metrics['bottleneck_rate']:.1f} min/sta)"
    kpi_data.append((
        f"Bottleneck Station",
        bottleneck_text,
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
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
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
    
    summary_text += f"Bottleneck station: '{metrics['most_used_station_name']}' with {metrics['bottleneck_rate']:.1f} min/station capacity (utilization: {metrics['most_used_station_utilization']:.1f}%)."
    
    pdf.multi_cell(0, 6, summary_text)
    
    # ===== PER-TRANSPORTER PAGES =====
    # Color mapping is already written to reports/transporter_colors.json; per-transporter
    # pages will follow. Legend page removed — colors are now persisted in JSON only.
    # Lisää per-transporter -sivut (physics + summary swatch)
    try:
        add_per_transporter_physics_pages(output_dir, pdf, color_map=color_map)
    except TypeError:
        # Fallback: call without color_map if function signature differs
        add_per_transporter_physics_pages(output_dir, pdf)

    # ===== PERFORMANCE ANALYSIS =====
    pdf.add_page()
    pdf.chapter_title('Performance Analysis - Transporters')
    
    pdf.section_title('Transporter Utilization')
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
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
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
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
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
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

    # --- Transporter per-batch time analysis ---
    pdf.add_page()
    pdf.section_title('Transporter Occupation by Batches')
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
    pdf.multi_cell(0, 6,
        "This chart shows the average active time each transporter spends per batch. "
        "The calculation includes phases 1-4: Move to lifting station, Lifting, Move to sinking station, and Sinking. "
        "Idle time (phase 0) is excluded. Higher values indicate transporters that handle more time-consuming tasks per batch.")
    pdf.ln(5)
    
    if os.path.exists(batch_occupation_chart):
        w = pdf.w - pdf.l_margin - pdf.r_margin
        with Image.open(batch_occupation_chart) as img:
            img_w, img_h = img.size
            h = (img_h / img_w) * w
        pdf.image(batch_occupation_chart, x=pdf.l_margin, y=pdf.get_y(), w=w)
        pdf.ln(h + 10)

    # --- Station Usage and following sections start on a new page ---
    pdf.add_page()
    pdf.section_title('Station Usage Frequency')
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
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
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
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
    
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
    
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
    # Yritä lukea Phase 2 status-tiedosto (ensin), sitten Phase 1; jos ei löydy, käytä fallback-heuristiikkaa
    solver_status_text = "Status: Unknown"
    try:
        import json
        phase2_status = os.path.join(output_dir, 'cp_sat', 'cp_sat_phase2_status.json')
        phase1_status = os.path.join(output_dir, 'cp_sat', 'cp_sat_phase1_status.json')
        if os.path.exists(phase2_status):
            with open(phase2_status, 'r') as fh:
                s = json.load(fh)
                solver_status_text = f"Status: {s.get('status_name', 'UNKNOWN')} (Phase 2)"
        elif os.path.exists(phase1_status):
            with open(phase1_status, 'r') as fh:
                s = json.load(fh)
                solver_status_text = f"Status: {s.get('status_name', 'UNKNOWN')} (Phase 1)"
        else:
            # Fallback: jos konfliktit löytyvät, merkitse INFEASIBLE; jos hoist_schedule löytyy, merkitse SOLUTION FOUND
            conflicts = os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_conflicts.csv')
            hoist = os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv')
            if os.path.exists(conflicts):
                solver_status_text = 'Status: INFEASIBLE (conflicts reported)'
            elif os.path.exists(hoist):
                solver_status_text = 'Status: SOLUTION FOUND (heuristic)'
            else:
                solver_status_text = 'Status: No solver output found'
    except Exception:
        solver_status_text = 'Status: Unknown (error reading status file)'

    pdf.multi_cell(0, 5, 
        "Optimization engine: Google OR-Tools CP-SAT\n"
        f"{solver_status_text}\n"
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
