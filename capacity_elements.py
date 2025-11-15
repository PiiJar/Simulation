import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json

def format_time(seconds):
    """Formats seconds into MM:SS string."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def create_capacity_background(report_data_path, max_time_minutes=12):
    """
    Creates the static background for the capacity visualization.

    This includes the axis lines, time-based grid circles, and the target cycle time circle.
    """
    max_time_seconds = max_time_minutes * 60

    # --- 1. Setup Polar Plot ---
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw={'polar': True})
    
    # Configure the plot appearance
    ax.set_facecolor('white')
    ax.set_ylim(0, max_time_seconds)
    
    # Hide default grid and labels
    ax.grid(False)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    
    # Remove the outer circular boundary (spine)
    ax.spines['polar'].set_visible(False)

    # --- 2. Draw the Three Main Axes with Scale Marks ---
    angles_deg = [90, 210, 330]
    angles_rad = [np.deg2rad(d) for d in angles_deg]
    
    # Define tick lengths as fixed visual distances
    major_tick_visual_length = 15  # For 60-second (minute) marks
    minor_tick_visual_length = 8   # For 15-second marks (shorter)
    
    for angle in angles_rad:
        # Draw the main axis line
        ax.plot([angle, angle], [0, max_time_seconds], color='black', linewidth=1.5)
        
        # Add scale marks (ticks) along each axis
        # Major ticks every 60 seconds (1 minute)
        for r in np.arange(60, max_time_seconds + 1, 60):
            # Calculate angle offset that gives constant visual length
            # Arc length = r * theta, so theta = arc_length / r
            if r > 0:
                angle_offset = major_tick_visual_length / r
                ax.plot([angle - angle_offset, angle + angle_offset], 
                       [r, r], color='black', linewidth=1.2)
        
        # Minor ticks every 15 seconds (shorter than major ticks)
        for r in np.arange(15, max_time_seconds + 1, 15):
            if r % 60 != 0:  # Skip major tick positions
                if r > 0:
                    angle_offset = minor_tick_visual_length / r
                    ax.plot([angle - angle_offset, angle + angle_offset], 
                           [r, r], color='grey', linewidth=0.8)

    # --- 5. Load data and draw cycle time circles ---
    try:
        with open(report_data_path, 'r') as f:
            data = json.load(f)
        
        # Get simulated cycle time
        simulated_cycle_time = data.get('simulation', {}).get('steady_state_avg_cycle_time_seconds', 0)
        
        # Get target cycle time from goals.json (not from report data)
        target_cycle_time = 10 * 60  # Default fallback
        goals_path = Path(report_data_path).parent.parent / 'initialization' / 'goals.json'
        if goals_path.exists():
            try:
                with open(goals_path, 'r') as f:
                    goals_data = json.load(f)
                    target_pace = goals_data.get('target_pace', {})
                    target_cycle_time = target_pace.get('average_batch_interval_seconds', 10 * 60)
            except Exception as e:
                print(f"Warning: Could not load target cycle time from goals.json: {e}")
        
        # Get maximum transporter avg time per batch (in minutes, convert to seconds)
        transporter_stats = data.get('transporter_statistics', [])
        max_transporter_time = 0
        if transporter_stats:
            max_transporter_time = max(t.get('avg_time_per_batch_minutes', 0) for t in transporter_stats) * 60
        
        # Get maximum minimum_cycle_time_seconds from all treatment program steps
        max_station_cycle_time = 0
        programs = data.get('treatment_programs', {}).get('programs', {})
        if programs:
            for program in programs.values():
                steps = program.get('steps', [])
                for step in steps:
                    cycle_time = step.get('minimum_cycle_time_seconds', 0)
                    if cycle_time > max_station_cycle_time:
                        max_station_cycle_time = cycle_time
            
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error reading {report_data_path}: {e}. Using defaults.")
        simulated_cycle_time = 0
        target_cycle_time = 0
        max_transporter_time = 0
        max_station_cycle_time = 0

    # Draw target cycle time circle (black)
    if target_cycle_time > 0 and target_cycle_time <= max_time_seconds:
        ax.plot(np.linspace(0, 2 * np.pi, 100), [target_cycle_time] * 100,
                color='black', linewidth=2.5, linestyle='-', 
                label=f'Target Cycle Time ({format_time(target_cycle_time)})')
    
    # Draw simulated cycle time circle (green if within target, red if outside)
    if simulated_cycle_time > 0 and simulated_cycle_time <= max_time_seconds:
        color = 'green' if simulated_cycle_time <= target_cycle_time else 'red'
        ax.plot(np.linspace(0, 2 * np.pi, 100), [simulated_cycle_time] * 100,
                color=color, linewidth=2.5, linestyle='-', 
                label=f'Simulated Avg Cycle Time ({format_time(simulated_cycle_time)})')
    
    # --- 6. Draw three points and connect them to form a triangle ---
    # Point 1: Max transporter time on vertical axis (90 degrees)
    point1_angle = np.pi / 2
    point1_radius = max_transporter_time if max_transporter_time > 0 else 0
    
    # Point 2: Max station cycle time on lower-right axis (210 degrees)
    point2_angle = np.deg2rad(210)
    point2_radius = max_station_cycle_time if max_station_cycle_time > 0 else 0
    
    # Point 3: Hardcoded 6 minutes on lower-left axis (330 degrees)
    point3_angle = np.deg2rad(330)
    point3_radius = 6 * 60  # 6 minutes in seconds
    
    # Draw the three points
    if point1_radius > 0 and point1_radius <= max_time_seconds:
        ax.plot(point1_angle, point1_radius, 'o', color='blue', markersize=10, 
                label=f'Max Transporter Time ({format_time(point1_radius)})')
    
    if point2_radius > 0 and point2_radius <= max_time_seconds:
        ax.plot(point2_angle, point2_radius, 'o', color='purple', markersize=10, 
                label=f'Max Station Cycle Time ({format_time(point2_radius)})')
    
    if point3_radius > 0 and point3_radius <= max_time_seconds:
        ax.plot(point3_angle, point3_radius, 'o', color='orange', markersize=10, 
                label=f'Third Point (Hardcoded: {format_time(point3_radius)})')
    
    # Connect the three points to form a triangle
    if all(r > 0 and r <= max_time_seconds for r in [point1_radius, point2_radius, point3_radius]):
        triangle_angles = [point1_angle, point2_angle, point3_angle, point1_angle]  # Close the triangle
        triangle_radii = [point1_radius, point2_radius, point3_radius, point1_radius]
        ax.plot(triangle_angles, triangle_radii, color='darkblue', linewidth=2, linestyle='-', alpha=0.7)
        ax.fill(triangle_angles[:-1], triangle_radii[:-1], color='lightblue', alpha=0.3)
        
        # Draw circle at the furthest triangle point (bottleneck indicator)
        max_triangle_radius = max(point1_radius, point2_radius, point3_radius)
        if max_triangle_radius > 0 and max_triangle_radius <= max_time_seconds:
            ax.plot(np.linspace(0, 2 * np.pi, 100), [max_triangle_radius] * 100,
                    color='orange', linewidth=2, linestyle='--', alpha=0.6,
                    label=f'Bottleneck ({format_time(max_triangle_radius)})')

    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.15))
    ax.set_title("Capacity Visualization", fontsize=16, pad=20)

    return fig, ax

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
    fig, _ = create_capacity_background(report_data_path=report_data_file)

    output_path = images_dir / 'capacity_background.png'
    fig.savefig(output_path, dpi=150, bbox_inches='tight')

    print(f"Capacity visualization background saved to: {output_path}")
