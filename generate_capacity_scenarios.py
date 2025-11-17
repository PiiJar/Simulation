"""
Generate capacity visualization scenarios for demonstration purposes.

Creates multiple capacity_elements visualizations with different constraint scenarios:
1. Transporter constraint exceeds target (11 min), simulated at 12 min
2. Station constraint exceeds target (11 min), simulated at 12 min
3. Unit constraint exceeds target (11 min), simulated at 12 min
4. All constraints below target, simulated at 11 min (exceeds target)
5. All constraints below target, simulated at 9 min (meets target)
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json
import math
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

def format_time(seconds):
    """Formats seconds into MM:SS string."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def create_capacity_scenario(
    scenario_name,
    target_cycle_time,
    transporter_constraint,
    station_constraint,
    unit_constraint,
    simulated_cycle_time,
    output_path,
    max_time_minutes=12,
    image_pixels=1600,
    dpi=100
):
    """
    Creates a capacity visualization for a specific scenario.
    
    Args:
        scenario_name: Name of the scenario for display
        target_cycle_time: Target cycle time in seconds
        transporter_constraint: Transporter limitation in seconds
        station_constraint: Station group limitation in seconds
        unit_constraint: Unit number limitation in seconds
        simulated_cycle_time: Actual simulated cycle time in seconds
        output_path: Path where to save the image
        max_time_minutes: Maximum time range for visualization
        image_pixels: Image size in pixels
        dpi: DPI for the output image
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

    # Determine the maximum radius we need to display based on data
    max_needed = max(
        simulated_cycle_time or 0,
        target_cycle_time or 0,
        transporter_constraint or 0,
        station_constraint or 0,
        unit_constraint or 0,
    )

    # Axis endpoint: floor((max_needed + 120s) / 60s) * 60s
    axis_max_seconds = int(math.floor((max_needed + 120) / 60.0) * 60)

    # Display max for plot limits: extend slightly beyond axis end to allow tick extensions
    display_max_seconds = axis_max_seconds + 120

    # Draw axes and ticks
    angles_deg = [90, 210, 330]
    angles_rad = [np.deg2rad(d) for d in angles_deg]

    major_interval = 60
    minor_interval = 15
    major_arc_seconds = 15
    minor_arc_seconds = 5

    for angle in angles_rad:
        # Draw axis line from 0 to axis_max_seconds
        ax.plot([angle, angle], [0, axis_max_seconds], color='black', linewidth=0.9)

        # Major ticks (every 60s up to axis_max_seconds)
        for r in np.arange(major_interval, axis_max_seconds + 1, major_interval):
            if r <= 0:
                continue
            angle_offset = major_arc_seconds / float(r)
            ax.plot([angle - angle_offset, angle + angle_offset], [r, r], color='black', linewidth=0.9)

            # Radial extension for major tick
            tick_extra = min(major_interval, display_max_seconds - r)
            if tick_extra > 0:
                ax.plot([angle, angle], [r, r + tick_extra], color='black', linewidth=0.9)

        # Minor ticks (every 15s but skip multiples of 60s)
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
    
    # --- Draw three constraint points and connect them to form a triangle ---
    point1_angle = np.pi / 2  # 90 degrees - vertical (Transporter)
    point2_angle = np.deg2rad(210)  # lower-right (Station)
    point3_angle = np.deg2rad(330)  # lower-left (Unit)
    
    point1_radius = transporter_constraint
    point2_radius = station_constraint
    point3_radius = unit_constraint
    
    # Draw the three points with distinct colors
    if point1_radius > 0 and point1_radius <= display_max_seconds:
        ax.plot(point1_angle, point1_radius, 'o', color='#2196F3', markersize=10,
                label=f'Transporter Limitation ({format_time(point1_radius)})')

    if point2_radius > 0 and point2_radius <= display_max_seconds:
        ax.plot(point2_angle, point2_radius, 'o', color='#9C27B0', markersize=10,
                label=f'Station Limitation ({format_time(point2_radius)})')

    if point3_radius > 0 and point3_radius <= display_max_seconds:
        ax.plot(point3_angle, point3_radius, 'o', color='#2E7D32', markersize=10,
                label=f'Container Limitation ({format_time(point3_radius)})')
    
    # Connect the three points to form a triangle
    if all(r > 0 and r <= display_max_seconds for r in [point1_radius, point2_radius, point3_radius]):
        triangle_angles = [point1_angle, point2_angle, point3_angle, point1_angle]
        triangle_radii = [point1_radius, point2_radius, point3_radius, point1_radius]

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

    # Save the figure
    fig.savefig(output_path, dpi=dpi)
    plt.close(fig)
    print(f"Scenario '{scenario_name}' saved to: {output_path}")

def generate_all_scenarios():
    """Generate all demonstration scenarios."""
    
    # Create output directory
    output_dir = Path('output/demo')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Common parameters
    target = 10 * 60  # 10 minutes in seconds
    
    # Scenario 1: Transporter constraint exceeds target
    create_capacity_scenario(
        scenario_name="Transporter Bottleneck",
        target_cycle_time=target,
        transporter_constraint=11 * 60,  # 11 minutes
        station_constraint=9 * 60,       # 9 minutes
        unit_constraint=8 * 60,          # 8 minutes
        simulated_cycle_time=12 * 60,    # 12 minutes
        output_path=output_dir / 'capacity_scenario_1.png'
    )
    
    # Scenario 2: Station constraint exceeds target
    create_capacity_scenario(
        scenario_name="Station Bottleneck",
        target_cycle_time=target,
        transporter_constraint=8 * 60,   # 8 minutes
        station_constraint=11 * 60,      # 11 minutes
        unit_constraint=9 * 60,          # 9 minutes
        simulated_cycle_time=12 * 60,    # 12 minutes
        output_path=output_dir / 'capacity_scenario_2.png'
    )
    
    # Scenario 3: Unit constraint exceeds target
    create_capacity_scenario(
        scenario_name="Unit Number Bottleneck",
        target_cycle_time=target,
        transporter_constraint=9 * 60,   # 9 minutes
        station_constraint=8 * 60,       # 8 minutes
        unit_constraint=11 * 60,         # 11 minutes
        simulated_cycle_time=12 * 60,    # 12 minutes
        output_path=output_dir / 'capacity_scenario_3.png'
    )
    
    # Scenario 4: All constraints below target, but simulated exceeds target
    create_capacity_scenario(
        scenario_name="Task Sync Constraint (Exceeds Target)",
        target_cycle_time=target,
        transporter_constraint=8 * 60,   # 8 minutes
        station_constraint=8.5 * 60,     # 8.5 minutes
        unit_constraint=9 * 60,          # 9 minutes
        simulated_cycle_time=11 * 60,    # 11 minutes
        output_path=output_dir / 'capacity_scenario_4.png'
    )
    
    # Scenario 5: All constraints below target, simulated slightly worse than theoretical but better than target
    create_capacity_scenario(
        scenario_name="Meets Target (Good Performance)",
        target_cycle_time=target,
        transporter_constraint=8 * 60,   # 8 minutes
        station_constraint=8.5 * 60,     # 8.5 minutes
        unit_constraint=9 * 60,          # 9 minutes
        simulated_cycle_time=9 * 60 + 30,  # 9.5 minutes (30 seconds worse than theoretical)
        output_path=output_dir / 'capacity_scenario_5.png'
    )
    
    print(f"\n✅ All {5} scenarios generated successfully in {output_dir}")

if __name__ == '__main__':
    generate_all_scenarios()
