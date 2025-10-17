"""
optimize_makespan.py
-------------------
Minimoi tuotantolinjan kokonaisläpimenoaika (makespan) PuLP-kirjastolla.
Lue snapshotista tehtävälista, rakenna optimointimalli ja tallenna uusi aikataulu.
"""
import os
import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, value

# Parametrit
INPUT_FILENAME = "generate_tasks.csv"  # Muokkaa tarvittaessa
OUTPUT_FILENAME = "optimized_schedule.csv"

def optimize_makespan(input_path, output_path):
    print(f"Ladataan tehtävät: {input_path}")
    df = pd.read_csv(input_path)

    # Oletetaan sarakkeet: TaskID, Station, Duration, Batch, Predecessor (tai vastaavat)
    tasks = df['TaskID'].tolist()
    durations = dict(zip(df['TaskID'], df['Duration']))
    stations = dict(zip(df['TaskID'], df['Station']))
    batches = dict(zip(df['TaskID'], df['Batch']))
    # Predecessor: edeltävä tehtävä (None jos ensimmäinen)
    predecessors = dict(zip(df['TaskID'], df.get('Predecessor', [None]*len(df))))

    # Optimointimalli
    prob = LpProblem("MinimizeMakespan", LpMinimize)

    # Muuttujat: aloitusajat
    start = {t: LpVariable(f"start_{t}", lowBound=0) for t in tasks}
    # Kokonaisläpimenoaika
    makespan = LpVariable("makespan", lowBound=0)

    # Tavoite: minimoi makespan
    prob += makespan

    # Jokainen tehtävä päättyy ennen makespania
    for t in tasks:
        prob += start[t] + durations[t] <= makespan

    # Edeltävyysrajoitteet (jos Predecessor-sarake on käytössä)
    for t in tasks:
        pred = predecessors[t]
        if pd.notna(pred):
            prob += start[t] >= start[pred] + durations[pred]

    # Aseman kapasiteettirajoite: ei päällekkäisiä tehtäviä
    for s in set(stations.values()):
        ts = [t for t in tasks if stations[t] == s]
        for i in range(len(ts)):
            for j in range(i+1, len(ts)):
                t1, t2 = ts[i], ts[j]
                # Ei päällekkäisyyttä: t1 ennen t2 TAI t2 ennen t1
                y = LpVariable(f"order_{t1}_{t2}", cat='Binary')
                prob += start[t1] + durations[t1] <= start[t2] + (1-y)*1e6
                prob += start[t2] + durations[t2] <= start[t1] + y*1e6

    print("Ratkaistaan optimointimalli...")
    prob.solve()
    print(f"Tila: {LpStatus[prob.status]}")
    print(f"Optimaalinen makespan: {value(makespan)}")

    # Tallennetaan uusi aikataulu
    df['OptimizedStart'] = [value(start[t]) for t in tasks]
    df['OptimizedEnd'] = [value(start[t]) + durations[t] for t in tasks]
    df.to_csv(output_path, index=False)
    print(f"Tallennettu: {output_path}")

def find_latest_logs_dir(base_dir="output"):
    # Etsitään viimeisin simulaation Logs-hakemisto (output/YYYY-MM-DD_HH-MM/Logs)
    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"{base_dir} ei löydy")
    subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    # Etsitään kansiot, jotka noudattavat aikaleimaformaattia
    subdirs = sorted([d for d in subdirs if len(d) >= 16 and d[4] == '-' and d[7] == '-' and d[10] == '_' and d[13] == '-'], reverse=True)
    for d in subdirs:
        logs_dir = os.path.join(base_dir, d, "Logs")
        if os.path.isdir(logs_dir):
            return logs_dir
    raise FileNotFoundError("Yhtään Logs-hakemistoa ei löytynyt output-kansiosta.")

if __name__ == "__main__":
    output_dir = os.path.join("output", "optimized")
    os.makedirs(output_dir, exist_ok=True)
    try:
        logs_dir = find_latest_logs_dir()
        input_path = os.path.join(logs_dir, INPUT_FILENAME)
        print(f"Käytetään syötteenä: {input_path}")
    except Exception as e:
        print(f"Virhe Logs-hakemiston etsimisessä: {e}")
        exit(1)
    output_path = os.path.join(output_dir, OUTPUT_FILENAME)
    optimize_makespan(input_path, output_path)
