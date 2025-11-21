
import os
import pandas as pd

def preprocess_for_cpsat(output_dir):
    
    # Read data from initialization and save all preprocessed files to the cp_sat directory
    init_dir = os.path.join(output_dir, "initialization")
    cp_sat_dir = os.path.join(output_dir, "cp_sat")
    os.makedirs(cp_sat_dir, exist_ok=True)
    
    # Read production plan for batch start station lookup
    production_df = pd.read_csv(os.path.join(init_dir, "production.csv"))
    
    # For each batch, create the correct program file based on production.csv
    originals_dir = os.path.join(output_dir, "initialization", "treatment_program_originals")
    for _, row in production_df.iterrows():
        batch_num = int(row["Batch"])
        program_num = int(row["Treatment_program"])
        src = os.path.join(originals_dir, f"Batch_{batch_num:03d}_Treatment_program_{program_num:03d}.csv")
        dst = os.path.join(cp_sat_dir, f"cp_sat_treatment_program_{batch_num}.csv")
        df = pd.read_csv(src)
        # Add step 0 at the beginning
        start_station = int(row["Start_station"])
        step0 = {
            "Stage": 0,
            "MinStat": start_station,
            "MaxStat": start_station,
            "MinTime": "00:00:00",
            "MaxTime": "100:00:00",
            "CalcTime": "00:00:00"
        }
        # Varmista, että CalcTime on olemassa myös muissa riveissä
        if "CalcTime" not in df.columns:
            df["CalcTime"] = df["MinTime"]
        # Yhdistä oikeassa sarakejärjestyksessä
        columns = ["Stage", "MinStat", "MaxStat", "MinTime", "MaxTime", "CalcTime"]
        df = pd.concat([pd.DataFrame([step0], columns=columns), df[columns]], ignore_index=True)
        # Replace Stage column with running numbers (0,1,2,...)
        df["Stage"] = range(len(df))
        df.to_csv(dst, index=False, encoding="utf-8")
    
    # Create cp_sat_batches.csv (copy production.csv, but with the correct name and all columns)
    production = pd.read_csv(os.path.join(init_dir, "production.csv"))
    batches_path = os.path.join(cp_sat_dir, "cp_sat_batches.csv")
    # Säilytä kaikki sarakkeet, myös Start_optimized, jos se on olemassa
    production.to_csv(batches_path, index=False, encoding="utf-8")
    
    # Preprocesses existing data into a format suitable for CP-SAT, but does not invent any new data.
    # All data is read from output_dir and saved with _cpsat.csv suffix.
    import shutil

    def _read_csv_lenient(path: str):
        """Read CSV and tolerate extra/missing fields by truncating/padding to header length."""
        import csv
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            cols = [h.strip() for h in header]
            rows = []
            for parts in reader:
                if parts is None:
                    continue
                vals = (parts + [None]*len(cols))[:len(cols)]
                rows.append(dict(zip(cols, vals)))
        df = pd.DataFrame(rows)
        # Coerce common numeric columns
        for c in ['Number', 'Tank', 'Group', 'X Position', 'Dropping_Time', 'Device_delay']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        # Convert to integers where appropriate
        for c in ['Number', 'Tank', 'Group']:
            if c in df.columns:
                df[c] = df[c].fillna(0).astype(int)
        return df

    # Load stations from JSON
    from load_stations_json import load_stations_from_json
    stations = load_stations_from_json(init_dir)

    # Load transporters from JSON
    from load_transporters_json import load_transporters_from_json
    phys_df, task_df, start_pos_df = load_transporters_from_json(init_dir)

    def _to_int(x, default=0):
        try:
            v = int(float(x))
            return v
        except Exception:
            return int(default)

    def _derive_minmax(row, model):
        # Poimi 100/200/300/400 arvot, 0 = ei käytössä
        min_lift_100 = _to_int(row.get('Min_Lift_Station_100', 0), 0)
        max_lift_100 = _to_int(row.get('Max_Lift_Station_100', 0), 0)
        min_sink_100 = _to_int(row.get('Min_Sink_Station_100', 0), 0)
        max_sink_100 = _to_int(row.get('Max_Sink_Station_100', 0), 0)
        
        min_lift_200 = _to_int(row.get('Min_Lift_Station_200', 0), 0)
        max_lift_200 = _to_int(row.get('Max_Lift_Station_200', 0), 0)
        min_sink_200 = _to_int(row.get('Min_Sink_Station_200', 0), 0)
        max_sink_200 = _to_int(row.get('Max_Sink_Station_200', 0), 0)
        
        min_lift_300 = _to_int(row.get('Min_Lift_Station_300', 0), 0)
        max_lift_300 = _to_int(row.get('Max_Lift_Station_300', 0), 0)
        min_sink_300 = _to_int(row.get('Min_Sink_Station_300', 0), 0)
        max_sink_300 = _to_int(row.get('Max_Sink_Station_300', 0), 0)
        
        min_lift_400 = _to_int(row.get('Min_Lift_Station_400', 0), 0)
        max_lift_400 = _to_int(row.get('Max_Lift_Station_400', 0), 0)
        min_sink_400 = _to_int(row.get('Min_Sink_Station_400', 0), 0)
        max_sink_400 = _to_int(row.get('Max_Sink_Station_400', 0), 0)

        if str(model).strip().upper() == '2D':
            # 2D: käytä ensimmäistä ei-nolla aluetta
            for ml, mxl, ms, mxs in [(min_lift_100, max_lift_100, min_sink_100, max_sink_100),
                                      (min_lift_200, max_lift_200, min_sink_200, max_sink_200),
                                      (min_lift_300, max_lift_300, min_sink_300, max_sink_300),
                                      (min_lift_400, max_lift_400, min_sink_400, max_sink_400)]:
                if ml or mxl or ms or mxs:
                    return (ml or 0, mxl or 0, ms or 0, mxs or 0)
            return (0, 0, 0, 0)
            
        # 3D: käytä kaikkien alueiden yhteenliitettynä (min = pienin, max = suurin)
        mins_lift = [v for v in [min_lift_100, min_lift_200, min_lift_300, min_lift_400] if v]
        maxs_lift = [v for v in [max_lift_100, max_lift_200, max_lift_300, max_lift_400] if v]
        mins_sink = [v for v in [min_sink_100, min_sink_200, min_sink_300, min_sink_400] if v]
        maxs_sink = [v for v in [max_sink_100, max_sink_200, max_sink_300, max_sink_400] if v]
        min_lift = min(mins_lift) if mins_lift else 0
        max_lift = max(maxs_lift) if maxs_lift else 0
        min_sink = min(mins_sink) if mins_sink else 0
        max_sink = max(maxs_sink) if maxs_sink else 0
        return (min_lift, max_lift, min_sink, max_sink)

    # Rakenna transporters DataFrame yhdistämällä task_df ja phys_df
    task_df_out = task_df.copy()
    phys_df_out = phys_df.copy()
    
    rows = []
    for _, r in task_df.iterrows():
        t_id = _to_int(r.get('Transporter_id', 0), 0)
        model = r.get('Model', '2D')
        min_lift, max_lift, min_sink, max_sink = _derive_minmax(r, model)
        
        base = {
            'Transporter_id': t_id,
            'Model': model,
            'Min_Lift_Station': min_lift,
            'Max_Lift_Station': max_lift,
            'Min_Sink_Station': min_sink,
            'Max_Sink_Station': max_sink,
        }
        
        # Liitä fysiikka-arvot
        p = phys_df[phys_df['Transporter_id'] == t_id]
        if not p.empty:
            p = p.iloc[0]
            # Päivitetyt sarakkeet X ja Y erottelulle
            for col in ['X_acceleration_time (s)', 'X_deceleration_time (s)', 'X_max_speed (mm/s)',
                        'Y_acceleration_time (s)', 'Y_deceleration_time (s)', 'Y_max_speed (mm/s)',
                        'Z_total_distance (mm)', 'Z_slow_distance_dry (mm)', 'Z_slow_distance_wet (mm)',
                        'Z_slow_end_distance (mm)', 'Z_slow_speed (mm/s)', 'Z_fast_speed (mm/s)',
                        'Avoid_distance (mm)']:
                if col in phys_df.columns:
                    base[col] = p.get(col)
        rows.append(base)
    
    transporters = pd.DataFrame(rows)
    
    # Järjestä sarakkeet
    ordered_cols = [
        'Transporter_id','Model',
        'Min_Lift_Station','Max_Lift_Station','Min_Sink_Station','Max_Sink_Station',
        'X_acceleration_time (s)','X_deceleration_time (s)','X_max_speed (mm/s)',
        'Y_acceleration_time (s)','Y_deceleration_time (s)','Y_max_speed (mm/s)',
        'Z_total_distance (mm)','Z_slow_distance_dry (mm)','Z_slow_distance_wet (mm)',
        'Z_slow_end_distance (mm)','Z_slow_speed (mm/s)','Z_fast_speed (mm/s)',
        'Avoid_distance (mm)'
    ]
    transporters = transporters[[c for c in ordered_cols if c in transporters.columns]]
    
    from transporter_physics import calculate_physics_transfer_time, calculate_lift_time, calculate_sink_time
    transfer_tasks_path = os.path.join(cp_sat_dir, "cp_sat_transfer_tasks.csv")
    rows = []
    # Jokaiselle nostimelle kaikki mahdolliset siirrot sen nosto- ja laskualueiden perusteella
    for _, transporter_row in transporters.iterrows():
        transporter_id = int(transporter_row["Transporter_id"])
        model = str(transporter_row.get('Model', '2D')).strip().upper()
        # Lue asemavälit: nostolle (lift) ja laskulle (sink)
        min_lift = int(transporter_row.get("Min_Lift_Station", transporter_row.get("Min_lift_station", transporter_row.get("MinLiftStation", 0))))
        max_lift = int(transporter_row.get("Max_Lift_Station", transporter_row.get("Max_lift_station", transporter_row.get("MaxLiftStation", 0))))
        min_sink = int(transporter_row.get("Min_Sink_Station", transporter_row.get("Min_sink_station", transporter_row.get("MinSinkStation", 0))))
        max_sink = int(transporter_row.get("Max_Sink_Station", transporter_row.get("Max_sink_station", transporter_row.get("MaxSinkStation", 0))))

        # Sallitut asemat, jotka oikeasti löytyvät stations.csv:stä
        lift_candidates = [s for s in range(min_lift, max_lift + 1) if s in set(stations["Number"])]
        sink_candidates = [s for s in range(min_sink, max_sink + 1) if s in set(stations["Number"])]

        # Lasketaan siirtoajat kaikille sallituilla (from,to) pareille
        for from_station in lift_candidates:
            from_row = stations[stations["Number"] == from_station]
            if from_row.empty:
                continue
            from_info = from_row.iloc[0]
            # "Pienemmästä minimistä suurempaan maksimiin" tulkitaan kattamaan koko sallitun välin
            for to_station in sink_candidates:
                to_row = stations[stations["Number"] == to_station]
                if to_row.empty:
                    continue
                to_info = to_row.iloc[0]
                # Laske nosto- ja laskuajat; salli NaN -> 0.0 fallback
                try:
                    lift_time = round(float(calculate_lift_time(from_info, transporter_row)), 1)
                except Exception:
                    lift_time = 0.0
                if pd.isna(lift_time):
                    lift_time = 0.0
                try:
                    sink_time = round(float(calculate_sink_time(to_info, transporter_row)), 1)
                except Exception:
                    sink_time = 0.0
                if pd.isna(sink_time):
                    sink_time = 0.0
                # Laske siirtoajat X ja mahdollinen Y (3D)
                # X-suunnan aika kuten ennenkin
                if from_station == to_station:
                    x_time = 0.0
                else:
                    x_time = round(float(calculate_physics_transfer_time(from_info, to_info, transporter_row)), 1)
                transfer_time = x_time
                if model == '3D':
                    # Y-suunnan aika kerran laskettuna (vakio 4000 mm), käytetään samoja fysiikkaparametreja kuin X:ssä
                    # Lasketaan Y vain jos liikutaan eri linjojen välillä (100-sarja vs 200-sarja)
                    def _line_of(station_number: int) -> int:
                        try:
                            return int(station_number) // 100
                        except Exception:
                            return 0
                    y_distance = 4000 if _line_of(from_station) != _line_of(to_station) else 0
                    if y_distance > 0:
                        # Rakennetaan keinotekoiset station-rivit, joilla X Position erotus = y_distance
                        import pandas as _pd
                        fake_from = _pd.Series({'X Position': 0})
                        fake_to = _pd.Series({'X Position': y_distance})
                        y_time = round(float(calculate_physics_transfer_time(fake_from, fake_to, transporter_row)), 1)
                    else:
                        y_time = 0.0
                    # TransferTime = max(X, Y)
                    transfer_time = max(x_time, y_time)

                # OUTPUT CONTRACT CHANGE:
                # - For 3D, store doubled Lift/Sink directly in columns LiftTime/SinkTime
                # - For 2D, store as-is
                # - TotalTaskTime is always computed uniformly as LiftTime + TransferTime + SinkTime
                if model == '3D':
                    lift_out = round(2*float(lift_time), 1)
                    sink_out = round(2*float(sink_time), 1)
                else:
                    lift_out = round(float(lift_time), 1)
                    sink_out = round(float(sink_time), 1)
                total_task_time = round(float(lift_out) + float(transfer_time) + float(sink_out), 1)
                rows.append({
                    "Transporter": transporter_id,
                    "From_Station": from_station,
                    "To_Station": to_station,
                    "LiftTime": lift_out,
                    "TransferTime": transfer_time,
                    "SinkTime": sink_out,
                    "TotalTaskTime": total_task_time
                })
    transfer_tasks = pd.DataFrame(rows)
    # Järjestä sarakkeet haluttuun järjestykseen
    transfer_tasks = transfer_tasks[["Transporter", "From_Station", "To_Station", "LiftTime", "TransferTime", "SinkTime", "TotalTaskTime"]]
    transfer_tasks.to_csv(transfer_tasks_path, index=False)

    # Also save files required by CP-SAT optimization with correct names to cp_sat directory
    stations.to_csv(os.path.join(cp_sat_dir, "cp_sat_stations.csv"), index=False, encoding="utf-8")
    transporters.to_csv(os.path.join(cp_sat_dir, "cp_sat_transporters.csv"), index=False, encoding="utf-8")
    # Kirjoita myös erilliset lähdetiedostojen normalisoidut näkymät, jos saatavilla
    try:
        if task_df_out is not None and not task_df_out.empty:
            task_out_path = os.path.join(cp_sat_dir, "cp_sat_transporters_task_areas.csv")
            task_df_out.to_csv(task_out_path, index=False, encoding="utf-8")
    except Exception:
        pass
    try:
        if phys_df_out is not None and not phys_df_out.empty:
            phys_out_path = os.path.join(cp_sat_dir, "cp_sat_transporters_physics.csv")
            phys_df_out.to_csv(phys_out_path, index=False, encoding="utf-8")
    except Exception:
        pass

    # --- Precompute maximum process-time window across used programs ---
    try:
        print("Esilaskenta: maksimi prosessiaikaikkuna (cp_sat_maximum_process_time.csv)")
        batches_path = os.path.join(cp_sat_dir, "cp_sat_batches.csv")
        transfers_path = os.path.join(cp_sat_dir, "cp_sat_transfer_tasks.csv")
        if not os.path.exists(batches_path) or not os.path.exists(transfers_path):
            print("  VAROITUS: Ei voitu laskea maksimi-ikkunaa (puuttuu cp_sat_batches.csv tai cp_sat_transfer_tasks.csv)")
            return
        batches_df = pd.read_csv(batches_path)
        transfers_df = pd.read_csv(transfers_path)

        # Laske keskimääräinen siirtoaika (vain oikeat siirrot TransferTime > 0)
        transfers_df["TransferTime"] = pd.to_numeric(transfers_df["TransferTime"], errors="coerce").fillna(0.0)
        nonzero = transfers_df[transfers_df["TransferTime"] > 0]
        avg_transfer = float(nonzero["TransferTime"].mean()) if not nonzero.empty else 0.0

        # Käytössä olevat ohjelmat
        used_programs = sorted(set(pd.to_numeric(batches_df["Treatment_program"], errors="coerce").dropna().astype(int).tolist()))
        rows = []
        for prog in used_programs:
            # Etsi mikä tahansa erä, joka käyttää tätä ohjelmaa, ja lue sen ohjelmatiedosto
            cand_batches = batches_df[batches_df["Treatment_program"] == prog]["Batch"].astype(int).tolist()
            if not cand_batches:
                continue
            b = int(cand_batches[0])
            prog_path = os.path.join(cp_sat_dir, f"cp_sat_treatment_program_{b}.csv")
            if os.path.exists(prog_path):
                prog_df = pd.read_csv(prog_path)
            else:
                # Varavaihtoehto: initialization/treatment_program_XXX.csv
                init_prog_path = os.path.join(init_dir, f"treatment_program_{int(prog):03d}.csv")
                if not os.path.exists(init_prog_path):
                    print(f"  VAROITUS: Ohjelmatiedosto puuttuu: {prog_path} ja {init_prog_path}")
                    continue
                prog_df = pd.read_csv(init_prog_path)

            # Stage > 0 rivit
            if "Stage" not in prog_df.columns:
                print(f"  VAROITUS: Ohjelmatiedosto ilman Stage-saraketta: {prog_path}")
                continue
            stage_df = prog_df[prog_df["Stage"] > 0].copy()
            if stage_df.empty:
                stages_count = 0
                max_proc = 0
            else:
                # Muunna MinTime sekunneiksi; tue sekä hh:mm:ss että sekuntimuotoa
                try:
                    min_secs = pd.to_timedelta(stage_df["MinTime"]).dt.total_seconds().fillna(0).astype(int)
                except Exception:
                    min_secs = pd.to_numeric(stage_df["MinTime"], errors="coerce").fillna(0).astype(int)
                min_proc = int(min_secs.sum())
                stages_count = int(stage_df.shape[0])

            transfer_moves = stages_count  # s=1: start->st1, + väliin siirrot
            transfer_total_avg = int(round(transfer_moves * avg_transfer))
            total_window = int(min_proc + transfer_total_avg)

            rows.append({
                "Treatment_program": int(prog),
                "Stages": stages_count,
                "MinProcessTime_sum": int(min_proc),
                "AvgTransferTime": float(round(avg_transfer, 3)),
                "TransferMoves": int(transfer_moves),
                "TransferAvgTotal": int(transfer_total_avg),
                "TotalMinWindow": int(total_window),
            })

        # Valitse lyhin (MinTime + siirrot) ramp-up laskentaan
        out_df = pd.DataFrame(rows).sort_values(["TotalMinWindow", "Treatment_program"], ascending=[True, True]).reset_index(drop=True)
        if out_df.empty:
            print("  VAROITUS: Ei voitu laskea maksimi-ikkunaa (ei ohjelmia)")
            return
        sel = out_df.iloc[0].to_dict()
        sel_row = {
            "Treatment_program": int(sel["Treatment_program"]),
            "Stages": int(sel["Stages"]),
            "MinProcessTime_sum": int(sel["MinProcessTime_sum"]),
            "AvgTransferTime": float(sel["AvgTransferTime"]),
            "TransferMoves": int(sel["TransferMoves"]),
            "TransferAvgTotal": int(sel["TransferAvgTotal"]),
            "TotalMinWindow": int(sel["TotalMinWindow"]),
            "SELECTED": True,
        }
        out_df["SELECTED"] = False
        result_df = pd.concat([out_df, pd.DataFrame([sel_row])], ignore_index=True)
        out_path = os.path.join(cp_sat_dir, "cp_sat_maximum_process_time.csv")
        result_df.to_csv(out_path, index=False)
        print(f"  Maksimi-ikkuna laskettu ja tallennettu: {out_path}")
    except Exception as e:
        print(f"  VAROITUS: Maksimi-ikkunan esilaskenta epäonnistui: {e}")

    # --- Päivitä goals.json ramp_up:lla ja tarkalla kapasiteetilla ---
    try:
        import json
        goals_path = os.path.join(init_dir, "goals.json")
        if not os.path.exists(goals_path):
            print(f"  VAROITUS: goals.json ei löytynyt päivitystä varten: {goals_path}")
        else:
            with open(goals_path, "r", encoding="utf-8") as f:
                goals = json.load(f)

            # Lue tarkka minimi prosessiaika ja siirtojen määrä sekä keskimääräinen siirtoaika
            max_proc_path = os.path.join(cp_sat_dir, "cp_sat_maximum_process_time.csv")
            if not os.path.exists(max_proc_path):
                print(f"  VAROITUS: cp_sat_maximum_process_time.csv puuttuu, ramp_up-arvoa ei päivitetä")
            else:
                # import pandas as pd (poistettu, pd on jo importattu tiedoston alussa)
                max_proc_df = pd.read_csv(max_proc_path)
                # Valitse rivi, jossa SELECTED==True, muuten ensimmäinen
                sel = max_proc_df[max_proc_df["SELECTED"] == True] if "SELECTED" in max_proc_df.columns else max_proc_df.iloc[[0]]
                if sel.empty:
                    sel = max_proc_df.iloc[[0]]
                sel = sel.iloc[0]
                # Käytä MinProcessTime_sum jos saatavilla, muuten fallback MaxProcessTime_sum
                if "MinProcessTime_sum" in sel:
                    min_process_time = int(sel["MinProcessTime_sum"])
                else:
                    min_process_time = int(sel.get("MaxProcessTime_sum", 0))
                n_transfers = int(sel["TransferMoves"])
                avg_transfer_time = float(sel["AvgTransferTime"])
                ramp_up = min_process_time + n_transfers * avg_transfer_time

                # Päivitä goals.json:iin ramp_up ja recalculated targets
                # Oletetaan 8h simulaatio (tai haetaan se goalsista)
                sim_hours = goals.get("simulation_goals", {}).get("simulation_period", {}).get("duration_hours", 8.0)
                
                # Laske tuottava aika simulaatiossa
                productive_hours = sim_hours - (ramp_up / 3600.0)
                if productive_hours < 0:
                    productive_hours = 0

                # --- KORJAUS: Laske vaadittu tahti (batches/h) perustuen vuositason tuottavaan aikaan ---
                # 1. Hae vuositavoite ja vuositunnit goals.jsonista
                annual_batches = goals.get("target_pace", {}).get("annual_batches", 0)
                annual_hours = goals.get("target_pace", {}).get("annual_production_hours", 0)
                
                # 2. Laske vuositason ramp-up hukka
                # Oletus: 1 vuoro/pv, 5 pv/vko, 48 vko/vuosi (nämä pitäisi olla customer.jsonissa, mutta arvioidaan tässä)
                # Parempi tapa: annual_hours / 8h = vuorojen määrä (jos 8h vuoro)
                shifts_per_year = annual_hours / 8.0 if annual_hours > 0 else 240 # fallback 240
                annual_ramp_loss_hours = shifts_per_year * (ramp_up / 3600.0)
                
                # 3. Todellinen vuotuinen tuottava aika
                annual_productive_hours = annual_hours - annual_ramp_loss_hours
                if annual_productive_hours <= 0:
                    annual_productive_hours = 1 # estä nollalla jako

                # 4. Uusi, kireämpi tahti (batches per productive hour)
                required_batches_per_hour = annual_batches / annual_productive_hours

                # 5. Laske simulaation tavoite tällä kireämmällä tahdilla
                new_total_batches = int(round(required_batches_per_hour * productive_hours))
                
                # Laske cycle time tälle tahdille
                cycle_time_sec = round(3600 / required_batches_per_hour, 2) if required_batches_per_hour > 0 else None

                # PÄIVITÄ goals.json tavoitteet
                current_total = goals.get("totals", {}).get("total_simulation_batches", 0)
                goals["totals"]["total_simulation_batches"] = new_total_batches
                
                # Päivitä myös simulation_targets
                if "simulation_targets" in goals:
                    for target in goals["simulation_targets"]:
                        old_target = target.get("target_batches", 0)
                        if current_total > 0:
                            # Skaalaa suhteessa uuteen kokonaismäärään
                            # Huom: Jos annual_batches oli oikein, tämä pitäisi täsmätä suoraan
                            new_target = int(round(old_target * (new_total_batches / current_total)))
                        else:
                            new_target = 0
                        target["target_batches"] = new_target
                        target["target_pieces"] = new_target * target.get("pieces_per_batch", 1)

                # Kirjoita tiedot goals.json:iin
                goals["target_pace"]["ramp_up_seconds"] = ramp_up
                goals["target_pace"]["productive_hours"] = round(productive_hours, 3)
                goals["target_pace"]["batches_per_hour_productive"] = round(required_batches_per_hour, 3)
                goals["target_pace"]["cycle_time_seconds_productive"] = cycle_time_sec
                goals["target_pace"]["annual_productive_hours"] = round(annual_productive_hours, 1)
                goals["target_pace"]["ramp_up_calculation"] = {
                    "min_process_time": min_process_time,
                    "n_transfers": n_transfers,
                    "avg_transfer_time": avg_transfer_time,
                    "formula": "ramp_up = min_process_time + n_transfers * avg_transfer_time"
                }
                goals["target_pace"]["update_note"] = "Target recalculated based on REAL productive hours (annual - ramp_up_loss)"

                with open(goals_path, "w", encoding="utf-8") as f:
                    json.dump(goals, f, indent=2, ensure_ascii=False)
                print(f"  goals.json päivitetty ramp_up:lla ja kapasiteetilla: {goals_path}")
    except Exception as e:
        print(f"  VAROITUS: goals.json päivitys epäonnistui: {e}")