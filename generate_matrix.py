
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
	Luo yksinkertaisen matriisin käyttäen CP-SAT optimoinnin tuloksia.
	EI tee optimointia, vain simuloi tuotantokoneen näkökulmaa.
    
	LOGIIKKA:
	1. Käyttää Start_optimized aikoja production.csv:stä (CP-SAT:n tulos)
	2. Käyttää CalcTime arvoja optimoiduista ohjelmista (CP-SAT:n tulos)
	3. Laskee yksinkertaisen aikajanahoidon: start_time + transport_time + calc_time
	4. EI ratkaise asemakonflikteja - käyttää vain ensimmäistä vapaata asemaa
	"""
	logs_dir = os.path.join(output_dir, "logs")
	optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")
	output_file = os.path.join(logs_dir, "line_matrix.csv")
    
	# Lataa lähtötiedot - production.csv jossa Start_optimized (CP-SAT:n tulos)
	production_df = load_production_batches_stretched(output_dir)
	stations_df = load_stations(output_dir)
	transporters_df = pd.read_csv(os.path.join(output_dir, "initialization", "transporters.csv"))
	
	# Lue esilasketut siirtoajat
	transfers_path = os.path.join(output_dir, "cp_sat", "cp_sat_transfer_tasks.csv")
	if not os.path.exists(transfers_path):
		raise FileNotFoundError(f"Precomputed transfer times file not found: {transfers_path}\nRun preprocessing/optimization first!")
	try:
		transfers_df = pd.read_csv(transfers_path)
		transfers_df["Transporter"] = transfers_df["Transporter"].astype(int)
		transfers_df["From_Station"] = transfers_df["From_Station"].astype(int)
		transfers_df["To_Station"] = transfers_df["To_Station"].astype(int)
	except Exception as e:
		raise RuntimeError(f"Failed to load precomputed transfer times: {e}")
    
def generate_matrix_pure(output_dir):
	"""
	Luo yksinkertaisen matriisin käyttäen CP-SAT optimoinnin tuloksia.
	EI tee optimointia, vain simuloi tuotantokoneen näkökulmaa.
    
	LOGIIKKA:
	1. Käyttää Start_optimized aikoja production.csv:stä (CP-SAT:n tulos)
	2. Käyttää CalcTime arvoja optimoiduista ohjelmista (CP-SAT:n tulos)
	3. Laskee yksinkertaisen aikajanahoidon: start_time + transport_time + calc_time
	4. EI ratkaise asemakonflikteja - käyttää vain ensimmäistä vapaata asemaa
	"""
	logs_dir = os.path.join(output_dir, "logs")
	optimized_dir = os.path.join(output_dir, "cp_sat", "treatment_program_optimized")
	output_file = os.path.join(logs_dir, "line_matrix.csv")
    
	# Lataa lähtötiedot - production.csv jossa Start_optimized (CP-SAT:n tulos)
	production_df = load_production_batches_stretched(output_dir)
	stations_df = load_stations(output_dir)
	transporters_df = pd.read_csv(os.path.join(output_dir, "initialization", "transporters.csv"))
	
	# Lue esilasketut siirtoajat
	transfers_path = os.path.join(output_dir, "cp_sat", "cp_sat_transfer_tasks.csv")
	if not os.path.exists(transfers_path):
		raise FileNotFoundError(f"Precomputed transfer times file not found: {transfers_path}\nRun preprocessing/optimization first!")
	try:
		transfers_df = pd.read_csv(transfers_path)
		transfers_df["Transporter"] = transfers_df["Transporter"].astype(int)
		transfers_df["From_Station"] = transfers_df["From_Station"].astype(int)
		transfers_df["To_Station"] = transfers_df["To_Station"].astype(int)
	except Exception as e:
		raise RuntimeError(f"Failed to load precomputed transfer times: {e}")
    
	all_rows = []
    
	# Käy läpi erät aikajärjestyksessä
	production_df_sorted = production_df.sort_values('Start_time_seconds').reset_index(drop=True)
	
	for _, batch_row in production_df_sorted.iterrows():
		batch_id = int(batch_row["Batch"])
		start_station = int(batch_row["Start_station"])
		treatment_program = int(batch_row["Treatment_program"])
		start_time_seconds = float(batch_row["Start_time_seconds"])

		prog_df = load_batch_program_optimized(optimized_dir, batch_id, treatment_program)

		# Stage 0: Siirto start_station → ensimmäinen käsittelyasema
		first_prog_row = prog_df.iloc[0]
		first_min_stat = int(first_prog_row["MinStat"])
		first_max_stat = int(first_prog_row["MaxStat"])
        
		# Valitse ensimmäinen asema käsittelyvaiheen alueelta (yksinkertainen valinta)
		target_station = first_min_stat
        
		# Hae siirtoaika Stage 0:lle 
		transporter = select_capable_transporter(start_station, target_station, stations_df, transporters_df)
		transporter_id = int(transporter["Transporter_id"])
		match = transfers_df[(transfers_df["Transporter"] == transporter_id) & 
		                    (transfers_df["From_Station"] == start_station) & 
		                    (transfers_df["To_Station"] == target_station)]
		if not match.empty:
			transport_time_0 = float(match.iloc[0]["TotalTaskTime"])
		else:
			raise RuntimeError(f"Precomputed transfer time missing for Transporter={transporter_id}, From={start_station}, To={target_station}")
		
		# Stage 0: Siirto alkaa start_time:ssa
		stage0_exit = int(start_time_seconds)
        
		all_rows.append({
			"Batch": batch_id,
			"Program": treatment_program,
			"Treatment_program": treatment_program,
			"Stage": 0,
			"Station": start_station,
			"MinTime": 0,
			"MaxTime": 0,
			"CalcTime": 0,
			"EntryTime": int(start_time_seconds),
			"ExitTime": stage0_exit,
			"TransportTime": transport_time_0
		})

		# Käsittele varsinaiset käsittelyvaiheet
		current_time = start_time_seconds
		previous_station = start_station

		for i, (_, prog_row) in enumerate(prog_df.iterrows()):
			stage = int(prog_row["Stage"])
			min_time = prog_row["MinTime"]
			max_time = prog_row["MaxTime"]
			calc_time = prog_row["CalcTime"]
			min_stat = int(prog_row["MinStat"])
			max_stat = int(prog_row["MaxStat"])

			# Yksinkertainen aseman valinta: aina ensimmäinen asema alueelta
			if i == 0:
				# Ensimmäinen vaihe käyttää jo valittua asemaa
				current_station = target_station
			else:
				current_station = min_stat
			
			# Hae siirtoaika edellisestä asemasta nykyiseen
			transporter = select_capable_transporter(previous_station, current_station, stations_df, transporters_df)
			transporter_id = int(transporter["Transporter_id"])
			match = transfers_df[(transfers_df["Transporter"] == transporter_id) & 
			                    (transfers_df["From_Station"] == previous_station) & 
			                    (transfers_df["To_Station"] == current_station)]
			if not match.empty:
				transport_time = float(match.iloc[0]["TotalTaskTime"])
			else:
				raise RuntimeError(f"Precomputed transfer time missing for Transporter={transporter_id}, From={previous_station}, To={current_station}")
            
			# Yksinkertainen aikajana: edellinen loppu + siirtoaika
			entry_time = int(current_time + transport_time)
			exit_time = entry_time + int(calc_time)
			
			all_rows.append({
				"Batch": batch_id,
				"Program": treatment_program,
				"Treatment_program": treatment_program,
				"Stage": stage,
				"Station": current_station,
				"MinTime": int(min_time),
				"MaxTime": int(max_time),
				"CalcTime": int(calc_time),
				"EntryTime": entry_time,
				"ExitTime": exit_time,
				"TransportTime": transport_time
			})

			# Päivitä seuraavaa vaihetta varten
			current_time = exit_time
			previous_station = current_station
    
	# Luo DataFrame ja tallenna
	matrix = pd.DataFrame(all_rows)
    
	# Pyöristä float-sarakkeet
	for col in matrix.select_dtypes(include=['float']).columns:
		matrix[col] = matrix[col].round(2)
    
	os.makedirs(os.path.dirname(output_file), exist_ok=True)
	matrix.to_csv(output_file, index=False)
    
	# Lokita toiminta
	log_file = os.path.join(logs_dir, "simulation_log.csv")
	if os.path.exists(log_file):
		with open(log_file, "a", encoding="utf-8") as f:
			timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
			f.write(f"{timestamp},TASK,Simple matrix generated using optimization results: {os.path.basename(output_file)}\n")
			f.write(f"{timestamp},TASK,Rows in matrix: {len(matrix)}\n")
    
	return matrix

def generate_matrix(output_dir):
	"""Wrapper-funktio yhteensopivuuden vuoksi"""
	return generate_matrix_pure(output_dir)

if __name__ == "__main__":
	import sys
	output_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
	generate_matrix(output_dir)
