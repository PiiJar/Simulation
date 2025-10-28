import pandas as pd
import os

def compare_matrix_and_optimized(matrix_path, optimized_path, output_path=None):
    # Lue tiedostot
    df_matrix = pd.read_csv(matrix_path)
    df_opt = pd.read_csv(optimized_path)

    # Valitse olennaiset sarakkeet
    matrix_cols = ['Batch', 'Stage', 'EntryTime', 'ExitTime']
    opt_cols = ['Batch', 'Stage', 'Lift_time', 'Sink_time']

    # Yhdistä batch+stage-avaimella
    merged = pd.merge(
        df_matrix[matrix_cols],
        df_opt[opt_cols],
        on=['Batch', 'Stage'],
        how='outer',
        suffixes=('_matrix', '_opt')
    )

    # Erot
    merged['Entry_diff'] = merged['EntryTime'] - merged['Lift_time']
    merged['Exit_diff'] = merged['ExitTime'] - merged['Sink_time']

    # Tallenna taulukko
    if output_path:
        merged.to_csv(output_path, index=False)
        print(f"Tallennettu: {output_path}")
    else:
        print(merged)

if __name__ == "__main__":
    output_dir = "output/2025-10-25_08-46-50/logs"
    matrix = os.path.join(output_dir, "line_matrix_stretched.csv")
    opt = os.path.join(output_dir, "transporter_tasks_optimized.csv")
    out = os.path.join(output_dir, "matrix_vs_optimized.csv")
    compare_matrix_and_optimized(matrix, opt, out)
