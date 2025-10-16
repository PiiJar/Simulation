import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import timedelta

def visualize_original_matrix(output_dir):
    """
    Visualisoi alkuperäisen line-matriisin Gantt-kaaviona.
    
    Args:
        output_dir: Polku tuloskansion juureen
    """
    
    print(f"📊 Visualisoidaan alkuperäinen matriisi kansiosta: {output_dir}")
    
    # Lataa matriisi
    matrix_file = os.path.join(output_dir, "line_matrix_original.csv")
    if not os.path.exists(matrix_file):
        raise FileNotFoundError(f"Matriisitiedostoa ei löydy: {matrix_file}")
    
    df = pd.read_csv(matrix_file)
    print(f"📈 Ladattu {len(df)} vaihetta")
    
    # Luo Gantt-kaavio
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # Värit eri erille
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # Käy läpi kaikki erät
    batches = df['Batch'].unique()
    y_pos = 0
    y_labels = []
    
    for batch in sorted(batches):
        batch_data = df[df['Batch'] == batch]
        color = colors[(batch-1) % len(colors)]
        
        for _, row in batch_data.iterrows():
            if row['CalcTime'] > 0:  # Älä näytä Loading/Unloading
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
        
        y_labels.append(f"Erä {batch}")
        y_pos += 1
    
    # Aseta akselit
    ax.set_yticks(range(len(batches)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel('Aika (tunnit)')
    ax.set_ylabel('Tuotantoerät')
    ax.set_title('Alkuperäinen Line-matriisi (Fysiikkapohjainen)', fontsize=14, fontweight='bold')
    
    # Lisää ruudukko
    ax.grid(True, alpha=0.3)
    
    # Tallenna kuva
    output_file = os.path.join(output_dir, "line_matrix_original_visual.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"💾 Visualisointi tallennettu: {output_file}")
    
    # Näytä tilastoja
    print("\n📊 MATRIISIN TILASTOT:")
    print(f"  Ereitä yhteensä: {len(batches)}")
    print(f"  Vaiheita yhteensä: {len(df)}")
    
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
        print(f"  Siirtoajat (fysiikkap.):")
        print(f"    Min: {min(transfer_times):.1f}s")
        print(f"    Max: {max(transfer_times):.1f}s") 
        print(f"    Keskiarvo: {sum(transfer_times)/len(transfer_times):.1f}s")
        print(f"    (Aiemmin vakio: 40s)")
    
    # Kokonaisajat
    total_times = []
    for batch in batches:
        batch_data = df[df['Batch'] == batch]
        start_time = batch_data['EntryTime'].min()
        end_time = batch_data['ExitTime'].max()
        total_time = end_time - start_time
        total_times.append(total_time)
        print(f"  Erä {batch}: {total_time/3600:.2f}h ({timedelta(seconds=int(total_time))})")
    
    print(f"\n✅ Visualisointi valmis!")
    return output_file

if __name__ == "__main__":
    import sys
    
    # Käytä viimeisintä output-kansiota jos ei parametria
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_base = "output"
        if os.path.exists(output_base):
            # Etsi viimeisin kansio
            subdirs = [d for d in os.listdir(output_base) if os.path.isdir(os.path.join(output_base, d))]
            if subdirs:
                latest_dir = max(subdirs)
                output_dir = os.path.join(output_base, latest_dir)
            else:
                output_dir = "output"
        else:
            output_dir = "output"
    
    visualize_original_matrix(output_dir)
