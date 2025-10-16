# Alkuperäisen matriisin luonti - Dokumentaatio

## Yleiskuvaus

Alkuperäisen matriisin luonti (`generate_matrix_original.py`) on tuotantolinjan simuloinnin vaihe 3, joka luo konfliktivapaan aikataulun kaikille tuotantoerille.

## Algoritmin toiminta

### 1. Lähtötiedot
- **Production.csv**: Tuotantoerien tiedot (Batch, Start_time, Start_station, Treatment_program)
- **Käsittelyohjelmat**: Erä- ja ohjelmakohtaiset `.csv`-tiedostot (Stage, MinStat, MaxStat, CalcTime)
- **Stations.csv**: Asemien sijaintitiedot (Number, X Position)
- **Transporters.csv**: Nostinten vastuualueet ja parametrit

### 2. Pääalgoritmi

#### 2.1 Erien järjestys
```
# Production.csv:n järjestys on se järjestys missä eriä tarkastellaan
# EI järjestetä uudelleen!
```
Erät käsitellään Production.csv:n alkuperäisessä järjestyksessä.

#### 2.2 Erä kerrallaan käsittely

##### Ensimmäinen erä (silmukan ulkopuolella)
```python
# Käsittele ensimmäinen erä erikseen - ei konfliktitarkastelua
first_batch = production_df.iloc[0]
batch_id = first_batch['Batch']
treatment_program = first_batch['Treatment_program']
start_time = first_batch['Start_time_seconds']
start_station = first_batch['Start_station']

# Lataa ensimmäisen erän ohjelma
batch_program = load_batch_program(output_dir, batch_id, treatment_program)

# Sisäsilmukka: Ensimmäisen erän vaiheet (ilman konfliktitarkastelua)
for stage_index, stage_row in batch_program.iterrows():
    # Yksinkertainen asemavalinta ja aikataulutus
    # (tarkennetaan jatkossa)
```

##### Loput erät (konfliktienratkaisusilmukka)
```python
# Käsittele loput erät (indeksi 1 eteenpäin)
for i in range(1, len(production_df)):
    batch_data = production_df.iloc[i]
    # Käsittele yksi erä kerrallaan konfliktienratkaisulla
```

Jokainen seuraava erä käsitellään peräkkäin:

1. **Lataa erän ohjelma** (`load_batch_program`)
2. **Luo nykyinen matriisi** aikaisemmista eristä
3. **Sisäsilmukka: Erän ohjelman vaiheet** (konfliktienratkaisulla)
4. **Lisää matriisiin** ja jatka seuraavaan erään

#### 2.3 Silmukoiden rakenne

##### Ensimmäinen erä (erilliskäsittely)
```python
# Ensimmäinen erä - ei konfliktitarkastelua
first_batch = production_df.iloc[0]
batch_program = load_batch_program(output_dir, batch_id, treatment_program)

current_time = first_batch['Start_time_seconds']  # Aloitusaika
prev_station = first_batch['Start_station']       # Aloitusasema

for stage_index, stage_row in batch_program.iterrows():
    stage = stage_row['Stage']
    min_stat = stage_row['MinStat']
    max_stat = stage_row['MaxStat']
    calc_time = stage_row['CalcTime']  # Asemalla oloaika
    
    # 1. Valitse ensimmäinen sopiva asema (min_stat -> max_stat)
    # 2. Laske nostinfysiikka (Phase_2-4, Phase_1=0)
    # 3. entry_time = current_time + transport_time
    # 4. exit_time = entry_time + calc_time
    # 5. Lisää matriisiin
    # 6. current_time = exit_time (seuraavaa vaihetta varten)
    # 7. prev_station = selected_station
```

##### Loput erät (konfliktienratkaisusilmukka)
```python
# Loput erät - konfliktienratkaisu
for i in range(1, len(production_df)):
    batch_data = production_df.iloc[i]
    original_start_time = batch_data['Start_time_seconds']  # Production.csv:stä
    batch_program = load_batch_program(output_dir, batch_id, treatment_program)
    
    # Erän käsittely (mahdollisesti useita kierroksia alkuajan siirron takia)
    current_start_time = original_start_time
    
    while True:  # Kunnes konfliktivapaa aikataulu löytyy
        conflict_found = False
        current_time = current_start_time
        
        # Sisäsilmukka: Erän vaiheet
        for stage_index, stage_row in batch_program.iterrows():
            stage = stage_row['Stage']
            min_stat = stage_row['MinStat']
            max_stat = stage_row['MaxStat']
            calc_time = stage_row['CalcTime']
            
            # Testaa asemavaihtoehdot min_stat -> max_stat
            station_found = False
            for test_station in range(min_stat, max_stat + 1):
                # Laske fysiikka (Phase_2-4)
                # Laske nostinfysiikan mukainen vaihtoaika asemalle
                # earliest_free_time = edellinen_exit + (vaiheet_2-4) + siirto + (vaiheet_2-4)
                # entry_time = max(current_time + transport_time, earliest_free_time)
                # exit_time = entry_time + calc_time
                
                # Tarkasta rinnakkaiset asemat
                parallel_stations = find_parallel_stations(test_station)
                actual_station, has_conflict = check_station_conflict(
                    current_matrix, parallel_stations, entry_time, exit_time
                )
                
                if not has_conflict:
                    # Asema vapaa - käytä sitä
                    station_found = True
                    current_time = exit_time  # Seuraava vaihe alkaa tästä
                    break
            
            if not station_found:
                # Kaikki asemavaihtoehdot konfliktissa
                # Laske nostinfysiikan mukainen vaihtoaika ja siirrä erän alkuaikaa
                earliest_free_time = laske_fysiikkapohjanen_vapautumisaika(parallel_stations)
                required_delay = earliest_free_time - current_time
                current_start_time += required_delay
                conflict_found = True
                break  # Poistu vaihesilmukasta, aloita erä alusta
        
        if not conflict_found:
            # Koko erä saatiin käsiteltyä konfliktittomasti
            # Kirjoita matriisiin ja siirry seuraavaan erään
            break
```

#### 2.4 Yksittäisen vaiheen aikataulutus

##### Ensimmäinen erä (yksinkertainen aikataulutus)
Ensimmäiselle erälle ei tehdä konfliktitarkastelua, vaan lasketaan suoraan aikataulu:

1. **Asemavalinta yksinkertainen**
   - Käy läpi asemat `min_stat` → `max_stat`
   - Valitse ensimmäinen sopiva asema
   - Valitse sopiva nostin (`select_capable_transporter`)

2. **Fysiikkalaskennat (nostinfysiikka)**
   ```python
   # Nostin on jo valmiiksi nostoasemalla, ei tarvita Phase_1
   # phase_1 = 0  (siirto nostopisteeseen ei tarvita)
   phase_2 = calculate_lift_time(lift_station)  
   phase_3 = calculate_physics_transfer_time(lift_station → sink_station)
   phase_4 = calculate_sink_time(sink_station)
   
   transport_time = phase_2 + phase_3 + phase_4  # Vain vaiheet 2-4
   entry_time = current_time + transport_time
   ```

3. **Asemalla oloaika (CalcTime)**
   ```python
   # Asemalla olo aika käsittelyohjelman CalcTime-kentän mukaan
   task_duration = stage_row['CalcTime']  # sekunteja
   exit_time = entry_time + task_duration
   ```

4. **Matriisiin lisäys**
   ```python
   matrix_row = {
       'Batch': batch_id,
       'Stage': stage,
       'Station': selected_station,
       'EntryTime': entry_time,
       'ExitTime': exit_time,
       'Phase_1': 0,           # Nostin jo valmiiksi nostoasemalla
       'Phase_2': phase_2,     # Nostaminen
       'Phase_3': phase_3,     # Siirto laskupisteeseen
       'Phase_4': phase_4,     # Laskeminen
       'CalcTime': task_duration
   }
   ```

5. **Seuraavan vaiheen aloitusaika**
   ```python
   current_time = exit_time  # Seuraava vaihe alkaa kun edellinen päättyy
   ```

##### Loput erät (konfliktienratkaisu)
Seuraavilla erillä tehdään täysi konfliktitarkastelu:

**Ulkosilmukka - Erä kerrallaan:**
1. **Erän alkuaika** otetaan Production.csv:stä
2. **Sisäsilmukka - Vaiheen käsittely:**
   - Laske milloin erä on käsittelyohjelman mukaisella seuraavalla asemalla
   - **Konfliktitarkastelu**: Jos laskuaseman kaikki rinnakkaiset ovat varattuja
   - **Viiveen laskenta**: Kuinka kauan myöhempään erä voisi ensiksi vapautuvalle rinnakkaiselle asemalle tulla (konfliktivapaa)
   - **Alkuajan siirto**: Lisää viive Production-tiedoston kyseisen erän alkuaikaan
   - **Uudelleenlaskenta**: Laske aikataulu uudella alkuajalla (ei konfliktia)
   - **Jatka seuraavaan vaiheeseen**: Käsittelyohjelman seuraava askel samalla logiikalla
3. **Konfliktivapaa aikataulu** kirjoitetaan matriisiin
4. **Seuraava erä**: Sama prosessi, jatka kunnes kaikki erät ja kaikkien erien vaiheet matriisissa

**Yksityiskohtainen algoritmi:**

Jokaista erän vaihetta (Stage) kohti:

1. **Asemavaihtoehtojen testaaminen**
   - Käy läpi asemat `min_stat` → `max_stat`
   - Valitse sopiva nostin (`select_capable_transporter`)

2. **Fysiikkalaskennat**
   ```python
   # Nostin on jo valmiiksi nostoasemalla
   phase_2 = calculate_lift_time(lift_station)  
   phase_3 = calculate_physics_transfer_time(lift_station → sink_station)
   phase_4 = calculate_sink_time(sink_station)
   transport_time = phase_2 + phase_3 + phase_4
   entry_time = current_time + transport_time
   exit_time = entry_time + task_duration
   ```

3. **Konfliktientarkastelu**
   ```python
   parallel_stations = find_parallel_stations(test_station, stations_df)
   actual_station, has_conflict = check_station_conflict(
       current_matrix, parallel_stations, entry_time, exit_time
   )
   ```

4. **Konfliktinratkaisu**
   - Jos **ei konfliktia** → käytä asemaa ja jatka seuraavaan vaiheeseen
   - Jos **konflikti** → testaa seuraavaa asemaa valikoimasta
   - Jos **kaikki asemat konfliktissa** → siirrä koko erän alkuaikaa myöhemmäksi ja aloita erä alusta

5. **Erän alkuajan siirto (jos tarvitaan)**
   ```python
   # Laske nostinfysiikan mukainen vaihtoaika
   # (ei erillistä turvamarginaalia - fysiikka antaa luonnollisen marginaalin)
   earliest_free_time = laske_ensiksi_vapautuva_aika_fysiikalla(rinnakkaiset_asemat)
   required_delay = earliest_free_time - current_entry_time
   
   # Lisää viive erän alkuaikaan
   new_start_time = original_start_time + required_delay
   
   # Aloita erän laskenta alusta uudella alkuajalla
   return create_processing_matrix_for_batch(..., new_start_time)
   ```

### 3. Rinnakkaiset asemat

#### 3.1 Määritelmä
Rinnakkaiset asemat = asemat samalla X-koordinaatilla
```python
def find_parallel_stations(station, stations_df):
    x_pos = station_row['X Position'].iloc[0]
    parallel = stations_df[stations_df['X Position'] == x_pos]['Number'].tolist()
    return parallel
```

#### 3.2 Konfliktientarkastelu
```python
def check_station_conflict(matrix, station_list, entry_time, exit_time):
    for station in station_list:
        station_tasks = matrix[matrix['Station'] == station]
        
        conflict = False
        for _, task in station_tasks.iterrows():
            if not (exit_time <= task['EntryTime'] or entry_time >= task['ExitTime']):
                conflict = True
                break
        
        if not conflict:
            return station, False  # Vapaa asema löytyi
    
    return station_list[0], True  # Kaikki varattu
```

### 4. Konfliktienratkaisu - Erän alkuajan siirto

**Huomio**: Tätä tarvitaan vain toisesta erästä eteenpäin, koska ensimmäiselle erälle ei voi syntyä konflikteja.

#### 4.1 Konfliktin havaitseminen
Kun kaikkien asemavaihtoehtojen (`min_stat` → `max_stat`) kaikki rinnakkaiset asemat ovat varattuja haluttuna aikana.

#### 4.2 Viiveen laskenta (nostinfysiikka)
```python
def laske_ensiksi_vapautuva_aika(parallel_stations, current_matrix, haluttu_entry_time):
    """Löytää milloin ensimmäinen rinnakkainen asema todella vapautuu nostinfysiikan mukaan"""
    earliest_free_time = haluttu_entry_time
    
    for station in parallel_stations:
        station_tasks = current_matrix[current_matrix['Station'] == station]
        conflicting_tasks = station_tasks[station_tasks['ExitTime'] > haluttu_entry_time]
        
        if not conflicting_tasks.empty:
            # Asema vapautuu kun viimeinen tehtävä on viety pois
            last_task_exit = conflicting_tasks['ExitTime'].min()
            
            # Nostinfysiikan mukainen vaihtoaika:
            # 1. Edellinen erä viedään pois (sen vaiheet 2-4)
            # 2. Siirto laskuasemalta nostoasemalle (nostimen liike)  
            # 3. Uusi erä tuodaan tilalle (uuden erän vaiheet 2-4)
            
            prev_phases_234 = edellisen_eran_vaiheet_2_4()  # Vie pois
            transport_return = calculate_physics_transfer_time(laskuasema → nostoasema)
            new_phases_234 = uuden_eran_vaiheet_2_4()      # Tuo tilalle
            
            total_change_time = prev_phases_234 + transport_return + new_phases_234
            station_free_time = last_task_exit + total_change_time
            
            earliest_free_time = max(earliest_free_time, station_free_time)
    
    return earliest_free_time

# Erän alkuajan siirto
required_delay = earliest_free_time - original_entry_time
new_start_time = original_start_time + required_delay
```

#### 4.3 Uudelleenlaskenta
Kun erän alkuaikaa on siirretty:

1. **Aloita erä alusta** uudella `current_start_time`
2. **Käy kaikki vaiheet uudelleen läpi** - aiemmat laskelmat eivät enää päde
3. **Jatka kunnes konfliktivapaa aikataulu** löytyy koko erälle
4. **Kirjoita matriisiin** ja siirry seuraavaan erään

#### 4.4 Rekursiivinen ratkaisu
```python
# Jos konflikti löytyy, aloita erä kokonaan alusta
if conflict_found:
    current_start_time += required_delay
    # Palaa while-silmukan alkuun, aloita erä alusta
    continue  
```

### 5. Fysiikkalaskennat

#### 5.1 Nostinvalinta
```python
def select_capable_transporter(lift_station, sink_station, stations_df, transporters_df):
    lift_x = stations_df[stations_df['Number'] == lift_station]['X Position'].iloc[0]
    sink_x = stations_df[stations_df['Number'] == sink_station]['X Position'].iloc[0]
    
    for _, transporter in transporters_df.iterrows():
        min_x = transporter['Min_x_position']
        max_x = transporter['Max_x_Position']
        
        if min_x <= lift_x <= max_x and min_x <= sink_x <= max_x:
            return transporter
```

#### 5.2 Aikakomponentit (nostinfysiikka)
- **Phase_1**: `0` 
  - **Ei tarvita** - Nostin on jo valmiiksi nostoasemalla (optimoinnin lopputulos)
- **Phase_2**: `calculate_lift_time(lift_station)`  
  - Nostaminen asemalta
- **Phase_3**: `calculate_physics_transfer_time(lift_station → sink_station)`
  - Siirtoaika nostopisteestä laskupisteeseen
- **Phase_4**: `calculate_sink_time(sink_station)`
  - Laskeminen asemalle

**Huomio**: Vain vaiheet 2-4 lasketaan, koska optimoinnin tavoite on että nostin on jo valmiiksi oikeassa paikassa.

Kaikki fysiikkalaskennat tulevat `transporter_physics.py` moduulista.

## Tulosmatriisi

### Rakenne
```csv
Batch,Program,Treatment_program,Stage,Station,MinTime,MaxTime,CalcTime,EntryTime,ExitTime,Phase_1,Phase_2,Phase_3,Phase_4
```

### Sarakkeiden merkitys
- **Batch**: Erän numero
- **Stage**: Vaiheen numero (0 = aloitusasema)
- **Station**: Valittu asema (laskuasema)
- **EntryTime**: Aika kun erä saapuu asemalle (sekunteja)
- **ExitTime**: Aika kun erä lähtee asemalta (sekunteja)
- **Phase_1-4**: Fysiikka-ajat (sekunteja), Phase_1 = 0

### Ominaisuudet
- ✅ **Ei konflikteja**: Jokainen asema vapaa tarvittuna aikana
- ✅ **Optimoitu järjestys**: Erät alkavat mahdollisimman varhain
- ✅ **Fysiikkapohjaiset ajat**: Kaikki siirtoajat laskettu tarkasti
- ✅ **Rinnakkaisuus**: Hyödyntää samansijaisia asemia

---

**Tiedosto**: `generate_matrix_original.py`  
**Vaihe**: 3  
**Syöte**: Production.csv, käsittelyohjelmat, Stations.csv, Transporters.csv  
**Tuloste**: `logs/line_matrix_original.csv`
