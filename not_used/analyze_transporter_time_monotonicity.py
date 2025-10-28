import os
import pandas as pd

def find_latest_logs_dir(output_root):
    # Etsi uusin output-kansio
    subdirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
    subdirs = [d for d in subdirs if d.startswith('202')]
    if not subdirs:
        raise FileNotFoundError("Yhtään output-kansiota ei löytynyt.")
    latest = sorted(subdirs)[-1]
    return os.path.join(output_root, latest, "logs")

def analyze_monotonicity(output_root="output"):
    logs_dir = find_latest_logs_dir(output_root)
    movement_file = os.path.join(logs_dir, "transporters_movement.csv")
    if not os.path.exists(movement_file):
        print(f"Tiedostoa ei löydy: {movement_file}")
        return
    df = pd.read_csv(movement_file)
    print(f"Analysoidaan: {movement_file}\n")
    errors = []
    for transporter_id in sorted(df['Transporter'].unique()):
        t_df = df[df['Transporter'] == transporter_id].sort_values('Start_Time')
        prev_end = None
        for idx, row in t_df.iterrows():
            start = row['Start_Time']
            end = row['End_Time']
            if prev_end is not None and start < prev_end:
                errors.append({
                    'Transporter': transporter_id,
                    'Movement_ID': row.get('Movement_ID', idx+1),
                    'Prev_End': prev_end,
                    'Start': start,
                    'Batch': row.get('Batch', ''),
                    'Phase': row.get('Phase', ''),
                    'From_Station': row.get('From_Station', ''),
                    'To_Station': row.get('To_Station', ''),
                    'RowIdx': idx
                })
            prev_end = end

    # Lue nostintehtävät (stretched)
    tasks_file = os.path.join(logs_dir, "transporter_tasks_stretched.csv")
    if os.path.exists(tasks_file):
        tasks_df = pd.read_csv(tasks_file)
    else:
        tasks_df = None

    if errors:
        print("LÖYTYI AJASSA TAAKSEPÄIN SIIRTYMIÄ (max 5):")
        for err in errors[:5]:
            print(f"Nostin {err['Transporter']} | Movement_ID {err['Movement_ID']} | Batch {err['Batch']} | Phase {err['Phase']} | {err['From_Station']}->{err['To_Station']} | Edellinen loppu: {err['Prev_End']} | Seuraava alku: {err['Start']}")
            # Etsi liittyvä nostintehtävä
            if tasks_df is not None:
                # Yritetään täsmätä Transporter_id, Batch, mahdollisesti Stage
                match = tasks_df[(tasks_df['Transporter_id'] == err['Transporter']) & (tasks_df['Batch'] == err['Batch'])]
                if not match.empty:
                    # Jos movementin Phase on 1/2/3/4, yritetään täsmätä Stage
                    if 'Phase' in err and str(err['Phase']).isdigit():
                        # Stage = Phase movementissa, mutta voi olla eri numerointi, joten näytetään kaikki batchin tehtävät
                        print("  Liittyvät nostintehtävät (batch):")
                        print(match.to_string(index=False, max_rows=5))
                    else:
                        print("  Liittyvä nostintehtävä:")
                        print(match.head(1).to_string(index=False))
                else:
                    print("  Ei löytynyt täsmäävää nostintehtävää batchille.")
    else:
        print("Ei ajassa taaksepäin siirtymiä.")

if __name__ == "__main__":
    analyze_monotonicity()
