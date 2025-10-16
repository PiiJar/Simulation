#!/usr/bin/env python3
"""
Testiputki - VAIHE 3: Luo alkuperäinen line-matriisi

Tekee vain yhden vaiheen:
1. Lukee simulaatiokansion Initialization-tiedostot
2. Lukee original_programs-käsittelyohjelmat  
3. Luo alkuperäisen line-matriisin
4. Tallentaa sen Logs-kansioon
5. Kirjaa tapahtumat simulation_log.csv:hen
"""

import os
import sys
from datetime import datetime
import pandas as pd
from generate_matrix_original import generate_matrix_original
from generate_transporter_tasks_original import complete_transfer_task
import argparse

# Lisää projektin juuri Python-polkuun
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def append_to_log(output_dir, log_type, description):
    """Lisää merkinnän simulation_log.csv:hen"""
    log_file = os.path.join(output_dir, "Logs", "simulation_log.csv")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp},{log_type},{description}\n")

def load_stations(output_dir):
    """Lataa asemien tiedot Stations.csv:stä"""
    file_path = os.path.join(output_dir, "Initialization", "Stations.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Stations.csv ei löydy: {file_path}")
    
    return pd.read_csv(file_path)

def load_production_batches(output_dir):
    """Lataa Production.csv ja palauttaa tuotantoerien tiedot"""
    file_path = os.path.join(output_dir, "Initialization", "Production.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Production.csv ei löydy: {file_path}")
    
    df = pd.read_csv(file_path)
    # Muunna Start_time sekunneiksi
    df["Start_time_seconds"] = pd.to_timedelta(df["Start_time"]).dt.total_seconds()
    return df

def load_batch_program(output_dir, batch_id, treatment_program):
    """Lataa eräkohtainen ohjelmatiedosto original_programs-kansiosta"""
    # batch_id tulee muodossa "001", jos ei, muotoile se
    batch_str = str(batch_id).zfill(3)
    # UUSI: käytä tiedostonimeä program_{batch_str}.csv
    file_path = os.path.join(output_dir, "original_programs", f"program_{batch_str}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Eräohjelmaa ei löydy: {file_path}")
    
    df = pd.read_csv(file_path)
    print(f"Ladattiin ohjelma {file_path} sarakkeilla: {list(df.columns)}")
    
    # Varmista että tarvittavat sarakkeet ovat olemassa
    required_columns = ["MinTime", "CalcTime"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Pakollinen sarake '{col}' puuttuu tiedostosta {file_path}")
    
    df["MinTime"] = pd.to_timedelta(df["MinTime"]).dt.total_seconds()
    df["CalcTime"] = pd.to_timedelta(df["CalcTime"]).dt.total_seconds()
    
    return df

def create_processing_matrix_for_batch(prog_df, batch_id, start_time_seconds, output_dir):
    """Luo käsittelymatriisin yhdelle erälle sisältäen siirtovaiheajat"""
    rows = []
    
    # 1. Lisää Loading-asema (101) ensimmäiseksi
    rows.append({
        "Batch": int(batch_id),
        "Program": 1,
        "Stage": 0,  # Loading on vaihe 0
        "Station": 101,  # Loading-asema
        "MinTime": 0,
        "MaxTime": 0,
        "CalcTime": 0,
        "EntryTime": int(start_time_seconds),
        "ExitTime": int(start_time_seconds),
        "Phase_1": 0,  # Ei siirtoa edeltävässä rivissä
        "Phase_2": 0,
        "Phase_3": 0,
        "Phase_4": 0
    })
    
    # 2. Aloitetaan käsittelyvaiheet Loading-aseman jälkeen
    # Käytetään fysiikkapohjaista siirtoaikaa ja tallennetaan vaiheajat
    stations_df = load_stations(output_dir)
    
    previous_station = 101  # Loading-asema
    if len(prog_df) > 0:
        first_station = int(prog_df.iloc[0]["MinStat"])
        transfer_time, phases = calculate_physics_transfer_time_with_phases(previous_station, first_station, stations_df)
        first_phase_1, first_phase_2, first_phase_3, first_phase_4 = phases
    else:
        transfer_time = 40  # fallback
        first_phase_1, first_phase_2, first_phase_3, first_phase_4 = (10, 20, 10, 0)
    
    time = start_time_seconds + transfer_time  # fysiikkapohjainen siirto Loading-asemalta
    
    for i, (_, row) in enumerate(prog_df.iterrows()):
        stage = int(row["Stage"])
        station = int(row["MinStat"])
        min_time = row["MinTime"]
        max_time = row["MaxTime"]
        calc_time = row["CalcTime"]
        
        entry = time
        exit = entry + calc_time
        
        # Määritä tämän rivin siirtovaiheet (edellisestä siirosta)
        from_x = stations_df[stations_df['Number'] == previous_station].iloc[0]['X Position']
        to_x = stations_df[stations_df['Number'] == station].iloc[0]['X Position']
        # Phase_1: siirtyminen nostoasemalle (oletetaan 0, koska nostin on jo nostoasemalla)
        phase_1 = 0
        # Phase_2: nosto nostoasemalla
        phase_2 = complete_transfer_task(from_x, from_x, previous_station, previous_station, transporter_id=1, return_phases=True)[1]
        # Phase_3: vaakasiirto nostoasemalta laskuasemalle
        phase_3 = complete_transfer_task(from_x, to_x, previous_station, station, transporter_id=1, return_phases=True)[2]
        # Phase_4: lasku laskuasemalla
        phase_4 = complete_transfer_task(to_x, to_x, station, station, transporter_id=1, return_phases=True)[3]
        phase_2 = round(phase_2, 2)
        phase_3 = round(phase_3, 2)
        phase_4 = round(phase_4, 2)
        
        # Päivitä previous_station seuraavaa askelta varten
        previous_station = station
        
        # Laske fysiikkapohjainen siirtoaika seuraavaan asemaan (käytetään seuraavassa iteraatiossa)
        if i + 1 < len(prog_df):
            next_station = int(prog_df.iloc[i + 1]["MinStat"])
            transfer_time, phases = calculate_physics_transfer_time_with_phases(station, next_station, stations_df)
            next_phase_1, next_phase_2, next_phase_3, next_phase_4 = phases
        else:
            # Viimeinen vaihe -> Unloading-asemalle (111)
            transfer_time, phases = calculate_physics_transfer_time_with_phases(station, 111, stations_df)
            next_phase_1, next_phase_2, next_phase_3, next_phase_4 = phases
        
        time = exit + transfer_time  # seuraava vaihe alkaa fysiikkapohjaisen siirron jälkeen
        
        rows.append({
            "Batch": int(batch_id),
            "Program": 1,
            "Stage": stage,
            "Station": station,
            "MinTime": int(min_time),
            "MaxTime": int(max_time),
            "CalcTime": int(calc_time),
            "EntryTime": int(entry),
            "ExitTime": int(exit),
            "Phase_1": phase_1,
            "Phase_2": phase_2,
            "Phase_3": phase_3,
            "Phase_4": phase_4
        })    # Poistetaan Unloading-aseman (111) ylimääräinen lisäys
    return rows

def generate_matrix_step3(output_dir):
    """Kutsuu generate_matrix_original.py:n matriisigeneraattoria, jotta kaikki debugit ja muutokset ovat aina mukana."""
    return generate_matrix_original(output_dir)

def calculate_physics_transfer_time_with_phases(from_station, to_station, stations_df):
    """Laskee siirtoajan asemien välillä fysiikkapohjaisesti ja palauttaa vaiheajat"""
    FALLBACK_TIME = 40  # oletussiirtoaika jos fysiikkalaskenta epäonnistuu
    FALLBACK_PHASES = (10, 20, 10, 0)  # oletusvaihejako
    
    try:
        from_row = stations_df[stations_df['Number'] == from_station]
        to_row = stations_df[stations_df['Number'] == to_station]
        
        if from_row.empty or to_row.empty:
            print(f"  Aseman koordinaatteja ei löydy: {from_station} -> {to_station}, käytetään oletusaikaa {FALLBACK_TIME}s")
            return FALLBACK_TIME, FALLBACK_PHASES
        
        from_x = from_row.iloc[0]['X Position']
        to_x = to_row.iloc[0]['X Position']
        
        # Käytä fysiikkapohjaista laskentaa sisällyttäen nosto/lasku-operaatiot
        transfer_time, phase_1, phase_2, phase_3, phase_4 = complete_transfer_task(
            from_x, to_x, from_station, to_station, transporter_id=1, return_phases=True
        )
        phases = (phase_1, phase_2, phase_3, phase_4)
        
        print(f"  Fysiikkapohjainen siirtoaika {from_station} → {to_station}: {transfer_time:.2f}s (etäisyys: {abs(to_x-from_x)}mm)")
        print(f"    Vaiheet: Lift={phase_1:.1f}s, Move={phase_2:.1f}s, Sink={phase_3:.1f}s, Setup={phase_4:.1f}s")
        return transfer_time, phases
        
    except Exception as e:
        print(f"  Virhe fysiikkapohjaisessa laskennassa {from_station} -> {to_station}: {e}")
        return FALLBACK_TIME, FALLBACK_PHASES

def calculate_physics_transfer_time(from_station, to_station, stations_df):
    """Vanhan funktion yhteensopivuus - palauttaa vain kokonaisajan"""
    transfer_time, _ = calculate_physics_transfer_time_with_phases(from_station, to_station, stations_df)
    return transfer_time

def test_step_3(output_dir):
    """
    VAIHE 3: Luo alkuperäinen line-matriisi
    """
    from datetime import datetime
    from production_version_manager import save_production_original, save_production_after_conflicts
    
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 3 - ALKUPERÄINEN MATRIISI - ALKAA")
    try:
        # Tarkista että tarvittavat kansiot ovat olemassa
        required_paths = [
            os.path.join(output_dir, "Initialization"),
            os.path.join(output_dir, "original_programs"),
            os.path.join(output_dir, "Logs")
        ]
        for path in required_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Tarvittava kansio puuttuu: {path}")
        
        # TALLENNA ALKUPERÄINEN PRODUCTION.CSV
        save_production_original(output_dir)
        
        # Luo line-matriisi (tämä voi muuttaa Production.csv:tä konfliktien ratkaisun vuoksi)
        matrix = generate_matrix_step3(output_dir)
        
        # TALLENNA PRODUCTION.CSV ASEMAKONFLIKTIEN RATKAISUN JÄLKEEN
        save_production_after_conflicts(output_dir)
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        print(f"[{end}] VAIHE 3 - ALKUPERÄINEN MATRIISI - VALMIS")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] VIRHE: {e}")
        raise

def main():
    from datetime import datetime
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{start}] VAIHE 3 ALKAA")
    
    try:
        # output_dir on määritelty pääohjelmassa globaalina muuttujana
        global output_dir
        if output_dir is None:
            output_base = "output"
            if not os.path.exists(output_base):
                raise FileNotFoundError("output-kansiota ei löydy. Aja ensin test_step1.py ja test_step2.py")
            
            # Etsi uusin simulaatiokansio
            folders = [f for f in os.listdir(output_base) if os.path.isdir(os.path.join(output_base, f))]
            if not folders:
                raise FileNotFoundError("Simulaatiokansiota ei löydy. Aja ensin test_step1.py ja test_step2.py")
            
            folders.sort(reverse=True)  # Uusin ensin
            output_dir = os.path.join(output_base, folders[0])
        
        print(f"Käytetään simulaatiokansiota: {output_dir}")
        
        # Tarkista että tarvittavat kansiot ovat olemassa
        required_paths = [
            os.path.join(output_dir, "Initialization"),
            os.path.join(output_dir, "original_programs"),
            os.path.join(output_dir, "Logs")
        ]
        
        for path in required_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Tarvittava kansio puuttuu: {path}")
        
        print(f"Kaikki tarvittavat kansiot löytyvät")
        
        # Luo line-matriisi
        matrix = generate_matrix_step3(output_dir)
        
        print(f"\nVAIHE 3 VALMIS!")
        print(f"Luotiin matriisi {len(matrix)} vaiheella")
        print("Voit nyt jatkaa seuraavaan vaiheeseen")
        
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{end}] VAIHE 3 VALMIS")
        
        return output_dir, matrix
        
    except Exception as e:
        print(f"\nVIRHE: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    import argparse
    import glob
    parser = argparse.ArgumentParser(description="Suorita vaihe 3: Luo line-matriisi.")
    parser.add_argument('--output_dir', type=str, required=False, help='Simulaatiokansion polku')
    args = parser.parse_args()
    output_dir = args.output_dir

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not output_dir:
        output_base = os.path.join(script_dir, "output")
        subdirs = [d for d in glob.glob(os.path.join(output_base, "*")) if os.path.isdir(d)]
        if not subdirs:
            print("Ei output-kansioita löytynyt!")
            sys.exit(1)
        latest_dir = max(subdirs, key=os.path.getmtime)
        output_dir = latest_dir
        print(f"Käytetään uusinta kansiota: {output_dir}")
    else:
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(script_dir, output_dir)

    if not os.path.exists(output_dir):
        print(f"Annettu output_dir ei ole olemassa: {output_dir}")
        sys.exit(1)
    main()
    print("\nSeuraava vaihe: Visualisoi line-matriisi komennolla:")
    print(f"python test_step4.py --output_dir {output_dir}")
