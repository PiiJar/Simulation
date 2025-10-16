#!/usr/bin/env python3
"""
analyze_station_utilization.py

Analysoi asemien käyttöastetta ajan funktiona.
Yhdistää rinnakkaiset asemat (sama Name) yhdeksi prosessiasemaksi.
Jättää pois Loading ja Unloading asemat.

Author: Simulation Pipeline
Version: 1.0
Date: 2025-08-11
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from collections import defaultdict

def get_latest_output_dir():
    """Palauttaa uusimman output-kansion."""
    output_base = "output"
    if not os.path.exists(output_base):
        raise FileNotFoundError("Output directory not found")
    
    subdirs = [d for d in os.listdir(output_base) if os.path.isdir(os.path.join(output_base, d))]
    if not subdirs:
        raise FileNotFoundError("No output subdirectories found")
    
    # Järjestä kansiot nimien mukaan (aikaleima-format) ja ota uusin
    subdirs.sort(reverse=True)
    return os.path.join(output_base, subdirs[0])

def analyze_station_utilization():
    """
    Analysoi asemien käyttöastetta ajan funktiona rinnakkaiset asemat yhdistäen.
    """
    
    # Lataa data
    output_dir = get_latest_output_dir()
    matrix_file = os.path.join(output_dir, "logs", "line_matrix_original.csv")
    stations_file = os.path.join(output_dir, "initialization", "Stations.csv")
    
    if not os.path.exists(matrix_file):
        raise FileNotFoundError(f"Matrix file not found: {matrix_file}")
    if not os.path.exists(stations_file):
        raise FileNotFoundError(f"Stations file not found: {stations_file}")
    
    # Lataa data
    matrix_df = pd.read_csv(matrix_file)
    stations_df = pd.read_csv(stations_file)
    
    print("================================================================================")
    print("ASEMIEN KÄYTTÖASTEANALYYSI - RINNAKKAISET ASEMAT YHDISTETTYNÄ")
    print("================================================================================")
    
    # Ryhmittele asemat nimen mukaan ja suodata pois Loading/Unloading
    station_groups = defaultdict(list)
    station_names = {}
    
    for _, station in stations_df.iterrows():
        name = station['Name']
        number = int(station['Number'])
        
        # Jätä pois Loading ja Unloading
        if name in ['Loading', 'Unloading']:
            continue
            
        station_groups[name].append(number)
        station_names[number] = name
    
    # Järjestä asemaryhmät numeroiden mukaan
    for name in station_groups:
        station_groups[name].sort()
    
    print(f"Löydettiin {len(station_groups)} prosessiasemaa:")
    for name, numbers in station_groups.items():
        if len(numbers) > 1:
            print(f"  {name} {min(numbers)}-{max(numbers)} ({len(numbers)} rinnakkaista)")
        else:
            print(f"  {name} {numbers[0]} (1 asema)")
    print()
    
    # Laske kokonaisaika
    max_time = matrix_df['ExitTime'].max()
    min_time = matrix_df['EntryTime'].min()
    total_duration = max_time - min_time
    
    print(f"Simulaation kesto: {min_time:.0f}s - {max_time:.0f}s ({total_duration:.0f}s)")
    print()
    
    # Aikaikkunaanalyysi (5 minuutin ikkunat)
    window_size = 300  # 5 minuuttia
    time_windows = np.arange(min_time, max_time + window_size, window_size)
    
    utilization_data = {}
    
    for group_name, station_numbers in station_groups.items():
        utilization_over_time = []
        
        for window_start in time_windows[:-1]:
            window_end = window_start + window_size
            
            # Laske kuinka monta sekuntia rinnakkaiset asemat olivat käytössä tässä ikkunassa
            total_usage_seconds = 0
            
            for station_num in station_numbers:
                # Etsi kaikki tehtävät tällä asemalla tässä aikaikkunassa
                station_tasks = matrix_df[
                    (matrix_df['Station'] == station_num) &
                    (matrix_df['EntryTime'] < window_end) &
                    (matrix_df['ExitTime'] > window_start)
                ]
                
                for _, task in station_tasks.iterrows():
                    # Laske päällekkäisyys aikaikkunan kanssa
                    overlap_start = max(task['EntryTime'], window_start)
                    overlap_end = min(task['ExitTime'], window_end)
                    
                    if overlap_end > overlap_start:
                        total_usage_seconds += overlap_end - overlap_start
            
            # Käyttöaste: käytetty aika / (rinnakkaisten asemien määrä * aikaikkunan koko)
            max_possible_seconds = len(station_numbers) * window_size
            utilization_percent = (total_usage_seconds / max_possible_seconds) * 100
            
            utilization_over_time.append(min(utilization_percent, 100.0))  # Cap at 100%
        
        utilization_data[group_name] = utilization_over_time
    
    # Tulosta käyttöastetilastot
    print("KÄYTTÖASTETILASTOT:")
    print("-" * 60)
    print(f"{'Asema':<20} {'Keskim.':<8} {'Minimi':<8} {'Maksimi':<8} {'Huiput':<10}")
    print("-" * 60)
    
    for group_name, utilization_list in utilization_data.items():
        avg_util = np.mean(utilization_list)
        min_util = np.min(utilization_list)
        max_util = np.max(utilization_list)
        peak_count = sum(1 for u in utilization_list if u > 80)
        
        numbers = station_groups[group_name]
        if len(numbers) > 1:
            display_name = f"{group_name} {min(numbers)}-{max(numbers)}"
        else:
            display_name = f"{group_name} {numbers[0]}"
        
        print(f"{display_name:<20} {avg_util:>6.1f}% {min_util:>6.1f}% {max_util:>6.1f}% {peak_count:>8}x")
    
    print("-" * 60)
    print()
    
    # Tunnista pullonkaulat
    print("PULLONKAULAANALYYSI:")
    print("-" * 40)
    
    bottlenecks = []
    for group_name, utilization_list in utilization_data.items():
        avg_util = np.mean(utilization_list)
        max_util = np.max(utilization_list)
        peak_count = sum(1 for u in utilization_list if u > 80)
        
        if avg_util > 60 or max_util > 90 or peak_count > 5:
            bottlenecks.append((group_name, avg_util, max_util, peak_count))
    
    if bottlenecks:
        bottlenecks.sort(key=lambda x: x[1], reverse=True)  # Järjestä keskimääräisen käyttöasteen mukaan
        
        for i, (name, avg, max_util, peaks) in enumerate(bottlenecks, 1):
            numbers = station_groups[name]
            if len(numbers) > 1:
                display_name = f"{name} {min(numbers)}-{max(numbers)}"
            else:
                display_name = f"{name} {numbers[0]}"
            
            print(f"{i}. {display_name}")
            print(f"   Keskimääräinen käyttöaste: {avg:.1f}%")
            print(f"   Maksimi käyttöaste: {max_util:.1f}%")
            print(f"   Huippukuormitusikkunoita (>80%): {peaks}")
            print()
    else:
        print("Ei merkittäviä pullonkauloja havaittu.")
        print()
    
    # Luo visualisointi
    create_utilization_chart(utilization_data, station_groups, time_windows[:-1], output_dir)
    
    return utilization_data, station_groups

def create_utilization_chart(utilization_data, station_groups, time_windows, output_dir):
    """Luo käyttöastekaavio ajan funktiona."""
    
    # Järjestä asemat keskimääräisen käyttöasteen mukaan
    sorted_stations = sorted(utilization_data.items(), 
                           key=lambda x: np.mean(x[1]), reverse=True)
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Värit
    colors = plt.cm.Set3(np.linspace(0, 1, len(sorted_stations)))
    
    for i, (group_name, utilization_list) in enumerate(sorted_stations):
        numbers = station_groups[group_name]
        if len(numbers) > 1:
            label = f"{group_name} {min(numbers)}-{max(numbers)}"
        else:
            label = f"{group_name} {numbers[0]}"
        
        # Muunna aikaikkunat minuuteiksi
        time_minutes = [t/60 for t in time_windows]
        
        ax.plot(time_minutes, utilization_list, 
               color=colors[i], linewidth=2, alpha=0.8, label=label)
    
    # Lisää kriittisen tason viivat
    ax.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='Korkea kuormitus (80%)')
    ax.axhline(y=90, color='red', linestyle='--', alpha=0.7, label='Kriittinen kuormitus (90%)')
    
    ax.set_xlabel('Aika (minuuttia)', fontsize=12)
    ax.set_ylabel('Käyttöaste (%)', fontsize=12)
    ax.set_title('Asemien käyttöaste ajan funktiona (5min ikkunat)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    # Legend sivulle
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    
    # Tallenna
    output_file = os.path.join(output_dir, "logs", "station_utilization_timeline.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Käyttöastekaavio tallennettu: {output_file}")

if __name__ == "__main__":
    try:
        utilization_data, station_groups = analyze_station_utilization()
        print("Analyysi valmis!")
    except Exception as e:
        print(f"Virhe analyysissä: {e}")
