import os
import pandas as pd

def find_latest_logs_dir(output_root):
    subdirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
    subdirs = [d for d in subdirs if d.startswith('202')]
    if not subdirs:
        raise FileNotFoundError("Yhtään output-kansiota ei löytynyt.")
    latest = sorted(subdirs)[-1]
    return os.path.join(output_root, latest, "logs")

def analyze_discontinuity_context(output_root="output"):
    logs_dir = find_latest_logs_dir(output_root)
    movement_file = os.path.join(logs_dir, "transporters_movement.csv")
    df = pd.read_csv(movement_file)
    discontinuities = []
    for transporter_id in sorted(df['Transporter'].unique()):
        t_df = df[df['Transporter'] == transporter_id].sort_values(['Batch', 'Start_Time', 'Phase'])
        prev_phase = None
        prev_batch = None
        prev_idx = None
        for idx, row in t_df.iterrows():
            batch = row['Batch']
            phase = row['Phase']
            if prev_batch == batch:
                if not (phase == prev_phase + 1 or (prev_phase == 4 and phase == 0)):
                    discontinuities.append((prev_idx, idx))
            prev_phase = phase
            prev_batch = batch
            prev_idx = idx
    # Analysoi yhteisiä piirteitä
    print(f"Epäjatkuvuuksia löytyi: {len(discontinuities)}\n")
    for prev_idx, idx in discontinuities:
        prev_row = df.loc[prev_idx]
        row = df.loc[idx]
        print(f"---\nRivit: {prev_idx}, {idx}")
        print(f"Nostin: {row['Transporter']} | Batch: {row['Batch']} | Phase: {prev_row['Phase']}->{row['Phase']}")
        print(f"Edellinen kuvaus: {prev_row['Description']} | Seuraava kuvaus: {row['Description']}")
        print(f"Edellinen End_Time: {prev_row['End_Time']} | Seuraava Start_Time: {row['Start_Time']}")
        print(f"From_Station: {prev_row['From_Station']}->{row['From_Station']} | To_Station: {prev_row['To_Station']}->{row['To_Station']}")
        print(f"Onko nostimen eka rivi: {prev_idx == df[df['Transporter'] == row['Transporter']].index[0]}")
        print(f"Onko nostimen vika rivi: {idx == df[df['Transporter'] == row['Transporter']].index[-1]}")
        print(f"Onko batchin eka rivi: {prev_idx == df[(df['Transporter'] == row['Transporter']) & (df['Batch'] == row['Batch'])].index[0]}")
        print(f"Onko batchin vika rivi: {idx == df[(df['Transporter'] == row['Transporter']) & (df['Batch'] == row['Batch'])].index[-1]}")
        print(f"---\n")

if __name__ == "__main__":
    analyze_discontinuity_context()
