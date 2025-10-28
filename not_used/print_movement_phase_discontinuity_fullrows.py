import os
import pandas as pd

def find_latest_logs_dir(output_root):
    subdirs = [d for d in os.listdir(output_root) if os.path.isdir(os.path.join(output_root, d))]
    subdirs = [d for d in subdirs if d.startswith('202')]
    if not subdirs:
        raise FileNotFoundError("Yhtään output-kansiota ei löytynyt.")
    latest = sorted(subdirs)[-1]
    return os.path.join(output_root, latest, "logs")

def print_phase_discontinuity_fullrows(output_root="output"):
    logs_dir = find_latest_logs_dir(output_root)
    movement_file = os.path.join(logs_dir, "transporters_movement.csv")
    df = pd.read_csv(movement_file)
    error_rows = set()
    for transporter_id in sorted(df['Transporter'].unique()):
        t_df = df[df['Transporter'] == transporter_id].sort_values(['Start_Time', 'Phase'])
        prev_phase = None
        prev_idx = None
        prev_end = None
        for idx, row in t_df.iterrows():
            phase = row['Phase']
            start = row['Start_Time']
            end = row['End_Time']
            description = row['Description'] if 'Description' in row else ''
            prev_description = df.loc[prev_idx]['Description'] if prev_idx is not None and 'Description' in df.columns else ''
            if prev_idx is not None:
                # Suodata pois simuloinnin lopun keinotekoiset epäjatkuvuudet ja siirrot alkupaikkaan
                if (
                    description == 'Odotus simuloinnin lopussa'
                    or prev_description == 'Odotus simuloinnin lopussa'
                    or 'alkupaikkaan' in str(description).lower()
                    or 'alkupaikkaan' in str(prev_description).lower()
                ):
                    pass
                else:
                    # Ajallinen epäloogisuus: start < prev_end
                    if start < prev_end:
                        error_rows.add(tuple(df.loc[prev_idx].values))
                        error_rows.add(tuple(df.loc[idx].values))
                    # Vaiheiden epäloogisuus: sallitaan vain 4->0 ja nouseva järjestys
                    elif not (phase == prev_phase + 1 or (prev_phase == 4 and phase == 0)):
                        error_rows.add(tuple(df.loc[prev_idx].values))
                        error_rows.add(tuple(df.loc[idx].values))
            # Yksittäisen rivin sisäinen aikavirhe
            if start > end:
                error_rows.add(tuple(df.loc[idx].values))
            prev_phase = phase
            prev_idx = idx
            prev_end = end
    # Tulosta vain uniikit virherivit
    for row in error_rows:
        print(','.join(str(x) for x in row))

if __name__ == "__main__":
    print_phase_discontinuity_fullrows()
