#!/usr/bin/env python3
"""
Tarkista mitä ohjelmia generate_matrix() käyttää.
"""

import os
import glob

def check_program_usage():
    """Tarkista mitä käsittelyohjelmia käytetään"""
    
    latest_output = max(glob.glob("output/*/"), key=os.path.getctime)
    
    print(f"🔍 KÄSITTELYOHJELMIEN KÄYTTÖANALYYSI - {latest_output}")
    print("="*60)
    
    # Tarkista kansiot
    original_dir = os.path.join(latest_output, "original_programs")
    stretched_dir = os.path.join(latest_output, "stretched_programs") 
    optimized_dir = os.path.join(latest_output, "optimized_programs")
    
    dirs = [
        ("Original", original_dir),
        ("Stretched", stretched_dir),
        ("Optimized", optimized_dir)
    ]
    
    for name, dir_path in dirs:
        if os.path.exists(dir_path):
            files = os.listdir(dir_path)
            print(f"📁 {name}: {len(files)} tiedostoa")
        else:
            print(f"❌ {name}: Kansiota ei ole")
    
    print()
    
    # Vertaa Stage 3 CalcTime arvoja kaikissa erissä
    print("🔍 STAGE 3 CALCTIME VERTAILU (pitäisi näyttää optimointi):")
    
    batch_files = ["Batch_001_Treatment_program_001.csv", 
                   "Batch_002_Treatment_program_001.csv", 
                   "Batch_003_Treatment_program_001.csv", 
                   "Batch_004_Treatment_program_001.csv"]
    
    import pandas as pd
    
    for batch_file in batch_files:
        print(f"\n📊 {batch_file}:")
        
        for name, dir_path in dirs:
            if os.path.exists(dir_path):
                file_path = os.path.join(dir_path, batch_file)
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    stage3 = df[df['Stage'] == 3]
                    if not stage3.empty:
                        calc_time = stage3.iloc[0]['CalcTime']
                        min_time = stage3.iloc[0]['MinTime']
                        max_time = stage3.iloc[0]['MaxTime']
                        
                        # Tarkista onko optimoitu
                        is_optimized = calc_time == min_time
                        status = "✅ OPTIMOITU" if is_optimized else "⚠️  EI OPTIMOITU"
                        
                        print(f"  {name}: CalcTime={calc_time} {status}")
    
    # Tarkista mitä load_batch_program_stretched käyttää
    print(f"\n🎯 MITÄ generate_matrix() KÄYTTÄÄ:")
    print("   Kokeile simuloida load_batch_program_stretched() logiikkaa...")
    
    # Simuloi prefer_optimized=True logiikka
    test_batch = "Batch_001_Treatment_program_001.csv"
    
    # Tämä vastaa load_batch_program_stretched() logiikkaa
    if os.path.exists(optimized_dir):
        optimized_path = os.path.join(optimized_dir, test_batch)
        if os.path.exists(optimized_path):
            print(f"   ✅ Käyttää: optimized_programs/{test_batch}")
        else:
            print(f"   ⚠️  Käyttää: stretched_programs/{test_batch} (optimized ei löydy)")
    else:
        print(f"   ❌ Käyttää: stretched_programs/{test_batch} (optimized-kansiota ei ole)")

if __name__ == "__main__":
    check_program_usage()
