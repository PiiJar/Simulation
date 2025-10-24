# Google OR-Tools -mahdollisuudet tuotantolinjan optimointiin

## 📚 Mikä on Google OR-Tools?

Google OR-Tools on avoimen lähdekoodin optimointityökalupaketti, joka tarjoaa tehokkaita algoritmeja:
- **CP-SAT** (Constraint Programming - Satisfiability): Rajoiteohjelmointi
- **Linear/Integer Programming**: Lineaarinen ja kokonaislukuohjelmointi
- **Vehicle Routing**: Reittioptimointi
- **Graph algorithms**: Verkkoteoria ja virtaukset
- **Assignment**: Tehtävien jako

Projektin URL: https://developers.google.com/optimization

---

## 🎯 Sovellukset tähän projektiin

### 1. **Job Shop Scheduling Problem (JSSP)**
**Sopii parhaiten tähän projektiin!**

#### Mikä se on?
- Klassinen ongelma, jossa tehtävät (jobs) kulkevat koneiden (machines) läpi tietyissä vaiheissa (operations)
- Jokainen tehtävä vaatii resursseja (asemat, nostimet) tietyssä järjestyksessä
- Tavoite: Minimoi makespan (kokonaisaika) tai maksimoi läpimeno

#### Miten se sopii tähän projektiin?
- **Jobs** = Erät (Batch 1, 2, 3...)
- **Machines** = Asemat (Station 307, 308, ...) + Nostimet (Transporter 1, 2, 3)
- **Operations** = Käsittelyvaiheet (Stage 1, 2, 3, ...)
- **Durations** = CalcTime (käsittelyaika) + nostinsiirtoaika

#### OR-Tools toteutus: CP-SAT Solver
```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()

# Muuttujat: Jokaisen vaiheen start_time ja end_time
start_vars = {}
end_vars = {}

for batch in batches:
    for stage in stages:
        start = model.NewIntVar(0, horizon, f'start_b{batch}_s{stage}')
        end = model.NewIntVar(0, horizon, f'end_b{batch}_s{stage}')
        start_vars[(batch, stage)] = start
        end_vars[(batch, stage)] = end
        
        # Rajoite: end = start + duration
        model.Add(end == start + durations[(batch, stage)])

# Rajoite: Vaiheiden järjestys samassa erässä
for batch in batches:
    for i in range(len(stages) - 1):
        model.Add(start_vars[(batch, i+1)] >= end_vars[(batch, i)])

# Rajoite: Ei päällekkäisyyksiä samalla asemalla
for station in stations:
    intervals = []
    for (batch, stage) in tasks_on_station[station]:
        interval = model.NewIntervalVar(
            start_vars[(batch, stage)],
            durations[(batch, stage)],
            end_vars[(batch, stage)],
            f'interval_{batch}_{stage}'
        )
        intervals.append(interval)
    model.AddNoOverlap(intervals)

# Tavoite: Minimoi makespan
makespan = model.NewIntVar(0, horizon, 'makespan')
for batch in batches:
    model.Add(makespan >= end_vars[(batch, last_stage)])
    
model.Minimize(makespan)

solver = cp_model.CpSolver()
status = solver.Solve(model)
```

---

### 2. **Vehicle Routing Problem (VRP)**
**Optimoi nostimien reittejä!**

#### Mikä se on?
- Optimoidaan ajoneuvojen (tässä nostimien) reitit asiakkaiden (tässä asemien) välillä
- Huomioidaan kapasiteettirajoitukset, aikaikkunat, etäisyydet
- Tavoite: Minimoi kokonaismatka/aika tai ajoneuvomäärä

#### Miten se sopii tähän projektiin?
- **Vehicles** = Nostimet (Transporter 1, 2, 3)
- **Nodes** = Nosto- ja laskuasemat
- **Distance** = Fyysinen etäisyys (X-koordinaatti) tai siirtoaika
- **Time windows** = Käsittelyvaiheiden aikaikkunat (MinTime, MaxTime)
- **Capacity** = Nostimen toiminta-alue (Min_x_position, Max_x_Position)

#### OR-Tools toteutus: Routing
```python
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# Luo routing-malli
manager = pywrapcp.RoutingIndexManager(
    len(locations),  # Asemien määrä
    num_transporters,  # Nostimien määrä
    depot  # Alkupaikka
)

routing = pywrapcp.RoutingModel(manager)

# Etäisyysfunktio (X-koordinaattien erotus)
def distance_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return abs(stations[from_node]['X'] - stations[to_node]['X'])

transit_callback_index = routing.RegisterTransitCallback(distance_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

# Aikaikkunat
time_dimension = routing.AddDimension(
    transit_callback_index,
    slack_max=30,  # Maksimiodotusaika
    capacity=10000,  # Maksimiaika
    fix_start_cumul_to_zero=True,
    name='Time'
)

# Aseta aikaikkunat jokaiselle tehtävälle
time_dimension = routing.GetDimensionOrDie('Time')
for location_idx, time_window in enumerate(time_windows):
    index = manager.NodeToIndex(location_idx)
    time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

# Kapasiteettirajoitukset (nostimen toiminta-alue)
def demand_callback(from_index):
    from_node = manager.IndexToNode(from_index)
    return 1  # Jokainen tehtävä vie "yhden paikan"

demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0,  # Null capacity slack
    vehicle_capacities,  # Nostinkohtaiset kapasiteetit
    True,  # Start cumul to zero
    'Capacity'
)

# Ratkaise
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
)

solution = routing.SolveWithParameters(search_parameters)
```

---

### 3. **Assignment Problem**
**Tehtävien jako nostimille!**

#### Mikä se on?
- Yksinkertaisempi ongelma: Mitkä tehtävät kukin nostin hoitaa?
- Tavoite: Minimoi kokonaiskustannus tai maksimoi tasapaino

#### Miten se sopii tähän projektiin?
- **Workers** = Nostimet
- **Tasks** = Nostotehtävät (Batch, Stage)
- **Cost** = Siirtoaika tai etäisyys
- **Constraints** = Nostimen toiminta-alue, järjestyspakko

#### OR-Tools toteutus: Linear Assignment
```python
from ortools.linear_solver import pywraplp

solver = pywraplp.Solver.CreateSolver('SCIP')

# Muuttujat: x[t][h] = 1 jos tehtävä t annetaan nostimelle h
x = {}
for task in tasks:
    for hoist in hoists:
        x[(task, hoist)] = solver.BoolVar(f'x_t{task}_h{hoist}')

# Rajoite: Jokainen tehtävä täytyy antaa täsmälleen yhdelle nostimelle
for task in tasks:
    solver.Add(sum(x[(task, hoist)] for hoist in hoists) == 1)

# Rajoite: Nostimen kapasiteetti (toiminta-alue)
for task in tasks:
    for hoist in hoists:
        if not hoist_can_reach(hoist, task):
            solver.Add(x[(task, hoist)] == 0)

# Tavoite: Minimoi kokonaissiirtoaika
objective = solver.Objective()
for task in tasks:
    for hoist in hoists:
        cost = calculate_transfer_cost(task, hoist)
        objective.SetCoefficient(x[(task, hoist)], cost)
objective.SetMinimization()

status = solver.Solve()
```

---

## 🔥 Suositukset tähän projektiin

### **Parhaat lähestymistavat:**

#### 1. **Hybrid: CP-SAT + fysiikkamalli** (Suositus #1)
- Käytä CP-SAT:ia Job Shop -ongelmaan (makespan-optimointi)
- Lisää fyysiset rajoitteet (nopeus, kiihdytys) CP-SAT-rajoitteina
- Laske todelliset siirtoajat fysiikkamallilla, anna ne CP-SAT:lle syötteenä

**Edut:**
- Optimaalinen makespan
- Ei manuaalista konfliktien ratkaisua
- Skaalautuu hyvin (satoja tehtäviä)
- Tukee monimutkaisia rajoitteita

#### 2. **Routing + Assignment** (Suositus #2)
- Käytä Routing-mallia nostimien reittien optimointiin
- Käytä Assignment-mallia tehtävien jakoon nostimille
- Sovita yhteen kaksi ratkaisua

**Edut:**
- Hyvä nostimien kuormitustasapaino
- Minimoi tyhjäajot
- Helppo lisätä aikaikkunat

#### 3. **Pure CP-SAT with disjunctive constraints** (Suositus #3)
- Mallinna koko ongelma yhtenä CP-SAT-mallina
- Käytä `AddNoOverlap` -rajoitteita asemille ja nostimille
- Lisää precedence-rajoitteet vaiheiden järjestykselle

**Edut:**
- Yksinkertaisin koodi
- Tehokas globaali optimointi
- Helppo debugata

---

## 📊 Vertailu: Nykyinen vs. OR-Tools

| Ominaisuus | Nykyinen (Greedy + Stretch) | OR-Tools (CP-SAT) |
|------------|----------------------------|-------------------|
| **Makespan** | Ei optimaalinen | Optimaalinen |
| **Konfliktit** | Manuaalinen ratkaisu | Automaattinen |
| **Kuormitustasapaino** | Ei takuuta | Optimoitavissa |
| **Joustavuus** | Kiinteä algoritmi | Muokattavat rajoitteet |
| **Nopeus** | Nopea (O(n²)) | Hitaampi, mutta tehokas |
| **Skaalautuvuus** | Rajallinen | Hyvä (tuhannet muuttujat) |
| **Debugattavuus** | Helppo | Keskitaso |

---

## 🚀 Seuraavat askeleet

### Vaihe 1: Asenna OR-Tools
```bash
.venv/bin/pip install ortools
```

### Vaihe 2: Tee prototyyppi
1. Luo yksinkertainen Job Shop -malli (3 erää, 5 vaihetta)
2. Vertaa tuloksia nykyiseen
3. Mittaa suorituskyky

### Vaihe 3: Integroi fysiikkamalli
1. Laske siirtoajat `transporter_physics.py`:llä
2. Anna ne syötteenä CP-SAT:lle
3. Päivitä rajoitteet

### Vaihe 4: Laajenna
1. Lisää monimutkaisemmat rajoitteet (esim. vähimmäis-/maksimikäsittelyajat)
2. Optimoi useita tavoitteita (makespan + kuormitustasapaino)
3. Lisää real-time-optimointi (päivitä ratkaisu dynaamisesti)

---

## 📖 Hyödylliset resurssit

- **OR-Tools dokumentaatio**: https://developers.google.com/optimization
- **Job Shop Scheduling esimerkki**: https://developers.google.com/optimization/scheduling/job_shop
- **Vehicle Routing esimerkki**: https://developers.google.com/optimization/routing
- **CP-SAT Primer**: https://github.com/google/or-tools/blob/stable/ortools/sat/doc/README.md
- **Python API Reference**: https://google.github.io/or-tools/python/

---

## 💡 Yhteenveto

Google OR-Tools tarjoaa **teollisuustason optimointiratkaisun** tälle projektille. Parhaat hyödyt:

1. ✅ **Optimaalinen makespan** → Nopeampi tuotanto
2. ✅ **Automaattinen konfliktien ratkaisu** → Ei manuaalista venytyslaskentaa
3. ✅ **Kuormitustasapaino** → Nostimet hyödynnetään tasaisesti
4. ✅ **Joustavuus** → Helppo lisätä uusia rajoitteita
5. ✅ **Skaalautuvuus** → Toimii myös suurille tuotantomäärille

**Suositus**: Aloita CP-SAT Job Shop -mallilla ja integroi fysiikkamalli siirtoaikojen laskentaan.

---

## 🔧 Integrointi nykyiseen simulaatioputkeen

### Nykyinen putki (7 vaihetta):

```
VAIHE 1: Simulaatiokansion luonti
  ↓
VAIHE 2: Käsittelyohjelmien luonti (original_programs/)
  ↓
VAIHE 2.5: Kopioi original_programs → optimized_programs/
  ↓
VAIHE 3: Alkuperäisen matriisin luonti (line_matrix_original.csv)
  ↓
VAIHE 4: Alkuperäisen matriisin visualisointi
  ↓
VAIHE 5: Nostimien tehtävien käsittely ⚠️ TÄMÄ KORVATAAN CP-SAT:lla
  │  - generate_tasks() → transporter_tasks_raw.csv
  │  - order_tasks() → transporter_tasks_ordered.csv
  │  - resolve_station_conflicts() → transporter_tasks_resolved.csv
  │  - stretch_tasks() → transporter_tasks_stretched.csv
  ↓
VAIHE 6: Muokatun matriisin luonti (line_matrix_stretched.csv)
  ↓
VAIHE 6.1-6.5: Nostimien liikkeiden luonti
  ↓
VAIHE 7: Visualisointi ja raportit
```

### 🎯 CP-SAT:n paikka: **VAIHE 5 → VAIHE 5 CP-SAT**

**Perustelut:**

#### ✅ Miksi juuri VAIHE 5?

1. **Kaikki tarvittava data on jo olemassa:**
   - `line_matrix_original.csv` sisältää kaikki erät, vaiheet, asemat ja käsittelyajat
   - `production.csv` sisältää erien aloitusajat ja -asemat
   - `treatment_program_*.csv` sisältää vaiheiden minimi-/maksimiajat
   - `stations.csv` ja `transporters.csv` sisältävät fyysiset parametrit

2. **Nykyinen VAIHE 5 on täsmälleen Job Shop -ongelma:**
   - `generate_tasks()` → Luo tehtävät (CP-SAT tekee tämän implisiittisesti)
   - `order_tasks()` → Järjestää tehtävät (CP-SAT optimoi järjestyksen)
   - `resolve_station_conflicts()` → Ratkaisee päällekkäisyydet (CP-SAT: NoOverlap-rajoite)
   - `stretch_tasks()` → Venyttää konflikteja (CP-SAT: ei tarvetta, löytää optimaalisen)

3. **CP-SAT korvaa kaikki 4 alivaiheetta yhdellä optimoinnilla:**
   - Ei enää greedy-algoritmia → globaali optimointi
   - Ei manuaalista konfliktien ratkaisua → automaattinen
   - Ei venytyslaskentaa → optimaalinen aikataulu suoraan

4. **Lopputulos on sama muoto:**
   - CP-SAT tuottaa: `transporter_tasks_optimized.csv`
   - Sama rakenne kuin nykyinen `transporter_tasks_stretched.csv`
   - Vaiheet 6–7 toimivat täsmälleen samoin

#### 📋 Uusi VAIHE 5 CP-SAT:

```python
def test_step_5_cpsat(output_dir):
    """
    VAIHE 5 CP-SAT: Nostimien tehtävien optimointi
    """
    from datetime import datetime
    start = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{start}] VAIHE 5 CP-SAT - OPTIMOINTI - ALKAA")
    
    # 1. Lataa syötteet
    matrix = pd.read_csv(os.path.join(output_dir, "logs", "line_matrix_original.csv"))
    production = pd.read_csv(os.path.join(output_dir, "initialization", "production.csv"))
    stations = pd.read_csv(os.path.join(output_dir, "initialization", "stations.csv"))
    transporters = pd.read_csv(os.path.join(output_dir, "initialization", "transporters.csv"))
    
    # 2. Laske fyysiset siirtoajat (käytä olemassa olevaa transporter_physics.py)
    transfer_times = calculate_all_transfer_times(stations, transporters, matrix)
    
    # 3. Rakenna ja ratkaise CP-SAT Job Shop -malli
    from optimize_cpsat import optimize_transporter_schedule
    optimized_tasks = optimize_transporter_schedule(
        matrix=matrix,
        production=production,
        transfer_times=transfer_times,
        transporters=transporters
    )
    
    # 4. Tallenna optimoitu aikataulu
    output_path = os.path.join(output_dir, "logs", "transporter_tasks_optimized.csv")
    optimized_tasks.to_csv(output_path, index=False)
    
    end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"[{end}] VAIHE 5 CP-SAT - OPTIMOINTI - VALMIS")
    print(f"  → Optimoitu makespan: {optimized_tasks['Sink_time'].max()} s")
    
    return optimized_tasks
```

### 🔄 Integraatiostrategia (Asteittainen siirtymä):

#### **Vaihtoehto A: Rinnakkaiset versiot (Suositus kehitysvaiheessa)**

```python
# main.py
if USE_CPSAT_OPTIMIZATION:
    # VAIHE 5 CP-SAT: Optimointi
    test_step_5_cpsat(output_dir)
else:
    # VAIHE 5 (vanha): Greedy + stretch
    test_step_5(output_dir)
```

**Edut:**
- Helppo vertailla tuloksia
- Voi ajaa molemmat ja verrata makespan-arvoja
- Turvallinen siirtymä (vanha versio säilyy)

#### **Vaihtoehto B: Hybridi (Suositus tuotantoon)**

```python
# VAIHE 5: Nostimien tehtävien käsittely
test_step_5_cpsat(output_dir)  # CP-SAT-optimointi

# VAIHE 5.5: Post-processing (jos tarvitaan)
# Esim. lisää pienet viilaukset tai rajoitteet joita CP-SAT ei tue
refine_schedule(output_dir)
```

**Edut:**
- Paras molemmista maailmoista
- CP-SAT tekee raskaan optimoinnin
- Voi lisätä käsin erikoistapauksia

#### **Vaihtoehto C: Täysi korvaus**

```python
# VAIHE 5: Nostimien tehtävien optimointi (CP-SAT)
test_step_5_cpsat(output_dir)
# Vanha test_step_5() → poistetaan/arkistoidaan
```

**Edut:**
- Yksinkertaisin koodi
- Ei ylläpidettäviä rinnakkaisia versioita
- Paras suorituskyky

### 📊 Vertailu: Ennen vs. Jälkeen

| Vaihe | Nykyinen (Greedy) | CP-SAT | Muutos |
|-------|-------------------|--------|--------|
| **Syötteet** | line_matrix_original.csv | line_matrix_original.csv | Ei muutosta |
| **Prosessi** | 4 erillistä vaihetta (generate, order, resolve, stretch) | 1 optimointi | Yksinkertaisempi |
| **Tuloste** | transporter_tasks_stretched.csv | transporter_tasks_optimized.csv | Sama rakenne |
| **Vaiheet 6-7** | Toimii | Toimii | Ei muutosta |
| **Makespan** | Ei optimaalinen (~20-30% huonompi) | Optimaalinen | ✅ Parempi |
| **Ajoaika** | <1s | 1-10s (riippuu koosta) | Hitaampi, mutta OK |

### 🎯 Suositus:

**Aloita Vaihtoehdolla A (rinnakkaiset versiot):**

1. **Kehitä CP-SAT-moduuli:** `optimize_cpsat.py`
2. **Luo uusi funktio:** `test_step_5_cpsat(output_dir)`
3. **Lisää kytkin:** `USE_CPSAT_OPTIMIZATION = True/False` (config.py)
4. **Vertaile tuloksia:**
   - Aja molemmat versiot samalla datalla
   - Vertaa makespan-arvoja
   - Tarkista että lopputulos on sama muoto
5. **Kun CP-SAT on valmis → Vaihtoehto C (täysi korvaus)**

### 🛠️ Tiedostot joita tarvitaan:

```
simulation/
├── optimize_cpsat.py          # ⭐ UUSI: CP-SAT Job Shop -optimoija
├── test_step_5_cpsat.py       # ⭐ UUSI: VAIHE 5 CP-SAT wrapper
├── config.py                  # ⭐ PÄIVITÄ: Lisää USE_CPSAT_OPTIMIZATION
├── main.py                    # ⭐ PÄIVITÄ: Kutsu test_step_5_cpsat() jos enabled
├── test_step_5.py             # ⚠️ ARKISTO: Vanha versio (säilytä vertailua varten)
└── transporter_physics.py     # ✅ EI MUUTOSTA: Käytetään CP-SAT:n kanssa
```

---

**Yhteenveto:** CP-SAT korvaa täsmälleen VAIHE 5:n, koska se ratkaisee saman ongelman (nostimien tehtävien aikataulutus) optimaalisesti. Muut vaiheet 1-4 ja 6-7 pysyvät ennallaan.
