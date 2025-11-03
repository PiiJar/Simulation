"""
CP-SAT Optimoinnin vaihe 1: Asemaoptimointi

Tämä moduuli toteuttaa tuotantolinjan optimoinnin ensimmäisen vaiheen:
- Minimoi kokonaistuotantoajan (max ExitTime)
- Välttää asemien päällekkäiskäytön
- Valitsee sopivat nostimet ja rinnakkaisasemat
- Tuottaa pohjan vaiheen 2 nostinoptimoinnille
"""

import os
import pandas as pd
from ortools.sat.python import cp_model

# Valinnainen logger, jos käytettävissä
try:
    from simulation_logger import get_logger
except Exception:
    def get_logger():
        return None

# Visualisointi: käytetään olemassa olevaa skriptiä jos saatavilla
try:
    import visualize_schedule  # provides plot_schedule(df, output_dir, filename)
except Exception:
    visualize_schedule = None

def load_input_data(output_dir):
    """Lataa kaikki tarvittavat lähtötiedot."""
    cp_sat_dir = os.path.join(output_dir, "cp_sat")
    
    # Perustiedostot
    batches = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_batches.csv"))
    stations = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_stations.csv"))
    transporters = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_transporters.csv"))
    transfer_tasks = pd.read_csv(os.path.join(cp_sat_dir, "cp_sat_transfer_tasks.csv"))
    
    # Käsittelyohjelmat
    print("Ladataan käsittelyohjelmat...")
    treatment_programs = {}
    for _, batch in batches.iterrows():
        batch_num = int(batch['Batch'])
        print(f"  Käsitellään erää {batch_num}")
        program_file = f"cp_sat_treatment_program_{batch_num}.csv"
        file_path = os.path.join(cp_sat_dir, program_file)
        print(f"    Luetaan tiedostoa: {file_path}")
        if not os.path.exists(file_path):
            print(f"    VIRHE: Tiedostoa ei löydy: {file_path}")
            continue
        df = pd.read_csv(file_path)
        # Muunna aikakentät sekunneiksi
        df['MinTime'] = pd.to_timedelta(df['MinTime']).dt.total_seconds().astype(int)
        df['MaxTime'] = pd.to_timedelta(df['MaxTime']).dt.total_seconds().astype(int)
        # Varmista että vaiheet ovat numerojärjestyksessä
        df = df.sort_values('Stage').reset_index(drop=True)
        treatment_programs[batch_num] = df
        print(f"    OK: Ohjelma ladattu ({len(df)} vaihetta)")
    print(f"Käsittelyohjelmia ladattu: {len(treatment_programs)}")
    print(f"Saatavilla olevat erät: {list(treatment_programs.keys())}")
    
    return batches, stations, transporters, transfer_tasks, treatment_programs

def calculate_time_parameters(transfer_tasks):
    """Laske average_task_time ja change_time."""
    # Pyöristetään kokonaisluvuksi CP-SAT-yhteensopivuuden vuoksi
    average_task_time = round(transfer_tasks['TotalTaskTime'].mean())
    change_time = 2 * average_task_time
    return average_task_time, change_time

def get_parallel_stations(stations):
    """Ryhmittele rinnakkaiset asemat Group-numeron mukaan."""
    return stations.groupby('Group')['Number'].apply(list).to_dict()

def get_station_groups(stations):
    """Luo asema -> Group mappaus."""
    return stations.set_index('Number')['Group'].to_dict()

def get_transporter_areas(transporters):
    """Määritä kunkin nostimen toiminta-alue asemaväleinä (lift/sink)."""
    areas = {}
    def _as_int(val, default=0):
        try:
            if pd.isna(val):
                return int(default)
            return int(val)
        except Exception:
            return int(default)
    for _, row in transporters.iterrows():
        transporter_id = _as_int(row.get('Transporter_id'))
        areas[transporter_id] = {
            'min_lift': _as_int(row.get('Min_Lift_Station', row.get('Min_lift_station', row.get('MinLiftStation', 0))), 0),
            'max_lift': _as_int(row.get('Max_Lift_Station', row.get('Max_lift_station', row.get('MaxLiftStation', 0))), 0),
            'min_sink': _as_int(row.get('Min_Sink_Station', row.get('Min_sink_station', row.get('MinSinkStation', 0))), 0),
            'max_sink': _as_int(row.get('Max_Sink_Station', row.get('Max_sink_station', row.get('MaxSinkStation', 0))), 0)
        }
    return areas

def find_identical_batches(batches):
    """Ryhmittele identtiset erät (sama Treatment_program)."""
    return batches.groupby('Treatment_program')['Batch'].apply(list).to_dict()

class CpSatPhase1Optimizer:
    def __init__(self, output_dir):
        """Alusta optimoija ja lataa lähtötiedot."""
        self.output_dir = output_dir
        (
            self.batches,
            self.stations,
            self.transporters,
            self.transfer_tasks,
            self.treatment_programs
        ) = load_input_data(output_dir)
        
        self.average_task_time, self.change_time = calculate_time_parameters(
            self.transfer_tasks
        )
        
        self.parallel_stations = get_parallel_stations(self.stations)
        self.station_groups = get_station_groups(self.stations)
        self.identical_batches = find_identical_batches(self.batches)
        self.transporter_areas = get_transporter_areas(self.transporters)
        # Asemien paikkatietoja hyödynnetään fysiikkalaskentoihin, ei enää nostimen aluevalintaan
        # Salli puuttuvat arvot → 0
        xpos = pd.to_numeric(self.stations['X Position'], errors='coerce').fillna(0).round().astype(int)
        self.station_positions = dict(zip(self.stations['Number'].astype(int), xpos))
        
        # CP-SAT model
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Optimoinnin muuttujat
        self.batch_starts = {}  # Stage 0 ExitTime
        self.station_assignments = {}  # Asemavalinnat
        self.entry_times = {}  # Saapumisajat asemille
        self.exit_times = {}  # Poistumisajat asemilta
        self.transporter_assignments = {}  # Nostinvalinnat
        
    def create_variables(self):
        """Luo optimoinnin muuttujat."""
        max_time = 24 * 60 * 60  # 24h sekunteina
        
        for _, batch in self.batches.iterrows():
            batch_id = batch['Batch']
            # Käytä AINA batch-kohtaista ohjelmaa (avaimena batch_id)
            program = self.treatment_programs[batch_id]
            
            # Stage 0 ExitTime (optimoinnin päämuuttuja)
            self.batch_starts[batch_id] = self.model.NewIntVar(
                0, max_time, f'start_{batch_id}'
            )
            
            # Käy läpi kaikki vaiheet (paitsi Stage 0)
            for _, stage in program.iterrows():
                if stage['Stage'] == 0:
                    continue
                    
                # Asemavalinta MinStat-MaxStat väliltä
                station_var = self.model.NewIntVar(
                    stage['MinStat'],
                    stage['MaxStat'],
                    f'station_{batch_id}_{stage["Stage"]}'
                )
                self.station_assignments[(batch_id, stage['Stage'])] = station_var  # Tallennetaan suoraan muuttuja
                
                # Saapumis- ja poistumisajat
                entry_var = self.model.NewIntVar(
                    0, max_time,
                    f'entry_{batch_id}_{stage["Stage"]}'
                )
                self.entry_times[(batch_id, stage['Stage'])] = entry_var
                
                # ExitTime = EntryTime + MinTime
                exit_var = self.model.NewIntVar(
                    0, max_time,
                    f'exit_{batch_id}_{stage["Stage"]}'
                )
                self.exit_times[(batch_id, stage['Stage'])] = exit_var
                
                # Nostinvalinta asemalle
                try:
                    transporter_var = self.model.NewIntVar(
                        1,
                        len(self.transporters),
                        f'transporter_{batch_id}_{stage["Stage"]}'
                    )
                    self.transporter_assignments[(batch_id, stage['Stage'])] = transporter_var
                except Exception as e:
                    print(f"    VIRHE: Nostin-muuttujan luonti epäonnistui: {str(e)}")
                    raise
                
    def add_transporter_area_constraints(self):
        """Lisää nostimien toiminta-aluerajoitteet."""
        for (batch_id, stage), station_var in self.station_assignments.items():
            # Haetaan vaiheen tiedot käsittelyohjelmasta
            # Käytä batch-kohtaista ohjelmaa
            program = self.treatment_programs[batch_id]
            stage_row = program[program['Stage'] == stage].iloc[0]
            if (batch_id, stage) not in self.transporter_assignments:
                raise KeyError(f"Transporter assignment not found for ({batch_id}, {stage})")
            transporter_var = self.transporter_assignments[(batch_id, stage)]
            
            # Luo boolean-muuttujat jokaiselle mahdolliselle nostimelle
            for transporter_id, area in self.transporter_areas.items():
                can_handle = self.model.NewBoolVar(
                    f'can_handle_{transporter_id}_{batch_id}_{stage}'
                )
                
                # Jos nostin on valittu, sen pitää pystyä käsittelemään asema
                self.model.Add(
                    transporter_var == transporter_id
                ).OnlyEnforceIf(can_handle)
                
                # Jos nostin valittu, aseman (sink) pitää olla nostimen sallimalla laskualueella
                self.model.Add(
                    station_var >= area['min_sink']
                ).OnlyEnforceIf(can_handle)
                self.model.Add(
                    station_var <= area['max_sink']
                ).OnlyEnforceIf(can_handle)
                
    def add_station_constraints(self):
        """Lisää asemien käyttörajoitteet ja siirtoajat täsmälleen vaatimusten mukaan."""
        # 1. Siirtoajat asemalta toiselle (SAMAN ERÄN sisällä)
        for _, batch in self.batches.iterrows():
            batch_id = int(batch['Batch'])
            if batch_id not in self.treatment_programs:
                raise KeyError(f"Treatment program not found for batch {batch_id}")
            program = self.treatment_programs[batch_id]
            
            # Käy läpi erän vaiheet järjestyksessä (paitsi Stage 0)
            stages = program[program['Stage'] > 0].sort_values('Stage')

            # Stage 0 -> ensimmäinen varsinainen vaihe: täsmälleen average_task_time siirtoa
            if not stages.empty:
                first_stage = int(stages.iloc[0]['Stage'])
                first_entry = self.entry_times[(batch_id, first_stage)]
                start_exit = self.batch_starts[batch_id]  # Stage 0 ExitTime
                self.model.Add(first_entry == start_exit + self.average_task_time)
            for i in range(len(stages) - 1):
                curr_stage = stages.iloc[i]['Stage']
                next_stage = stages.iloc[i + 1]['Stage']
                
                # Hae todelliset asemien numerot
                curr_station = self.station_assignments[(batch_id, curr_stage)]
                next_station = self.station_assignments[(batch_id, next_stage)]
                
                # Vaatimusten mukaan siirtoaika on AINA täsmälleen average_task_time
                curr_exit = self.exit_times[(batch_id, curr_stage)]
                next_entry = self.entry_times[(batch_id, next_stage)]
                self.model.Add(next_entry == curr_exit + self.average_task_time)
        
        # 2. Asemavaraukset ja vaihtoajat (ERI ERIEN välillä)
        for _, batch1 in self.batches.iterrows():
            b1 = int(batch1['Batch'])
            prog1 = self.treatment_programs[b1]
            
            for _, batch2 in self.batches.iterrows():
                if b1 >= batch2['Batch']:  # Vältä tuplataarkistukset
                    continue
                    
                b2 = int(batch2['Batch'])
                prog2 = self.treatment_programs[b2]
                
                # Käy läpi kaikki vaiheet molemmista ohjelmista
                for _, stage1 in prog1.iterrows():
                    s1 = stage1['Stage']
                    if s1 == 0:  # Stage 0:lla saa olla päällekkäisyyksiä
                        continue
                        
                    for _, stage2 in prog2.iterrows():
                        s2 = stage2['Stage']
                        if s2 == 0:
                            continue
                        
                        # 1. Tarkista käyttävätkö erät samaa asemaa
                        station1 = self.station_assignments[(b1, s1)]
                        station2 = self.station_assignments[(b2, s2)]
                        exit_b1 = self.exit_times[(b1, s1)]
                        entry_b1 = self.entry_times[(b1, s1)]
                        exit_b2 = self.exit_times[(b2, s2)]
                        entry_b2 = self.entry_times[(b2, s2)]

                        # Sama asema? Vaihtoaika koskee vain tätä tapausta
                        same_station = self.model.NewBoolVar(f'same_station_{b1}_{s1}_{b2}_{s2}')
                        self.model.Add(station1 == station2).OnlyEnforceIf(same_station)
                        self.model.Add(station1 != station2).OnlyEnforceIf(same_station.Not())

                        # Jos sama asema, täytyy päättää kumpi menee ensin ja erottaa change_time:lla
                        b1_before_b2 = self.model.NewBoolVar(f'b1_before_b2_{b1}_{s1}_{b2}_{s2}')
                        # b2 alkaa vasta kun b1 on poistunut + vaihtoaika
                        self.model.Add(
                            entry_b2 >= exit_b1 + self.change_time
                        ).OnlyEnforceIf([same_station, b1_before_b2])
                        # b1 alkaa vasta kun b2 on poistunut + vaihtoaika
                        self.model.Add(
                            entry_b1 >= exit_b2 + self.change_time
                        ).OnlyEnforceIf([same_station, b1_before_b2.Not()])

                        # HUOM: jos asema ei ole sama, ei lisätä järjestys- tai väliyhtälöitä
                        # (rinnakkaisasemat toimivat itsenäisesti, ei change_time-vaatimusta)
                            
    def add_sequence_constraints(self):
        """Lisää erien sisäiset järjestysrajoitteet."""
        print("Lisätään sekvensointirajoitteita...")
        for _, batch in self.batches.iterrows():
            batch_id = int(batch['Batch'])
            print(f"  Käsitellään erää {batch_id}")
            if batch_id not in self.treatment_programs:
                raise KeyError(f"Treatment program not found for batch {batch_id}")
            program = self.treatment_programs[batch_id]
            prev_exit = self.batch_starts[batch_id]  # Stage 0 ExitTime
            
            # Käydään läpi vain ne vaiheet jotka eivät ole Stage 0
            stages_gt_0 = program[program['Stage'] > 0]
            
            for _, stage_row in stages_gt_0.iterrows():
                stage = stage_row['Stage']
                # Seuraava vaihe voi alkaa vasta kun edellinen on päättynyt
                curr_entry = self.entry_times[(batch_id, stage)]
                self.model.Add(curr_entry >= prev_exit)
                
                # ExitTime = EntryTime + MinTime
                curr_exit = self.exit_times[(batch_id, stage)]
                self.model.Add(
                    curr_exit == curr_entry + stage_row['MinTime']
                )
                
                prev_exit = curr_exit
                
    def add_identical_batch_constraints(self):
        """Lukitse identtisten erien keskinäinen järjestys."""
        for program_id, batch_list in self.identical_batches.items():
            for i in range(len(batch_list) - 1):
                b_prev = batch_list[i]
                b_next = batch_list[i + 1]
                # 1) Stage 0 -tasolla: b_prev start <= b_next start
                self.model.Add(self.batch_starts[b_prev] <= self.batch_starts[b_next])

                # 2) Varmista myös, että ensimmäisen varsinaisen vaiheen (Stage > 0)
                #    EntryTime noudattaa samaa järjestystä.
                prog_prev = self.treatment_programs[b_prev]
                prog_next = self.treatment_programs[b_next]
                # Oletus: identtiset erät -> sama vaihejoukko; valitaan pienin Stage > 0
                first_stage_prev = int(prog_prev[prog_prev['Stage'] > 0]['Stage'].min())
                first_stage_next = int(prog_next[prog_next['Stage'] > 0]['Stage'].min())
                # Lukitse järjestys ensimmäisessä varsinaisessa vaiheessa
                self.model.Add(
                    self.entry_times[(b_prev, first_stage_prev)] <=
                    self.entry_times[(b_next, first_stage_next)]
                )
                
    def add_station_group_constraints(self):
        """Varmista että asemavalinta kunnioittaa Group-rajoitteita."""
        for (batch_id, stage), station_var in self.station_assignments.items():
            # Hae valitun aseman ryhmä
            selected_group = self.model.NewIntVar(1, max(self.station_groups.values()), f'group_{batch_id}_{stage}')
            
            # Yhdistä asema ja ryhmä
            for station, group in self.station_groups.items():
                is_this_station = self.model.NewBoolVar(f'is_station_{station}_{batch_id}_{stage}')
                self.model.Add(station_var == station).OnlyEnforceIf(is_this_station)
                self.model.Add(selected_group == group).OnlyEnforceIf(is_this_station)
                
            # Varmista että asema on sallitulla välillä stage-kohtaisesti
            # Käytä batch-kohtaista ohjelmaa myös tässä
            program = self.treatment_programs[batch_id]
            stage_row = program[program['Stage'] == stage].iloc[0]
            self.model.Add(station_var >= stage_row['MinStat'])
            self.model.Add(station_var <= stage_row['MaxStat'])
            
    def set_objective(self):
        """Aseta optimointitavoite: minimoi max(ExitTime)."""
        max_exit = self.model.NewIntVar(0, 24*60*60, 'max_exit')
        
        # max_exit on suurempi kuin mikä tahansa ExitTime
        for exit_var in self.exit_times.values():
            self.model.Add(max_exit >= exit_var)
            
        # Minimoi tätä maksimiarvoa
        self.model.Minimize(max_exit)
        
    def solve(self):
        """Ratkaise optimointiongelma."""
        print("Ratkaistaan optimointiongelma...")
        print("1. Luodaan muuttujat...")
        self.create_variables()
        print("2. Lisätään asemarajoitteet...")
        self.add_station_constraints()
        print("3. Lisätään sekvensointirajoitteet...")
        self.add_sequence_constraints()
        print("4. Lisätään identtisten erien rajoitteet...")
        self.add_identical_batch_constraints()
        print("5. Lisätään asemaryhmien rajoitteet...")
        self.add_station_group_constraints()
        print("6. Lisätään nostinalueiden rajoitteet...")
        self.add_transporter_area_constraints()
        self.set_objective()
        
        # Ratkaise malli
        status = self.solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self.create_result_dataframe()
        else:
            raise ValueError("Optimointi ei löytänyt ratkaisua!")
            
    def create_result_dataframe(self):
        """Luo tulostiedosto määrittelyn mukaisessa muodossa."""
        results = []
        
        for _, batch in self.batches.iterrows():
            batch_id = int(batch['Batch'])
            program = self.treatment_programs[batch_id]
            
            # Hae aloitusasema Stage 0 -> Stage 1 siirtoa varten
            start_station = int(batch['Start_station'])
            
            for _, stage in program.iterrows():
                stage_num = int(stage['Stage'])
                if stage_num == 0:
                    continue  # Stage 0:sta ei tallenneta rivejä
                    
                # Kerää rivin tiedot
                station = self.solver.Value(
                    self.station_assignments[(batch_id, stage_num)]
                )
                entry_time = self.solver.Value(
                    self.entry_times[(batch_id, stage_num)]
                )
                exit_time = self.solver.Value(
                    self.exit_times[(batch_id, stage_num)]
                )
                
                # Määritä nostin asemien perusteella
                if stage_num == 1:
                    # Stage 0 -> Stage 1: käytä start_station -> station väliä
                    from_station = start_station
                else:
                    # Muut siirrot: käytä edellisen vaiheen asemaa
                    prev_stage = program[program['Stage'] == stage_num - 1].iloc[0]
                    from_station = self.solver.Value(
                        self.station_assignments[(batch_id, stage_num - 1)]
                    )
                
                # Etsi sopiva nostin, joka kattaa molemmat asemat (lift ja sink -väleinä)
                transporter = None
                for t_id, area in self.transporter_areas.items():
                    if (area['min_lift'] <= from_station <= area['max_lift'] and 
                        area['min_sink'] <= station <= area['max_sink']):
                        transporter = t_id
                        break
                
                if transporter is None:
                    # Kirjaa virhe lokiin ja nosta poikkeus
                    logger = get_logger()
                    if logger:
                        logger.log(
                            'ERROR',
                            f"No capable transporter for batch={batch_id}, tp={int(batch['Treatment_program'])}, "
                            f"stage={stage_num}, from={from_station}, to={station}"
                        )
                    raise ValueError(
                        f"Sopivaa nostinta ei löydy siirrolle {from_station}->{station} (batch {batch_id}, stage {stage_num})"
                    )
                
                results.append({
                    'Transporter': transporter,
                    'Batch': batch_id,
                    'Treatment_program': batch['Treatment_program'],
                    'Stage': stage_num,
                    'Station': station,
                    'EntryTime': entry_time,
                    'ExitTime': exit_time
                })
                
        # Muodosta DataFrame ja järjestä määrittelyn mukaisesti
        df = pd.DataFrame(results)
        df = df.sort_values(['Transporter', 'ExitTime'])
        
        # Tallenna tulos cp_sat-kansioon
        cp_sat_dir = os.path.join(self.output_dir, "cp_sat")
        result_path = os.path.join(cp_sat_dir, "cp_sat_batch_schedule.csv")
        df.to_csv(result_path, index=False)
        print(f"Tallennettu aikataulu: {result_path}")

        # Vaihe 1: Lisää yksinkertainen visualisointi heti aikataulun tallennuksen jälkeen
        try:
            if visualize_schedule is not None and hasattr(visualize_schedule, "plot_schedule"):
                out_img = visualize_schedule.plot_schedule(df, self.output_dir, filename="schedule_gantt.png")
                print(f"Tallennettu visualisointi: {out_img}")
            else:
                # Fallback: ei visualisointimoduulia saatavilla
                print("Visualisointimoduulia ei löytynyt – ohitetaan kuvagenerointi vaiheessa 1.")
        except Exception as viz_err:
            print(f"Visualisoinnin luonti epäonnistui: {viz_err}")
        
        return df

def optimize_phase_1(output_dir):
    """Pääfunktio vaiheen 1 optimoinnille."""
    optimizer = CpSatPhase1Optimizer(output_dir)
    return optimizer.solve()