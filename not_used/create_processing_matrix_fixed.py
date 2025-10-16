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
        "Remaining": 0,
        "Phase_1": 0,  # Ei siirtoa edeltävässä rivissä
        "Phase_2": 0,
        "Phase_3": 0,
        "Phase_4": 0
    })
    
    # 2. Aloitetaan käsittelyvaiheet Loading-aseman jälkeen
    # Käytetään fysiikkapohjaista siirtoaikaa ja tallennetaan vaiheajat
    from test_step3 import load_stations, calculate_physics_transfer_time_with_phases
    
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
        if i == 0:
            # Ensimmäinen vaihe - siirto Loading-asemalta
            current_phase_1, current_phase_2, current_phase_3, current_phase_4 = first_phase_1, first_phase_2, first_phase_3, first_phase_4
        else:
            # Myöhemmät vaiheet - käytä edellisessä iteraatiossa laskettuja vaiheita
            current_phase_1, current_phase_2, current_phase_3, current_phase_4 = next_phase_1, next_phase_2, next_phase_3, next_phase_4
        
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
            "Remaining": int(calc_time),  # koko aika on jäljellä
            "Phase_1": round(current_phase_1, 2),  # Edeltävän siirron nosto
            "Phase_2": round(current_phase_2, 2),  # Edeltävän siirron vaakasiirto
            "Phase_3": round(current_phase_3, 2),  # Edeltävän siirron lasku
            "Phase_4": round(current_phase_4, 2)   # Edeltävän siirron asettuminen
        })
    
    # 3. Lisää Unloading-asema (111) viimeiseksi
    unloading_entry = time
    
    # Viimeisen siirron vaiheajat Unloading-asemalle
    if len(prog_df) > 0:
        last_station = int(prog_df.iloc[-1]["MinStat"])
        _, last_phases = calculate_physics_transfer_time_with_phases(last_station, 111, stations_df)
        last_phase_1, last_phase_2, last_phase_3, last_phase_4 = last_phases
    else:
        last_phase_1, last_phase_2, last_phase_3, last_phase_4 = (10, 20, 10, 0)
    
    rows.append({
        "Batch": int(batch_id),
        "Program": 1,
        "Stage": len(prog_df) + 1,  # Unloading on viimeinen vaihe
        "Station": 111,  # Unloading-asema
        "MinTime": 0,
        "MaxTime": 0,
        "CalcTime": 0,
        "EntryTime": int(unloading_entry),
        "ExitTime": int(unloading_entry),
        "Remaining": 0,
        "Phase_1": round(last_phase_1, 2),  # Viimeisen siirron nosto
        "Phase_2": round(last_phase_2, 2),  # Viimeisen siirron vaakasiirto
        "Phase_3": round(last_phase_3, 2),  # Viimeisen siirron lasku
        "Phase_4": round(last_phase_4, 2)   # Viimeisen siirron asettuminen
    })
    
    return rows
