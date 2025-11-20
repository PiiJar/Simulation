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
    cycle_time_seconds = report_data.get('simulation', {}).get('steady_state_avg_cycle_time_seconds', 0)
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
        pdf.ln(2)

        # Draw the Z-profile bar as before
        left = pdf.l_margin + 2
        bar_width = 12
        top = pdf.get_y() + 4
        max_bar_height = max(100, pdf.h * 0.45)
        bar_height = min(max_bar_height, pdf.h - top - 70)
        bar_height = bar_height * float(Z_BAR_VERTICAL_SCALE)
        scale = bar_height / ZT if ZT > 0 else 1.0

        fill_color = top_color
        if color_map and t in color_map:
            try:
                hexc = color_map[t]
                rcol, gcol, bcol = tuple(int(hexc.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                fill_color = (rcol, gcol, bcol)
            except Exception:
                pass
        pdf.set_draw_color(*border)
        pdf.set_fill_color(*fill_color)
        pdf.rect(left, top, bar_width, bar_height, 'F')
        pdf.rect(left, top, bar_width, bar_height, 'D')

        # --- NEW: Speed vs Time plot for x-movement (horizontal) ---
        # Read transporter x-physics from CSV
        import matplotlib.pyplot as plt
        import numpy as np
        import tempfile
        import pandas as pd
        # Find transporter row in physics CSV
        candidates = [
            os.path.join(output_dir, 'cp_sat', 'cp_sat_transporters.csv'),
            os.path.join(output_dir, 'initialization', 'transporters.csv'),
        ]
        path = next((p for p in candidates if os.path.exists(p)), None)
        if path:
            df = pd.read_csv(path)
            tid_col = None
            for key in ['Transporter_id', 'Transporter', 'Id']:
                if key in df.columns:
                    tid_col = key
                    break
            if tid_col is None:
                tid_col = df.columns[0]
            row = df[df[tid_col] == t]
            if row.empty:
                row = df[df[tid_col].astype(str) == str(t)]
            if not row.empty:
                row = row.iloc[0]
                # Get physics params
                max_speed = float(row.get('Max_speed (mm/s)', 0.0))
                acc_time = float(row.get('Acceleration_time (s)', 0.0))
                dec_time = float(row.get('Deceleration_time (s)', 0.0))
                # Only plot if all params are positive
                if max_speed > 0 and acc_time > 0 and dec_time > 0:
                    def speed_profile(distance):
                        # Returns (t, v) arrays for the move
                        accel = max_speed / acc_time
                        decel = max_speed / dec_time
                        t_accel_full = max_speed / accel
                        t_decel_full = max_speed / decel
                        s_accel_full = 0.5 * accel * t_accel_full ** 2
                        s_decel_full = 0.5 * decel * t_decel_full ** 2
                        
                        if distance < s_accel_full + s_decel_full:
                            # Triangular profile - doesn't reach max_speed
                            # v_peak^2 = 2 * accel * s_accel
                            # v_peak^2 = 2 * decel * s_decel
                            # s_accel + s_decel = distance
                            # Solve: v_peak = sqrt(2 * distance * accel * decel / (accel + decel))
                            v_peak = np.sqrt(2 * distance * accel * decel / (accel + decel))
                            t_accel = v_peak / accel
                            t_decel = v_peak / decel
                            t_total = t_accel + t_decel
                            t = np.linspace(0, t_total, 100)
                            v = np.where(t < t_accel, 
                                        accel * t, 
                                        v_peak - decel * (t - t_accel))
                            v = np.clip(v, 0, v_peak)
                        else:
                            # Trapezoidal profile
                            s_const = distance - s_accel_full - s_decel_full
                            t_const = s_const / max_speed
                            t1 = np.linspace(0, t_accel_full, 40)
                            t2 = np.linspace(t_accel_full, t_accel_full + t_const, 20)
                            t3 = np.linspace(t_accel_full + t_const, t_accel_full + t_const + t_decel_full, 40)
                            v1 = accel * t1
                            v2 = np.full_like(t2, max_speed)
                            v3 = max_speed - decel * (t3 - (t_accel_full + t_const))
                            t = np.concatenate([t1, t2, t3])
                            v = np.concatenate([v1, v2, v3])
                            v = np.clip(v, 0, max_speed)
                        return t, v

                    # increase figure size to make the X-graph taller; was (5.5,2.2)
                    fig, ax = plt.subplots(figsize=(8.5, 4.2))
                    # Use transporter color for all curves
                    transporter_color = fill_color  # Using the same color as the Z-profile bar
                    # Convert RGB tuple (0-255) to hex for matplotlib
                    if isinstance(transporter_color, tuple) and len(transporter_color) == 3:
                        transporter_hex = '#{:02x}{:02x}{:02x}'.format(
                            int(transporter_color[0]), 
                            int(transporter_color[1]), 
                            int(transporter_color[2])
                        )
                    else:
                        transporter_hex = '#3498db'  # fallback blue
                    
                    dists = [500, 2500, 5000]
                    labels = ['500 mm move', '2500 mm move', '5000 mm move']
                    all_tmax = []
                    all_vmax = []
                    for i, dist in enumerate(dists):
                        tvals, vvals = speed_profile(dist)
                        all_tmax.append(np.max(tvals) if len(tvals) else 0)
                        all_vmax.append(np.max(vvals) if len(vvals) else 0)
                        ax.plot(tvals, vvals, color=transporter_hex, label=labels[i], alpha=0.7 + i*0.15, linewidth=2)

                    # Determine axis bounds: origin at (0,0) in lower-left
                    import math
                    max_t = max(all_tmax) if all_tmax else 0
                    max_v = max(all_vmax) if all_vmax else 0
                    # Ceil to next full second for nicer integer ticks
                    max_t_ceiled = max(1, int(math.ceil(max_t)))
                    max_v_ceiled = max(1, int(math.ceil(max_v)))
                    # Add small margin to ensure rightmost gridline is visible
                    ax.set_xlim(0, max_t_ceiled + 0.5)
                    ax.set_ylim(0, max_v_ceiled)

                    # Set x-axis ticks to full-second integer ticks
                    xticks = np.arange(0, max_t_ceiled + 1, 1)
                    ax.set_xticks(xticks)

                    # Ensure spine/axis placement is the conventional lower-left origin
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.xaxis.set_ticks_position('bottom')
                    ax.yaxis.set_ticks_position('left')

                    # No tick marks - only labels
                    ax.tick_params(axis='x', which='major', length=0, width=0)
                    ax.tick_params(axis='y', which='major', length=0, width=0)
                    ax.minorticks_off()

                    # Use consistent font sizes optimized for visual appearance in PDF
                    # These sizes are tuned to match the upper Z-graph visual appearance
                    ax.set_xlabel('Time (s)', fontsize=10)
                    ax.set_ylabel('Speed (mm/s)', fontsize=10)
                    ax.tick_params(axis='both', which='major', labelsize=10)

                    # No standalone title per request; legend removed
                    ax.grid(alpha=0.3)
                    
                    # Add distance labels at end of each curve (right-aligned near endpoint, above X-axis)
                    for i, (dist, label_text) in enumerate(zip(dists, ['500 mm', '2500 mm', '5000 mm'])):
                        tvals, vvals = speed_profile(dist)
                        if len(tvals) > 0:
                            # Get endpoint coordinates
                            t_end = tvals[-1]
                            # Place text above X-axis (positive Y), slightly left of endpoint
                            ax.text(t_end - 0.3, max_v_ceiled * 0.05, label_text, 
                                   ha='right', va='bottom', fontsize=10, color='black',
                                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='none', alpha=0.8))
                    
                    plt.tight_layout()
                    # Save to temp file and insert into PDF
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmpf:
                        fig.savefig(tmpf.name, dpi=120, bbox_inches='tight')
                        plt.close(fig)
                        img_x = left + bar_width + 15
                        img_y = top + bar_height + 15
                        img_w = pdf.w - pdf.l_margin - img_x - 2
                        # triple the previous image height to make the X-graph three times taller, then reduce by 10%
                        img_h = 38 * 3 * 0.9  # mm (reduced by 10%)
                        # Place image full width below Z-bar with increased margin
                        pdf.set_xy(pdf.l_margin, top + bar_height + 15)
                        pdf.image(tmpf.name, x=pdf.l_margin, y=top + bar_height + 15, w=pdf.w - pdf.l_margin - pdf.r_margin, h=img_h)
        # --- END NEW ---

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
                    pdf.set_font(BODY_FONT_NAME, '', max(8, BODY_FONT_SIZE - 1))
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

            # Horizontal helper lines across the axes at measurement levels (behind curves)
            try:
                pdf.set_line_width(0.2)
                pdf.set_draw_color(200, 200, 200)
                for val in (ZD, ZW, Z_fast_end, ZT):
                    if val is None:
                        continue
                    y_pos = top + bar_height - (val * scale)
                    if y_pos < top:
                        y_pos = top
                    if y_pos > top + bar_height:
                        y_pos = top + bar_height
                    # draw faint horizontal line across the time-axis area
                    pdf.line(axis_x, y_pos, axis_x + axis_width, y_pos)
            except Exception:
                pass

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

            # Horizontal axis (time) at axis_bottom - BLACK color
            pdf.set_draw_color(0, 0, 0)
            pdf.set_line_width(0.5)
            pdf.line(axis_x, axis_bottom, axis_x + axis_width, axis_bottom)
            # choose mm per 0.5s
            mm_per_half_sec = 10
            # limit by axis_width
            num_div = int(axis_width // mm_per_half_sec)
            pdf.set_font(BODY_FONT_NAME, '', max(8, BODY_FONT_SIZE - 1))
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
            pdf.set_font(BODY_FONT_NAME, '', max(8, BODY_FONT_SIZE - 1))
            # Draw faint vertical grid lines at each full second across the axes
            for s in range(0, num_seconds + 1, tick_seconds):
                frac = s / float(max(1, num_seconds))
                x_tick = axis_x + frac * axis_width
                # grid line (light gray) - keep for time reference
                pdf.set_draw_color(200, 200, 200)
                pdf.set_line_width(0.2)
                pdf.line(x_tick, axis_bottom, x_tick, axis_top)
                # tick mark REMOVED per user request - no black marks on X-axis
                # Label only (black text)
                pdf.set_draw_color(0, 0, 0)
                txt = f"{s:d}"
                pdf.set_xy(x_tick - 6, axis_bottom + 1)
                pdf.cell(12, 4, txt, ln=0, align='C')
                pdf.set_x(pdf.l_margin)

            # Axis titles
            # NOTE: per request, do not render the Y-axis 'Height (mm)' label to reduce clutter
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(BODY_FONT_NAME, '', max(8, BODY_FONT_SIZE - 1))
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
                                # Raise labels higher (y - 6 instead of y - 2) to prevent overlap with grid lines
                                if 'type1 lift' in lbl_map:
                                    et = end_time_map.get('type1 lift', effective_total_seconds)
                                    lx = compute_anchor_x_for_label(et)
                                    lx = fit_text_x(lx, lbl_map['type1 lift'])
                                    pdf.set_xy(lx, y_lift - 6)
                                    pdf.cell(0, 4, lbl_map['type1 lift'], ln=0, align='L')

                                if 'type0 lift' in lbl_map:
                                    et = end_time_map.get('type0 lift', effective_total_seconds)
                                    lx = compute_anchor_x_for_label(et)
                                    lx = fit_text_x(lx, lbl_map['type0 lift'])
                                    pdf.set_xy(lx, y_lift - 6)
                                    pdf.cell(0, 4, lbl_map['type0 lift'], ln=0, align='L')

                                if 'type1 sink' in lbl_map:
                                    et = end_time_map.get('type1 sink', effective_total_seconds)
                                    lx = compute_anchor_x_for_label(et)
                                    lx = fit_text_x(lx, lbl_map['type1 sink'])
                                    pdf.set_xy(lx, y_sink + 2)
                                    pdf.cell(0, 4, lbl_map['type1 sink'], ln=0, align='L')

                                if 'type0 sink' in lbl_map:
                                    et = end_time_map.get('type0 sink', effective_total_seconds)
                                    lx = compute_anchor_x_for_label(et)
                                    lx = fit_text_x(lx, lbl_map['type0 sink'])
                                    pdf.set_xy(lx, y_sink + 2)
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
    transporter_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_transporter_schedule.csv'))
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
    transporter_schedule = pd.read_csv(os.path.join(output_dir, 'cp_sat', 'cp_sat_transporter_schedule.csv'))
    
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
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    chart_path = os.path.join(images_dir, 'transporter_batch_occupation.png')
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
    images_dir = os.path.join(reports_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    chart_path = os.path.join(images_dir, 'batch_leadtime_chart.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


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
    pdf.set_font('Arial', 'B', 28)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 15, 'Simulation Report', ln=1, align='C')
    pdf.ln(10)
    
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
                conflicts = os.path.join(output_dir, 'cp_sat', 'cp_sat_transporter_conflicts.csv')
                transporter = os.path.join(output_dir, 'cp_sat', 'cp_sat_transporter_schedule.csv')
                if os.path.exists(conflicts):
                    solver_status = 'INFEASIBLE'
                elif os.path.exists(transporter):
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
        pdf.chapter_title('Customer and Plant Information')
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
        ('Customer and Plant Information', '3'),
        ('Executive Summary', '4'),
        ('Transporter Performance Analysis', 'xx'),
        ('Station Occupation Analysis', 'xx'),
        ('Conclusions', 'xx'),
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
    pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
    pdf.multi_cell(0, 6, 
        "Key performance indicators from the simulation run. "
        "These metrics provide a high-level overview of production efficiency, "
        "resource utilization, and throughput.")
    pdf.ln(5)

    # Add production status cards (3 across)
    cards_dir = os.path.join(output_dir, 'reports', 'images')
    card_files = [
        'card_annual_production.png',
        'card_performance.png',
        'card_workload_balance.png'
    ]
    cards_exist = all(os.path.exists(os.path.join(cards_dir, cf)) for cf in card_files)
    if cards_exist:
        y_start = pdf.get_y()
        # Use same layout as KPI boxes: 3 cards across with consistent spacing
        card_width_mm = 55  # Same width as KPI boxes
        card_height_mm = 55  # Square cards
        x_spacing = 62  # Same spacing as KPI boxes (55mm + 7mm gap)
        x_start = pdf.l_margin
        for idx, card_file in enumerate(card_files):
            card_path = os.path.join(cards_dir, card_file)
            x = x_start + idx * x_spacing
            pdf.image(card_path, x=x, y=y_start, w=card_width_mm, h=card_height_mm)
        # Move below the cards
        pdf.set_y(y_start + card_height_mm + 8)
    pdf.ln(3)
    
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
    pdf.add_page()
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
    pdf.chapter_title('Stations')
    
    # --- Stations Configuration Table ---
    init_dir_abs = os.path.join(output_dir, '..', '..', 'initialization')
    task_areas_csv = os.path.join(init_dir_abs, 'transporters _task_areas.csv')
    
    # Load stations from JSON
    from load_stations_json import load_stations_from_json
    stations_df = load_stations_from_json(init_dir_abs)
    
    # Load transporter task areas
    task_areas = {}
    if os.path.exists(task_areas_csv):
        task_areas_df = pd.read_csv(task_areas_csv)
        for _, tr in task_areas_df.iterrows():
            tr_id = int(tr['Transporter_id'])
            task_areas[tr_id] = {
                'lift_min_100': int(tr['Min_Lift_Station_100']),
                'lift_max_100': int(tr['Max_Lift_Station_100']),
                'sink_min_100': int(tr['Min_Sink_Station_100']),
                'sink_max_100': int(tr['Max_Sink_Station_100']),
            }
        
        # Helper function to convert hex color to RGB tuple
        def hex_to_rgb(hex_color):
            """Convert hex color (#RRGGBB) to RGB tuple (R, G, B)"""
            if hex_color.startswith('#'):
                hex_color = hex_color[1:]
            return (
                int(hex_color[0:2], 16),
                int(hex_color[2:4], 16),
                int(hex_color[4:6], 16)
            )
        
        pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
        pdf.multi_cell(0, 6,
            "The table below shows the configuration of all stations in the production line, including their "
            "tank assignments, positions, processing times, and equipment delays. 'X' symbols indicate transporter work zones "
            "with colors matching each transporter. Stations with the same Group number are interchangeable in the process.")
        pdf.ln(5)
        
        # Table configuration
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(200, 200, 200)
        
        # Column widths - spans content width (210mm - 20mm left margin - 10mm right margin = 180mm total)
        # Added Tank column, adjusted widths
        col_widths = [14, 12, 12, 10, 10, 10, 10, 50, 16, 16, 16]
        headers = ['Station', 'Tank', 'Group', 'L1', 'S1', 'L2', 'S2', 'Name', 'X Pos', 'Drop (s)', 'Device (s)']
        
        # Header row with colored transporter columns
        for i, header in enumerate(headers):
            # Color transporter headers to match their colors
            if header == 'L1' or header == 'S1':
                if color_map and 1 in color_map:
                    r, g, b = hex_to_rgb(color_map[1])
                    pdf.set_text_color(r, g, b)
            elif header == 'L2' or header == 'S2':
                if color_map and 2 in color_map:
                    r, g, b = hex_to_rgb(color_map[2])
                    pdf.set_text_color(r, g, b)
            
            pdf.cell(col_widths[i], 7, header, 1, 0, 'C', True)
            
            # Reset text color after colored headers
            if header in ['L1', 'S1', 'L2', 'S2']:
                pdf.set_text_color(0, 0, 0)
        pdf.ln()
        
        # Data rows
        pdf.set_font('Arial', '', 9)
        for idx, row in stations_df.iterrows():
            station_num = int(row['Number'])
            tank_num = int(row['Tank'])
            group_num = int(row['Group'])
            
            # Determine transporter zone symbols (all use 'X')
            l1_has_mark = False  # Transporter 1 lift
            s1_has_mark = False  # Transporter 1 sink
            l2_has_mark = False  # Transporter 2 lift
            s2_has_mark = False  # Transporter 2 sink
            
            if 1 in task_areas:
                if task_areas[1]['lift_min_100'] <= station_num <= task_areas[1]['lift_max_100']:
                    l1_has_mark = True
                if task_areas[1]['sink_min_100'] <= station_num <= task_areas[1]['sink_max_100']:
                    s1_has_mark = True
            
            if 2 in task_areas:
                if task_areas[2]['lift_min_100'] <= station_num <= task_areas[2]['lift_max_100']:
                    l2_has_mark = True
                if task_areas[2]['sink_min_100'] <= station_num <= task_areas[2]['sink_max_100']:
                    s2_has_mark = True
            
            # Alternate row background: white (False) and light gray (True)
            fill = idx % 2 == 1
            if fill:
                pdf.set_fill_color(245, 245, 245)
            
            # Regular columns
            pdf.cell(col_widths[0], 6, str(station_num), 1, 0, 'C', fill)
            pdf.cell(col_widths[1], 6, str(tank_num), 1, 0, 'C', fill)
            pdf.cell(col_widths[2], 6, str(group_num), 1, 0, 'C', fill)
            
            # Transporter zone columns with colored and bold 'X'
            # L1 - Transporter 1 lift
            if l1_has_mark and color_map and 1 in color_map:
                r, g, b = hex_to_rgb(color_map[1])
                pdf.set_text_color(r, g, b)
                pdf.set_font('Arial', 'B', 9)  # Bold for X
                pdf.cell(col_widths[3], 6, 'X', 1, 0, 'C', fill)
                pdf.set_font('Arial', '', 9)  # Reset to regular
                pdf.set_text_color(0, 0, 0)  # Reset to black
            else:
                pdf.cell(col_widths[3], 6, '', 1, 0, 'C', fill)
            
            # S1 - Transporter 1 sink
            if s1_has_mark and color_map and 1 in color_map:
                r, g, b = hex_to_rgb(color_map[1])
                pdf.set_text_color(r, g, b)
                pdf.set_font('Arial', 'B', 9)  # Bold for X
                pdf.cell(col_widths[4], 6, 'X', 1, 0, 'C', fill)
                pdf.set_font('Arial', '', 9)  # Reset to regular
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(col_widths[4], 6, '', 1, 0, 'C', fill)
            
            # L2 - Transporter 2 lift
            if l2_has_mark and color_map and 2 in color_map:
                r, g, b = hex_to_rgb(color_map[2])
                pdf.set_text_color(r, g, b)
                pdf.set_font('Arial', 'B', 9)  # Bold for X
                pdf.cell(col_widths[5], 6, 'X', 1, 0, 'C', fill)
                pdf.set_font('Arial', '', 9)  # Reset to regular
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(col_widths[5], 6, '', 1, 0, 'C', fill)
            
            # S2 - Transporter 2 sink
            if s2_has_mark and color_map and 2 in color_map:
                r, g, b = hex_to_rgb(color_map[2])
                pdf.set_text_color(r, g, b)
                pdf.set_font('Arial', 'B', 9)  # Bold for X
                pdf.cell(col_widths[6], 6, 'X', 1, 0, 'C', fill)
                pdf.set_font('Arial', '', 9)  # Reset to regular
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(col_widths[6], 6, '', 1, 0, 'C', fill)
            
            # Rest of the columns
            pdf.cell(col_widths[7], 6, str(row['Name']), 1, 0, 'L', fill)
            pdf.cell(col_widths[8], 6, f"{int(row['X Position'])}", 1, 0, 'R', fill)
            
            # Drop (s) - bold if non-zero
            drop_time = float(row['Dropping_Time'])
            if drop_time != 0:
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(col_widths[9], 6, f"{drop_time:.1f}", 1, 0, 'R', fill)
                pdf.set_font('Arial', '', 9)
            else:
                pdf.cell(col_widths[9], 6, f"{drop_time:.1f}", 1, 0, 'R', fill)
            
            # Device (s) - bold if non-zero
            device_delay = float(row['Device_delay'])
            if device_delay != 0:
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(col_widths[10], 6, f"{device_delay:.1f}", 1, 0, 'R', fill)
                pdf.set_font('Arial', '', 9)
            else:
                pdf.cell(col_widths[10], 6, f"{device_delay:.1f}", 1, 0, 'R', fill)
            
            pdf.ln()
        
        pdf.ln(10)
    
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
    
    # Stations-taulukko (tiivistetty) - Load from JSON
    from load_stations_json import load_stations_from_json
    stations_df = load_stations_from_json(init_dir)
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
            # Fallback: jos konfliktit löytyvät, merkitse INFEASIBLE; jos transporter_schedule löytyy, merkitse SOLUTION FOUND
            conflicts = os.path.join(output_dir, 'cp_sat', 'cp_sat_transporter_conflicts.csv')
            transporter = os.path.join(output_dir, 'cp_sat', 'cp_sat_transporter_schedule.csv')
            if os.path.exists(conflicts):
                solver_status_text = 'Status: INFEASIBLE (conflicts reported)'
            elif os.path.exists(transporter):
                solver_status_text = 'Status: SOLUTION FOUND (heuristic)'
            else:
                solver_status_text = 'Status: No solver output found'
    except Exception:
        solver_status_text = 'Status: Unknown (error reading status file)'

    pdf.multi_cell(0, 5, 
        "Optimization engine: Google OR-Tools CP-SAT\n"
        f"{solver_status_text}\n"
        f"Total makespan: {metrics['makespan_seconds']} seconds")
    
    # ===== APPENDIX 4 - FLOWCHART =====
    # Add matrix timeline pages (one per page, rotated 90 degrees counter-clockwise)
    images_dir = os.path.join(reports_dir, 'images')
    matrix_pages = sorted([f for f in os.listdir(images_dir) if f.startswith('matrix_timeline_page_') and f.endswith('.png') and '_rotated' not in f])
    
    if matrix_pages:
        # Add Appendix 4 title page
        pdf.add_page()
        pdf.chapter_title('Appendix 4 - Flowchart')
        pdf.set_font(BODY_FONT_NAME, '', BODY_FONT_SIZE)
        pdf.multi_cell(0, 6,
            "Matrix timeline visualization showing batch flow through stations over time. "
            "Each page displays a 5400-second (90-minute) window of the production schedule. "
            "The flowchart is rotated 90 degrees counter-clockwise for optimal viewing.")
        pdf.ln(5)
        
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
