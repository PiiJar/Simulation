import os
import pandas as pd
import sys

# Lisätään polku, jotta voidaan importata cp_sat_phase_1
sys.path.append(os.getcwd())

try:
    from cp_sat_phase_1 import load_input_data
except ImportError:
    print("Virhe: cp_sat_phase_1.py ei löytynyt tai import epäonnistui.")
    sys.exit(1)

def find_latest_output_dir(base_dir="output"):
    """Etsii uusimman simulaatiokansion."""
    if not os.path.exists(base_dir):
        return None
    subdirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not subdirs:
        return None
    return max(subdirs, key=os.path.getmtime)

def analyze_bottlenecks_and_suggest_order(output_dir):
    print(f"--- Pullonkaula-analyysi kansiolle: {output_dir} ---")
    
    # 1. Lataa data
    try:
        batches, stations, transporters, transfer_tasks, treatment_programs = load_input_data(output_dir)
    except Exception as e:
        print(f"Datan lataus epäonnistui: {e}")
        return

    # 2. Laske asemien kokonaiskuormitus RYHMITTÄIN
    print("\nAnalysoidaan asemien kuormitusta (huomioiden rinnakkaisasemat)...")
    
    # Hae ryhmätiedot: Group -> [Station IDs]
    group_to_stations = stations.groupby('Group')['Number'].apply(list).to_dict()
    station_to_group = stations.set_index('Number')['Group'].to_dict()
    
    group_load = {} # {group_id: total_seconds}
    
    for b_id, program in treatment_programs.items():
        for _, row in program.iterrows():
            if row['Stage'] == 0: continue
            
            stat = int(row['MinStat'])
            duration = row['MinTime']
            
            # Selvitä mihin ryhmään asema kuuluu
            # Jos MinStat ei löydy suoraan (esim. on vain alueen alku), etsi ensimmäinen validi asema väliltä
            group_id = station_to_group.get(stat)
            if group_id is None:
                # Etsi joku asema väliltä MinStat-MaxStat
                for s in range(int(row['MinStat']), int(row['MaxStat']) + 1):
                    if s in station_to_group:
                        group_id = station_to_group[s]
                        break
            
            if group_id is not None:
                group_load[group_id] = group_load.get(group_id, 0) + duration

    # 3. Tunnista pullonkaula (Load / Capacity)
    if not group_load:
        print("Ei asemakuormitusta havaittu.")
        return

    # Laske kapasiteetti (altaiden määrä)
    group_capacity = {g: len(s_list) for g, s_list in group_to_stations.items()}
    
    # Laske suhteellinen kuormitus (Load / Count)
    normalized_load = {}
    for g, load in group_load.items():
        count = group_capacity.get(g, 1)
        normalized_load[g] = load / count

    bottleneck_group = max(normalized_load, key=normalized_load.get)
    max_norm_load = normalized_load[bottleneck_group]
    
    print(f"\nTOP 3 Kuormitetuimmat ryhmät (Load / Count):")
    sorted_groups = sorted(normalized_load.items(), key=lambda x: x[1], reverse=True)
    for g, norm_load in sorted_groups[:3]:
        count = group_capacity.get(g, 1)
        total_load = group_load[g]
        print(f"  Ryhmä {g} ({count} asemaa): {total_load}s / {count} = {norm_load:.0f}s per allas ({(norm_load/3600):.1f} h)")

    print(f"\n>> PÄÄPULLONKAULA on ryhmä {bottleneck_group} <<")

    # 4. Pisteytä erät pullonkaularyhmän käytön mukaan
    print(f"\nLasketaan erien kuormitus ryhmälle {bottleneck_group}...")
    batch_scores = []
    
    for b_id, program in treatment_programs.items():
        score = 0
        for _, row in program.iterrows():
            # Tarkista osuuko vaihe tähän ryhmään
            # Yksinkertaistus: katsotaan MinStatin ryhmää
            stat = int(row['MinStat'])
            g = station_to_group.get(stat)
            if g is None:
                 for s in range(int(row['MinStat']), int(row['MaxStat']) + 1):
                    if s in station_to_group:
                        g = station_to_group[s]
                        break
            
            if g == bottleneck_group:
                score += row['MinTime']
        
        prog_id = batches.loc[batches['Batch'] == b_id, 'Treatment_program'].values[0]
        batch_scores.append({
            'Batch': b_id, 
            'Program': prog_id, 
            'BottleneckLoad': score
        })

    df_scores = pd.DataFrame(batch_scores)
    
    # Näytä jakauma
    print("\nErien kuormitusjakauma (esimerkki):")
    print(df_scores.groupby('Program')['BottleneckLoad'].mean().reset_index().rename(columns={'BottleneckLoad': 'Avg_Load_Sec'}))

    # 5. Generoi ehdotus (Interleaving Heuristic)
    # Järjestä erät kuormituksen mukaan laskevasti
    df_sorted = df_scores.sort_values('BottleneckLoad', ascending=False).reset_index(drop=True)
    
    # Jaa kahteen osaan: Raskaat ja Kevyet
    mid_point = len(df_sorted) // 2
    heavy_half = df_sorted.iloc[:mid_point]
    light_half = df_sorted.iloc[mid_point:]
    
    suggested_order = []
    # "Vetoketju"-tekniikka: Ota vuorotellen raskas ja kevyt
    # (Tai jos toinen lista on pidempi, ota sieltä loput)
    h_idx, l_idx = 0, 0
    while h_idx < len(heavy_half) or l_idx < len(light_half):
        if h_idx < len(heavy_half):
            suggested_order.append(heavy_half.iloc[h_idx])
            h_idx += 1
        if l_idx < len(light_half):
            # Otetaan kevyt käänteisessä järjestyksessä (kevyin ensin) maksimoimaan kontrasti?
            # Tai vain järjestyksessä. Kokeillaan "kevyin ensin" tässä kohtaa.
            # light_half on jo järjestetty (raskaimmasta kevyimpään).
            # Otetaan light_half:n lopusta (kevyin)
            suggested_order.append(light_half.iloc[-(l_idx+1)]) 
            l_idx += 1
            
    print(f"\n--- EHDOTETTU JÄRJESTYS (Heuristiikka) ---")
    print("Idea: Vuorotellaan raskaita ja kevyitä käyttäjiä pullonkaulalla.")
    print(f"{'Järjestys':<10} | {'Batch':<10} | {'Program':<10} | {'Load (s)':<10}")
    print("-" * 50)
    
    for i, item in enumerate(suggested_order):
        print(f"{i+1:<10} | {item['Batch']:<10} | {item['Program']:<10} | {item['BottleneckLoad']:<10}")

    print("\nAnalyysi valmis. Tätä järjestystä voidaan käyttää model.AddHint() syötteenä.")

if __name__ == "__main__":
    # Etsi uusin output-kansio automaattisesti
    latest_dir = find_latest_output_dir()
    if latest_dir:
        analyze_bottlenecks_and_suggest_order(latest_dir)
    else:
        print("Ei output-kansiota löytynyt. Aja ensin simulaatio (main.py).")
