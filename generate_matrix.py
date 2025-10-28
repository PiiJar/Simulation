
import os
import pandas as pd
from datetime import datetime

def load_stations(output_dir):
	"""Lataa Stations.csv tiedoston"""
	stations_file = os.path.join(output_dir, "initialization", "stations.csv")
	if not os.path.exists(stations_file):
		raise FileNotFoundError(f"Stations.csv ei löydy: {stations_file}")
	return pd.read_csv(stations_file)

def select_capable_transporter(lift_station, sink_station, stations_df, transporters_df):
	"""
	Valitsee sopivan nostimen tehtävälle stations ja transporters tietojen perusteella.
	Kopioi alkuperäisen logiikan generate_matrix_original.py:stä.
	"""
	# Hae asemien x-koordinaatit
	lift_x = stations_df[stations_df['Number'] == lift_station]['X Position'].iloc[0]
	sink_x = stations_df[stations_df['Number'] == sink_station]['X Position'].iloc[0]
    
	# Käy läpi nostimet järjestyksessä
	for _, transporter in transporters_df.iterrows():
		min_x = transporter['Min_x_position']
		max_x = transporter['Max_x_Position']
        
		# Tarkista että molemmat asemat ovat nostimen alueella
		if min_x <= lift_x <= max_x and min_x <= sink_x <= max_x:
			return transporter
    
	# Jos mikään nostin ei pysty, palautetaan ensimmäinen (virhetilanne)
	return transporters_df.iloc[0]

def select_available_station(min_stat, max_stat, station_reservations, entry_time, exit_time):
	"""
	Valitsee ensimmäisen vapaan aseman MinStat-MaxStat väliltä numerojärjestyksessä.
	Yksinkertaistettu versio alkuperäisestä - ei kirjaa konflikteja.
	"""
	for station in range(min_stat, max_stat + 1):
		if station not in station_reservations:
			station_reservations[station] = []
        
		# Tarkista onko asema vapaa haluttuna aikana
		is_available = True
		for reservation in station_reservations[station]:
			res_start, res_end = reservation[:2]
			# Jos aikavälit menevät päällekkäin
			latest_start = max(entry_time, res_start)
			earliest_end = min(exit_time, res_end)
			if earliest_end > latest_start:  # Päällekkäisyys löytyi
				is_available = False
				break
        
		if is_available:
			return station
    
	# Jos mikään ei ole vapaa, palauta ensimmäinen
	return min_stat

def load_production_batches_stretched(output_dir):
	"""Lataa Production.csv ja palauttaa tuotantoerien tiedot päivitetyillä lähtöajoilla"""
	# Lue AINA initialization/production.csv (sisältää kaikki sarakkeet: Start_original, Start_stretch, Start_optimized)
	production_file = os.path.join(output_dir, "initialization", "production.csv")
    
	if not os.path.exists(production_file):
		raise FileNotFoundError(f"Production.csv ei löydy: {production_file}")
    
	df = pd.read_csv(production_file)
    
	# Käytetään VAIN Start_optimized -kenttää (CP-SAT optimoinnin tulos)
	if "Start_optimized" in df.columns and df["Start_optimized"].notna().any():
		start_field = "Start_optimized"
	else:
		raise ValueError(f"Start_optimized-kenttää ei löydy production.csv:stä tai se on tyhjä. Sarakkeet: {list(df.columns)}.\nVarmista, että optimointi on ajettu ja tulokset tallennettu oikein.")

	# Muunna Start_optimized (HH:MM:SS) sekunneiksi laskentaa varten
	df["Start_time_seconds"] = pd.to_timedelta(df[start_field]).dt.total_seconds()

	return df

def load_batch_program_optimized(programs_dir, batch_id, treatment_program):
	"""
	Lataa eräkohtainen ohjelmatiedosto optimized_programs kansiosta.
	"""
	batch_str = str(batch_id).zfill(3)
	program_str = str(treatment_program).zfill(3)
    
	# Käytä aina optimized_programs kansiota
	file_path = os.path.join(programs_dir, f"Batch_{batch_str}_Treatment_program_{program_str}.csv")
    
	if not os.path.exists(file_path):
		raise FileNotFoundError(f"Eräohjelmaa ei löydy: {file_path}")
    
	df = pd.read_csv(file_path)
    
	# Muunna ajat sekunteiksi
	df["MinTime"] = pd.to_timedelta(df["MinTime"]).dt.total_seconds()
	df["MaxTime"] = pd.to_timedelta(df["MaxTime"]).dt.total_seconds()
    
	if "CalcTime" in df.columns:
		df["CalcTime"] = pd.to_timedelta(df["CalcTime"]).dt.total_seconds()
	else:
		df["CalcTime"] = df["MinTime"]
    
	return df

def generate_matrix_pure(output_dir):
	"""
	Luo lopullisen matriisin päivitetyn Production.csv:n ja optimoitujen ohjelmien perusteella.
	EI ratkaise konflikteja, EI päivitä Production.csv:ää.
    
	LOGIIKKA:
	1. Käyttää päivitettyä Production.csv Start_time kenttää (muuntaa sekunteiksi)
	2. Käyttää AINA optimoituja ohjelmia (optimized_programs/) 
	3. Laskee EntryTime/ExitTime peräkkäisesti ohjelman vaiheiden mukaan
	4. Huomioi rinnakkaiset asemat (MinStat-MaxStat) asemavarausten kanssa
	5. Laskee nostimen fysiikan (Phase_1, Phase_2, Phase_3, Phase_4)
	"""
	logs_dir = os.path.join(output_dir, "logs")
	optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")
	output_file = os.path.join(logs_dir, "line_matrix.csv")
    
	# Lataa lähtötiedot - päivitetty Production.csv jossa Start_time ON oikein
	production_df = load_production_batches_stretched(output_dir)
	stations_df = load_stations(output_dir)
	transporters_df = pd.read_csv(os.path.join(output_dir, "initialization", "transporters.csv"))
	# Lue esilasketut siirtoajat (nostinliikkeet) tiedostosta uudella nimellä ja sijainnilla
	transfers_path = os.path.join(output_dir, "cp_sat", "cp_sat_transfer_tasks.csv")
	if not os.path.exists(transfers_path):
		raise FileNotFoundError(f"Precomputed transfer times file not found: {transfers_path}\nRun preprocessing/optimization first!")
	try:
		transfers_df = pd.read_csv(transfers_path)
		for col in ["Batch", "Stage", "From_Station", "To_Station"]:
			if col in transfers_df.columns:
				transfers_df[col] = transfers_df[col].astype(int)
	except Exception as e:
		raise RuntimeError(f"Failed to load precomputed transfer times: {e}")
    
	# Asemavaraukset rinnakkaisten asemien hallintaan
	station_reservations = {}
    
	all_rows = []
    
	# 📌 Ohjelmoidaan matrix, jossa otetaan huomioin sekä asemien että nostinten rajoitukset
	station_reservations = {}  # Jokaiselle asemalle: [(start, end), ...]
	transporter_free_at = 0  # KRIITTINEN: Milloin nostin on vapaa aloittamaan seuraavan tehtävän

	all_rows = []
    
	# KRIITTINEN: Käy läpi erät AIKAJÄRJESTYKSESSÄ (Start_time_seconds)
	# Muuten erät menevät päällekkäin kun ne prosessoidaan väärässä järjestyksessä!
	production_df_sorted = production_df.sort_values('Start_time_seconds').reset_index(drop=True)    # Käy läpi jokainen erä AIKAJÄRJESTYKSESSÄ
	for _, batch_row in production_df_sorted.iterrows():
		batch_id = int(batch_row["Batch"])
		start_station = int(batch_row["Start_station"])
		treatment_program = int(batch_row["Treatment_program"])
		start_time_seconds = float(batch_row["Start_time_seconds"])

		prog_df = load_batch_program_optimized(optimized_dir, batch_id, treatment_program)

	# Stage 0: Laske transport-aika start_station → ensimmäinen käsittelyasema
		first_prog_row = prog_df.iloc[0]
		first_min_stat = int(first_prog_row["MinStat"])
		first_max_stat = int(first_prog_row["MaxStat"])
        
		# Valitse kohdestation (Stage 1:n asema)
		# Jos transfers_df sisältää Sink_stat, käytä sitä
		temp_sink_stat = None
		if transfers_df is not None:
			match = transfers_df[(transfers_df["Batch"] == batch_id) & (transfers_df["Stage"] == 0)]
			if not match.empty and "Sink_stat" in match.columns:
				try:
					temp_sink_stat = int(match.iloc[0]["Sink_stat"])
				except Exception:
					temp_sink_stat = None
		# Muuten valitse ensimmäinen vapaa asema MinStat–MaxStat -väliltä
		if temp_sink_stat is None:
			temp_sink_stat = select_available_station(first_min_stat, first_max_stat, station_reservations, 
													  int(start_time_seconds), int(start_time_seconds))
        
		# Hae esilasketut siirtoajat Stage 0:lle
		match = transfers_df[(transfers_df["Batch"] == batch_id) & (transfers_df["Stage"] == 0)]
		if not match.empty:
			phase_2_0 = match.iloc[0]["Phase_2"] if "Phase_2" in match.columns else 0
			phase_3_0 = match.iloc[0]["Phase_3"] if "Phase_3" in match.columns else 0
			phase_4_0 = match.iloc[0]["Phase_4"] if "Phase_4" in match.columns else 0
		else:
			raise RuntimeError(f"Precomputed transfer times missing for Batch={batch_id}, Stage=0. Run preprocessing/optimization first!")
		transport_time_0 = phase_2_0 + phase_3_0 + phase_4_0
		# Stage 0 ExitTime = start_time (nostin lähtee liikkeelle start-aikaan)
		stage0_exit = int(start_time_seconds)
        
		# Stage 0 = Tuotannosta ensimmäiselle asemalle siirto
		all_rows.append({
			"Batch": batch_id,
			"Program": treatment_program,
			"Treatment_program": treatment_program,
			"Stage": 0,
			"Station": start_station,
			"MinTime": 0,
			"MaxTime": 0,
			"CalcTime": 0,
			# Stage 0 EntryTime on tuotannon start_time
			"EntryTime": int(start_time_seconds),
			"ExitTime": stage0_exit,
			"Phase_1": 0.0,
			"Phase_2": phase_2_0,
			"Phase_3": phase_3_0,
			"Phase_4": phase_4_0
		})

		if start_station not in station_reservations:
			station_reservations[start_station] = []
		station_reservations[start_station].append((start_time_seconds, stage0_exit))

		previous_sink_stat = temp_sink_stat  # Stage 0 päättyy ensimmäiselle käsittelyasemalle
		previous_exit = stage0_exit

		for i, (_, prog_row) in enumerate(prog_df.iterrows()):
			stage = int(prog_row["Stage"])
			min_time = prog_row["MinTime"]
			max_time = prog_row["MaxTime"]
			calc_time = prog_row["CalcTime"]
			min_stat = int(prog_row["MinStat"])
			max_stat = int(prog_row["MaxStat"])

			if i == 0:
				lift_stat = start_station
			else:
				lift_stat = previous_sink_stat

			temp_entry = int(previous_exit)
			temp_exit = temp_entry + int(calc_time)
			# Ensimmäinen käsittelyvaihe käyttää Stage 0 -valittua asemaa jos saatavilla
			if i == 0 and previous_sink_stat is not None:
				sink_stat = int(previous_sink_stat)
			else:
				sink_stat = select_available_station(min_stat, max_stat, station_reservations, temp_entry, temp_exit)

			transporter = select_capable_transporter(lift_stat, sink_stat, stations_df, transporters_df)
			lift_station_row = stations_df[stations_df['Number'] == lift_stat].iloc[0]
			sink_station_row = stations_df[stations_df['Number'] == sink_stat].iloc[0]

			# Hae esilasketut siirtoajat Stage > 0
			match = transfers_df[(transfers_df["Batch"] == batch_id) & (transfers_df["Stage"] == stage)]
			if not match.empty:
				phase_1 = match.iloc[0]["Phase_1"] if "Phase_1" in match.columns else 0
				phase_2 = match.iloc[0]["Phase_2"] if "Phase_2" in match.columns else 0
				phase_3 = match.iloc[0]["Phase_3"] if "Phase_3" in match.columns else 0
				phase_4 = match.iloc[0]["Phase_4"] if "Phase_4" in match.columns else 0
			else:
				raise RuntimeError(f"Precomputed transfer times missing for Batch={batch_id}, Stage={stage}. Run preprocessing/optimization first!")
			transport_time = phase_2 + phase_3 + phase_4
            
			# EntryTime = edellinen exit + siirtoaika (P2+P3+P4)
			# Sink valmis = EntryTime (nostin on juuri laskenut erän)
			# Käsittely: Sink valmis ... Lift alkaa
			# ExitTime = Sink valmis + CalcTime + Phase_2 (Lift)
            
			tentative_entry_time = int(previous_exit + transport_time)
			tentative_exit_time = tentative_entry_time + int(calc_time) + int(phase_2)  # FIX: Lisää Phase_2 (Lift)
            
			# KRIITTINEN: Asema on varattu koko ajan kun nostin on siellä:
			# - Varaustila alkaa: EntryTime - Phase_4 (nostin saapuu)
			# - Varaustila päättyy: ExitTime (nostin lähtee)
			reservation_start = tentative_entry_time - int(phase_4)  # Nostin saapuu
			reservation_end = tentative_exit_time  # Nostin lähtee
            
			# KRIITTINEN: Nostin ei voi aloittaa uutta tehtävää ennen kuin edellinen valmis!
			# Nostin vapautuu = edellisen tehtävän ExitTime
			# Jos nostin ei ole vielä vapaa, ODOTA
			if reservation_start < transporter_free_at:
				shift = transporter_free_at - reservation_start
				tentative_entry_time += shift
				tentative_exit_time += shift
				reservation_start = tentative_entry_time - int(phase_4)
				reservation_end = tentative_exit_time
            
			# Tarkista onko sink_stat varattu - JOS ON, ODOTA kunnes vapautuu!
			if sink_stat in station_reservations:
				for res_start, res_end in station_reservations[sink_stat]:
					# Jos tentatiivinen varaus menee päällekkäin toisen varauksen kanssa
					if reservation_start < res_end and reservation_end > res_start:
						# SIIRRÄ varaus kokonaan edellisen varauksen jälkeen
						shift = res_end - reservation_start
						tentative_entry_time += shift
						tentative_exit_time += shift
						reservation_start = tentative_entry_time - int(phase_4)
						reservation_end = tentative_exit_time
            
			entry_time = tentative_entry_time
			exit_time = tentative_exit_time
            
			# Päivitä nostimen vapautumisaika
			transporter_free_at = exit_time

			# Täsmädebug: Tulosta väliarvot erän 1, vaiheen 1 kohdalla
			# if batch_id == 1 and stage == 1:
			#     print(f"[DEBUG MATRIX] batch=1, stage=1, previous_exit={previous_exit}, phase_2={phase_2}, phase_3={phase_3}, phase_4={phase_4}, transport_time={transport_time}, entry_time={entry_time}")

			# Tallenna aseman TODELLINEN varaus (nostin saapuu → nostin lähtee)
			if sink_stat not in station_reservations:
				station_reservations[sink_stat] = []
			station_reservations[sink_stat].append((reservation_start, reservation_end))

			all_rows.append({
				"Batch": batch_id,
				"Program": treatment_program,
				"Treatment_program": treatment_program,
				"Stage": stage,
				"Station": sink_stat,
				"MinTime": int(min_time),
				"MaxTime": int(max_time),
				"CalcTime": int(calc_time),
				"EntryTime": entry_time,
				"ExitTime": exit_time,
				"Phase_1": round(phase_1, 2),
				"Phase_2": round(phase_2, 2),
				"Phase_3": round(phase_3, 2),
				"Phase_4": round(phase_4, 2)
			})



			previous_sink_stat = sink_stat
			previous_exit = exit_time
    
	# Luo DataFrame ja tallenna
	matrix = pd.DataFrame(all_rows)
    
	# Pyöristä float-sarakkeet
	for col in matrix.select_dtypes(include=['float']).columns:
		matrix[col] = matrix[col].round(2)
    
	# Poista Phase_x sarakkeet ennen tallennusta
	phase_cols = [col for col in matrix.columns if col.startswith("Phase_")]
	matrix_no_phase = matrix.drop(columns=phase_cols)
	os.makedirs(os.path.dirname(output_file), exist_ok=True)
	matrix_no_phase.to_csv(output_file, index=False)
    
	# Lokita toiminta
	log_file = os.path.join(logs_dir, "simulation_log.csv")
	if os.path.exists(log_file):
		with open(log_file, "a", encoding="utf-8") as f:
			timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
			f.write(f"{timestamp},TASK,Stretched matrix generated (pure): {os.path.basename(output_file)}\n")
			f.write(f"{timestamp},TASK,Rows in stretched matrix: {len(matrix)}\n")
    
	return matrix

def generate_matrix(output_dir):
	"""Wrapper-funktio yhteensopivuuden vuoksi"""
	return generate_matrix_pure(output_dir)

if __name__ == "__main__":
	import sys
	output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
	generate_matrix(output_dir)
