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
        for c in ['Number', 'X Position', 'Dropping_Time', 'Device_delay']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        return df

    stations = _read_csv_lenient(os.path.join(init_dir, "stations.csv"))

    # Uudet määrittelyt: tehtäväalueet ja fysiikka
    task_areas_path = os.path.join(init_dir, "transporters _task_areas.csv")
    phys_path = os.path.join(init_dir, "transporters _physics.csv")
    legacy_transporters_path = os.path.join(init_dir, "transporters.csv")  # legacy (no longer used)

    def _to_int(x, default=0):
        try:
            v = int(float(x))
            return v
        except Exception:
            return int(default)

    def _derive_minmax(row, model):
        # Poimi 100/200 arvot, 0 = ei käytössä
        min_lift_100 = _to_int(row.get('Min_Lift_Station_100', 0), 0)
        max_lift_100 = _to_int(row.get('Max_Lift_Station_100', 0), 0)
        min_sink_100 = _to_int(row.get('Min_Sink_Station_100', 0), 0)
        max_sink_100 = _to_int(row.get('Max_Sink_Station_100', 0), 0)
        # Joissain tiedostoissa 200-sarakkeen nimi on sekoittunut ("Max_Sink_Station_200Avoid")
        # Korjataan se lukemalla molemmat alias-nimet.
        min_lift_200 = _to_int(row.get('Min_Lift_Station_200', 0), 0)
        max_lift_200 = _to_int(row.get('Max_Lift_Station_200', 0), 0)
        min_sink_200 = _to_int(row.get('Min_Sink_Station_200', 0), 0)
        max_sink_200 = _to_int(row.get('Max_Sink_Station_200', row.get('Max_Sink_Station_200Avoid', 0)), 0)

        if str(model).strip().upper() == '2D':
            return (
                min_lift_100 or 0,
                max_lift_100 or 0,
                min_sink_100 or 0,
                max_sink_100 or 0,
            )
        # 3D: käytä molemmat alueet yhteenliitettynä (min = pienin, max = suurin). Välialueiden aukot
        # suodatetaan myöhemmin stations-listalla.
        mins_lift = [v for v in [min_lift_100, min_lift_200] if v]
        maxs_lift = [v for v in [max_lift_100, max_lift_200] if v]
        mins_sink = [v for v in [min_sink_100, min_sink_200] if v]
        maxs_sink = [v for v in [max_sink_100, max_sink_200] if v]
        min_lift = min(mins_lift) if mins_lift else 0
        max_lift = max(maxs_lift) if maxs_lift else 0
        min_sink = min(mins_sink) if mins_sink else 0
        max_sink = max(maxs_sink) if maxs_sink else 0
        return (min_lift, max_lift, min_sink, max_sink)

    # Rakenna transporters DataFrame yhdistämällä uudet määrittelyt; fallback legacyyn.
    transporters = None
    # Pidä mahdolliset normalisoidut lähde-DataFramet talteen myös erillisiksi cp_sat-vienneiksi
    task_df_out = None
    phys_df_out = None
    try:
        # Lue vain odotetut sarakkeet, jotta mahdolliset extra-sarakkeet (fysiikka tms.) eivät riko jäsennystä
        expected_cols = [
            'Transporter_id','Model',
            'Min_Lift_Station_100','Max_Lift_Station_100','Min_Sink_Station_100','Max_Sink_Station_100',
            'Min_Lift_Station_200','Max_Lift_Station_200','Min_Sink_Station_200','Max_Sink_Station_200',
            'Avoid'
        ]
        # Lue indekseillä vain ensimmäiset 10 saraketta, jotta mahdolliset ylimääräiset arvot riveillä eivät siirrä dataa vääriin sarakkeisiin
        base_names = [
            'Transporter_id','Model',
            'Min_Lift_Station_100','Max_Lift_Station_100','Min_Sink_Station_100','Max_Sink_Station_100',
            'Min_Lift_Station_200','Max_Lift_Station_200','Min_Sink_Station_200','Max_Sink_Station_200'
        ]
        def _read_task_areas_safely(path: str):
            """
            Lue tehtäväalueet varmasti oikein, riippumatta oudoista otsikoista tai ylimääräisistä arvoista.
            Käytetään aina manuaalista CSV-lukua ja mapataan selkeästi 11 ensimmäistä kenttää:
            [Transporter_id, Model, Min_Lift_Station_100, Max_Lift_Station_100, Min_Sink_Station_100, Max_Sink_Station_100,
             Min_Lift_Station_200, Max_Lift_Station_200, Min_Sink_Station_200, Max_Sink_Station_200(Avoid), Avoid]
            """
            import csv
            rows = []
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # discard header
                for parts in reader:
                    if not parts or len(parts) == 0:
                        continue
                    # Ota enintään 11 kenttää, täydennä puuttuvat None:lla
                    parts = (parts + [None]*11)[:11]
                    rows.append({
                        'Transporter_id': parts[0],
                        'Model': parts[1],
                        'Min_Lift_Station_100': parts[2],
                        'Max_Lift_Station_100': parts[3],
                        'Min_Sink_Station_100': parts[4],
                        'Max_Sink_Station_100': parts[5],
                        'Min_Lift_Station_200': parts[6],
                        'Max_Lift_Station_200': parts[7],
                        'Min_Sink_Station_200': parts[8],
                        # Otsikon mukaan tämä voi olla Max_Sink_Station_200 tai Max_Sink_Station_200Avoid
                        'Max_Sink_Station_200': parts[9],
                        'Avoid': parts[10] if len(parts) > 10 else None,
                    })
            df = pd.DataFrame(rows)
            # Puhdista tyypit
            def _clean_int_series(s):
                return s.apply(lambda v: _to_int(v, 0))
            for c in ['Transporter_id', 'Min_Lift_Station_100','Max_Lift_Station_100','Min_Sink_Station_100','Max_Sink_Station_100',
                      'Min_Lift_Station_200','Max_Lift_Station_200','Min_Sink_Station_200','Max_Sink_Station_200','Avoid']:
                if c in df.columns:
                    df[c] = _clean_int_series(df[c])
            # Model säilytetään merkkijonona
            if 'Model' in df.columns:
                df['Model'] = df['Model'].astype(str).str.strip()
            return df

        task_df = _read_task_areas_safely(task_areas_path)
        # Varmista sarakenimet
        task_df.columns = [c.strip() for c in task_df.columns]
        if set(base_names).issubset(set(task_df.columns)):
            # Supista vain olennaiset
            task_df = task_df[base_names]
        # Siivoa sarakenimet mahdollisista välilyönneistä
        task_df.columns = [c.strip() for c in task_df.columns]
        # Jos Max_Sink_Station_200 on sekoittunut Avoidiin (paholainen yhdistänyt otsikot), nimeä uudelleen
        if 'Max_Sink_Station_200Avoid' in task_df.columns and 'Max_Sink_Station_200' not in task_df.columns:
            task_df = task_df.rename(columns={'Max_Sink_Station_200Avoid': 'Max_Sink_Station_200'})
        # Jos Avoid puuttuu kokonaan, lisätään oletusarvo 2
        if 'Avoid' not in task_df.columns:
            task_df['Avoid'] = 2
        # Talleta normalisoitu task areas -näkymä vientiä varten
        ordered_task_cols = [
            'Transporter_id','Model',
            'Min_Lift_Station_100','Max_Lift_Station_100','Min_Sink_Station_100','Max_Sink_Station_100',
            'Min_Lift_Station_200','Max_Lift_Station_200','Min_Sink_Station_200','Max_Sink_Station_200',
            'Avoid'
        ]
        task_df_out = task_df[[c for c in ordered_task_cols if c in task_df.columns]].copy()

        def _read_physics_safely(path: str):
            import csv
            cols = [
                'Transporter_id','Acceleration_time (s)','Deceleration_time (s)','Max_speed (mm/s)',
                'Z_total_distance (mm)','Z_slow_distance_dry (mm)','Z_slow_distance_wet (mm)',
                'Z_slow_end_distance (mm)','Z_slow_speed (mm/s)','Z_fast_speed (mm/s)'
            ]
            rows = []
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for parts in reader:
                    if not parts:
                        continue
                    parts = (parts + [None]*len(cols))[:len(cols)]
                    rows.append(dict(zip(cols, parts)))
            df = pd.DataFrame(rows)
            # Tyypitä: id int, muut numerisiksi
            if 'Transporter_id' in df.columns:
                df['Transporter_id'] = df['Transporter_id'].apply(lambda v: _to_int(v, 0))
            for c in cols[1:]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            return df

        phys_df = None
        try:
            phys_df = _read_physics_safely(phys_path)
        except Exception:
            phys_df = None
        if phys_df is not None:
            phys_df_out = phys_df.copy()

        rows = []
        for _, r in task_df.iterrows():
            t_id = _to_int(r.get('Transporter_id', 0), 0)
            model = r.get('Model', '2D')
            min_lift, max_lift, min_sink, max_sink = _derive_minmax(r, model)
            avoid = _to_int(r.get('Avoid', 2), 2)
            base = {
                'Transporter_id': t_id,
                'Model': model,
                'Avoid': avoid,
                'Min_Lift_Station': min_lift,
                'Max_Lift_Station': max_lift,
                'Min_Sink_Station': min_sink,
                'Max_Sink_Station': max_sink,
            }
            # Liitä fysiikka-arvot jos saatavilla
            if phys_df is not None:
                p = phys_df[phys_df.get('Transporter_id', pd.Series(dtype=int)) == t_id]
                if not p.empty:
                    p = p.iloc[0]
                    for col in [
                        'Acceleration_time (s)', 'Deceleration_time (s)', 'Max_speed (mm/s)',
                        'Z_total_distance (mm)', 'Z_slow_distance_dry (mm)', 'Z_slow_distance_wet (mm)',
                        'Z_slow_end_distance (mm)', 'Z_slow_speed (mm/s)', 'Z_fast_speed (mm/s)'
                    ]:
                        if col in phys_df.columns:
                            base[col] = p.get(col)
            rows.append(base)
        transporters = pd.DataFrame(rows)
        # Järjestä sarakkeet mahdollisimman yhteensopivaksi CP-SAT:n kanssa
        # HUOM: Säilytä myös 'Model' jotta 3D-logiikka toimii siirtoajan esilaskennassa
        ordered_cols = [
            'Transporter_id','Model',
            'Min_Lift_Station','Max_Lift_Station','Min_Sink_Station','Max_Sink_Station','Avoid',
            'Acceleration_time (s)','Deceleration_time (s)','Max_speed (mm/s)',
            'Z_total_distance (mm)','Z_slow_distance_dry (mm)','Z_slow_distance_wet (mm)',
            'Z_slow_end_distance (mm)','Z_slow_speed (mm/s)','Z_fast_speed (mm/s)'
        ]
        # Säilytä vain olemassa olevat sarakkeet tässä järjestyksessä
        transporters = transporters[[c for c in ordered_cols if c in transporters.columns]]
    except Exception as e:
        # Älä enää käytä legacy-transporters.csv:tä: syötevirhe pitää korjata uusissa lähteissä
        raise RuntimeError(f"Failed to build transporters from task_areas/physics: {e}")
    
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
                # Muunna MaxTime sekunneiksi; tue sekä hh:mm:ss että sekuntimuotoa
                try:
                    max_secs = pd.to_timedelta(stage_df["MaxTime"]).dt.total_seconds().fillna(0).astype(int)
                except Exception:
                    max_secs = pd.to_numeric(stage_df["MaxTime"], errors="coerce").fillna(0).astype(int)
                max_proc = int(max_secs.sum())
                stages_count = int(stage_df.shape[0])

            transfer_moves = stages_count  # s=1: start->st1, + väliin siirrot
            transfer_total_avg = int(round(transfer_moves * avg_transfer))
            total_window = int(max_proc + transfer_total_avg)

            rows.append({
                "Treatment_program": int(prog),
                "Stages": stages_count,
                "MaxProcessTime_sum": int(max_proc),
                "AvgTransferTime": float(round(avg_transfer, 3)),
                "TransferMoves": int(transfer_moves),
                "TransferAvgTotal": int(transfer_total_avg),
                "TotalMaxWindow": int(total_window),
            })

        out_df = pd.DataFrame(rows).sort_values(["TotalMaxWindow", "Treatment_program"], ascending=[False, True]).reset_index(drop=True)
        if out_df.empty:
            print("  VAROITUS: Ei voitu laskea maksimi-ikkunaa (ei ohjelmia)")
            return
        sel = out_df.iloc[0].to_dict()
        sel_row = {
            "Treatment_program": int(sel["Treatment_program"]),
            "Stages": int(sel["Stages"]),
            "MaxProcessTime_sum": int(sel["MaxProcessTime_sum"]),
            "AvgTransferTime": float(sel["AvgTransferTime"]),
            "TransferMoves": int(sel["TransferMoves"]),
            "TransferAvgTotal": int(sel["TransferAvgTotal"]),
            "TotalMaxWindow": int(sel["TotalMaxWindow"]),
            "SELECTED": True,
        }
        out_df["SELECTED"] = False
        result_df = pd.concat([out_df, pd.DataFrame([sel_row])], ignore_index=True)
        out_path = os.path.join(cp_sat_dir, "cp_sat_maximum_process_time.csv")
        result_df.to_csv(out_path, index=False)
        print(f"  Maksimi-ikkuna laskettu ja tallennettu: {out_path}")
    except Exception as e:
        print(f"  VAROITUS: Maksimi-ikkunan esilaskenta epäonnistui: {e}")