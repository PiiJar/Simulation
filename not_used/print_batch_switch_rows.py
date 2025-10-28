import os
import pandas as pd

def find_latest_logs_dir(output_root):
    subdirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
    subdirs = [d for d in subdirs if d.startswith('202')]
    if not subdirs:
        raise FileNotFoundError("Yhtään output-kansiota ei löytynyt.")
    latest = sorted(subdirs)[-1]
    return os.path.join(output_root, latest, "logs")

def print_batch_switch_rows(output_root="output"):
    logs_dir = find_latest_logs_dir(output_root)
    movement_file = os.path.join(logs_dir, "transporters_movement.csv")
    df = pd.read_csv(movement_file)
    for transporter_id in sorted(df['Transporter'].unique()):
        t_df = df[df['Transporter'] == transporter_id].sort_values(['Start_Time', 'Phase'])
        prev_batch = None
        prev_idx = None
        for idx, row in t_df.iterrows():
            batch = row['Batch']
            if prev_batch is not None and batch != prev_batch:
                print(','.join(str(x) for x in df.loc[prev_idx].values))
                print(','.join(str(x) for x in df.loc[idx].values))
            prev_batch = batch
            prev_idx = idx

if __name__ == "__main__":
    print_batch_switch_rows()
