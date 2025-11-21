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
import json
from datetime import datetime
import pandas as pd
import numpy as np
from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mtick
from load_customer_json import get_customer_plant_legacy_format
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
        # Levennä vain vasenta marginaalia, oikea pysyy oletussa (10mm)
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
    """Laske keskeiset suorituskykymittarit report_data.json tiedostosta"""
    metrics = {}
    
    # Lue report_data.json
    report_data_path = os.path.join(output_dir, 'reports', 'report_data.json')
    with open(report_data_path, 'r') as f:
        report_data = json.load(f)
    
    # Makespan (kokonaisaika) from simulation data
    makespan_seconds = report_data['simulation']['duration_seconds']
    metrics['makespan_seconds'] = makespan_seconds
    metrics['makespan_hours'] = makespan_seconds / 3600
    
    # Muotoile makespan hh:mm:ss
    makespan_hours = int(makespan_seconds // 3600)
    makespan_minutes = int((makespan_seconds % 3600) // 60)
    makespan_secs = int(makespan_seconds % 60)
    metrics['makespan_formatted'] = f"{makespan_hours:02d}:{makespan_minutes:02d}:{makespan_secs:02d}"
    
    # Erämäärä
    metrics['total_batches'] = report_data['simulation']['total_batches']
    
    # Keskimääräinen läpimenoaika (calculate from batch schedule CSV)
    batch_schedule_file = os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv')
    if os.path.exists(batch_schedule_file):
        batch_schedule = pd.read_csv(batch_schedule_file)
        batch_times = batch_schedule.groupby('Batch').agg({'EntryTime': 'min', 'ExitTime': 'max'})
        batch_times['LeadTime'] = batch_times['ExitTime'] - batch_times['EntryTime']
        avg_lead_time_seconds = batch_times['LeadTime'].mean()
    else:
        avg_lead_time_seconds = 0
    
    metrics['avg_lead_time'] = avg_lead_time_seconds / 3600
    metrics['avg_lead_time_seconds'] = int(avg_lead_time_seconds)
    
    # Muotoile hh:mm:ss
    hours = int(avg_lead_time_seconds // 3600)
    minutes = int((avg_lead_time_seconds % 3600) // 60)
    seconds = int(avg_lead_time_seconds % 60)
    metrics['avg_lead_time_formatted'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Avg. Cycle Time from simulation data
    cycle_time_seconds = report_data['simulation']['steady_state_avg_cycle_time_seconds']
    metrics['takt_time_seconds'] = cycle_time_seconds
    
    # Muotoile hh:mm:ss
    takt_hours = int(cycle_time_seconds // 3600)
    takt_minutes = int((cycle_time_seconds % 3600) // 60)
    takt_secs = int(cycle_time_seconds % 60)
    metrics['takt_time_formatted'] = f"{takt_hours:02d}:{takt_minutes:02d}:{takt_secs:02d}"
    
    # Erien määrä tunnissa (from scaled production estimates)
    metrics['batches_per_hour'] = report_data['simulation_info']['scaled_production_estimates']['batches_per_hour']
    
    # Nostimen käyttöaste from transporter_statistics
    for transporter_data in report_data['transporter_statistics']:
        t_id = transporter_data['transporter_id']
        utilization = transporter_data['utilization_percent']
        metrics[f'transporter_{t_id}_utilization'] = utilization
    
    # Pullonkaula-analyysi from capacity_constraints
    station_limitation = report_data['capacity_constraints']['constraints']['station_limitation']
    
    # Bottleneck information  
    bottleneck_stage = station_limitation.get('limiting_stage', 0)
    bottleneck_rate = station_limitation['cycle_time_minutes']
    
    # Station name (simple placeholder - Stage number)
    bottleneck_station_name = f"Stage {bottleneck_stage}"
    
    metrics['most_used_station_group'] = bottleneck_stage
    metrics['most_used_station_name'] = bottleneck_station_name
    metrics['most_used_station_utilization'] = 0  # Placeholder
    metrics['bottleneck_rate'] = bottleneck_rate  # min/station
    metrics['theoretical_takt_time'] = "N/A"
    metrics['theoretical_takt_seconds'] = 0
    metrics['group_utilization'] = {}
    
    # Käsittelyohjelmat (Treatment Programs) from production.csv
    production_file = os.path.join(output_dir, 'initialization', 'production.csv')
    if os.path.exists(production_file):
        production_df = pd.read_csv(production_file)
        program_counts = production_df['Treatment_program'].value_counts().sort_index()
        total_batches = metrics['total_batches']
        
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
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    chart_path = os.path.join(images_dir, 'utilization_chart.png')
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

        # Annotate heights (mm) near change points
        # Nudge labels slightly above helper lines so they don't overlap
        label_offset = max(5.0, 0.01 * max_height)
        ax.text(
            x + bar_width/2 + 0.15,
            r['Z_slow_dry'] + label_offset,
            f"{int(r['Z_slow_dry'])} mm",
            va='bottom', fontsize=8
        )
        ax.text(
            x + bar_width/2 + 0.15,
            r['Z_fast_end'] + label_offset,
            f"{int(r['Z_fast_end'])} mm",
            va='bottom', fontsize=8
        )

    ax.set_xlim(-1, n)
    ax.set_ylim(0, max_height * 1.05 if max_height > 0 else 1)
    # Remove title and ylabel to match lower plot (they have their own labels)
    # Disable grid completely - no vertical or horizontal lines
    ax.grid(False)
    ax.set_axisbelow(True)
    
    # CRITICAL: Remove xticks BEFORE any other axis modifications
    ax.set_xticks([])
    ax.xaxis.set_ticks_position('none')
    ax.yaxis.set_ticks_position('none')

    # --- Vertical helper lines: seconds based on transporter vertical-motion durations ---
    # Compute per-transporter vertical move time from transporter physics (z speeds), not from batch ExitTime.
    max_time = 0.0
    # Try to load transporter physics/speeds from snapshot or initialization
    candidates = [
        os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv'),
        os.path.join(output_dir, 'initialization', 'transporters.csv'),
        os.path.join(output_dir, 'initialization', 'transporters_physics.csv'),
    ]
    tpath = next((p for p in candidates if os.path.exists(p)), None)
    trans_df = None
    if tpath:
        try:
            trans_df = pd.read_csv(tpath)
        except Exception:
            trans_df = None

    for r in rows:
        try:
            ZT = float(r.get('Z_total', 0.0))
            ZD = float(r.get('Z_slow_dry', 0.0))
            ZE = float(r.get('Z_slow_end', 0.0))
        except Exception:
            continue

        # Defaults if speeds not found
        z_slow_speed = 100.0  # mm/s fallback
        z_fast_speed = 500.0  # mm/s fallback

        if trans_df is not None:
            # find matching transporter row by Transporter id if available
            tid = r.get('Transporter')
            try:
                # match common id column names
                if 'Transporter_id' in trans_df.columns:
                    prow = trans_df[trans_df['Transporter_id'] == tid]
                elif 'Transporter' in trans_df.columns:
                    prow = trans_df[trans_df['Transporter'] == tid]
                elif 'Id' in trans_df.columns:
                    prow = trans_df[trans_df['Id'] == tid]
                else:
                    prow = trans_df.iloc[[0]]
                if not prow.empty:
                    prow = prow.iloc[0]
                    z_slow_speed = float(prow.get('Z_slow_speed (mm/s)', prow.get('Z_slow_speed', z_slow_speed)))
                    z_fast_speed = float(prow.get('Z_fast_speed (mm/s)', prow.get('Z_fast_speed', z_fast_speed)))
            except Exception:
                pass

        # Compute fast distance
        fast_dist = max(0.0, ZT - ZD - ZE)
        # Time components (device delays excluded here; this is pure motion time)
        t_slow1 = ZD / max(z_slow_speed, 1e-6)
        t_fast = fast_dist / max(z_fast_speed, 1e-6)
        t_slow2 = ZE / max(z_slow_speed, 1e-6)
        t_total = t_slow1 + t_fast + t_slow2
        if t_total > max_time:
            max_time = t_total

    # Ensure a sensible min and ceil
    import math
    if max_time <= 0:
        max_time = max(1.0, float(n))
    max_time_ceiled = int(math.ceil(max_time))

    # Map seconds [0..max_time_ceiled] onto x positions [0..n-1]
    if n > 1 and max_time_ceiled > 0:
        x_scale = (n - 1) / float(max_time_ceiled)
        seconds = np.arange(0, max_time_ceiled + 1, 1)
        sec_x = seconds * x_scale
        # Avoid creating huge tick arrays that break Matplotlib's locator.
        # Cap the number of drawn ticklines to a reasonable value (user-requested: 60).
        max_draw = 60
        if len(sec_x) > max_draw:
            step = int(math.ceil(len(sec_x) / float(max_draw)))
            draw_x = sec_x[::step]
        else:
            draw_x = sec_x
        # Draw vertical second lines (subtle dashed) at the chosen positions
        # REMOVED: No vertical gridlines - clean X-axis
        # for sx in draw_x:
        #     if -1 <= sx <= n:
        #         ax.axvline(x=sx, color='gray', linestyle='--', linewidth=0.8, alpha=0.25, zorder=3)
        # Set x-ticks with second labels (show integer seconds like lower plot)
        # Compute which seconds correspond to these x positions
        if len(draw_x) > 0 and len(seconds) > 0:
            # Map draw_x back to seconds
            second_labels = []
            for dx in draw_x:
                # Find closest second
                if x_scale > 0:
                    sec = int(round(dx / x_scale))
                    second_labels.append(str(sec))
                else:
                    second_labels.append('')
            # DISABLE X-TICKS COMPLETELY TO PREVENT VERTICAL LINES
            # ax.set_xticks(draw_x)
            # ax.set_xticklabels(second_labels)
            # Instead, manually place text labels without tick marks
            for i, (dx, lbl) in enumerate(zip(draw_x, second_labels)):
                if -1 <= dx <= n and lbl:
                    ax.text(dx, -0.03 * max_height, lbl, ha='center', va='top', fontsize=10)
        else:
            # ax.set_xticks(draw_x)
            # ax.set_xticklabels([''] * len(draw_x))
            pass
    else:
        # fallback: vertical lines at transporter positions
        # ax.set_xticks(x_positions)
        # ax.set_xticklabels([''] * len(x_positions))
        # Grid removed - no vertical lines
        pass

    # --- Horizontal helper lines: only at measurement levels we have (e.g., Z_slow_dry, Z_fast_end, Z_total)
    measure_levels = set()
    for r in rows:
        try:
            measure_levels.add(float(r['Z_slow_dry']))
            measure_levels.add(float(r['Z_fast_end']))
            measure_levels.add(float(r['Z_total']))
        except Exception:
            continue
    # Ensure 0 is included
    measure_levels.add(0.0)
    measure_levels = sorted(measure_levels)
    # Draw horizontal lines at these measurement levels
    ylim_top = max_height * 1.05 if max_height > 0 else 1
    for y in measure_levels:
        ax.hlines(y, xmin=-1, xmax=n, colors='gray', linestyles='-', linewidth=0.6, alpha=0.25, zorder=2)

    # Ensure y-ticks include measurement levels (merge with default yticks)
    existing_yticks = list(ax.get_yticks())
    combined_yticks = sorted(set(existing_yticks) | set(measure_levels))
    ax.set_yticks(combined_yticks)

    # Tick positions already set earlier - just ensure no tick marks are drawn
    ax.tick_params(axis='both', which='major', length=0, width=0)
    
    # Hide top and right spines, make bottom and left black
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_edgecolor('black')
    ax.spines['bottom'].set_linewidth(0.8)
    ax.spines['left'].set_edgecolor('black')
    ax.spines['left'].set_linewidth(0.8)

    # Apply consistent font family and size (matching lower X-speed chart)
    import matplotlib as mpl
    mpl_family = mpl.rcParams.get('font.family', None)
    mpl_size = mpl.rcParams.get('font.size', None)
    # If family is a list, take the first
    if isinstance(mpl_family, (list, tuple)) and mpl_family:
        mpl_family = mpl_family[0]
    # No axis labels - keep clean like lower plot which has them outside the matplotlib figure
    if mpl_size:
        ax.tick_params(axis='both', which='major', labelsize=mpl_size, length=0, width=0)
        # Legend with matching font
        handles = [
            patches.Patch(color=slow_color, label='Slow speed zone'),
            patches.Patch(color=fast_color, label='Fast speed zone'),
        ]
        ax.legend(handles=handles, loc='upper right', fontsize=mpl_size)
    else:
        # Legend
        handles = [
            patches.Patch(color=slow_color, label='Slow speed zone'),
            patches.Patch(color=fast_color, label='Fast speed zone'),
        ]
        ax.legend(handles=handles, loc='upper right')

    plt.tight_layout()
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    chart_path = os.path.join(images_dir, 'transporter_vertical_speed_profile.png')
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
    z_slow_speed = get_col(df, 'Z_slow_speed (mm/s)', 'z_slow_speed')
    z_fast_speed = get_col(df, 'Z_fast_speed (mm/s)', 'z_fast_speed')
    x_max_speed = get_col(df, 'X_max_speed (mm/s)', 'x_max_speed')
    x_acc_time = get_col(df, 'X_acceleration_time (s)', 'x_acceleration')
    x_dec_time = get_col(df, 'X_deceleration_time (s)', 'x_deceleration')

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
        ZS = num(r[z_slow_speed.name]) if z_slow_speed is not None else 100.0
        ZF = num(r[z_fast_speed.name]) if z_fast_speed is not None else 200.0
        
        XS = num(r[x_max_speed.name]) if x_max_speed is not None else 1000.0
        XA = num(r[x_acc_time.name]) if x_acc_time is not None else 1.0
        XD = num(r[x_dec_time.name]) if x_dec_time is not None else 1.0

        rows.append({
            'Transporter': t,
            'Z_total': ZT,
            'Z_slow_dry': ZD,
            'Z_slow_wet': ZW,
            'Z_slow_end': ZE,
            'Z_slow_speed': ZS,
            'Z_fast_speed': ZF,
            'X_speed': XS,
            'X_acc_time': XA,
            'X_dec_time': XD
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


def generate_z_profile_chart(transporter_id, physics, output_dir):
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Unpack physics
    z_total = physics.get('Z_total', 0)
    z_slow_dry = physics.get('Z_slow_dry', 0)
    z_slow_wet = physics.get('Z_slow_wet', 0)
    z_slow_end = physics.get('Z_slow_end', 0)
    z_slow_speed = physics.get('Z_slow_speed', 1)
    z_fast_speed = physics.get('Z_fast_speed', 1)
    
    if z_slow_speed <= 0: z_slow_speed = 1
    if z_fast_speed <= 0: z_fast_speed = 1

    def get_lift_profile(slow_dist):
        # 0 -> slow_dist (slow) -> fast -> z_total - slow_end (fast) -> z_total (slow)
        # Clamp distances
        s_dist = min(slow_dist, z_total)
        e_dist = min(z_slow_end, z_total)
        if s_dist + e_dist > z_total:
            # Overlap, adjust? Just clamp e_dist
            e_dist = max(0, z_total - s_dist)
            
        fast_dist = max(0, z_total - s_dist - e_dist)
        
        times = [0]
        dists = [0]
        
        # Phase 1: Slow up
        t1 = s_dist / z_slow_speed
        times.append(t1)
        dists.append(s_dist)
        
        # Phase 2: Fast up
        t2 = t1 + fast_dist / z_fast_speed
        times.append(t2)
        dists.append(s_dist + fast_dist)
        
        # Phase 3: Slow end
        t3 = t2 + e_dist / z_slow_speed
        times.append(t3)
        dists.append(z_total)
        
        return times, dists

    def get_sink_profile(slow_dist):
        # z_total -> fast -> slow_dist (fast ends) -> 0 (slow)
        s_dist = min(slow_dist, z_total)
        fast_dist = max(0, z_total - s_dist)
        
        times = [0]
        dists = [z_total]
        
        # Phase 1: Fast down
        t1 = fast_dist / z_fast_speed
        times.append(t1)
        dists.append(z_total - fast_dist) # should be s_dist
        
        # Phase 2: Slow down
        t2 = t1 + s_dist / z_slow_speed
        times.append(t2)
        dists.append(0)
        
        return times, dists

    # Generate data
    dry_lift_t, dry_lift_z = get_lift_profile(z_slow_dry)
    wet_lift_t, wet_lift_z = get_lift_profile(z_slow_wet)
    dry_sink_t, dry_sink_z = get_sink_profile(z_slow_dry) # Assuming dry sink uses dry slow zone
    wet_sink_t, wet_sink_z = get_sink_profile(z_slow_wet)
    
    # Plot
    plt.figure(figsize=(10, 4))
    plt.plot(dry_lift_t, dry_lift_z, label='Dry Lift (Type 0)', color='blue')
    plt.plot(dry_sink_t, dry_sink_z, label='Dry Sink (Type 0)', color='cyan', linestyle='--')
    plt.plot(wet_lift_t, wet_lift_z, label='Wet Lift (Type 1)', color='green')
    plt.plot(wet_sink_t, wet_sink_z, label='Wet Sink (Type 1)', color='lime', linestyle='--')
    
    plt.title(f'Transporter {transporter_id} Z movement')
    plt.xlabel('Time (s)')
    plt.ylabel('Distance (mm)')
    plt.grid(True)
    plt.legend()
    
    images_dir = os.path.join(output_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    filename = f'transporter_{transporter_id}_z_movement.png'
    filepath = os.path.join(images_dir, filename)
    plt.savefig(filepath)
    plt.close()
    return filepath


def generate_x_speed_chart(transporter_id, physics, output_dir):
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    import numpy as np
    
    x_speed = physics.get('X_speed', 1000)
    x_acc_time = physics.get('X_acc_time', 1)
    x_dec_time = physics.get('X_dec_time', 1)
    
    distances = [500, 2500, 5000]
    colors = ['red', 'blue', 'green']
    
    plt.figure(figsize=(10, 4))
    
    for dist, color in zip(distances, colors):
        # Calculate profile
        accel = x_speed / x_acc_time if x_acc_time > 0 else x_speed
        decel = x_speed / x_dec_time if x_dec_time > 0 else x_speed
        
        s_accel = 0.5 * accel * x_acc_time**2
        s_decel = 0.5 * decel * x_dec_time**2
        
        times = []
        speeds = []
        
        if dist < s_accel + s_decel:
            # Triangle profile
            # v_peak = sqrt(2 * dist * (accel * decel) / (accel + decel))
            v_peak = np.sqrt(2 * dist * (accel * decel) / (accel + decel))
            t1 = v_peak / accel
            t2 = t1 + v_peak / decel
            
            times = [0, t1, t2]
            speeds = [0, v_peak, 0]
        else:
            # Trapezoid profile
            t1 = x_acc_time
            s_const = dist - s_accel - s_decel
            t_const = s_const / x_speed
            t2 = t1 + t_const
            t3 = t2 + x_dec_time
            
            times = [0, t1, t2, t3]
            speeds = [0, x_speed, x_speed, 0]
            
        plt.plot(times, speeds, label=f'{dist} mm', color=color)
        
    plt.title(f'Transporter {transporter_id} X movement speed profile')
    plt.xlabel('Time (s)')
    plt.ylabel('Speed (mm/s)')
    plt.grid(True)
    plt.legend()
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    
    images_dir = os.path.join(output_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    filename = f'transporter_{transporter_id}_x_speed.png'
    filepath = os.path.join(images_dir, filename)
    plt.savefig(filepath)
    plt.close()
    return filepath

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
        pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
        description = (
            'The charts on this page illustrate transporter movement durations (horizontal axis represents time). '
            'The upper chart displays different lift and sink movements at dry and wet stations. '
            'The lower chart shows the duration of three different horizontal transfer distances. '
            'The total duration of a transporter task is additionally affected by station-specific dropping times '
            'and potential equipment delays.'
        )
        text_width_full = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.set_xy(pdf.l_margin, pdf.get_y())
        pdf.multi_cell(text_width_full, 6, description)
        pdf.ln(10)

        # --- Z-Movement Chart ---
        chart_path = generate_z_profile_chart(t, r, output_dir)
        if os.path.exists(chart_path):
            img_y = pdf.get_y() + 2
            img_w = pdf.w - pdf.l_margin - pdf.r_margin
            pdf.image(chart_path, x=pdf.l_margin, y=img_y, w=img_w)

        # --- X-Movement Speed Profile Chart ---
        x_speed_chart_path = generate_x_speed_chart(t, r, output_dir)
        if os.path.exists(x_speed_chart_path):
            # Estimate Z-chart height (aspect ratio 10:4)
            img_w = pdf.w - pdf.l_margin - pdf.r_margin
            z_chart_h = img_w * 0.4
            
            # Position X-chart below Z-chart
            # Z-chart was placed at pdf.get_y() + 2
            # So X-chart should be at (pdf.get_y() + 2) + z_chart_h + 5
            x_chart_y = (pdf.get_y() + 2) + z_chart_h + 10
            
            # Check page break
            if x_chart_y + z_chart_h > pdf.h - pdf.b_margin:
                pdf.add_page()
                x_chart_y = pdf.t_margin
                
            pdf.image(x_speed_chart_path, x=pdf.l_margin, y=x_chart_y, w=img_w)

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
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    chart_path = os.path.join(images_dir, 'transporter_temporal_load.png')
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
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    chart_path = os.path.join(images_dir, 'transporter_task_distribution.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def create_station_usage_chart(output_dir, reports_dir):
    """Luo asemaryhmien ajallinen käyttöastekaavio"""
    station_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_station_schedule.csv'))
    batch_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv'))
    
    # Load stations from JSON
    from load_stations_json import load_stations_from_json
    init_dir = os.path.join(output_dir, 'initialization')
    stations_df = load_stations_from_json(init_dir)
    
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
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    chart_path = os.path.join(images_dir, 'station_usage_chart.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def create_station_radar_chart(output_dir, reports_dir):
    """Luo asemaryhmien kuormitus-radarkaavio (pullonkaula-analyysi)"""
    station_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_station_schedule.csv'))
    batch_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_batch_schedule.csv'))
    
    # Load stations from JSON
    from load_stations_json import load_stations_from_json
    init_dir = os.path.join(output_dir, 'initialization')
    stations_df = load_stations_from_json(init_dir)
    
    # Laske kunkin aseman työaika
    station_schedule['Duration'] = station_schedule['ExitTime'] - station_schedule['EntryTime']
    
    # Lisää asemaryhmä- ja nimitiedot
    station_info = stations_df.set_index('Number')[['Group', 'Name']].to_dict('index')
    station_schedule['Group'] = station_schedule['Station'].map(lambda s: station_info.get(s, {}).get('Group', 0))
    
    # Laske kokonaistyöaika per ryhmä
    group_work_time = station_schedule.groupby('Group')['Duration'].sum()
    
    # Asemien määrä per ryhmä
    stations_per_group = stations_df.groupby('Group').size()
    
    # Erät yhteensä
    total_batches = batch_schedule['Batch'].nunique()
    if total_batches == 0:
        return None

    # Laske "Group Cycle Time" = (TotalWorkTime / TotalBatches) / NumStations
    group_cycle_times = {}
    all_groups = sorted(stations_df['Group'].unique())
    
    for group in all_groups:
        total_duration = group_work_time.get(group, 0)
        num_stations = stations_per_group.get(group, 1)
        cycle_time = (total_duration / total_batches) / num_stations
        group_cycle_times[group] = cycle_time
        
    # Etsi pullonkaula (maksimi cycle time)
    if not group_cycle_times:
        return None
        
    max_cycle_time = max(group_cycle_times.values())
    if max_cycle_time == 0:
        return None

    # Laske suhteellinen kuormitus (Load %)
    group_loads = []
    group_labels = []
    
    # Järjestys: Asemaryhmäjärjestys (oletetaan numeerinen järjestys Group ID:n mukaan)
    for group in all_groups:
        load_pct = (group_cycle_times[group] / max_cycle_time) * 100
        group_loads.append(load_pct)
        
        # Hae ryhmän nimi (ensimmäinen asema)
        group_stations = stations_df[stations_df['Group'] == group]
        if not group_stations.empty:
            group_labels.append(group_stations.iloc[0]['Name'])
        else:
            group_labels.append(f"G{group}")

    # --- Plotting Radar Chart ---
    N = len(group_labels)
    theta = np.linspace(0.0, 2 * np.pi, N, endpoint=False)
    width = 2 * np.pi / N
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})
    
    # Set start to top (pi/2) and direction clockwise (-1)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    
    # Draw bars
    bars = ax.bar(theta, group_loads, width=width, bottom=0.0, color='#3498db', alpha=0.6, edgecolor='white')
    
    # Labels
    ax.set_xticks(theta)
    ax.set_xticklabels(group_labels)
    
    # Y-axis (Load %)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], color='gray', size=8)
    
    ax.set_title('Bottleneck Analysis: Relative Load per Station Group\n(100% = Bottleneck Pace)', va='bottom', fontsize=14, fontweight='bold')
    
    # Highlight bottleneck (100%)
    for bar, val in zip(bars, group_loads):
        if val >= 99.9:
            bar.set_color('#e74c3c') # Red for bottleneck
            bar.set_alpha(0.8)
    
    plt.tight_layout()
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    chart_path = os.path.join(images_dir, 'station_radar_chart.png')
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
    z_slow_speed = get_col(df, 'Z_slow_speed (mm/s)', 'z_slow_speed')
    z_fast_speed = get_col(df, 'Z_fast_speed (mm/s)', 'z_fast_speed')
    x_max_speed = get_col(df, 'X_max_speed (mm/s)', 'x_max_speed')
    x_acc_time = get_col(df, 'X_acceleration_time (s)', 'x_acceleration')
    x_dec_time = get_col(df, 'X_deceleration_time (s)', 'x_deceleration')

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
        ZS = num(r[z_slow_speed.name]) if z_slow_speed is not None else 100.0
        ZF = num(r[z_fast_speed.name]) if z_fast_speed is not None else 200.0
        
        XS = num(r[x_max_speed.name]) if x_max_speed is not None else 1000.0
        XA = num(r[x_acc_time.name]) if x_acc_time is not None else 1.0
        XD = num(r[x_dec_time.name]) if x_dec_time is not None else 1.0

        rows.append({
            'Transporter': t,
            'Z_total': ZT,
            'Z_slow_dry': ZD,
            'Z_slow_wet': ZW,
            'Z_slow_end': ZE,
            'Z_slow_speed': ZS,
            'Z_fast_speed': ZF,
            'X_speed': XS,
            'X_acc_time': XA,
            'X_dec_time': XD
        })

    rows = [r for r in rows if r['Z_total'] > 0]
    return sorted(rows, key=lambda x: x['Transporter'])


def generate_simulation_report(output_dir):
    """Pääfunktio: luo tyylikkään PDF-raportin"""
    
    # Lue perustiedot
    init_dir = os.path.join(output_dir, 'initialization')
    reports_dir = os.path.join(output_dir, 'reports')
    report_data_path = os.path.join(reports_dir, 'report_data.json')
    
    try:
        df_cp = get_customer_plant_legacy_format(init_dir)
        customer = str(df_cp.iloc[0]['Customer'])
        plant = str(df_cp.iloc[0]['Plant'])
    except Exception as e:
        print(f"Warning: Could not load customer.json: {e}")
        customer = 'Customer'
        plant = 'Plant'
    
    # Derive report timestamp from the simulation snapshot folder name when possible
    folder_name = os.path.basename(os.path.abspath(output_dir))
    timestamp = None
    try:
        import re
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", folder_name)
        if m:
            ts_fragment = m.group(1)
            date_part, time_part = ts_fragment.split('_', 1)
            time_part = time_part.replace('-', ':')
            ts_dt = datetime.strptime(f"{date_part} {time_part}", '%Y-%m-%d %H:%M:%S')
            timestamp = ts_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            mtime = os.path.getmtime(output_dir)
            ts_dt = datetime.fromtimestamp(mtime)
            timestamp = ts_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Laske KPI:t
    metrics = calculate_kpi_metrics(output_dir)

    # Lataa transporterien metatiedot ja määritä värit
    transporters_info = load_transporter_info(output_dir)
    color_map = assign_transporter_colors(transporters_info)
    os.makedirs(reports_dir, exist_ok=True)
    try:
        import json
        with open(os.path.join(reports_dir, 'transporter_colors.json'), 'w', encoding='utf-8') as jf:
            json.dump(color_map, jf, indent=2)
    except Exception:
        pass

    # Luo kaaviot
    transporter_pie_charts = []
    for i in range(1, 30):
        pie_path = os.path.join(reports_dir, f'transporter_{i}_phases_pie.png')
        if os.path.exists(pie_path):
            transporter_pie_charts.append(pie_path)

    temporal_load_chart = create_transporter_temporal_load_chart(output_dir, reports_dir, color_map=color_map)
    station_chart = create_station_usage_chart(output_dir, reports_dir)
    leadtime_chart = None
    vertical_speed_chart = None

    # Luo PDF
    pdf = EnhancedSimulationReport(customer, plant, timestamp)
    
    # ===== ETUSIVU =====
    pdf.add_page()
    pdf.set_y(25)
    
    # Otsikko
    pdf.set_font('Arial', 'B', 28)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 15, 'Simulation Report', ln=1, align='C')
    pdf.ln(10)
    
    # Asiakastiedot
    pdf.set_font('Arial', '', 14)
    pdf.set_text_color(52, 73, 94)
    pdf.cell(0, 8, customer, ln=1, align='C')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 7, plant, ln=1, align='C')  # 8 -> 7
    pdf.ln(4)  # 5 -> 4
    
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 7, timestamp, ln=1, align='C')  # 8 -> 7
    pdf.ln(10)  # 15 -> 10
    
    # Capacity elements -kuva etusivulle
    first_page_img = os.path.join(reports_dir, 'images', 'capacity_elements.png')
    image_start_y = pdf.get_y()
    image_end_y = image_start_y
    
    if os.path.exists(first_page_img):
        try:
            # Muunna JPEG:ksi ja tallenna vain reports/images/ kansioon
            images_dir = os.path.join(reports_dir, 'images')
            jpg_path = os.path.join(images_dir, 'capacity_elements.jpg')
            
            with Image.open(first_page_img) as im:
                if im.mode in ('RGBA', 'LA'):
                    bg = Image.new('RGB', im.size, (255, 255, 255))
                    bg.paste(im, mask=im.split()[-1])
                    im_to_save = bg
                else:
                    im_to_save = im.convert('RGB')
                
                # Tallenna vain images-kansioon
                im_to_save.save(jpg_path, format='JPEG', quality=85)
                
                # Laske kuvan korkeus PDF:ssä (kasvatettu 80%)
                w = (pdf.w - pdf.l_margin - pdf.r_margin) * 0.8
                img_w, img_h = im.size
                h = (img_h / img_w) * w
                image_end_y = pdf.get_y() + h
            
            # Keskitä kuva marginaalien väliin
            available_width = pdf.w - pdf.l_margin - pdf.r_margin
            x_offset = pdf.l_margin + (available_width - w) / 2
            pdf.image(jpg_path, x=x_offset, y=pdf.get_y(), w=w)
        except Exception as e:
            print(f"[WARN] Cover image failed: {e}")
    
    # Status indicator below image
    pdf.set_y(image_end_y + 5)
    
    # Read target and simulated cycle times from report data
    target_met = False
    target_cycle_time = 0
    simulated_cycle_time = 0
    
    try:
        with open(report_data_path, 'r') as f:
            report_data = json.load(f)
        
        simulated_cycle_time = report_data.get('simulation', {}).get('steady_state_avg_cycle_time_seconds', 0)
        
        # Get target from goals.json
        goals_path = os.path.join(output_dir, 'initialization', 'goals.json')
        if os.path.exists(goals_path):
            with open(goals_path, 'r') as f:
                goals_data = json.load(f)
                target_pace = goals_data.get('target_pace', {})
                target_cycle_time = target_pace.get('target_cycle_time_seconds') or target_pace.get('average_batch_interval_seconds', 0)
        
        if target_cycle_time > 0 and simulated_cycle_time > 0:
            target_met = simulated_cycle_time <= target_cycle_time
    except Exception as e:
        print(f"[WARN] Could not determine target status: {e}")
    
    # Draw status box
    box_width = 60
    box_height = 12
    # Keskitä laatikko marginaalien väliin
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    box_x = pdf.l_margin + (available_width - box_width) / 2
    
    if target_met:
        # Green box for TARGET MET
        pdf.set_fill_color(46, 125, 50)  # Dark green
        pdf.set_text_color(255, 255, 255)  # White text
        status_text = 'TARGET MET'
    else:
        # Red box for TARGET MISSED
        pdf.set_fill_color(198, 40, 40)  # Dark red
        pdf.set_text_color(255, 255, 255)  # White text
        status_text = 'TARGET MISSED'
    
    pdf.rect(box_x, pdf.get_y(), box_width, box_height, 'F')
    pdf.set_font('Arial', 'B', 14)
    pdf.set_xy(box_x, pdf.get_y() + 3)
    pdf.cell(box_width, 6, status_text, 0, 0, 'C')
    
    # Additional info text below status box
    pdf.set_y(pdf.get_y() + 10)
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(52, 73, 94)
    # Keskitä teksti marginaalien väliin
    pdf.set_x(pdf.l_margin)
    pdf.cell(available_width, 5, 'More information in report', 0, 1, 'C')
    
    # Kansion nimi alas oikeaan (sivu 1:n loppuun)
    pdf.set_y(pdf.h - 20)  # 20mm sivun alareunasta
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 5, folder_name, 0, 0, 'R')
    


    # ===== CUSTOMER AND PLANT INFORMATION (always page 3) =====
    # This block is now moved after the Table of Contents to ensure correct order
    def add_customer_plant_info_page():
        report_data_path = os.path.join(reports_dir, 'report_data.json')
        with open(report_data_path, 'r') as f:
            report_data = json.load(f)
        
        # Use NEW structure with fallback to legacy
        customer_plant = report_data.get('customer_and_plant', {})
        sim_results = report_data.get('simulation_results', {})
        prod_targets = report_data.get('production_targets', {})
        metadata_info = report_data.get('metadata', {})
        
        # Fallback to legacy structure if new structure is empty
        if not customer_plant:
            sim_info = report_data.get('simulation_info', {})
            customer_plant = {
                'customer_name': sim_info.get('customer_name', '-'),
                'customer_id': sim_info.get('customer_id', '-'),
                'plant_name': sim_info.get('plant_name', '-'),
                'plant_id': sim_info.get('plant_id', '-'),
                'plant_location': sim_info.get('plant_location', {}),
                'available_containers': sim_info.get('available_containers', '-'),
                'annual_production_targets': sim_info.get('annual_production_targets', []),
                'products': sim_info.get('products', []),
                'production_schedule': sim_info.get('production_schedule', {})
            }
            sim_results = {
                'total_batches': sim_info.get('total_batches', '-'),
                'total_production_time': sim_info.get('total_production_time', '-'),
                'ramp_up_time': sim_info.get('ramp_up_time', '-'),
                'steady_state_time': sim_info.get('steady_state_time', '-'),
                'ramp_down_time': sim_info.get('ramp_down_time', '-'),
                'scaled_production_estimates': sim_info.get('scaled_production_estimates', {})
            }
            prod_targets = sim_info.get('production_targets', {})
            metadata_info = {
                'folder_name': sim_info.get('folder_name', '-'),
                'report_generated': sim_info.get('report_generated', '-')
            }
        
        customer = customer_plant.get('customer_name', '-')
        plant = customer_plant.get('plant_name', '-')
        location = customer_plant.get('plant_location', {})
        city = location.get('city', '-')
        country = location.get('country', '-')
        available_containers = customer_plant.get('available_containers', '-')
        total_batches = sim_results.get('total_batches', '-')
        total_prod_time = sim_results.get('total_production_time', '-')
        ramp_up = sim_results.get('ramp_up_time', '-')
        steady = sim_results.get('steady_state_time', '-')
        ramp_down = sim_results.get('ramp_down_time', '-')
        
        # Read solver status
        solver_status = "Unknown"
        try:
            phase2_status = os.path.join(output_dir, 'cp_sat', 'cp_sat_phase2_status.json')
            phase1_status = os.path.join(output_dir, 'cp_sat', 'cp_sat_phase1_status.json')
            if os.path.exists(phase2_status):
                with open(phase2_status, 'r') as fh:
                    s = json.load(fh)
                    solver_status = s.get('status_name', 'UNKNOWN')
            elif os.path.exists(phase1_status):
                with open(phase1_status, 'r') as fh:
                    s = json.load(fh)
                    solver_status = s.get('status_name', 'UNKNOWN')
            else:
                # Fallback heuristic
                conflicts = os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_conflicts.csv')
                hoist = os.path.join(output_dir, 'cp_sat', 'cp_sat_hoist_schedule.csv')
                if os.path.exists(conflicts):
                    solver_status = 'INFEASIBLE'
                elif os.path.exists(hoist):
                    solver_status = 'OPTIMAL'
        except Exception:
            solver_status = "Unknown"
        # Annual estimate
        scaled = sim_results.get('scaled_production_estimates', {})
        year = scaled.get('year', {})
        annual_batches = year.get('total_batches', '-')
        by_product = year.get('by_product', {})
        prod_name = '-'
        prod_pieces = '-'
        if by_product:
            prod = next(iter(by_product.values()))
            prod_name = prod.get('name', '-')
            prod_pieces = prod.get('pieces', '-')

        pdf.add_page()
        pdf.chapter_title('Basic Information')
        pdf.ln(8)
        pdf.set_font(BODY_FONT_NAME, '', 12)

        label_width = 38
        value_width = 0  # 0 means extend to right margin

        pdf.set_font(BODY_FONT_NAME, 'B', 12)
        pdf.cell(label_width, 8, "Customer:", ln=0)
        pdf.set_font(BODY_FONT_NAME, '', 12)
        pdf.cell(value_width, 8, f"{customer}", ln=1)

        pdf.set_font(BODY_FONT_NAME, 'B', 12)
        pdf.cell(label_width, 8, "Plant:", ln=0)
        pdf.set_font(BODY_FONT_NAME, '', 12)
        pdf.cell(value_width, 8, f"{plant}", ln=1)

        pdf.set_font(BODY_FONT_NAME, 'B', 12)
        pdf.cell(label_width, 8, "Location:", ln=0)
        pdf.set_font(BODY_FONT_NAME, '', 12)

        pdf.cell(value_width, 8, f"{city}, {country}", ln=1)
        pdf.ln(8)  # Blank line after Location

        # Annual production estimate block - from report_data.json
        pdf.set_font(BODY_FONT_NAME, 'B', 12)
        pdf.cell(0, 8, "Annual production estimate:", ln=1)
        pdf.set_font(BODY_FONT_NAME, '', 12)
        
        # Get annual production targets from report_data
        targets = customer_plant.get('annual_production_targets', [])
        if targets:
            for target in targets:
                product_id = target.get('product_id', 'N/A')
                quantity = target.get('target_quantity', 0)
                unit = target.get('unit', 'pieces')
                pdf.cell(label_width, 7, f"Product {product_id}:", ln=0)
                pdf.cell(value_width, 7, f"{quantity:,} {unit}/year", ln=1)
        else:
            # Fallback to old data if targets not available
            pdf.cell(0, 7, f"Batches per year: {annual_batches}", ln=1)
            pdf.cell(0, 7, f"Product: {prod_name}", ln=1)
            pdf.cell(0, 7, f"Pieces per year: {prod_pieces}", ln=1)
        
        pdf.ln(8)  # Blank line
        
        # Production times section
        pdf.set_font(BODY_FONT_NAME, 'B', 12)
        pdf.cell(0, 8, "Production times:", ln=1)
        pdf.set_font(BODY_FONT_NAME, '', 12)
        
        prod_schedule = customer_plant.get('production_schedule', {})
        hours_per_shift = prod_schedule.get('hours_per_shift', 0)
        shifts_per_day = prod_schedule.get('shifts_per_day', 0)
        days_per_week = prod_schedule.get('days_per_week', 0)
        weeks_per_year = prod_schedule.get('weeks_per_year', 0)
        
        pdf.cell(label_width, 7, "Shift:", ln=0)
        pdf.cell(value_width, 7, f"{hours_per_shift} hours", ln=1)
        
        pdf.cell(label_width, 7, "Day:", ln=0)
        pdf.cell(value_width, 7, f"{shifts_per_day} shifts", ln=1)
        
        pdf.cell(label_width, 7, "Week:", ln=0)
        pdf.cell(value_width, 7, f"{days_per_week} days", ln=1)
        
        pdf.cell(label_width, 7, "Year:", ln=0)
        pdf.cell(value_width, 7, f"{weeks_per_year} weeks", ln=1)
        
        # Calculate correct total hours (in case customer.json has wrong value)
        correct_total_hours = weeks_per_year * days_per_week * shifts_per_day * hours_per_shift
        pdf.cell(label_width, 7, "Total hours:", ln=0)
        pdf.cell(value_width, 7, f"{correct_total_hours:,.1f} hours/year", ln=1)
        
        # Total steady hours per year
        total_steady_hours = prod_targets.get('total_steady_hours_per_year', 0)
        pdf.cell(label_width, 7, "Total steady hours:", ln=0)
        pdf.cell(value_width, 7, f"{total_steady_hours:,.1f} hours/year (Total hours - ramp-up times)", ln=1)
        
        pdf.ln(8)  # Blank line
        
        # Batch size section
        pdf.set_font(BODY_FONT_NAME, 'B', 12)
        pdf.cell(0, 8, "Batch size:", ln=1)
        pdf.set_font(BODY_FONT_NAME, '', 12)
        
        products_list = customer_plant.get('products', [])
        annual_targets = customer_plant.get('annual_production_targets', [])
        
        # Create a map of product_id to annual target
        target_map = {}
        for target in annual_targets:
            pid = target.get('product_id', '')
            qty = target.get('target_quantity', 0)
            target_map[pid] = qty
        
        for product in products_list:
            product_id = product.get('product_id', 'N/A')
            pieces_per_batch = product.get('pieces_per_batch', 0)
            pdf.cell(label_width, 7, f"Product {product_id}:", ln=0)
            pdf.cell(value_width, 7, f"{pieces_per_batch} pieces/batch", ln=1)
        
        # Add calculation line
        if len(products_list) > 0:
            calculation_parts = []
            for product in products_list:
                product_id = product.get('product_id', 'N/A')
                pieces_per_batch = product.get('pieces_per_batch', 1)
                annual_qty = target_map.get(product_id, 0)
                calculation_parts.append(f"{annual_qty:,} / {pieces_per_batch}")
            
            total_batches = sum([target_map.get(p.get('product_id', ''), 0) / p.get('pieces_per_batch', 1) for p in products_list])
            calculation_text = " + ".join(calculation_parts) + f" = {total_batches:,.0f} batches/year"
            pdf.cell(label_width, 7, "----> ", ln=0)
            pdf.cell(value_width, 7, calculation_text, ln=1)
            
            # Add batches per hour calculation
            batches_per_hour = total_batches / total_steady_hours if total_steady_hours > 0 else 0
            
            # Build the text with bold formatting inline
            pdf.set_font(BODY_FONT_NAME, '', 12)
            pdf.cell(label_width, 7, "----> ", ln=0)
            # Regular text part
            text_before = f"{total_batches:,.0f} / {total_steady_hours:,.1f} = "
            pdf.write(7, text_before)
            # Bold result
            pdf.set_font(BODY_FONT_NAME, 'B', 12)
            pdf.write(7, f"{batches_per_hour:.2f} batches/hour")
            pdf.ln()
            pdf.set_font(BODY_FONT_NAME, '', 12)

            # Add average cycle time
            if batches_per_hour > 0:
                seconds_per_batch = 3600 / batches_per_hour
                m, s = divmod(seconds_per_batch, 60)
                h, m = divmod(m, 60)
                cycle_time_str = "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))
                
                pdf.cell(label_width, 7, "----> ", ln=0)
                pdf.set_font(BODY_FONT_NAME, 'B', 12)
                pdf.cell(value_width, 7, f"{cycle_time_str} average cycle time", ln=1)
                pdf.set_font(BODY_FONT_NAME, '', 12)
        
        pdf.ln(8)  # Blank line
        
        # Simulation summary section
        pdf.set_font(BODY_FONT_NAME, 'B', 12)
        pdf.cell(0, 8, f"Simulation summary - Status: {solver_status}", ln=1)
        pdf.set_font(BODY_FONT_NAME, '', 12)
        
        # Target time from production_targets
        target_duration_hours = prod_targets.get('simulation_duration_hours', 0)
        pdf.cell(label_width, 7, "Target time:", ln=0)
        pdf.cell(value_width, 7, f"{target_duration_hours} hours", ln=1)
        
        # Calculate expected batches: batches_per_hour × target_duration_hours, rounded up
        import math
        expected_batches = math.ceil(batches_per_hour * target_duration_hours)
        pdf.cell(label_width, 7, "Target batches:", ln=0)
        pdf.write(7, f"{expected_batches} (Target time x Batches/hour)")
        pdf.ln()
        pdf.cell(label_width, 7, "Available units:", ln=0)
        pdf.cell(value_width, 7, f"{available_containers}", ln=1)
        pdf.cell(label_width, 7, "Total time:", ln=0)
        pdf.cell(value_width, 7, f"{total_prod_time}", ln=1)
        pdf.cell(label_width, 7, "Ramp-up:", ln=0)
        pdf.cell(value_width, 7, f"{ramp_up}", ln=1)
        pdf.cell(label_width, 7, "Steady-state:", ln=0)
        pdf.cell(value_width, 7, f"{steady}", ln=1)
        pdf.cell(label_width, 7, "Ramp-down:", ln=0)
        pdf.cell(value_width, 7, f"{ramp_down}", ln=1)
        pdf.ln(8)  # Blank line after simulation summary


    # ===== TABLE OF CONTENTS (always page 2) =====
    pdf.add_page()
    pdf.chapter_title('Table of Contents')
    toc_items = [
        ('Basic Information', '3'),
        ('Executive Summary', '4'),
        ('Transporter - Physics Profile', '5'),
        ('Transporter - Performance', '6'),
        ('Station Occupation Analysis', '7'),
        ('Appendix 1 - Stations', None),
        ('Appendix 2 - Transporters', None),
        ('Appendix 3 - Treatment programs', None),
        ('Appendix 4 - Flowchart', None),
    ]
    pdf.ln(8)
    toc_font_size = 13
    toc_line_height = 10
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    for label, page in toc_items:
        pdf.set_font(BODY_FONT_NAME, '', toc_font_size)
        pdf.set_x(pdf.l_margin)
        if page is None:
            pdf.cell(available_width, toc_line_height, label, 0, 1, 'L')
        else:
            pdf.cell(available_width * 0.7, toc_line_height, label, 0, 0, 'L')
            pdf.cell(available_width * 0.3, toc_line_height, page, 0, 1, 'R')
    pdf.ln(7)

    # --- After ToC, add customer/plant info page ---
    add_customer_plant_info_page()

    # ===== EXECUTIVE SUMMARY =====
    pdf.add_page()
    pdf.chapter_title('Executive Summary')
    # Lyhyt yhteenveto (Moved here)
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
    pdf.ln(5)
    
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
    
    # Summary text moved to top of page
    
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
    pdf.chapter_title('Transporter - Performance')
    
    pdf.section_title('Transporter Utilization')
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
    pdf.multi_cell(0, 6, 
        "Transporter utilization shows the percentage of time each transporter spent on different phases. "
        "Phases include: Idle (0), Moving to lifting station (1), Lifting (2), Moving to sinking station (3), Sinking (4). "
        "Higher productive time (non-idle) indicates better resource usage.")
    pdf.ln(3)
    
    # Näytä piirakkakaaviot rinnakkain (2 per rivi), keskitetty
    if transporter_pie_charts:
        charts_per_row = 2
        # Käytetään koko sivun leveyttä
        content_width = (pdf.w - pdf.l_margin - pdf.r_margin)
        chart_width = (content_width - 10) / charts_per_row  # 10mm väli
        
        # Ryhmittele kuvat riveihin
        rows = [transporter_pie_charts[i:i + charts_per_row] for i in range(0, len(transporter_pie_charts), charts_per_row)]
        
        for row_idx, row_charts in enumerate(rows):
            # Laske tämän rivin kuvien yhteisleveys
            row_count = len(row_charts)
            row_total_width = row_count * chart_width + (row_count - 1) * 10
            
            # Laske aloituskohta (x) jotta rivi on keskellä sivua
            page_width = pdf.w - pdf.l_margin - pdf.r_margin
            start_x = pdf.l_margin + (page_width - row_total_width) / 2
            
            # Tallenna y-positio rivin alussa
            y_start = pdf.get_y()
            max_h = 0
            
            for col_idx, pie_chart in enumerate(row_charts):
                x_pos = start_x + col_idx * (chart_width + 10)
                
                with Image.open(pie_chart) as img:
                    img_w, img_h = img.size
                    h = (img_h / img_w) * chart_width
                    if h > max_h:
                        max_h = h
                
                pdf.image(pie_chart, x=x_pos, y=y_start, w=chart_width)
            
            # Siirry seuraavalle riville korkeimman kuvan mukaan
            pdf.set_y(y_start + max_h + 5)
        
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
            
            # Tarkista mahtuuko sivuun, jos ei, skaalaa pienemmäksi
            space_left = pdf.h - pdf.b_margin - pdf.get_y()
            if h > space_left:
                scale_factor = space_left / h
                w = w * scale_factor
                h = space_left
        
        # Keskitä kuva
        x_pos = pdf.l_margin + (pdf.w - pdf.l_margin - pdf.r_margin - w) / 2
        pdf.image(temporal_load_chart, x=x_pos, y=pdf.get_y(), w=w)
        pdf.ln(h + 3)
    



    # ===== STATION OCCUPATION ANALYSIS =====
    pdf.add_page()
    pdf.chapter_title('Station Occupation Analysis')
    
    # Generate radar chart
    station_radar_chart = create_station_radar_chart(output_dir, reports_dir)
    
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
    pdf.multi_cell(0, 6, 
        "This chart shows the utilization of each station. "
        "High utilization indicates potential bottlenecks.")
    pdf.ln(5)
    
    available_height = pdf.h - pdf.get_y() - pdf.b_margin
    
    if os.path.exists(station_chart):
        w = pdf.w - pdf.l_margin - pdf.r_margin
        x = pdf.l_margin
        with Image.open(station_chart) as img:
            img_w, img_h = img.size
            h = (img_h / img_w) * w
            
            # If radar chart exists, limit height of the first chart to allow space
            if station_radar_chart and os.path.exists(station_radar_chart):
                max_h = available_height * 0.55
                if h > max_h:
                    scale = max_h / h
                    h = max_h
                    w = w * scale
                    x = pdf.l_margin + (pdf.w - pdf.l_margin - pdf.r_margin - w) / 2
        
        pdf.image(station_chart, x=x, y=pdf.get_y(), w=w)
        pdf.ln(h + 5)
        
    if station_radar_chart and os.path.exists(station_radar_chart):
        w = pdf.w - pdf.l_margin - pdf.r_margin
        x = pdf.l_margin
        with Image.open(station_radar_chart) as img:
            img_w, img_h = img.size
            h = (img_h / img_w) * w
            
            # Fit to remaining space
            space_left = pdf.h - pdf.get_y() - pdf.b_margin
            if h > space_left:
                scale = space_left / h
                h = space_left
                w = w * scale
                x = pdf.l_margin + (pdf.w - pdf.l_margin - pdf.r_margin - w) / 2
                
        pdf.image(station_radar_chart, x=x, y=pdf.get_y(), w=w)
        pdf.ln(h + 5)

    # ===== APPENDIX 1 - STATIONS =====
    pdf.add_page()
    pdf.chapter_title('Appendix 1 - Stations')
    
    stations_json_path = os.path.join(output_dir, 'initialization', 'stations.json')
    if os.path.exists(stations_json_path):
        with open(stations_json_path, 'r') as f:
            stations_data = json.load(f)
            
        stations = stations_data.get('stations', [])
        
        # Table configuration
        # Adjust widths to fit page (A4 width ~210mm, margins 20+10=30mm, available ~180mm)
        col_widths = [20, 85, 25, 25, 25]
        headers = ['Number', 'Name', 'X Pos', 'Drop (s)', 'Devices (s)']
        
        # Header
        pdf.set_font(BODY_FONT_NAME, 'B', 10)
        pdf.set_fill_color(200, 200, 200)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, header, 1, 0, 'C', 1)
        pdf.ln()
        
        # Rows
        pdf.set_font(BODY_FONT_NAME, '', 9)
        for station in stations:
            # Check for page break
            if pdf.get_y() > 270:
                pdf.add_page()
                # Re-print header
                pdf.set_font(BODY_FONT_NAME, 'B', 10)
                pdf.set_fill_color(200, 200, 200)
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 8, header, 1, 0, 'C', 1)
                pdf.ln()
                pdf.set_font(BODY_FONT_NAME, '', 9)

            # Format floats
            try:
                drop_time = float(station.get('dropping_time', 0))
                drop_str = f"{drop_time:.1f}"
            except (ValueError, TypeError):
                drop_str = "0.0"

            try:
                device_delay = float(station.get('device_delay', 0))
                device_str = f"{device_delay:.1f}"
            except (ValueError, TypeError):
                device_str = "0.0"

            pdf.cell(col_widths[0], 6, str(station.get('number', '')), 1, 0, 'C')
            pdf.cell(col_widths[1], 6, str(station.get('name', '')), 1, 0, 'L')
            pdf.cell(col_widths[2], 6, str(station.get('x_position', '')), 1, 0, 'C')
            pdf.cell(col_widths[3], 6, drop_str, 1, 0, 'C')
            pdf.cell(col_widths[4], 6, device_str, 1, 1, 'C')
    else:
        pdf.set_font(BODY_FONT_NAME, 'I', 11)
        pdf.cell(0, 10, "Stations data not found.", 0, 1)

    # ===== APPENDIX 2 - TRANSPORTERS =====
    pdf.add_page()
    pdf.chapter_title('Appendix 2 - Transporters')
    
    transporters_json_path = os.path.join(output_dir, 'initialization', 'transporters.json')
    if os.path.exists(transporters_json_path):
        with open(transporters_json_path, 'r') as f:
            transporters_data = json.load(f)
            
        transporters = transporters_data.get('transporters', [])
        
        if transporters:
            # Define rows (Attribute Label, Accessor Function)
            rows_config = [
                ('ID', lambda t: str(t.get('id', ''))),
                ('Model', lambda t: str(t.get('model', ''))),
                ('Start Station', lambda t: str(t.get('start_station', ''))),
                ('X Accel Time (s)', lambda t: str(t.get('physics', {}).get('x_acceleration_time_s', ''))),
                ('X Decel Time (s)', lambda t: str(t.get('physics', {}).get('x_deceleration_time_s', ''))),
                ('X Max Speed (mm/s)', lambda t: str(t.get('physics', {}).get('x_max_speed_mm_s', ''))),
                ('Z Total Dist (mm)', lambda t: str(t.get('physics', {}).get('z_total_distance_mm', ''))),
                ('Z Slow Dry (mm)', lambda t: str(t.get('physics', {}).get('z_slow_distance_dry_mm', ''))),
                ('Z Slow Wet (mm)', lambda t: str(t.get('physics', {}).get('z_slow_distance_wet_mm', ''))),
                ('Z Slow End (mm)', lambda t: str(t.get('physics', {}).get('z_slow_end_distance_mm', ''))),
                ('Z Slow Speed (mm/s)', lambda t: str(t.get('physics', {}).get('z_slow_speed_mm_s', ''))),
                ('Z Fast Speed (mm/s)', lambda t: str(t.get('physics', {}).get('z_fast_speed_mm_s', ''))),
                ('Avoid Dist (mm)', lambda t: str(t.get('physics', {}).get('avoid_distance_mm', ''))),
            ]
            
            # Column widths
            # First column (Labels): 60mm
            # Data columns: Remaining width divided by num transporters (max 50mm per col)
            label_col_width = 60
            available_width = pdf.w - pdf.l_margin - pdf.r_margin - label_col_width
            num_transporters = len(transporters)
            data_col_width = min(50, available_width / num_transporters) if num_transporters > 0 else 50
            
            # Header Row (Transporter IDs)
            pdf.set_font(BODY_FONT_NAME, 'B', 10)
            pdf.set_fill_color(200, 200, 200)
            
            # Top-left cell
            pdf.cell(label_col_width, 8, "Attribute", 1, 0, 'L', 1)
            
            for t in transporters:
                t_name = f"Transporter {t.get('id', '?')}"
                pdf.cell(data_col_width, 8, t_name, 1, 0, 'C', 1)
            pdf.ln()
            
            # Data Rows
            pdf.set_font(BODY_FONT_NAME, '', 10)
            for label, accessor in rows_config:
                pdf.set_font(BODY_FONT_NAME, 'B', 10)
                pdf.cell(label_col_width, 7, label, 1, 0, 'L')
                
                pdf.set_font(BODY_FONT_NAME, '', 10)
                for t in transporters:
                    val = accessor(t)
                    pdf.cell(data_col_width, 7, val, 1, 0, 'C')
                pdf.ln()
                
        else:
             pdf.set_font(BODY_FONT_NAME, 'I', 11)
             pdf.cell(0, 10, "No transporters found in data.", 0, 1)
             
    else:
        pdf.set_font(BODY_FONT_NAME, 'I', 11)
        pdf.cell(0, 10, "Transporters data not found.", 0, 1)

    # ===== APPENDIX 3 - TREATMENT PROGRAMS =====
    pdf.add_page()
    pdf.chapter_title('Appendix 3 - Treatment programs')
    
    # Load station names for mapping
    station_names = {}
    stations_json_path = os.path.join(output_dir, 'initialization', 'stations.json')
    if os.path.exists(stations_json_path):
        with open(stations_json_path, 'r') as f:
            s_data = json.load(f)
            for s in s_data.get('stations', []):
                station_names[int(s.get('number'))] = s.get('name', '')

    # Find treatment program files
    init_dir = os.path.join(output_dir, 'initialization')
    if os.path.exists(init_dir):
        program_files = [f for f in os.listdir(init_dir) if f.startswith('treatment_program_') and f.endswith('.csv')]
        program_files.sort()
        
        if not program_files:
            pdf.set_font(BODY_FONT_NAME, 'I', 11)
            pdf.cell(0, 10, "No treatment program files found.", 0, 1)
        
        for p_file in program_files:
            pdf.section_title(f"Program: {p_file}")
            
            try:
                df = pd.read_csv(os.path.join(init_dir, p_file))
                
                # Table config
                # Columns: Stage, MinStat, MaxStat, Station Name, MinTime, MaxTime
                # Widths: 15, 20, 20, 60, 25, 25 = 165
                col_widths = [15, 20, 20, 60, 25, 25]
                headers = ['Stage', 'Min', 'Max', 'Station Name', 'Min Time', 'Max Time']
                
                # Header
                pdf.set_font(BODY_FONT_NAME, 'B', 10)
                pdf.set_fill_color(200, 200, 200)
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 8, header, 1, 0, 'C', 1)
                pdf.ln()
                
                # Rows
                pdf.set_font(BODY_FONT_NAME, '', 9)
                for _, row in df.iterrows():
                    # Check page break
                    if pdf.get_y() > 270:
                        pdf.add_page()
                        pdf.set_font(BODY_FONT_NAME, 'B', 10)
                        pdf.set_fill_color(200, 200, 200)
                        for i, header in enumerate(headers):
                            pdf.cell(col_widths[i], 8, header, 1, 0, 'C', 1)
                        pdf.ln()
                        pdf.set_font(BODY_FONT_NAME, '', 9)
                    
                    min_stat = int(row.get('MinStat', 0))
                    max_stat = int(row.get('MaxStat', 0))
                    stat_name = station_names.get(min_stat, '')
                    
                    pdf.cell(col_widths[0], 6, str(row.get('Stage', '')), 1, 0, 'C')
                    pdf.cell(col_widths[1], 6, str(min_stat), 1, 0, 'C')
                    pdf.cell(col_widths[2], 6, str(max_stat), 1, 0, 'C')
                    pdf.cell(col_widths[3], 6, str(stat_name), 1, 0, 'L')
                    pdf.cell(col_widths[4], 6, str(row.get('MinTime', '')), 1, 0, 'C')
                    pdf.cell(col_widths[5], 6, str(row.get('MaxTime', '')), 1, 1, 'C')
                
                pdf.ln(10)
            except Exception as e:
                pdf.set_font(BODY_FONT_NAME, 'I', 11)
                pdf.cell(0, 10, f"Error reading {p_file}: {str(e)}", 0, 1)
    else:
        pdf.set_font(BODY_FONT_NAME, 'I', 11)
        pdf.cell(0, 10, "Initialization directory not found.", 0, 1)


    


    

    
    # ===== APPENDIX 4 - FLOWCHART =====
    # Add matrix timeline pages (one per page, rotated 90 degrees counter-clockwise)
    images_dir = os.path.join(reports_dir, 'images')
    matrix_pages = sorted([f for f in os.listdir(images_dir) if f.startswith('matrix_timeline_page_') and f.endswith('.png') and '_rotated' not in f])
    
    if matrix_pages:
        # Add each matrix page (one per PDF page, rotated)
        for i, matrix_page in enumerate(matrix_pages, 1):
            matrix_path = os.path.join(images_dir, matrix_page)
            
            # Add new page
            pdf.add_page()
            pdf.chapter_title(f'Appendix 4 - Flowchart (Page {i}/{len(matrix_pages)})')
            
            # Use pre-rotated image if available, otherwise use original
            rotated_path = matrix_path.replace('.png', '_rotated.png')
            image_to_use = rotated_path if os.path.exists(rotated_path) else matrix_path
            
            try:
                with Image.open(image_to_use) as img:
                    # Calculate dimensions to fit page after header
                    current_y = pdf.get_y()
                    page_width = pdf.w - pdf.l_margin - pdf.r_margin
                    available_height = pdf.h - current_y - pdf.b_margin
                    
                    img_width, img_height = img.size
                    aspect_ratio = img_width / img_height
                    
                    # Scale to fit available space while maintaining aspect ratio
                    if page_width / available_height > aspect_ratio:
                        # Height is limiting
                        pdf_height = available_height * 0.98
                        pdf_width = pdf_height * aspect_ratio
                    else:
                        # Width is limiting
                        pdf_width = page_width * 0.98
                        pdf_height = pdf_width / aspect_ratio
                    
                    # Center horizontally, place below header
                    x = pdf.l_margin + (page_width - pdf_width) / 2
                    y = current_y
                    
                    # Add image to PDF
                    pdf.image(image_to_use, x=x, y=y, w=pdf_width, h=pdf_height)
                    
            except Exception as e:
                print(f"[WARN] Could not add matrix page {matrix_page}: {e}")
    
    # Tallenna PDF
    pdf_path = os.path.join(reports_dir, f'simulation_report_{folder_name}.pdf')
    pdf.output(pdf_path)
    print(f"✅ Simulation report generated: {pdf_path}")
    
    return pdf_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
        generate_simulation_report(output_dir)
    else:
        print("Usage: python generate_simulation_report.py <output_directory>")
