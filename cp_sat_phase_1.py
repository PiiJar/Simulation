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

def load_input_data(output_dir):
    """Lataa kaikki tarvittavat lähtötiedot."""
    init_dir = os.path.join(output_dir, "initialization")
    
    # Perustiedostot
    batches = pd.read_csv(os.path.join(init_dir, "cp_sat_batches.csv"))
    stations = pd.read_csv(os.path.join(init_dir, "cp_sat_stations.csv"))
    transporters = pd.read_csv(os.path.join(init_dir, "cp_sat_transporters.csv"))
    transfer_tasks = pd.read_csv(os.path.join(init_dir, "cp_sat_transfer_tasks.csv"))
    
    # Käsittelyohjelmat
    treatment_programs = {}
    for _, batch in batches.iterrows():
        program_file = f"cp_sat_treatment_program_{batch['Treatment_program']}.csv"
        treatment_programs[batch['Treatment_program']] = pd.read_csv(
            os.path.join(init_dir, program_file)
        )
    
    return batches, stations, transporters, transfer_tasks, treatment_programs

def calculate_time_parameters(transfer_tasks):
    """Laske average_task_time ja change_time."""
    average_task_time = transfer_tasks['TotalTaskTime'].mean()
    change_time = 2 * average_task_time
    return average_task_time, change_time

def get_parallel_stations(stations):
    """Ryhmittele rinnakkaiset asemat Group-numeron mukaan."""
    return stations.groupby('Group')['Station'].apply(list).to_dict()

def get_station_groups(stations):
    """Luo asema -> Group mappaus."""
    return stations.set_index('Station')['Group'].to_dict()

def get_transporter_areas(transporters):
    """Määritä kunkin nostimen toiminta-alue."""
    areas = {}
    for _, row in transporters.iterrows():
        transporter_id = int(row['Transporter_id'])
        areas[transporter_id] = {
            'min_x': row['Min_x_position'],
            'max_x': row['Max_x_Position']
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
        self.station_positions = self.stations.set_index('Number')['X Position'].to_dict()
        
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
            program = self.treatment_programs[batch['Treatment_program']]
            
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
                self.station_assignments[(batch_id, stage['Stage'])] = station_var
                
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
                transporter_var = self.model.NewIntVar(
                    1,
                    len(self.transporters),
                    f'transporter_{batch_id}_{stage["Stage"]}'
                )
                self.transporter_assignments[(batch_id, stage['Stage'])] = transporter_var
                
    def add_transporter_area_constraints(self):
        """Lisää nostimien toiminta-aluerajoitteet."""
        for (batch_id, stage), station_var in self.station_assignments.items():
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
                
                # Aseman X-position pitää olla nostimen alueella
                position = self.model.NewIntVar(
                    0, 100000, f'position_{batch_id}_{stage}'
                )
                self.model.AddElement(
                    station_var.Index(),
                    [int(self.station_positions[s]) for s in sorted(self.station_positions.keys())],
                    position
                )
                
                # Jos nostin valittu, aseman pitää olla sen alueella
                self.model.Add(
                    position >= area['min_x']
                ).OnlyEnforceIf(can_handle)
                self.model.Add(
                    position <= area['max_x']
                ).OnlyEnforceIf(can_handle)
                
                # Vähintään yhden nostimen pitää pystyä käsittelemään asema
                self.model.Add(sum(
                    1 if area['min_x'] <= self.station_positions[s] <= area['max_x']
                    else 0
                    for s in range(
                        int(self.stations['Number'].min()),
                        int(self.stations['Number'].max()) + 1
                    )
                ) > 0)
                
    def add_station_constraints(self):
        """Lisää asemien käyttörajoitteet."""
        # Stage 0:lla saa olla päällekkäisiä eriä, muilla asemilla ei
        for _, batch1 in self.batches.iterrows():
            b1 = batch1['Batch']
            prog1 = self.treatment_programs[batch1['Treatment_program']]
            
            for _, batch2 in self.batches.iterrows():
                if b1 >= batch2['Batch']:  # Vältä tuplataarkistukset
                    continue
                    
                b2 = batch2['Batch']
                prog2 = self.treatment_programs[batch2['Treatment_program']]
                
                # Käy läpi kaikki vaiheet molemmista ohjelmista
                for _, stage1 in prog1.iterrows():
                    s1 = stage1['Stage']
                    if s1 == 0:  # Stage 0:lla saa olla päällekkäisyyksiä
                        continue
                        
                    for _, stage2 in prog2.iterrows():
                        s2 = stage2['Stage']
                        if s2 == 0:  # Stage 0:lla saa olla päällekkäisyyksiä
                            continue
                            
                        # Tarkista voivatko vaiheet käyttää samaa asemaa
                        station1 = self.station_assignments[(b1, s1)]
                        station2 = self.station_assignments[(b2, s2)]
                        
                        same_station = self.model.NewBoolVar(
                            f'same_station_{b1}_{s1}_{b2}_{s2}'
                        )
                        self.model.Add(
                            station1 == station2
                        ).OnlyEnforceIf(same_station)
                        
                        # Jos käyttävät samaa asemaa, varmista ettei päällekkäisyyttä
                        exit_b1 = self.exit_times[(b1, s1)]
                        entry_b2 = self.entry_times[(b2, s2)]
                        
                        # Joko b2 alkaa b1:n jälkeen + vaihtoaika
                        b2_after_b1 = self.model.NewBoolVar(
                            f'b2_after_b1_{b1}_{s1}_{b2}_{s2}'
                        )
                        self.model.Add(
                            entry_b2 >= exit_b1 + self.change_time
                        ).OnlyEnforceIf([same_station, b2_after_b1])
                        
                        # Tai b1 alkaa b2:n jälkeen + vaihtoaika
                        b1_after_b2 = self.model.NewBoolVar(
                            f'b1_after_b2_{b1}_{s1}_{b2}_{s2}'
                        )
                        self.model.Add(
                            entry_b2 + self.change_time <= exit_b1
                        ).OnlyEnforceIf([same_station, b1_after_b2])
                        
                        # Pakota valitsemaan toinen järjestys jos sama asema
                        self.model.Add(
                            b1_after_b2 + b2_after_b1 == 1
                        ).OnlyEnforceIf(same_station)
                            
    def add_sequence_constraints(self):
        """Lisää erien sisäiset järjestysrajoitteet."""
        for _, batch in self.batches.iterrows():
            batch_id = batch['Batch']
            program = self.treatment_programs[batch['Treatment_program']]
            
            prev_exit = self.batch_starts[batch_id]  # Stage 0 ExitTime
            
            for i in range(len(program)):
                if program.iloc[i]['Stage'] == 0:
                    continue
                    
                # Seuraava vaihe voi alkaa vasta kun edellinen on päättynyt
                curr_entry = self.entry_times[(batch_id, program.iloc[i]['Stage'])]
                self.model.Add(curr_entry >= prev_exit)
                
                # ExitTime = EntryTime + MinTime
                curr_exit = self.exit_times[(batch_id, program.iloc[i]['Stage'])]
                self.model.Add(
                    curr_exit == curr_entry + program.iloc[i]['MinTime']
                )
                
                prev_exit = curr_exit
                
    def add_identical_batch_constraints(self):
        """Lukitse identtisten erien keskinäinen järjestys."""
        for program_id, batch_list in self.identical_batches.items():
            for i in range(len(batch_list) - 1):
                # Seuraavan identtisen erän pitää lähteä myöhemmin
                self.model.Add(
                    self.batch_starts[batch_list[i]] <= 
                    self.batch_starts[batch_list[i + 1]]
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
            program = self.treatment_programs[self.batches[
                self.batches['Batch'] == batch_id
            ]['Treatment_program'].iloc[0]]
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
        self.create_variables()
        self.add_station_constraints()
        self.add_sequence_constraints()
        self.add_identical_batch_constraints()
        self.add_station_group_constraints()
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
            batch_id = batch['Batch']
            program = self.treatment_programs[batch['Treatment_program']]
            
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
                
                # Etsi sopiva nostin, joka kattaa molemmat asemat
                transporter = None
                for t_id, area in self.transporter_areas.items():
                    from_x = self.station_positions[from_station]
                    to_x = self.station_positions[station]
                    if (area['min_x'] <= from_x <= area['max_x'] and 
                        area['min_x'] <= to_x <= area['max_x']):
                        transporter = t_id
                        break
                
                if transporter is None:
                    raise ValueError(
                        f"Sopivaa nostinta ei löydy siirrolle {from_station}->{station}"
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
        
        # Tallenna tulos
        result_path = os.path.join(self.output_dir, "cp_sat_batch_schedule.csv")
        df.to_csv(result_path, index=False)
        
        return df

def optimize_phase_1(output_dir):
    """Pääfunktio vaiheen 1 optimoinnille."""
    optimizer = CpSatPhase1Optimizer(output_dir)
    return optimizer.solve()