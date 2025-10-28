import pandas as pd
import os

# Muokkaa polku tähän sopivaksi
def analyze_transporter_overlap(matrix_path):
    df = pd.read_csv(matrix_path)
    # Käydään kaikki asemat läpi, järjestetään EntryTime:n mukaan
    df2 = df.sort_values(["Station", "EntryTime"])
    prev_exit = None
    prev_row = None
    prev_station = None
    found = False
    for idx, row in df2.iterrows():
        station = row["Station"]
        entry = row["EntryTime"]
        exit = row["ExitTime"]
        if prev_station == station:
            if entry < prev_exit - 1e-6:
                print("Aikaparadoksi havaittu asemalla", station)
                print("Edellinen:", prev_row.to_dict())
                print("Nykyinen :", row.to_dict())
                print()
                found = True
                break  # Raportoi vain ensimmäinen tapaus
        prev_exit = exit
        prev_row = row
        prev_station = station
    if not found:
        print("Ei aikaparadokseja yhdelläkään asemalla.")

if __name__ == "__main__":
    # Oletetaan, että output-kansio on nykyisessä hakemistossa ja käytetään uusinta snapshotia
    logs_dir = os.path.join("output")
    # Etsi viimeisin snapshot
    if not os.path.exists(logs_dir):
        print("output-kansiota ei löydy")
        exit(1)
    subdirs = [d for d in os.listdir(logs_dir) if os.path.isdir(os.path.join(logs_dir, d))]
    if not subdirs:
        print("output-kansiosta ei löydy snapshot-kansioita")
        exit(1)
    latest = sorted(subdirs)[-1]
    matrix_path = os.path.join(logs_dir, latest, "logs", "line_matrix_stretched.csv")
    if not os.path.exists(matrix_path):
        print(f"Tiedostoa {matrix_path} ei löydy")
        exit(1)
    print(f"Analysoidaan {matrix_path}\n")
    analyze_transporter_overlap(matrix_path)
