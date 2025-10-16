"""
Nostimen 2 päällekkäisyyksien tarkistus
======================================

Tarkistaa onko nostimella 2 päällekkäisiä tehtäviä eri simulaatioversioissa.
Erityisesti tarkistetaan mainitsemasi tehtävät:
- Erä 3: 109 --> 110 
- Erä 2: 112 --> 113

Analyysissa käytetään kaikki versiot:
- stretched (perusoptimointi)
- optimized (optimoitu)  
- recursive_optimized (rekursiivinen optimointi)
"""

import pandas as pd
import os
from datetime import datetime

def check_transporter_2_overlaps(output_dir):
    """
    Tarkistaa nostimen 2 tehtävien päällekkäisyydet
    """
    print(f"\n🔍 NOSTIMEN 2 PÄÄLLEKKÄISYYKSIEN TARKISTUS")
    print(f"={'='*60}")
    
    # Käytetään transporters_movement.csv-tiedostoa joka sisältää aloitus- ja lopetusajat
    movement_file = os.path.join(output_dir, "logs", "transporters_movement.csv")
    
    if not os.path.exists(movement_file):
        print(f"❌ Tiedostoa ei löytynyt: {movement_file}")
        return 0
    
    print(f"� Käytetään tiedostoa: {os.path.basename(movement_file)}")
    
    try:
        df = pd.read_csv(movement_file)
        
        # Suodata nostimen 2 tehtävät ja vain siirtotehtävät (Phase=3 tarkoittaa siirtoa)
        transporter_2 = df[(df['Transporter'] == 2) & (df['Phase'] == 3)].copy()
        
        if len(transporter_2) == 0:
            print("❌ Ei siirtotehtäviä nostimelle 2")
            return 0
        
        # Järjestä aloitusajan mukaan
        transporter_2 = transporter_2.sort_values('Start_Time').reset_index(drop=True)
        
        print(f"\n📋 Nostimen 2 siirtotehtävät ({len(transporter_2)} kpl):")
        for idx, row in transporter_2.iterrows():
            print(f"  {idx+1}. Erä {row['Batch']:2d}: {row['From_Station']} --> {row['To_Station']} "
                  f"({row['Start_Time']:7.1f}s - {row['End_Time']:7.1f}s)")
        
        # Tarkista päällekkäisyydet
        overlaps = []
        for i in range(len(transporter_2)):
            for j in range(i+1, len(transporter_2)):
                task1 = transporter_2.iloc[i]
                task2 = transporter_2.iloc[j]
                
                # Tarkista päällekkäisyys
                if task1['End_Time'] > task2['Start_Time']:
                    overlap_start = max(task1['Start_Time'], task2['Start_Time'])
                    overlap_end = min(task1['End_Time'], task2['End_Time'])
                    overlap_duration = overlap_end - overlap_start
                    
                    if overlap_duration > 0:
                        overlap_info = {
                            'Task1_Batch': task1['Batch'],
                            'Task1_Route': f"{task1['From_Station']} -> {task1['To_Station']}",
                            'Task1_Start': task1['Start_Time'],
                            'Task1_End': task1['End_Time'],
                            'Task2_Batch': task2['Batch'],
                            'Task2_Route': f"{task2['From_Station']} -> {task2['To_Station']}",
                            'Task2_Start': task2['Start_Time'],
                            'Task2_End': task2['End_Time'],
                            'Overlap_Start': overlap_start,
                            'Overlap_End': overlap_end,
                            'Overlap_Duration': overlap_duration
                        }
                        
                        overlaps.append(overlap_info)
                        
                        print(f"\n⚠️  PÄÄLLEKKÄISYYS HAVAITTU!")
                        print(f"    Tehtävä 1: Erä {task1['Batch']} ({task1['From_Station']} -> {task1['To_Station']}) "
                              f"{task1['Start_Time']:.1f}s - {task1['End_Time']:.1f}s")
                        print(f"    Tehtävä 2: Erä {task2['Batch']} ({task2['From_Station']} -> {task2['To_Station']}) "
                              f"{task2['Start_Time']:.1f}s - {task2['End_Time']:.1f}s")
                        print(f"    Päällekkäisyys: {overlap_start:.1f}s - {overlap_end:.1f}s ({overlap_duration:.1f}s)")
        
        if not overlaps:
            print(f"\n✅ Ei päällekkäisyyksiä nostimella 2")
        else:
            print(f"\n❌ {len(overlaps)} päällekkäisyyttä nostimella 2!")
            
            # Tallenna päällekkäisyydet
            overlap_df = pd.DataFrame(overlaps)
            analysis_dir = os.path.join(output_dir, "Analysis")
            os.makedirs(analysis_dir, exist_ok=True)
            overlap_file = os.path.join(analysis_dir, "transporter_2_overlaps_detected.csv")
            overlap_df.to_csv(overlap_file, index=False)
            print(f"💾 Päällekkäisyydet tallennettu: {os.path.basename(overlap_file)}")
            
            # Etsi erityisesti mainitsemasi tehtävät
            print(f"\n🎯 ETSITÄÄN MAINITSEMIASI TEHTÄVIÄ:")
            print(f"   - Erä 3: 109 --> 110")
            print(f"   - Erä 2: 112 --> 113")
            
            found_conflicts = []
            for overlap in overlaps:
                task1_matches = (overlap['Task1_Batch'] == 3 and overlap['Task1_Route'] == "109 -> 110") or \
                               (overlap['Task1_Batch'] == 2 and overlap['Task1_Route'] == "112 -> 113")
                task2_matches = (overlap['Task2_Batch'] == 3 and overlap['Task2_Route'] == "109 -> 110") or \
                               (overlap['Task2_Batch'] == 2 and overlap['Task2_Route'] == "112 -> 113")
                
                if task1_matches or task2_matches:
                    found_conflicts.append(overlap)
                    print(f"\n🎯 LÖYTYI MAINITSEMASI KONFLIKTI:")
                    print(f"    Erä {overlap['Task1_Batch']}: {overlap['Task1_Route']} vs Erä {overlap['Task2_Batch']}: {overlap['Task2_Route']}")
                    print(f"    Päällekkäisyys: {overlap['Overlap_Duration']:.1f} sekuntia")
            
            if not found_conflicts:
                print(f"ℹ️  Mainitsemiasi tehtäviä ei löytynyt päällekkäisyyksistä")
        
        return len(overlaps)
        
    except Exception as e:
        print(f"❌ Virhe käsiteltäessä tiedostoa {movement_file}: {e}")
        return 0

if __name__ == "__main__":
    # Etsi viimeisin output-kansio
    output_base = "output"
    if os.path.exists(output_base):
        output_dirs = [d for d in os.listdir(output_base) if os.path.isdir(os.path.join(output_base, d))]
        if output_dirs:
            latest_dir = sorted(output_dirs)[-1]
            output_dir = os.path.join(output_base, latest_dir)
            print(f"📁 Käytetään output-kansiota: {latest_dir}")
            
            overlap_count = check_transporter_2_overlaps(output_dir)
            
            if overlap_count is not None:
                if overlap_count > 0:
                    print(f"\n⚠️  VAROITUS: {overlap_count} päällekkäisyyttä havaittu!")
                    print(f"    Rekursiivinen optimointi ei ole toiminut oikein.")
                else:
                    print(f"\n✅ Kaikki ok - ei päällekkäisyyksiä.")
            else:
                print(f"\n❌ Tarkistus epäonnistui.")
        else:
            print("❌ Output-kansioita ei löytynyt")
    else:
        print("❌ Output-kansiota ei löytynyt")
