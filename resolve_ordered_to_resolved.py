import pandas as pd
import os

def stretch_resolved_tasks(resolved_df):
    """
    Venyttää tehtävälistaa niin, että peräkkäisten tehtävien välillä on vähintään Phase_1:n verran väliä.
    Jos väli ei riitä, siirretään seuraavan erän tehtäviä eteenpäin.
    Kaikki vaihe (Phase_1...Phase_4) -sarakkeet kopioidaan sellaisenaan _stretched-tiedostoon.
    """
    df = resolved_df.copy()
    n = len(df)
    for i in range(1, n):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        required_gap = curr['Phase_1']
        actual_gap = curr['Lift_time'] - prev['Sink_time']
        if actual_gap < required_gap:
            shift = required_gap - actual_gap
            batch = curr['Batch']
            mask = (df.index >= i) & (df['Batch'] == batch)
            df.loc[mask, 'Lift_time'] += shift
            df.loc[mask, 'Sink_time'] += shift
    return df

def resolve_ordered_to_resolved(output_dir):
    logs_dir = os.path.join(output_dir, "Logs")
    ordered_file = os.path.join(logs_dir, "transporter_tasks_ordered.csv")
    resolved_file = os.path.join(logs_dir, "transporter_tasks_resolved.csv")
    df = pd.read_csv(ordered_file)
    if 'Parallel_group' not in df.columns:
        df['Parallel_group'] = 0
    changed = True
    while changed:
        changed = False
        for i in range(len(df)-1):
            curr = df.iloc[i]
            next_ = df.iloc[i+1]
            if (curr['Transporter_id'] == next_['Transporter_id'] and
                curr['Sink_stat'] == next_['Lift_stat'] and
                curr['Parallel_group'] == 0 and next_['Parallel_group'] == 0):
                # Vaihda järjestys
                df.iloc[i], df.iloc[i+1] = next_, curr
                changed = True
    df.to_csv(resolved_file, index=False)
    return resolved_file

def main(input_file, output_file):
    df = pd.read_csv(input_file)
    # Kaikki vaihe-sarakkeet (Phase_1...Phase_4) kopioidaan sellaisenaan
    df_stretched = stretch_resolved_tasks(df)
    df_stretched.to_csv(output_file, index=False, float_format='%.2f')

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Käyttö: python resolve_ordered_to_resolved.py input.csv output.csv")
    else:
        main(sys.argv[1], sys.argv[2])

