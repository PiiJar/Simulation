import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json
import math

def format_time(seconds):
    """Formats seconds into MM:SS string."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def create_capacity_background(report_data_path, max_time_minutes=12, image_pixels=1600, dpi=100):
    """
    Creates the static background for the capacity visualization.

    This includes the axis lines, time-based grid circles, and the target cycle time circle.
    """
    max_time_seconds = max_time_minutes * 60
    requested_max_seconds = max_time_minutes * 60

    # --- 1. Setup Polar Plot ---
    figsize_inches = image_pixels / dpi
    fig, ax = plt.subplots(figsize=(figsize_inches, figsize_inches), dpi=dpi, subplot_kw={'polar': True})
    
    # Maximize plot area but leave space at bottom for legend
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0.08)
    
    # Configure the plot appearance
    ax.set_facecolor('white')
    ax.set_ylim(0, requested_max_seconds)
    
    # Hide default grid and labels
    ax.grid(False)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    
    # Remove the outer circular boundary (spine)
    ax.spines['polar'].set_visible(False)

    # We'll draw axes/ticks later after we know the required display maximum (data-driven)

    # --- 5. Load data and draw cycle time circles ---
    try:
        with open(report_data_path, 'r') as f:
            data = json.load(f)
        
        # Get simulated cycle time using the same logic as the summary page:
        # 1) If available, compute from productive time: productive_time_seconds / productive_batches
        # 2) Fallback to steady_state_avg_cycle_time_seconds
        # 3) Fallback to batches_per_hour -> 3600 / bph
        simulated_cycle_time = None
        sim_section = data.get('simulation') or data.get('simulation_results') or {}
        if sim_section:
            # Try productive metrics first (this mirrors generate_simulation_report 'takt_time_seconds')
            prod_batches = sim_section.get('productive_batches')
            prod_time_sec = sim_section.get('productive_time_seconds')
            try:
                if prod_batches and prod_time_sec and float(prod_batches) > 0 and float(prod_time_sec) > 0:
                    simulated_cycle_time = float(prod_time_sec) / float(prod_batches)
            except Exception:
                simulated_cycle_time = None

            # Fallback: steady-state average cycle time
            if not simulated_cycle_time:
                simulated_cycle_time = sim_section.get('steady_state_avg_cycle_time_seconds')

            # Final fallback: batches_per_hour -> seconds per batch
            if not simulated_cycle_time:
                bph = None
                if isinstance(sim_section.get('scaled_production_estimates'), dict):
                    bph = sim_section.get('scaled_production_estimates', {}).get('batches_per_hour')
                bph = bph or sim_section.get('batches_per_hour')
                try:
                    if bph and float(bph) > 0:
                        simulated_cycle_time = 3600.0 / float(bph)
                except Exception:
                    simulated_cycle_time = None

        # Get target cycle time from report_data (production_targets.target_cycle_time_seconds)
        target_cycle_time = None
        prod_targets = data.get('production_targets') or {}
        if isinstance(prod_targets, dict):
            target_cycle_time = prod_targets.get('target_cycle_time_seconds') or prod_targets.get('average_batch_interval_seconds')
        elif isinstance(prod_targets, list) and len(prod_targets) > 0:
            first = prod_targets[0]
            if isinstance(first, dict):
                target_cycle_time = first.get('target_cycle_time_seconds') or first.get('average_batch_interval_seconds')

        # Fallback to older locations or goals.json if still missing
        if not target_cycle_time:
            # Check possible legacy key in root
            target_cycle_time = data.get('target_cycle_time_seconds') or data.get('simulation', {}).get('target_cycle_time_seconds')
        if not target_cycle_time:
            target_cycle_time = 10 * 60
            goals_path = Path(report_data_path).parent.parent / 'initialization' / 'goals.json'
            if goals_path.exists():
                try:
                    with open(goals_path, 'r') as f:
                        goals_data = json.load(f)
                        target_pace = goals_data.get('target_pace', {})
                        target_cycle_time = target_pace.get('target_cycle_time_seconds') or target_pace.get('average_batch_interval_seconds', 10 * 60)
                except Exception as e:
                    print(f"Warning: Could not load target cycle time from goals.json: {e}")
        
        # Get capacity constraints (three key cycle time limitations)
        capacity_constraints = data.get('capacity_constraints', {}).get('constraints', {})
        
        # Point 1: Transporter limitation
        transporter_limitation = capacity_constraints.get('transporter_limitation', {})
        point1_radius = transporter_limitation.get('cycle_time_seconds', 0)
        
        # Point 2: Station limitation
        station_limitation = capacity_constraints.get('station_limitation', {})
        point2_radius = station_limitation.get('cycle_time_seconds', 0)
        
        # Point 3: Container limitation
        container_limitation = capacity_constraints.get('container_limitation', {})
        point3_radius = container_limitation.get('cycle_time_seconds', 0)
            
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error reading {report_data_path}: {e}. Using defaults.")
        simulated_cycle_time = 0
        target_cycle_time = 0
        point1_radius = 0
        point2_radius = 0
        point3_radius = 0

    # Determine the maximum radius we need to display based on data (the outermost circle)
    max_needed = max(
        simulated_cycle_time or 0,
        target_cycle_time or 0,
        point1_radius or 0,
        point2_radius or 0,
        point3_radius or 0,
    )

    # Log computed key values for diagnostics
    try:
        print(f"[capacity_elements] target_cycle_time={target_cycle_time}, simulated_cycle_time={simulated_cycle_time}")
    except Exception:
        pass

    # Axis endpoint: floor((max_needed + 120s) / 60s) * 60s
    # This ensures axes end at a full minute and extend at most 2 minutes beyond outermost circle
    axis_max_seconds = int(math.floor((max_needed + 120) / 60.0) * 60)

    # Display max for plot limits: extend slightly beyond axis end to allow tick extensions
    display_max_seconds = axis_max_seconds + 120

    # Now draw axes and ticks
    # Draw three radial axes (in degrees 90, 210, 330 -> up, lower-right, lower-left)
    angles_deg = [90, 210, 330]
    angles_rad = [np.deg2rad(d) for d in angles_deg]

    # Simplified, explicit tick rules:
    # - Major ticks: every 60 s (1 minute)
    # - Minor ticks: every 15 s (quarter minute), but not where a major tick exists
    # - Visual arc lengths are fixed to represent a small time unit (seconds)
    # - Major tick radial extensions extend up to 60s but capped at display_max_seconds
    major_interval = 60
    minor_interval = 15
    major_arc_seconds = 15   # visual arc length along circumference (in seconds)
    minor_arc_seconds = 5    # smaller visual arc for minor ticks

    for angle in angles_rad:
        # Draw axis line from 0 to axis_max_seconds (the rounded-down full minute)
        ax.plot([angle, angle], [0, axis_max_seconds], color='black', linewidth=0.9)

        # Major ticks (every 60s up to axis_max_seconds)
        for r in np.arange(major_interval, axis_max_seconds + 1, major_interval):
            if r <= 0:
                continue
            # Convert fixed arc length (in seconds) into angle offset at radius r
            angle_offset = major_arc_seconds / float(r)
            ax.plot([angle - angle_offset, angle + angle_offset], [r, r], color='black', linewidth=0.9)

            # Radial extension for major tick: extend up to 60s but not beyond display_max
            tick_extra = min(major_interval, display_max_seconds - r)
            if tick_extra > 0:
                ax.plot([angle, angle], [r, r + tick_extra], color='black', linewidth=0.9)

        # Minor ticks (every 15s but skip multiples of 60s, up to axis_max_seconds)
        for r in np.arange(minor_interval, axis_max_seconds + 1, minor_interval):
            if r <= 0 or (r % major_interval) == 0:
                continue
            angle_offset = minor_arc_seconds / float(r)
            ax.plot([angle - angle_offset, angle + angle_offset], [r, r], color='grey', linewidth=0.6)

    # Set final ylim
    ax.set_ylim(0, display_max_seconds)

    # Draw target cycle time circle (black)
    if target_cycle_time > 0 and target_cycle_time <= display_max_seconds:
        ax.plot(np.linspace(0, 2 * np.pi, 100), [target_cycle_time] * 100,
                color='black', linewidth=2.5, linestyle='-', 
                label=f'Target Cycle Time ({format_time(target_cycle_time)})')
    
    # Draw simulated cycle time circle (green if within target, red if outside)
    if simulated_cycle_time > 0 and simulated_cycle_time <= display_max_seconds:
        color = 'green' if simulated_cycle_time <= target_cycle_time else 'red'
        ax.plot(np.linspace(0, 2 * np.pi, 100), [simulated_cycle_time] * 100,
                color=color, linewidth=2.5, linestyle='-', 
                label=f'Simulated Avg Cycle Time ({format_time(simulated_cycle_time)})')
    
    # --- 6. Draw three points and connect them to form a triangle ---
    # Three capacity constraints determine triangle points:
    # Point 1: Transporter limitation on vertical axis (90 degrees)
    point1_angle = np.pi / 2
    point1_label = "Transporter Limitation"
    
    # Point 2: Station limitation on lower-right axis (210 degrees)
    point2_angle = np.deg2rad(210)
    point2_label = "Station Limitation"
    
    # Point 3: Container limitation on lower-left axis (330 degrees)
    point3_angle = np.deg2rad(330)
    point3_label = "Container Limitation"
    
    # Draw the three points with distinct colors:
    # Point 1 (Transporter): Blue
    # Point 2 (Station): Purple
    # Point 3 (Container): Dark Green
    if point1_radius > 0 and point1_radius <= display_max_seconds:
        ax.plot(point1_angle, point1_radius, 'o', color='#2196F3', markersize=10,
                label=f'{point1_label} ({format_time(point1_radius)})')

    if point2_radius > 0 and point2_radius <= display_max_seconds:
        ax.plot(point2_angle, point2_radius, 'o', color='#9C27B0', markersize=10,
                label=f'{point2_label} ({format_time(point2_radius)})')

    if point3_radius > 0 and point3_radius <= display_max_seconds:
        ax.plot(point3_angle, point3_radius, 'o', color='#2E7D32', markersize=10,
                label=f'{point3_label} ({format_time(point3_radius)})')
    
    # Connect the three points to form a triangle
    if all(r > 0 and r <= display_max_seconds for r in [point1_radius, point2_radius, point3_radius]):
        triangle_angles = [point1_angle, point2_angle, point3_angle, point1_angle]  # Close the triangle
        triangle_radii = [point1_radius, point2_radius, point3_radius, point1_radius]

        # Make triangle outline thinner and dashed so it's visually lighter
        ax.plot(triangle_angles, triangle_radii, color='darkblue', linewidth=1.0, linestyle='--', alpha=0.8)
        ax.fill(triangle_angles[:-1], triangle_radii[:-1], color='lightblue', alpha=0.3)

        # Draw circle at the furthest triangle point (bottleneck indicator)
        max_triangle_radius = max(point1_radius, point2_radius, point3_radius)
    if max_triangle_radius > 0 and max_triangle_radius <= display_max_seconds:
        ax.plot(np.linspace(0, 2 * np.pi, 100), [max_triangle_radius] * 100,
            color='orange', linewidth=2.5, linestyle='--', alpha=0.6,
            label=f'Bottleneck ({format_time(max_triangle_radius)})')
    
    # Fill the area between theoretical best (bottleneck) and simulated cycle time with transparent orange
    if max_triangle_radius > 0 and simulated_cycle_time > 0 and max_triangle_radius <= display_max_seconds and simulated_cycle_time <= display_max_seconds:
        theta = np.linspace(0, 2 * np.pi, 100)
        inner_radius = min(max_triangle_radius, simulated_cycle_time)
        outer_radius = max(max_triangle_radius, simulated_cycle_time)
        ax.fill_between(theta, inner_radius, outer_radius, color='orange', alpha=0.15)

    # Add legend at the bottom of the image
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle as LegendCircle
    
    from matplotlib.patches import Patch
    
    legend_elements = [
        Line2D([0], [0], color='black', linewidth=2, label='Time scale (minutes)'),
        Line2D([0], [0], color='black', linewidth=2.5, linestyle='-', label='Target cycle time'),
        Line2D([0], [0], color='gold', linewidth=2.5, linestyle='--', label='Theoretical best cycle time'),
        Line2D([0], [0], color='red', linewidth=2.5, linestyle='-', label='Simulated cycle time'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2196F3', markersize=10, label='Transporter constraint'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#9C27B0', markersize=10, label='Station group constraint'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2E7D32', markersize=10, label='Unit number constraint'),
        Patch(facecolor='orange', alpha=0.15, label='Task sync. constraint'),
    ]
    
    ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.02), 
              ncol=4, frameon=True, fontsize=14, fancybox=True, shadow=True)

    return fig, ax


def generate_capacity_visualization(output_dir: str):
    """
    Generate capacity visualization for the given output directory.
    
    Args:
        output_dir: Path to simulation output directory
    """
    from pathlib import Path
    
    output_path = Path(output_dir)
    report_data_file = output_path / 'reports' / 'report_data.json'
    images_dir = output_path / 'reports' / 'images'
    
    # Ensure the target directory exists
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate and save the background image
    image_pixels = 1600
    dpi = 100
    fig, _ = create_capacity_background(report_data_path=report_data_file, max_time_minutes=12, image_pixels=image_pixels, dpi=dpi)
    
    output_file = images_dir / 'capacity_elements.png'
    fig.savefig(output_file, dpi=dpi)
    
    return str(output_file)


if __name__ == '__main__':
    # Find the latest simulation directory (exclude 'previews' folder)
    output_dir = Path('output')
    simulation_dirs = [p for p in output_dir.glob('*') if p.is_dir() and p.name != 'previews']
    latest_snapshot = sorted(simulation_dirs, key=lambda p: p.stat().st_mtime)[-1]

    # Define paths within the snapshot
    report_data_file = latest_snapshot / 'reports' / 'report_data.json'
    images_dir = latest_snapshot / 'reports' / 'images'

    # Ensure the target directory exists
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from: {report_data_file}")

    # Generate and save the background image using data from the latest simulation
    image_pixels = 1600
    dpi = 100
    fig, _ = create_capacity_background(report_data_path=report_data_file, max_time_minutes=12, image_pixels=image_pixels, dpi=dpi)

    output_path = images_dir / 'capacity_elements.png'
    # Save without bbox trimming to keep exact pixel dimensions
    fig.savefig(output_path, dpi=dpi)

    print(f"Capacity visualization background saved to: {output_path}")
