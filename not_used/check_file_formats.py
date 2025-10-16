#!/usr/bin/env python3
"""
Tarkista eri nostintehtävätiedostojen formaatit
"""

import pandas as pd
import os

def check_file_formats(output_dir):
    """Tarkista eri nostintehtävätiedostojen formaatit"""
    
    files = [
        'transporter_tasks_final.csv',
        'transporter_tasks_from_matrix.csv', 
        'transporter_tasks_resolved.csv',
        'transporter_tasks_optimized.csv',
        'transporter_tasks_stretched.csv'
    ]
    
    for filename in files:
        filepath = os.path.join(output_dir, "logs", filename)
        try:
            df = pd.read_csv(filepath)
            print(f"📁 **{filename}:**")
            print(f"   Rivejä: {len(df)}")
            print(f"   Sarakkeet: {df.columns.tolist()[:8]}")
            if len(df.columns) > 8:
                print(f"   ... (+{len(df.columns)-8} lisää)")
            print()
        except Exception as e:
            print(f"❌ **{filename}:** VIRHE - {e}")
            print()

if __name__ == "__main__":
    output_dir = "output/2025-08-07_08-09-19"
    check_file_formats(output_dir)
