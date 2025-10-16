#!/usr/bin/env python3
"""
Analysoi nostimen 1 tehtävälistoja: ordered vs stretched
"""

import pandas as pd
import os

def analyze_transporter_1(output_dir):
    logs_dir = os.path.join(output_dir, "logs")
    ordered_file = os.path.join(logs_dir, "transporter_tasks_ordered.csv")
    stretched_file = os.path.join(logs_dir, "transporter_tasks_stretched.csv")
    
    # Lue molemmat tiedostot
    df_ordered = pd.read_csv(ordered_file)
    df_stretched = pd.read_csv(stretched_file)
    
    # Filtraa nostimen 1 tehtävät
    t1_ordered = df_ordered[df_ordered['Transporter_id'] == 1].copy()
    t1_stretched = df_stretched[df_stretched['Transporter_id'] == 1].copy()
    
    print("=" * 80)
    print("NOSTIMEN 1 TEHTÄVÄANALYYSI: ORDERED vs STRETCHED")
    print("=" * 80)
    
    print(f"\nOrdered tehtäviä: {len(t1_ordered)}")
    print(f"Stretched tehtäviä: {len(t1_stretched)}")
    
    print("\n" + "=" * 80)
    print("VERTAILU TEHTÄVÄ KERRALLAAN")
    print("=" * 80)
    
    # Yhdistä vertailua varten (käyttäen batch+stage identifiointiin)
    print(f"{'#':<3} {'Batch':<5} {'Stage':<5} {'ORDERED':<25} {'STRETCHED':<25} {'MUUTOS':<15}")
    print("-" * 80)
    
    for i in range(max(len(t1_ordered), len(t1_stretched))):
        if i < len(t1_ordered):
            o_row = t1_ordered.iloc[i]
            o_info = f"B{o_row['Batch']}S{o_row['Stage']}: {o_row['Lift_time']}-{o_row['Sink_time']}"
            o_batch = o_row['Batch']
            o_stage = o_row['Stage']
        else:
            o_info = "---"
            o_batch = None
            o_stage = None
            
        if i < len(t1_stretched):
            s_row = t1_stretched.iloc[i]
            s_info = f"B{s_row['Batch']}S{s_row['Stage']}: {s_row['Lift_time']}-{s_row['Sink_time']}"
            s_batch = s_row['Batch']
            s_stage = s_row['Stage']
        else:
            s_info = "---"
            s_batch = None
            s_stage = None
            
        # Laske muutos
        if (i < len(t1_ordered) and i < len(t1_stretched) and 
            o_batch == s_batch and o_stage == s_stage):
            lift_change = s_row['Lift_time'] - o_row['Lift_time']
            sink_change = s_row['Sink_time'] - o_row['Sink_time']
            change = f"L+{lift_change:.0f} S+{sink_change:.0f}"
        else:
            change = "JÄRJESTYS MUUTOS"
            
        print(f"{i+1:<3} {o_batch if o_batch else '---':<5} {o_stage if o_stage else '---':<5} {o_info:<25} {s_info:<25} {change:<15}")
    
    print("\n" + "=" * 80)
    print("KONFLIKTIT JA JÄRJESTYSMUUTOKSET")
    print("=" * 80)
    
    # Etsi konfliktit ordered-listassa
    print("\nKONFLIKTIT ORDERED-LISTASSA:")
    for i in range(len(t1_ordered) - 1):
        curr = t1_ordered.iloc[i]
        next_task = t1_ordered.iloc[i + 1]
        gap = next_task['Lift_time'] - curr['Sink_time']
        if gap < 0:
            print(f"  KONFLIKTI {i+1}-{i+2}: B{curr['Batch']}S{curr['Stage']} päättyy {curr['Sink_time']}, "
                  f"B{next_task['Batch']}S{next_task['Stage']} alkaa {next_task['Lift_time']} (GAP: {gap})")
    
    # Etsi konfliktit stretched-listassa
    print("\nKONFLIKTIT STRETCHED-LISTASSA:")
    conflicts_found = False
    for i in range(len(t1_stretched) - 1):
        curr = t1_stretched.iloc[i]
        next_task = t1_stretched.iloc[i + 1]
        gap = next_task['Lift_time'] - curr['Sink_time']
        if gap < 0:
            print(f"  KONFLIKTI {i+1}-{i+2}: B{curr['Batch']}S{curr['Stage']} päättyy {curr['Sink_time']}, "
                  f"B{next_task['Batch']}S{next_task['Stage']} alkaa {next_task['Lift_time']} (GAP: {gap})")
            conflicts_found = True
    
    if not conflicts_found:
        print("  Ei konflikteja löytynyt!")
    
    # Etsi järjestysmuutokset
    print("\nJÄRJESTYSMUUTOKSET:")
    
    # Luo tunnisteet vertailua varten
    ordered_ids = [(row['Batch'], row['Stage']) for _, row in t1_ordered.iterrows()]
    stretched_ids = [(row['Batch'], row['Stage']) for _, row in t1_stretched.iterrows()]
    
    if ordered_ids != stretched_ids:
        print("  JÄRJESTYS ON MUUTTUNUT!")
        print(f"  Ordered:   {ordered_ids[:10]}...")
        print(f"  Stretched: {stretched_ids[:10]}...")
    else:
        print("  Järjestys säilynyt samana")

if __name__ == "__main__":
    import sys
    import glob
    
    # Hae viimeisin output-kansio jos ei annettu
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_base = os.path.join(script_dir, "output")
        subdirs = [d for d in glob.glob(os.path.join(output_base, "*")) if os.path.isdir(d)]
        if subdirs:
            output_dir = max(subdirs, key=os.path.getmtime)
        else:
            print("Ei output-kansiota löytynyt!")
            sys.exit(1)
    
    analyze_transporter_1(output_dir)
