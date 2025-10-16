import pandas as pd
import os
from datetime import timedelta

def update_production_schedule(output_dir):
    """
    Päivittää Production.csv Start_time-arvoja ja luo Production_updated.csv
    perustuen nostintehtävien venytyksiin
    """
    print("📅 Päivitetään tuotanto-aikataulua venytyksen mukaan...")
    
    # Lue alkuperäinen Production.csv
    production_file = os.path.join(output_dir, "Initialization", "Production.csv")
    if not os.path.exists(production_file):
        raise FileNotFoundError(f"Production.csv ei löydy: {production_file}")
    
    production_df = pd.read_csv(production_file)
    print(f"📊 Alkuperäinen aikataulu {len(production_df)} erälle")
    
    # Lue venytetyt nostintehtävät
    stretched_file = os.path.join(output_dir, "Logs", "transporter_tasks_stretched.csv")
    if not os.path.exists(stretched_file):
        print("⚠️  Ei venytettyä tiedostoa - käytetään alkuperäistä aikataulua")
        # Kopioi alkuperäinen
        output_file = os.path.join(output_dir, "Production_updated.csv")
        production_df.to_csv(output_file, index=False)
        return production_df
    
    tasks_df = pd.read_csv(stretched_file)    # Hae uudet Loading-aseman (101) aloitusajat jokaiselle erälle
    # Loading-aseman tehtävät ovat FromStation=101 → ToStation=102
    loading_tasks = tasks_df[(tasks_df['FromStation'] == 101) & (tasks_df['ToStation'] == 102)]
    
    print(f"🔍 Löytyi {len(loading_tasks)} Loading-aseman tehtävää")
    
    updated_production = production_df.copy()
    changes_made = 0
    
    for _, task in loading_tasks.iterrows():
        batch_id = int(task['Batch'])  # Batch on numero transporter_tasks:ssa
        new_start_seconds = task['StartTime']
        
        # Muunna sekunnit takaisin HH:MM:SS muotoon
        hours = int(new_start_seconds // 3600)
        minutes = int((new_start_seconds % 3600) // 60)
        seconds = int(new_start_seconds % 60)
        new_start_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"        # Päivitä Production.csv:ssä (Batch voi olla numero tai merkkijono)
        mask = updated_production['Batch'] == batch_id
        if mask.sum() == 0:
            # Yritä merkkijono-muodossa
            batch_str = str(batch_id).zfill(3)
            mask = updated_production['Batch'] == batch_str
        
        if mask.sum() == 1:
            old_time = updated_production.loc[mask, 'Start_time'].iloc[0]
            old_seconds = pd.to_timedelta(old_time).total_seconds()
            updated_production.loc[mask, 'Start_time'] = new_start_time
            
            if abs(old_seconds - new_start_seconds) > 1:  # Yli 1s ero
                shift = new_start_seconds - old_seconds
                print(f"   📦 Erä {batch_id}: {old_time} → {new_start_time} ({shift:+.0f}s)")
                changes_made += 1
            else:
                print(f"   ✅ Erä {batch_id}: aika pysyi ennallaan ({old_time})")
        else:
            print(f"   ⚠️  Erää {batch_id} ei löytynyt Production.csv:stä")
    
    # Tallenna päivitetty Production
    output_file = os.path.join(output_dir, "Production_updated.csv")
    updated_production.to_csv(output_file, index=False)
    
    if changes_made > 0:
        print(f"✅ Päivitetty {changes_made} erän aloitusaikaa")
        print(f"💾 Tallennettu: {output_file}")
    else:
        print("✅ Ei muutoksia aloitusaikoihin tarvittu")
    
    return updated_production

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    update_production_schedule(output_dir)
