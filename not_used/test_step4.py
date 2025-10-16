#!/usr/bin/env python3
"""
Testiputki - VAIHE 4: Visualisoi alkuperäinen line-matriisi

Tekee vain yhden vaiheen:
1. Lukee line_matrix_original.csv simulaatiokansiosta
2. Luo timeline-visualisoinnin näyttäen erien liikkumisen asemien kautta
3. Tallentaa visualisoinnin Logs-kansioon
4. Näyttää tilastoja matriisista
5. Kirjaa tapahtumat simulation_log.csv:hen
"""

import os
import sys
from datetime import datetime

# Lisää projektin juuri Python-polkuun
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import timeline visualization
from visualize_original_matrix import visualize_original_matrix

def append_to_log(output_dir, log_type, description):
    """Lisää merkinnän simulation_log.csv:hen"""
    log_file = os.path.join(output_dir, "Logs", "simulation_log.csv")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp},{log_type},{description}\n")

def visualize_original_matrix_step4(output_dir):
    """
    Visualisoi alkuperäisen line-matriisin Gantt-kaaviona simulaatiokansiossa.
    """
    
    print("Visualisoidaan alkuperäinen matriisi...")
    append_to_log(output_dir, "VISUAL", "Started visualizing original line matrix")
    
    # Lataa matriisi Logs-kansiosta
    matrix_file = os.path.join(output_dir, "Logs", "line_matrix_original.csv")
    if not os.path.exists(matrix_file):
        raise FileNotFoundError(f"Matriisitiedostoa ei löydy: {matrix_file}")
    
    df = pd.read_csv(matrix_file)
    print(f"Ladattu {len(df)} vaihetta")
    append_to_log(output_dir, "VISUAL", f"Loaded matrix with {len(df)} stages")
    
    # Luo Gantt-kaavio
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # Värit eri erille
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # Käy läpi kaikki erät
    batches = df['Batch'].unique()
    y_pos = 0
    y_labels = []
    
    append_to_log(output_dir, "VISUAL", f"Creating Gantt chart for {len(batches)} batches")
    
    for batch in sorted(batches):
        batch_data = df[df['Batch'] == batch]
        color = colors[(batch-1) % len(colors)]
        
        for _, row in batch_data.iterrows():
            if row['CalcTime'] > 0:  # Älä näytä Loading/Unloading (CalcTime=0)
                # Muunna sekunnit tunneiksi ja minuuteiksi
                start_hours = row['EntryTime'] / 3600
                duration_hours = row['CalcTime'] / 3600
                
                # Piirrä palkki
                ax.barh(y_pos, duration_hours, left=start_hours, 
                       color=color, alpha=0.7, edgecolor='black', linewidth=0.5)
                
                # Lisää teksti palkkiin
                station_name = f"St{row['Station']}"
                ax.text(start_hours + duration_hours/2, y_pos, station_name, 
                       ha='center', va='center', fontsize=8, fontweight='bold')
        
        y_labels.append(f"Batch {batch}")
        y_pos += 1
    
    # Aseta akselit
    ax.set_yticks(range(len(batches)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Production Batches')
    ax.set_title('Original Line Matrix Visualization', fontsize=14, fontweight='bold')
    
    # Lisää ruudukko
    ax.grid(True, alpha=0.3)
    
    # Tallenna kuva Logs-kansioon
    output_file = os.path.join(output_dir, "Logs", "line_matrix_original_visual.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()  # Sulje kuva muistin säästämiseksi
    
    print(f"Visualisointi tallennettu: {output_file}")
    append_to_log(output_dir, "VISUAL", f"Gantt chart saved to {output_file}")
    
    # Näytä tilastoja
    print("\nMATRIISIN TILASTOT:")
    print(f"  Eria yhteensa: {len(batches)}")
    print(f"  Vaiheita yhteensa: {len(df)}")
    
    append_to_log(output_dir, "VISUAL", f"Matrix statistics: {len(batches)} batches, {len(df)} stages")
    
    # Analysoi siirtoaikoja (EntryTime - edellisen ExitTime)
    transfer_times = []
    for batch in batches:
        batch_data = df[df['Batch'] == batch].sort_values('Stage')
        for i in range(1, len(batch_data)):
            prev_exit = batch_data.iloc[i-1]['ExitTime']
            curr_entry = batch_data.iloc[i]['EntryTime']
            transfer_time = curr_entry - prev_exit
            if transfer_time > 0:
                transfer_times.append(transfer_time)
    
    if transfer_times:
        print(f"  Siirtoajat:")
        print(f"    Min: {min(transfer_times):.1f}s")
        print(f"    Max: {max(transfer_times):.1f}s") 
        print(f"    Keskiarvo: {sum(transfer_times)/len(transfer_times):.1f}s")
        
        append_to_log(output_dir, "VISUAL", f"Transfer times: min={min(transfer_times):.1f}s, max={max(transfer_times):.1f}s, avg={sum(transfer_times)/len(transfer_times):.1f}s")
    
    # Kokonaisajat
    total_times = []
    for batch in batches:
        batch_data = df[df['Batch'] == batch]
        start_time = batch_data['EntryTime'].min()
        end_time = batch_data['ExitTime'].max()
        total_time = end_time - start_time
        total_times.append(total_time)
        print(f"  Batch {batch}: {total_time/3600:.2f}h ({timedelta(seconds=int(total_time))})")
        
        append_to_log(output_dir, "VISUAL", f"Batch {batch} total time: {total_time/3600:.2f}h")
    
    append_to_log(output_dir, "VISUAL", "Matrix visualization completed successfully")
    return output_file

def test_step_4(simulation_dir=None):
    """
    VAIHE 4: Visualisoi alkuperäinen line-matriisi
    """
    print("TESTIPUTKI - VAIHE 4")
    print("=" * 30)
    
    try:
        # Jos simulation_dir ei ole annettu, etsi uusin
        if simulation_dir is None:
            output_base = "output"
            if not os.path.exists(output_base):
                raise FileNotFoundError("output-kansiota ei loydy. Aja ensin test_step1.py - test_step3.py")
            
            # Etsi uusin simulaatiokansio
            folders = [f for f in os.listdir(output_base) if os.path.isdir(os.path.join(output_base, f))]
            if not folders:
                raise FileNotFoundError("Simulaatiokansiota ei loydy. Aja ensin test_step1.py - test_step3.py")
            
            folders.sort(reverse=True)  # Uusin ensin
            simulation_dir = os.path.join(output_base, folders[0])
        
        print(f"Kaytetaan simulaatiokansiota: {simulation_dir}")
        
        # Tarkista että tarvittavat tiedostot ovat olemassa
        required_files = [
            os.path.join(simulation_dir, "Logs", "line_matrix_original.csv"),
            os.path.join(simulation_dir, "Logs", "simulation_log.csv")
        ]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Tarvittava tiedosto puuttuu: {file_path}")
        
        print("Kaikki tarvittavat tiedostot loytyvat")
        
        # Luo visualisointi
        visual_file = visualize_original_matrix_step4(simulation_dir)
        
        print(f"\nVAIHE 4 VALMIS!")
        print(f"Visualisointi luotu: {visual_file}")
        print("Voit nyt jatkaa seuraavaan vaiheeseen")
        
        return simulation_dir, visual_file
        
    except Exception as e:
        print(f"\nVIRHE: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    print(f"Aloitusaika: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Voidaan antaa simulaatiokansio argumenttina
    simulation_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    result_dir, result_file = test_step_4(simulation_dir)
    
    if result_dir and result_file:
        print(f"\nPaattymisaika: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Vaihe 4 suoritettu onnistuneesti!")
    else:
        print(f"\nKeskeytetty: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Vaihe 4 epaonnistui!")
        sys.exit(1)
